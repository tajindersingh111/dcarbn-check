from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.activity import EmissionScope, Scope2Method
from app.models.calculation import (
    CalculationMethod,
    CalculationRunStatus,
)


class Scope2HeadlineBasis(StrEnum):
    LOCATION_BASED = "location_based"
    MARKET_BASED = "market_based"


class CalculationRunCreate(BaseModel):
    software_version: str = Field(default="0.1.0", min_length=1, max_length=100)
    factor_policy_version: str = Field(
        default="approved-exact-v1",
        min_length=1,
        max_length=100,
    )
    allow_previous_year: bool = False
    allow_geography_fallback: bool = False


class CalculationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    inventory_id: UUID
    version: int
    status: CalculationRunStatus
    software_version: str
    factor_policy_version: str
    started_at: datetime | None
    completed_at: datetime | None
    approved_at: datetime | None
    approved_by: str | None
    activity_count: int
    result_count: int
    failed_count: int
    failure_message: str | None
    created_at: datetime
    updated_at: datetime


class CalculationResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    calculation_run_id: UUID
    activity_id: UUID
    factor_resolution_record_id: UUID | None
    selected_factor_id: UUID | None
    method: CalculationMethod
    scope: EmissionScope
    scope_3_category: int | None
    scope_2_method: Scope2Method
    original_activity_value: Decimal
    original_activity_unit: str
    factor_activity_value: Decimal
    factor_activity_unit: str
    factor_value: Decimal | None
    allocation_percentage: Decimal
    allocation_multiplier: Decimal
    gross_kg_co2e: Decimal
    allocated_kg_co2e: Decimal
    co2_kg: Decimal | None
    ch4_kg_co2e: Decimal | None
    n2o_kg_co2e: Decimal | None
    calculation_formula: str
    intermediate_values: dict[str, object]
    warnings: list[str]
    methodology_version: str
    created_at: datetime
    updated_at: datetime


class CalculationResultListResponse(BaseModel):
    items: list[CalculationResultResponse]
    total: int


class InventoryScopeSummaryItem(BaseModel):
    scope: EmissionScope
    scope_3_category: int | None
    scope_2_method: Scope2Method
    kg_co2e: Decimal
    t_co2e: Decimal


class InventoryCalculationSummary(BaseModel):
    calculation_run_id: UUID
    inventory_id: UUID
    scope_2_headline_basis: Scope2HeadlineBasis
    scope_1_kg_co2e: Decimal
    scope_2_location_based_kg_co2e: Decimal
    scope_2_market_based_kg_co2e: Decimal
    scope_3_kg_co2e: Decimal
    total_kg_co2e: Decimal
    total_t_co2e: Decimal
    items: list[InventoryScopeSummaryItem]
