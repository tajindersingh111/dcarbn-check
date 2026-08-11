from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal, get_current_principal, require_roles
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.workload import WorkloadStatus, WorkloadType
from app.schemas.workload import (
    MethodologyDualRunCreate,
    WorkloadListResponse,
    WorkloadQueueSnapshotResponse,
    WorkloadResponse,
)
from app.services.methodology_dual_run import enqueue_methodology_dual_run
from app.services.workload_rollout import (
    WorkloadRolloutDisabled,
    WorkloadRolloutNotAllowed,
    require_workload_rollout,
)
from app.services.workloads import (
    cancel_workload,
    get_workload,
    list_workloads,
    tenant_queue_snapshot,
)
from app.workers.errors import NonRetryableWorkloadError

router = APIRouter(prefix="/workloads")
workload_reader = Depends(
    require_roles("tenant_admin", "sustainability_manager", "data_reviewer")
)
workload_writer = Depends(
    require_roles("tenant_admin", "sustainability_manager")
)


@router.post(
    "/methodology-dual-runs",
    response_model=WorkloadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[workload_writer],
)
async def create_methodology_dual_run(
    payload: MethodologyDualRunCreate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> WorkloadResponse:
    try:
        require_workload_rollout(
            settings,
            tenant_id=principal.tenant_id,
            workload_type=WorkloadType.CALCULATION,
            require_methodology_packs=True,
        )
    except WorkloadRolloutDisabled as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except WorkloadRolloutNotAllowed as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    try:
        workload, _ = await enqueue_methodology_dual_run(
            db,
            tenant_id=principal.tenant_id,
            requested_by=principal.subject,
            governed_method_id=payload.governed_method_id,
            methodology_pack_id=payload.methodology_pack_id,
            emission_factor_id=payload.emission_factor_id,
            activity_value=payload.activity_value,
            allocation_percentage=payload.allocation_percentage,
            source_reference=payload.source_reference,
            inventory_id=payload.inventory_id,
        )
    except NonRetryableWorkloadError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return WorkloadResponse.model_validate(workload)


@router.get(
    "",
    response_model=WorkloadListResponse,
    dependencies=[workload_reader],
)
async def get_workloads(
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    cursor: UUID | None = Query(default=None),
    status_filter: WorkloadStatus | None = Query(default=None, alias="status"),
    workload_type: WorkloadType | None = Query(default=None),
) -> WorkloadListResponse:
    items, next_cursor = await list_workloads(
        db,
        tenant_id=principal.tenant_id,
        limit=limit,
        cursor=cursor,
        status_filter=status_filter,
        workload_type=workload_type,
    )
    return WorkloadListResponse(
        items=[WorkloadResponse.model_validate(item) for item in items],
        next_cursor=next_cursor,
    )


@router.get(
    "/metrics",
    response_model=WorkloadQueueSnapshotResponse,
    dependencies=[workload_reader],
)
async def get_workload_metrics(
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> WorkloadQueueSnapshotResponse:
    counts, age = await tenant_queue_snapshot(db, tenant_id=principal.tenant_id)
    return WorkloadQueueSnapshotResponse(
        counts_by_status=counts,
        oldest_queued_age_seconds=age,
    )


@router.get(
    "/{workload_id}",
    response_model=WorkloadResponse,
    dependencies=[workload_reader],
)
async def get_workload_by_id(
    workload_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> WorkloadResponse:
    workload = await get_workload(
        db,
        tenant_id=principal.tenant_id,
        workload_id=workload_id,
    )
    if workload is None:
        raise HTTPException(status_code=404, detail="Workload not found.")
    return WorkloadResponse.model_validate(workload)


@router.post(
    "/{workload_id}/cancel",
    response_model=WorkloadResponse,
    dependencies=[workload_writer],
)
async def cancel_workload_by_id(
    workload_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> WorkloadResponse:
    workload = await get_workload(
        db,
        tenant_id=principal.tenant_id,
        workload_id=workload_id,
    )
    if workload is None:
        raise HTTPException(status_code=404, detail="Workload not found.")
    cancelled = await cancel_workload(
        db,
        tenant_id=principal.tenant_id,
        workload_id=workload_id,
        cancelled_by=principal.subject,
    )
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A terminal workload cannot be cancelled.",
        )
    updated = await get_workload(
        db,
        tenant_id=principal.tenant_id,
        workload_id=workload_id,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Workload not found.")
    return WorkloadResponse.model_validate(updated)
