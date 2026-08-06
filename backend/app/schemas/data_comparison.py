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
