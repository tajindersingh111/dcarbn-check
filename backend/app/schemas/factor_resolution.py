from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.factors.resolution import MatchStrength, ResolutionOutcome
from app.models.emission_factor import GreenhouseGasComponent
from app.models.factor_resolution import ResolutionSource
from app.units.registry import Dimension


class UnitNormalizationRequest(BaseModel):
    value: Decimal
    unit: str = Field(min_length=1, max_length=100)
    target_unit: str | None = Field(default=None, min_length=1, max_length=100)


class UnitNormalizationResponse(BaseModel):
    original_value: Decimal
    original_unit: str
    normalized_value: Decimal
    normalized_unit: str
    dimension: Dimension
    conversion_multiplier: Decimal


class FactorResolutionRequest(BaseModel):
    activity_value: Decimal
    activity_unit: str = Field(min_length=1, max_length=100)
    reporting_year: int = Field(ge=1990, le=2200)
    geography_code: str = Field(min_length=2, max_length=20)
    scope: str = Field(min_length=1, max_length=50)
    level_1: str | None = Field(default=None, max_length=250)
    level_2: str | None = Field(default=None, max_length=250)
    level_3: str | None = Field(default=None, max_length=250)
    level_4: str | None = Field(default=None, max_length=250)
    column_text: str | None = Field(default=None, max_length=500)
    lifecycle_boundary: str | None = Field(default=None, max_length=150)
    greenhouse_gas_component: GreenhouseGasComponent = (
        GreenhouseGasComponent.TOTAL_CO2E
    )
    factor_set_id: UUID | None = None
    inventory_id: UUID | None = None
    allow_previous_year: bool = False
    allow_geography_fallback: bool = False
    source: ResolutionSource = ResolutionSource.API
    persist: bool = False

    @model_validator(mode="after")
    def require_classification(self) -> "FactorResolutionRequest":
        if not self.level_1 and not self.factor_set_id:
            raise ValueError(
                "level_1 or factor_set_id is required to avoid an "
                "unbounded factor search."
            )
        return self


class FactorCandidateResponse(BaseModel):
    factor_id: UUID
    source_factor_id: str
    score: int
    strength: MatchStrength
    reasons: list[str]
    warnings: list[str]
    factor_value: Decimal
    factor_activity_unit: str
    converted_activity_value: Decimal
    resulting_kg_co2e: Decimal


class FactorResolutionResponse(BaseModel):
    outcome: ResolutionOutcome
    selected: FactorCandidateResponse | None
    candidates: list[FactorCandidateResponse]
    warnings: list[str]
    normalized_activity_value: Decimal | None
    normalized_activity_unit: str | None
    resolution_record_id: UUID | None = None


class FactorResolutionRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    inventory_id: UUID | None
    selected_factor_id: UUID | None
    outcome: ResolutionOutcome
    match_strength: MatchStrength | None
    source: ResolutionSource
    original_activity_value: Decimal
    original_activity_unit: str
    normalized_activity_value: Decimal | None
    normalized_activity_unit: str | None
    selected_factor_activity_value: Decimal | None
    selected_factor_activity_unit: str | None
    selected_factor_value: Decimal | None
    resulting_kg_co2e: Decimal | None
    selected_score: int | None
    criteria: dict[str, object]
    candidate_summary: list[dict[str, object]]
    warnings: list[str]
    resolution_reason: str | None
    resolved_by: str
