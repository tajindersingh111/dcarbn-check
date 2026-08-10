from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workload import DurableWorkload, WorkloadStatus, WorkloadType

_REDACTED = "[REDACTED]"
_SENSITIVE_KEYS = ("authorization", "password", "secret", "token", "credential", "api_key")


def _now() -> datetime:
    return datetime.now(UTC)


def redact_diagnostics(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): (
                _REDACTED
                if any(part in str(key).casefold() for part in _SENSITIVE_KEYS)
                else redact_diagnostics(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_diagnostics(item) for item in value]
    if isinstance(value, tuple):
        return [redact_diagnostics(item) for item in value]
    return value


async def enqueue_workload(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    workload_type: WorkloadType,
    idempotency_key: str,
    requested_by: str,
    payload: dict[str, Any],
    organisation_id: UUID | None = None,
    inventory_id: UUID | None = None,
    priority: int = 0,
    max_attempts: int = 3,
    scheduled_at: datetime | None = None,
) -> tuple[DurableWorkload, bool]:
    existing = await db.scalar(
        select(DurableWorkload).where(
            DurableWorkload.tenant_id == tenant_id,
            DurableWorkload.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return existing, False

    workload = DurableWorkload(
        tenant_id=tenant_id,
        organisation_id=organisation_id,
        inventory_id=inventory_id,
        workload_type=workload_type,
        idempotency_key=idempotency_key,
        requested_by=requested_by,
        payload_json=redact_diagnostics(payload),
        priority=priority,
        max_attempts=max_attempts,
        scheduled_at=scheduled_at or _now(),
    )
    db.add(workload)
    await db.commit()
    await db.refresh(workload)
    return workload, True


async def recover_expired_leases(db: AsyncSession, *, now: datetime | None = None) -> int:
    current = now or _now()
    rows = list(
        (
            await db.scalars(
                select(DurableWorkload).where(
                    DurableWorkload.status.in_(
                        (WorkloadStatus.LEASED, WorkloadStatus.RUNNING)
                    ),
                    DurableWorkload.lease_expires_at < current,
                )
            )
        ).all()
    )
    for workload in rows:
        workload.lease_owner = None
        workload.lease_expires_at = None
        workload.heartbeat_at = None
        if workload.attempts >= workload.max_attempts:
            workload.status = WorkloadStatus.DEAD_LETTERED
            workload.completed_at = current
            workload.error_code = "lease_expired"
        else:
            workload.status = WorkloadStatus.QUEUED
            workload.scheduled_at = current
    await db.commit()
    return len(rows)


async def lease_next_workload(
    db: AsyncSession,
    *,
    worker_id: str,
    lease_seconds: int = 60,
    per_tenant_limit: int = 2,
    now: datetime | None = None,
) -> DurableWorkload | None:
    current = now or _now()
    await recover_expired_leases(db, now=current)
    candidates = list(
        (
            await db.scalars(
                select(DurableWorkload)
                .where(
                    DurableWorkload.status == WorkloadStatus.QUEUED,
                    DurableWorkload.scheduled_at <= current,
                )
                .order_by(
                    DurableWorkload.priority.desc(),
                    DurableWorkload.created_at.asc(),
                )
                .limit(100)
                .with_for_update(skip_locked=True)
            )
        ).all()
    )
    for workload in candidates:
        active = await db.scalar(
            select(func.count(DurableWorkload.id)).where(
                DurableWorkload.tenant_id == workload.tenant_id,
                DurableWorkload.status.in_(
                    (WorkloadStatus.LEASED, WorkloadStatus.RUNNING)
                ),
                or_(
                    DurableWorkload.lease_expires_at.is_(None),
                    DurableWorkload.lease_expires_at >= current,
                ),
            )
        )
        if int(active or 0) >= per_tenant_limit:
            continue
        workload.status = WorkloadStatus.LEASED
        workload.lease_owner = worker_id
        workload.lease_expires_at = current + timedelta(seconds=lease_seconds)
        workload.heartbeat_at = current
        workload.attempts += 1
        await db.commit()
        await db.refresh(workload)
        return workload
    return None


def _assert_lease(workload: DurableWorkload, worker_id: str) -> None:
    if workload.lease_owner != worker_id:
        raise ValueError("Workload is not leased by this worker.")
    if workload.status not in (WorkloadStatus.LEASED, WorkloadStatus.RUNNING):
        raise ValueError("Workload is not executable.")


async def mark_running(
    db: AsyncSession,
    workload: DurableWorkload,
    *,
    worker_id: str,
) -> DurableWorkload:
    _assert_lease(workload, worker_id)
    workload.status = WorkloadStatus.RUNNING
    workload.started_at = workload.started_at or _now()
    await db.commit()
    await db.refresh(workload)
    return workload


async def heartbeat(
    db: AsyncSession,
    workload: DurableWorkload,
    *,
    worker_id: str,
    lease_seconds: int = 60,
    progress_current: int | None = None,
    progress_total: int | None = None,
) -> None:
    _assert_lease(workload, worker_id)
    current = _now()
    workload.heartbeat_at = current
    workload.lease_expires_at = current + timedelta(seconds=lease_seconds)
    if progress_current is not None:
        workload.progress_current = progress_current
    if progress_total is not None:
        workload.progress_total = progress_total
    await db.commit()


async def succeed_workload(
    db: AsyncSession,
    workload: DurableWorkload,
    *,
    worker_id: str,
    result: dict[str, Any],
) -> None:
    _assert_lease(workload, worker_id)
    workload.status = WorkloadStatus.SUCCEEDED
    workload.result_json = redact_diagnostics(result)
    workload.completed_at = _now()
    workload.lease_owner = None
    workload.lease_expires_at = None
    await db.commit()


async def fail_workload(
    db: AsyncSession,
    workload: DurableWorkload,
    *,
    worker_id: str,
    error_code: str,
    error_message: str,
    retryable: bool,
    diagnostics: dict[str, Any] | None = None,
    retry_delay_seconds: int = 30,
) -> None:
    _assert_lease(workload, worker_id)
    current = _now()
    workload.error_code = error_code[:100]
    workload.error_message = error_message[:2000]
    workload.diagnostics_json = redact_diagnostics(diagnostics or {})
    workload.lease_owner = None
    workload.lease_expires_at = None
    if retryable and workload.attempts < workload.max_attempts:
        workload.status = WorkloadStatus.QUEUED
        workload.scheduled_at = current + timedelta(seconds=retry_delay_seconds)
    else:
        workload.status = (
            WorkloadStatus.FAILED
            if not retryable
            else WorkloadStatus.DEAD_LETTERED
        )
        workload.completed_at = current
    await db.commit()


async def cancel_workload(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    workload_id: UUID,
    cancelled_by: str,
) -> bool:
    workload = await db.scalar(
        select(DurableWorkload).where(
            DurableWorkload.id == workload_id,
            DurableWorkload.tenant_id == tenant_id,
        )
    )
    if workload is None:
        return False
    if workload.status in (
        WorkloadStatus.SUCCEEDED,
        WorkloadStatus.CANCELLED,
        WorkloadStatus.DEAD_LETTERED,
    ):
        return False
    workload.status = WorkloadStatus.CANCELLED
    workload.cancelled_by = cancelled_by
    workload.completed_at = _now()
    workload.lease_owner = None
    workload.lease_expires_at = None
    await db.commit()
    return True
