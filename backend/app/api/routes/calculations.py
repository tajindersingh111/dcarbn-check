from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal, get_current_principal, require_roles
from app.db.session import get_db
from app.schemas.calculation import (
    CalculationResultListResponse,
    CalculationResultResponse,
    CalculationRunCreate,
    CalculationRunResponse,
    InventoryCalculationSummary,
)
from app.services.calculations import (
    create_and_execute_calculation_run,
    get_calculation_run,
    list_calculation_results,
    summarize_calculation_run,
)

router = APIRouter()
calculator = Depends(require_roles("tenant_admin", "sustainability_manager"))


@router.post(
    "/inventories/{inventory_id}/calculation-runs",
    response_model=CalculationRunResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[calculator],
)
async def create_run(
    inventory_id: UUID,
    payload: CalculationRunCreate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> CalculationRunResponse:
    run = await create_and_execute_calculation_run(
        db,
        principal,
        inventory_id,
        payload,
    )
    return CalculationRunResponse.model_validate(run)


@router.get(
    "/calculation-runs/{run_id}",
    response_model=CalculationRunResponse,
)
async def get_run(
    run_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> CalculationRunResponse:
    run = await get_calculation_run(db, principal.tenant_id, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Calculation run not found.")
    return CalculationRunResponse.model_validate(run)


@router.get(
    "/calculation-runs/{run_id}/results",
    response_model=CalculationResultListResponse,
)
async def get_results(
    run_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> CalculationResultListResponse:
    run = await get_calculation_run(db, principal.tenant_id, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Calculation run not found.")
    items = await list_calculation_results(db, principal.tenant_id, run_id)
    return CalculationResultListResponse(
        items=[CalculationResultResponse.model_validate(item) for item in items],
        total=len(items),
    )


@router.get(
    "/calculation-runs/{run_id}/summary",
    response_model=InventoryCalculationSummary,
)
async def get_summary(
    run_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> InventoryCalculationSummary:
    return await summarize_calculation_run(db, principal.tenant_id, run_id)
