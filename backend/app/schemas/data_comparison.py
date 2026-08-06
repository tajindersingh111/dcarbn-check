from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.data_integration import (
    DataComparisonStatus,
    DataReportingBasis,
)


class DataCalculationComparisonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    operational_emission_id: UUID
    comparison_group_key: str
    dcarbn_result_id: UUID | None
    government_result_id: UUID | None
    status: DataComparisonStatus
    reporting_basis: DataReportingBasis
    basis_reason: str | None
    comparison_unavailable_reason: str | None
    absolute_delta_kg_co2e: Decimal | None
    percentage_delta: Decimal | None


class DataComparisonResultView(BaseModel):
    result_id: UUID
    allocated_kg_co2e: Decimal
    methodology_version: str
    calculation_method: str
    factor_id: UUID | None
    factor_value: Decimal | None
    warnings: list[str]
    lineage: dict[str, object]


class DataCalculationComparisonDetailResponse(
    DataCalculationComparisonResponse
):
    confirmed_scope: str | None
    confirmed_scope_3_category: int | None
    data_quality_level: str | None
    data_quality_score: int | None
    uncertainty_percentage: Decimal | None
    dcarbn_result: DataComparisonResultView | None
    government_result: DataComparisonResultView | None
