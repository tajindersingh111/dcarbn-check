from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    CurrentPrincipal,
    get_current_principal,
    require_roles,
)
from app.db.session import get_db
from app.schemas.workflows import (
    ApprovalQueueResponse,
    AuditReportListResponse,
    CalculationRunOption,
    CalculationRunOptionList,
    DashboardSummaryResponse,
    InventoryCreate,
    InventoryListResponse,
    InventoryResponse,
    ReportingPeriodCreate,
    ReportingPeriodListResponse,
    ReportingPeriodResponse,
)
from app.services.workflows import (
    create_inventory,
    create_reporting_period,
    dashboard_summary,
    get_inventory_response,
    list_approval_queue,
    list_audit_reports,
    list_calculation_run_options,
    list_inventories,
    list_reporting_periods,
)

router = APIRouter()
editor = Depends(
    require_roles("tenant_admin", "sustainability_manager")
)


@router.get("/dashboard", response_model=DashboardSummaryResponse)
async def get_dashboard(
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummaryResponse:
    return await dashboard_summary(db, principal.tenant_id)


@router.post(
    "/reporting-periods",
    response_model=ReportingPeriodResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[editor],
)
async def create_period(
    payload: ReportingPeriodCreate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> ReportingPeriodResponse:
    period = await create_reporting_period(db, principal, payload)
    return ReportingPeriodResponse.model_validate(period)


@router.get(
    "/reporting-periods",
    response_model=ReportingPeriodListResponse,
)
async def get_periods(
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> ReportingPeriodListResponse:
    items = await list_reporting_periods(db, principal.tenant_id)
    return ReportingPeriodListResponse(
        items=[ReportingPeriodResponse.model_validate(item) for item in items],
        total=len(items),
    )


@router.post(
    "/inventories",
    response_model=InventoryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[editor],
)
async def create_inventory_record(
    payload: InventoryCreate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> InventoryResponse:
    inventory = await create_inventory(db, principal, payload)
    response = await get_inventory_response(
        db,
        principal.tenant_id,
        inventory.id,
    )
    if response is None:
        raise HTTPException(status_code=500, detail="Inventory could not be loaded.")
    return response


@router.get("/inventories", response_model=InventoryListResponse)
async def get_inventories(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> InventoryListResponse:
    items, total = await list_inventories(
        db,
        principal.tenant_id,
        limit,
        offset,
    )
    return InventoryListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/inventories/{inventory_id}",
    response_model=InventoryResponse,
)
async def get_inventory(
    inventory_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> InventoryResponse:
    item = await get_inventory_response(
        db,
        principal.tenant_id,
        inventory_id,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory not found.")
    return item


@router.get(
    "/inventories/{inventory_id}/calculation-runs",
    response_model=CalculationRunOptionList,
)
async def get_calculation_runs(
    inventory_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> CalculationRunOptionList:
    runs = await list_calculation_run_options(
        db,
        principal.tenant_id,
        inventory_id,
    )
    return CalculationRunOptionList(
        items=[
            CalculationRunOption(
                id=run.id,
                inventory_id=run.inventory_id,
                version=run.version,
                status=run.status.value,
                completed_at=run.completed_at,
                activity_count=run.activity_count,
                result_count=run.result_count,
            )
            for run in runs
        ],
        total=len(runs),
    )


@router.get(
    "/inventory-approvals",
    response_model=ApprovalQueueResponse,
)
async def get_approval_queue(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> ApprovalQueueResponse:
    items, total = await list_approval_queue(
        db,
        principal.tenant_id,
        limit,
        offset,
    )
    return ApprovalQueueResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/audit-reports", response_model=AuditReportListResponse)
async def get_reports(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> AuditReportListResponse:
    items, total = await list_audit_reports(
        db,
        principal.tenant_id,
        limit,
        offset,
    )
    return AuditReportListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
