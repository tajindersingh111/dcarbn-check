from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    CurrentPrincipal,
    get_current_principal,
    require_roles,
)
from app.db.session import get_db
from app.schemas.data_comparison import DataCalculationComparisonResponse
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
