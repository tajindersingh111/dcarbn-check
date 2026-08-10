from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workload import DurableWorkload, WorkloadType
from app.services.methodology_dual_run import handle_methodology_dual_run
from app.services.workloads import (
    fail_workload,
    lease_next_workload,
    mark_running,
    refresh_workload_metrics,
    succeed_workload,
)
from app.workers.errors import NonRetryableWorkloadError

logger = logging.getLogger(__name__)
WorkloadHandler = Callable[[AsyncSession, DurableWorkload], Awaitable[dict[str, Any]]]


class WorkloadRegistry:
    """Small reviewed handler registry; payloads never select arbitrary code."""

    def __init__(self) -> None:
        self._handlers: dict[WorkloadType, WorkloadHandler] = {}

    def register(self, workload_type: WorkloadType, handler: WorkloadHandler) -> None:
        if workload_type in self._handlers:
            raise ValueError(f"Handler already registered for {workload_type.value}.")
        self._handlers[workload_type] = handler

    def resolve(self, workload_type: WorkloadType) -> WorkloadHandler:
        try:
            return self._handlers[workload_type]
        except KeyError as exc:
            raise LookupError(
                f"No approved handler registered for {workload_type.value}."
            ) from exc


def build_default_registry() -> WorkloadRegistry:
    """Return only handlers that have completed code review and equivalence tests."""
    registry = WorkloadRegistry()
    registry.register(WorkloadType.CALCULATION, handle_methodology_dual_run)
    return registry


async def _refresh_metrics_best_effort(db: AsyncSession) -> None:
    try:
        await refresh_workload_metrics(db)
    except Exception:
        logger.exception("Unable to refresh durable workload metrics.")


async def run_one(
    db: AsyncSession,
    *,
    worker_id: str,
    registry: WorkloadRegistry,
    lease_seconds: int = 60,
    per_tenant_limit: int = 2,
) -> bool:
    workload = await lease_next_workload(
        db,
        worker_id=worker_id,
        lease_seconds=lease_seconds,
        per_tenant_limit=per_tenant_limit,
    )
    if workload is None:
        await _refresh_metrics_best_effort(db)
        return False

    await mark_running(db, workload, worker_id=worker_id)
    try:
        handler = registry.resolve(workload.workload_type)
        result = await handler(db, workload)
    except LookupError:
        await fail_workload(
            db,
            workload,
            worker_id=worker_id,
            error_code="handler_not_registered",
            error_message="No approved handler is registered for this workload type.",
            retryable=False,
        )
    except NonRetryableWorkloadError:
        await fail_workload(
            db,
            workload,
            worker_id=worker_id,
            error_code="workload_validation_failed",
            error_message="The workload payload failed governed validation.",
            retryable=False,
        )
    except Exception:
        # Raw exception text can contain customer data or credentials and is not persisted.
        await fail_workload(
            db,
            workload,
            worker_id=worker_id,
            error_code="handler_failure",
            error_message="The workload handler failed. Consult protected worker logs.",
            retryable=True,
        )
    else:
        await succeed_workload(db, workload, worker_id=worker_id, result=result)
    await _refresh_metrics_best_effort(db)
    return True
