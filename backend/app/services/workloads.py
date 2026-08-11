from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.pagination import CursorPosition
from app.core.observability import (
    WORKLOAD_DURATION,
    WORKLOAD_OLDEST_QUEUED_AGE,
    WORKLOAD_QUEUE_DEPTH,
    WORKLOAD_TRANSITIONS,
)
from app.models.workload import DurableWorkload, WorkloadStatus, WorkloadType

_REDACTED = "[REDACTED]"
_SENSITIVE_KEYS = ("authorization", "password", "secret", "token", "credential", "api_key")
_TERMINAL_STATUSES = (
    WorkloadStatus.SUCCEEDED,
    WorkloadStatus.FAILED,
    WorkloadStatus.CANCELLED,
    WorkloadStatus.DEAD_LETTERED,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


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


def _record_transition(workload: DurableWorkload) -> None:
    WORKLOAD_TRANSITIONS.labels(
        workload_type=workload.workload_type.value,
        status=workload.status.value,
    ).inc()


def _record_duration(workload: DurableWorkload) -> None:
    if workload.started_at is None or workload.completed_at is None:
        return
    elapsed = (
        _utc(workload.completed_at) - _utc(workload.started_at)
    ).total_seconds()
    WORKLOAD_DURATION.labels(
        workload_type=workload.workload_type.value,
        status=workload.status.value,
    ).observe(max(elapsed, 0))


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
    _record_transition(workload)
    return workload, True


async def get_workload(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    workload_id: UUID,
) -> DurableWorkload | None:
    return cast(
        DurableWorkload | None,
        await db.scalar(
            select(DurableWorkload).where(
                DurableWorkload.id == workload_id,
                DurableWorkload.tenant_id == tenant_id,
            )
        ),
    )


async def list_workloads(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    limit: int = 50,
    cursor: CursorPosition | None = None,
    status_filter: WorkloadStatus | None = None,
    workload_type: WorkloadType | None = None,
) -> tuple[list[DurableWorkload], CursorPosition | None]:
    conditions: list[Any] = [DurableWorkload.tenant_id == tenant_id]
    if status_filter is not None:
        conditions.append(DurableWorkload.status == status_filter)
    if workload_type is not None:
        conditions.append(DurableWorkload.workload_type == workload_type)
    if cursor is not None:
        conditions.append(
            or_(
                DurableWorkload.created_at < cursor.created_at,
                and_(
                    DurableWorkload.created_at == cursor.created_at,
                    DurableWorkload.id < cursor.id,
                ),
            )
        )
    rows = list(
        (
            await db.scalars(
                select(DurableWorkload)
                .where(*conditions)
                .order_by(
                    DurableWorkload.created_at.desc(),
                    DurableWorkload.id.desc(),
                )
                .limit(limit + 1)
            )
        ).all()
    )
    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = (
        CursorPosition(created_at=items[-1].created_at, id=items[-1].id)
        if has_more and items
        else None
    )
    return items, next_cursor


async def tenant_queue_snapshot(
    db: AsyncSession,
    *,
    tenant_id: UUID,
) -> tuple[dict[str, int], float]:
    rows = (
        await db.execute(
            select(DurableWorkload.status, func.count(DurableWorkload.id))
            .where(DurableWorkload.tenant_id == tenant_id)
            .group_by(DurableWorkload.status)
        )
    ).all()
    counts = {status.value: int(count) for status, count in rows}
    oldest = await db.scalar(
        select(func.min(DurableWorkload.created_at)).where(
            DurableWorkload.tenant_id == tenant_id,
            DurableWorkload.status == WorkloadStatus.QUEUED,
        )
    )
    age = max((_now() - _utc(oldest)).total_seconds(), 0) if oldest else 0.0
    return counts, age


async def refresh_workload_metrics(db: AsyncSession) -> None:
    for workload_type in WorkloadType:
        for status in WorkloadStatus:
            WORKLOAD_QUEUE_DEPTH.labels(
                workload_type=workload_type.value,
                status=status.value,
            ).set(0)
        WORKLOAD_OLDEST_QUEUED_AGE.labels(
            workload_type=workload_type.value
        ).set(0)

    grouped = (
        await db.execute(
            select(
                DurableWorkload.workload_type,
                DurableWorkload.status,
                func.count(DurableWorkload.id),
            ).group_by(DurableWorkload.workload_type, DurableWorkload.status)
        )
    ).all()
    for workload_type, status, count in grouped:
        WORKLOAD_QUEUE_DEPTH.labels(
            workload_type=workload_type.value,
            status=status.value,
        ).set(int(count))

    oldest_rows = (
        await db.execute(
            select(
                DurableWorkload.workload_type,
                func.min(DurableWorkload.created_at),
            )
            .where(DurableWorkload.status == WorkloadStatus.QUEUED)
            .group_by(DurableWorkload.workload_type)
        )
    ).all()
    now = _now()
    for workload_type, oldest in oldest_rows:
        WORKLOAD_OLDEST_QUEUED_AGE.labels(
            workload_type=workload_type.value
        ).set(max((now - _utc(oldest)).total_seconds(), 0))


async def recover_expired_leases(
    db: AsyncSession,
    *,
    allowed_tenant_ids: Sequence[UUID] | None = None,
    allowed_workload_types: Sequence[WorkloadType] | None = None,
    now: datetime | None = None,
) -> int:
    current = now or _now()
    conditions: list[Any] = [
        DurableWorkload.status.in_(
            (WorkloadStatus.LEASED, WorkloadStatus.RUNNING)
        ),
        DurableWorkload.lease_expires_at < current,
    ]
    if allowed_tenant_ids is not None:
        conditions.append(DurableWorkload.tenant_id.in_(allowed_tenant_ids))
    if allowed_workload_types is not None:
        conditions.append(
            DurableWorkload.workload_type.in_(allowed_workload_types)
        )
    rows = list(
        (
            await db.scalars(
                select(DurableWorkload)
                .where(*conditions)
                .with_for_update(skip_locked=True)
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
            _record_duration(workload)
        else:
            workload.status = WorkloadStatus.QUEUED
            workload.scheduled_at = current
        _record_transition(workload)
    await db.commit()
    return len(rows)


async def lease_next_workload(
    db: AsyncSession,
    *,
    worker_id: str,
    lease_seconds: int = 60,
    per_tenant_limit: int = 2,
    allowed_tenant_ids: Sequence[UUID] | None = None,
    allowed_workload_types: Sequence[WorkloadType] | None = None,
    now: datetime | None = None,
) -> DurableWorkload | None:
    current = now or _now()
    await recover_expired_leases(
        db,
        allowed_tenant_ids=allowed_tenant_ids,
        allowed_workload_types=allowed_workload_types,
        now=current,
    )
    conditions: list[Any] = [
        DurableWorkload.status == WorkloadStatus.QUEUED,
        DurableWorkload.scheduled_at <= current,
    ]
    if allowed_tenant_ids is not None:
        conditions.append(DurableWorkload.tenant_id.in_(allowed_tenant_ids))
    if allowed_workload_types is not None:
        conditions.append(
            DurableWorkload.workload_type.in_(allowed_workload_types)
        )
    candidates = list(
        (
            await db.scalars(
                select(DurableWorkload)
                .where(*conditions)
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
        _record_transition(workload)
        return workload
    return None


async def _lock_current_lease(
    db: AsyncSession,
    workload: DurableWorkload,
    worker_id: str,
) -> DurableWorkload:
    current = await db.scalar(
        select(DurableWorkload)
        .where(DurableWorkload.id == workload.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if current is None:
        raise ValueError("Workload no longer exists.")
    if current.lease_owner != worker_id:
        raise ValueError("Workload is not leased by this worker.")
    if current.status not in (WorkloadStatus.LEASED, WorkloadStatus.RUNNING):
        raise ValueError("Workload is not executable.")
    if (
        current.lease_expires_at is None
        or _utc(current.lease_expires_at) <= _now()
    ):
        raise ValueError("Workload lease has expired.")
    return current


async def mark_running(
    db: AsyncSession,
    workload: DurableWorkload,
    *,
    worker_id: str,
) -> DurableWorkload:
    current = await _lock_current_lease(db, workload, worker_id)
    current.status = WorkloadStatus.RUNNING
    current.started_at = current.started_at or _now()
    await db.commit()
    await db.refresh(current)
    _record_transition(current)
    return current


async def heartbeat(
    db: AsyncSession,
    workload: DurableWorkload,
    *,
    worker_id: str,
    lease_seconds: int = 60,
    progress_current: int | None = None,
    progress_total: int | None = None,
) -> None:
    current_workload = await _lock_current_lease(db, workload, worker_id)
    current = _now()
    current_workload.heartbeat_at = current
    current_workload.lease_expires_at = current + timedelta(seconds=lease_seconds)
    if progress_current is not None:
        current_workload.progress_current = progress_current
    if progress_total is not None:
        current_workload.progress_total = progress_total
    await db.commit()


async def succeed_workload(
    db: AsyncSession,
    workload: DurableWorkload,
    *,
    worker_id: str,
    result: dict[str, Any],
) -> None:
    current = await _lock_current_lease(db, workload, worker_id)
    current.status = WorkloadStatus.SUCCEEDED
    current.result_json = redact_diagnostics(result)
    current.completed_at = _now()
    current.lease_owner = None
    current.lease_expires_at = None
    _record_transition(current)
    _record_duration(current)
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
    current_workload = await _lock_current_lease(db, workload, worker_id)
    current = _now()
    current_workload.error_code = error_code[:100]
    current_workload.error_message = error_message[:2000]
    current_workload.diagnostics_json = redact_diagnostics(diagnostics or {})
    current_workload.lease_owner = None
    current_workload.lease_expires_at = None
    if retryable and current_workload.attempts < current_workload.max_attempts:
        current_workload.status = WorkloadStatus.QUEUED
        current_workload.scheduled_at = current + timedelta(seconds=retry_delay_seconds)
    else:
        current_workload.status = (
            WorkloadStatus.FAILED
            if not retryable
            else WorkloadStatus.DEAD_LETTERED
        )
        current_workload.completed_at = current
        _record_duration(current_workload)
    _record_transition(current_workload)
    await db.commit()


async def cancel_workload(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    workload_id: UUID,
    cancelled_by: str,
) -> bool:
    workload = await db.scalar(
        select(DurableWorkload)
        .where(
            DurableWorkload.id == workload_id,
            DurableWorkload.tenant_id == tenant_id,
        )
        .with_for_update()
    )
    if workload is None or workload.status in _TERMINAL_STATUSES:
        return False
    workload.status = WorkloadStatus.CANCELLED
    workload.cancelled_by = cancelled_by
    workload.completed_at = _now()
    workload.lease_owner = None
    workload.lease_expires_at = None
    _record_transition(workload)
    _record_duration(workload)
    await db.commit()
    return True
