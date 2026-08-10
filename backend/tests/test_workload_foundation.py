from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workload import WorkloadStatus, WorkloadType
from app.services.workloads import (
    enqueue_workload,
    fail_workload,
    lease_next_workload,
    mark_running,
    redact_diagnostics,
    succeed_workload,
)

TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")


@pytest.mark.asyncio
async def test_duplicate_delivery_returns_one_governed_workload(
    db_session: AsyncSession,
) -> None:
    first, created = await enqueue_workload(
        db_session,
        tenant_id=TENANT_ID,
        workload_type=WorkloadType.CALCULATION,
        idempotency_key="inventory:one:calculation:v1",
        requested_by="tester@example.com",
        payload={"inventory_id": "one", "access_token": "do-not-store"},
    )
    duplicate, duplicate_created = await enqueue_workload(
        db_session,
        tenant_id=TENANT_ID,
        workload_type=WorkloadType.CALCULATION,
        idempotency_key="inventory:one:calculation:v1",
        requested_by="tester@example.com",
        payload={"inventory_id": "one"},
    )

    assert created is True
    assert duplicate_created is False
    assert duplicate.id == first.id
    assert first.payload_json["access_token"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_worker_lease_retry_and_success(db_session: AsyncSession) -> None:
    workload, _ = await enqueue_workload(
        db_session,
        tenant_id=TENANT_ID,
        workload_type=WorkloadType.REPORT_EXPORT,
        idempotency_key="report:one:pdf:v1",
        requested_by="tester@example.com",
        payload={"report_id": "one"},
        max_attempts=2,
    )
    leased = await lease_next_workload(db_session, worker_id="worker-a")
    assert leased is not None
    assert leased.id == workload.id
    assert leased.status == WorkloadStatus.LEASED
    assert leased.attempts == 1

    await mark_running(db_session, leased, worker_id="worker-a")
    await fail_workload(
        db_session,
        leased,
        worker_id="worker-a",
        error_code="temporary",
        error_message="Temporary protected dependency failure.",
        retryable=True,
        retry_delay_seconds=0,
    )
    assert leased.status == WorkloadStatus.QUEUED

    retried = await lease_next_workload(db_session, worker_id="worker-b")
    assert retried is not None
    await mark_running(db_session, retried, worker_id="worker-b")
    await succeed_workload(
        db_session,
        retried,
        worker_id="worker-b",
        result={"report_id": "one"},
    )
    assert retried.status == WorkloadStatus.SUCCEEDED
    assert retried.result_json == {"report_id": "one"}


def test_nested_diagnostics_are_redacted() -> None:
    assert redact_diagnostics(
        {"safe": 1, "nested": [{"Authorization": "Bearer secret"}]}
    ) == {"safe": 1, "nested": [{"Authorization": "[REDACTED]"}]}
