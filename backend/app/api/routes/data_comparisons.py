from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    CurrentPrincipal,
    get_current_principal,
    require_roles,
)
from app.db.session import get_db
from app.models.calculation import CalculationResult
from app.models.data_integration import (
    DataCalculationComparison,
    DataOperationalEmission,
)
from app.schemas.data_comparison import (
    DataCalculationComparisonDetailResponse,
    DataCalculationComparisonResponse,
    DataComparisonResultView,
)
from app.services.data_comparisons import generate_government_comparator


router = APIRouter(prefix="/integrations/data/comparisons")
comparison_reviewer = Depends(
    require_roles(
        "tenant_admin",
        "sustainability_manager",
        "data_reviewer",
        "inventory_approver",
    )
)


def _result_view(
    result: CalculationResult | None,
) -> DataComparisonResultView | None:
    if result is None:
        return None
    return DataComparisonResultView(
        result_id=result.id,
        allocated_kg_co2e=result.allocated_kg_co2e,
        methodology_version=result.methodology_version,
        calculation_method=result.method.value,
        factor_id=result.selected_factor_id,
        factor_value=result.factor_value,
        warnings=list(result.warnings),
        lineage=dict(result.intermediate_values),
    )


@router.get(
    "/operational-emissions/{emission_id}",
    response_model=DataCalculationComparisonDetailResponse,
)
async def get_operational_emission_comparison(
    emission_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DataCalculationComparisonDetailResponse:
    comparison = await db.scalar(
        select(DataCalculationComparison).where(
            DataCalculationComparison.tenant_id == principal.tenant_id,
            DataCalculationComparison.operational_emission_id == emission_id,
        )
    )
    if comparison is None:
        raise HTTPException(
            status_code=404,
            detail="Calculation comparison not found.",
        )
    emission = await db.scalar(
        select(DataOperationalEmission).where(
            DataOperationalEmission.id == emission_id,
            DataOperationalEmission.tenant_id == principal.tenant_id,
        )
    )
    if emission is None:
        raise HTTPException(
            status_code=404,
            detail="DcarbN operational-emission record not found.",
        )

    dcarbn_result = (
        await db.scalar(
            select(CalculationResult).where(
                CalculationResult.id == comparison.dcarbn_result_id,
                CalculationResult.tenant_id == principal.tenant_id,
            )
        )
        if comparison.dcarbn_result_id
        else None
    )
    government_result = (
        await db.scalar(
            select(CalculationResult).where(
                CalculationResult.id == comparison.government_result_id,
                CalculationResult.tenant_id == principal.tenant_id,
            )
        )
        if comparison.government_result_id
        else None
    )
    base = DataCalculationComparisonResponse.model_validate(
        comparison
    ).model_dump()
    return DataCalculationComparisonDetailResponse(
        **base,
        confirmed_scope=emission.confirmed_scope,
        confirmed_scope_3_category=emission.confirmed_scope_3_category,
        data_quality_level=emission.data_quality_level,
        data_quality_score=emission.data_quality_score,
        uncertainty_percentage=emission.uncertainty_percentage,
        dcarbn_result=_result_view(dcarbn_result),
        government_result=_result_view(government_result),
    )


@router.post(
    "/{comparison_id}/government",
    response_model=DataCalculationComparisonResponse,
    dependencies=[comparison_reviewer],
)
async def generate_government_comparison(
    comparison_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DataCalculationComparisonResponse:
    comparison = await generate_government_comparator(
        db,
        principal,
        comparison_id,
    )
    return DataCalculationComparisonResponse.model_validate(comparison)
