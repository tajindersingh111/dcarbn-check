from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal, require_roles
from app.models.tenant import Tenant
from app.models.workload import DurableWorkload, WorkloadStatus, WorkloadType
from app.services.workloads import (
    heartbeat,
    lease_next_workload,
    list_workloads,
    recover_expired_leases,
)

TENANT_A = UUID("11111111-1111-1111-1111-111111111111")
TENANT_B = UUID("22222222-2222-2222-2222-222222222222")


def _principal(tenant_id: UUID, *roles: str) -> CurrentPrincipal:
    return CurrentPrincipal(
        subject="user@example.com",
        tenant_id=tenant_id,
        roles=frozenset(roles),
    )


def _workload(tenant_id: UUID, key: str) -> DurableWorkload:
    return DurableWorkload(
        tenant_id=tenant_id,
        workload_type=WorkloadType.CALCULATION,
        idempotency_key=key,
        requested_by="tester@example.com",
        payload_json={"operation": "test"},
        scheduled_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_workload_listing_is_tenant_scoped_and_paginated(
    db_session: AsyncSession,
) -> None:
    db_session.add(
        Tenant(
            id=TENANT_B,
            name="Adversarial Tenant",
            slug="adversarial-tenant",
            is_active=True,
        )
    )
    own_first = _workload(TENANT_A, "own-first")
    own_second = _workload(TENANT_A, "own-second")
    foreign = _workload(TENANT_B, "foreign")
    db_session.add_all([own_first, own_second, foreign])
    await db_session.commit()

    first_page, cursor = await list_workloads(
        db_session,
        tenant_id=TENANT_A,
        limit=1,
    )
    assert len(first_page) == 1
    assert cursor is not None
    assert first_page[0].tenant_id == TENANT_A

    second_page, _ = await list_workloads(
        db_session,
        tenant_id=TENANT_A,
        limit=1,
        cursor=cursor,
    )
    assert len(second_page) == 1
    assert second_page[0].tenant_id == TENANT_A
    assert second_page[0].id != first_page[0].id


@pytest.mark.asyncio
async def test_workload_role_policy_rejects_viewer() -> None:
    reader = require_roles(
        "tenant_admin",
        "sustainability_manager",
        "data_reviewer",
    )
    writer = require_roles("tenant_admin", "sustainability_manager")

    accepted = await reader(_principal(TENANT_A, "data_reviewer"))
    assert accepted.tenant_id == TENANT_A
    with pytest.raises(HTTPException) as exc:
        await writer(_principal(TENANT_A, "viewer"))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_per_tenant_concurrency_limit_prevents_noisy_neighbour(
    db_session: AsyncSession,
) -> None:
    db_session.add(
        Tenant(
            id=TENANT_B,
            name="Second Tenant",
            slug="second-tenant",
            is_active=True,
        )
    )
    db_session.add_all(
        [
            _workload(TENANT_A, "tenant-a-1"),
            _workload(TENANT_A, "tenant-a-2"),
            _workload(TENANT_B, "tenant-b-1"),
        ]
    )
    await db_session.commit()

    first = await lease_next_workload(
        db_session,
        worker_id="worker-1",
        per_tenant_limit=1,
    )
    second = await lease_next_workload(
        db_session,
        worker_id="worker-2",
        per_tenant_limit=1,
    )

    assert first is not None and first.tenant_id == TENANT_A
    assert second is not None and second.tenant_id == TENANT_B


@pytest.mark.asyncio
async def test_lease_recovery_does_not_mutate_a_disallowed_tenant(
    db_session: AsyncSession,
) -> None:
    db_session.add(
        Tenant(
            id=TENANT_B,
            name="Approved Recovery Tenant",
            slug="approved-recovery-tenant",
            is_active=True,
        )
    )
    expired_at = datetime.now(UTC) - timedelta(minutes=1)
    disallowed = _workload(TENANT_A, "outside-recovery-scope")
    allowed = _workload(TENANT_B, "inside-recovery-scope")
    for item in (disallowed, allowed):
        item.status = WorkloadStatus.LEASED
        item.lease_owner = "expired-worker"
        item.lease_expires_at = expired_at
        item.attempts = 1
    db_session.add_all([disallowed, allowed])
    await db_session.commit()

    recovered = await recover_expired_leases(
        db_session,
        allowed_tenant_ids=(TENANT_B,),
        allowed_workload_types=(WorkloadType.CALCULATION,),
        now=datetime.now(UTC),
    )

    assert recovered == 1
    await db_session.refresh(disallowed)
    await db_session.refresh(allowed)
    assert disallowed.status == WorkloadStatus.LEASED
    assert disallowed.lease_owner == "expired-worker"
    assert allowed.status == WorkloadStatus.QUEUED
    assert allowed.lease_owner is None


@pytest.mark.asyncio
async def test_worker_leases_only_from_approved_rollout_scope(
    db_session: AsyncSession,
) -> None:
    db_session.add(
        Tenant(
            id=TENANT_B,
            name="Approved Pilot Tenant",
            slug="approved-pilot-tenant",
            is_active=True,
        )
    )
    disallowed = _workload(TENANT_A, "outside-pilot")
    allowed = _workload(TENANT_B, "inside-pilot")
    db_session.add_all([disallowed, allowed])
    await db_session.commit()

    leased = await lease_next_workload(
        db_session,
        worker_id="pilot-worker",
        allowed_tenant_ids=(TENANT_B,),
        allowed_workload_types=(WorkloadType.CALCULATION,),
    )

    assert leased is not None
    assert leased.id == allowed.id
    assert leased.tenant_id == TENANT_B
    await db_session.refresh(disallowed)
    assert disallowed.status == WorkloadStatus.QUEUED

    nothing = await lease_next_workload(
        db_session,
        worker_id="disabled-worker",
        allowed_tenant_ids=(),
        allowed_workload_types=(),
    )
    assert nothing is None


@pytest.mark.asyncio
async def test_stale_worker_cannot_extend_reassigned_lease(
    db_session: AsyncSession,
) -> None:
    workload = _workload(TENANT_A, "stale-lease")
    db_session.add(workload)
    await db_session.commit()
    leased = await lease_next_workload(
        db_session,
        worker_id="worker-old",
        lease_seconds=60,
    )
    assert leased is not None

    await db_session.execute(
        update(DurableWorkload)
        .where(DurableWorkload.id == leased.id)
        .values(
            lease_owner="worker-new",
            lease_expires_at=datetime.now(UTC) + timedelta(seconds=60),
        )
        .execution_options(synchronize_session=False)
    )
    await db_session.commit()

    with pytest.raises(ValueError, match="not leased"):
        await heartbeat(db_session, leased, worker_id="worker-old")
