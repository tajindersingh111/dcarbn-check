from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.calculations.governed_methods import validate_governed_method
from app.models.activity import (
    ActivityStatus,
    ActivityType,
    DataQualityLevel,
    EmissionScope,
    Scope2Method,
)


class ActivityCreate(BaseModel):
    organisation_id: UUID
    legal_entity_id: UUID | None = None
    site_id: UUID | None = None
    activity_type: ActivityType
    scope: EmissionScope
    scope_3_category: int | None = Field(default=None, ge=1, le=15)
    scope_2_method: Scope2Method = Scope2Method.NOT_APPLICABLE
    activity_date: date
    description: str = Field(min_length=1, max_length=500)
    activity_value: Decimal = Field(ge=0)
    activity_unit: str = Field(min_length=1, max_length=100)
    geography_code: str = Field(default="GB", min_length=2, max_length=20)
    factor_level_1: str | None = Field(default=None, max_length=250)
    factor_level_2: str | None = Field(default=None, max_length=250)
    factor_level_3: str | None = Field(default=None, max_length=250)
    factor_level_4: str | None = Field(default=None, max_length=250)
    factor_column_text: str | None = Field(default=None, max_length=500)
    lifecycle_boundary: str | None = Field(default=None, max_length=150)
    allocation_percentage: Decimal = Field(
        default=Decimal("100.00"),
        ge=0,
        le=100,
    )
    data_quality_level: DataQualityLevel = DataQualityLevel.UNKNOWN
    data_quality_score: int = Field(default=0, ge=0, le=100)
    source_system: str = Field(default="carbon-platform", max_length=100)
    source_record_id: str = Field(min_length=1, max_length=200)
    source_record_hash: str | None = Field(default=None, max_length=64)
    evidence_reference: str | None = Field(default=None, max_length=1000)
    metadata_json: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_scope(self) -> "ActivityCreate":
        if self.scope == EmissionScope.SCOPE_3 and self.scope_3_category is None:
            raise ValueError("scope_3_category is required for Scope 3 activities")
        if self.scope != EmissionScope.SCOPE_3 and self.scope_3_category is not None:
            raise ValueError("scope_3_category is only valid for Scope 3 activities")
        if self.scope == EmissionScope.SCOPE_2:
            if self.scope_2_method == Scope2Method.NOT_APPLICABLE:
                raise ValueError("Scope 2 activities require a Scope 2 method")
        elif self.scope_2_method != Scope2Method.NOT_APPLICABLE:
            raise ValueError("scope_2_method is only valid for Scope 2 activities")
        if not self.factor_level_1:
            raise ValueError("factor_level_1 is required for factor resolution")
        validate_governed_method(
            activity_type=self.activity_type,
            scope=self.scope,
            scope_3_category=self.scope_3_category,
            activity_unit=self.activity_unit,
            factor_level_1=self.factor_level_1,
            factor_level_2=self.factor_level_2,
            factor_level_3=self.factor_level_3,
            factor_level_4=self.factor_level_4,
            factor_column_text=self.factor_column_text,
            metadata_json=self.metadata_json,
            activity_value=self.activity_value,
            scope_2_method=self.scope_2_method,
        )
        return self


class ActivityUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=500)
    activity_value: Decimal | None = Field(default=None, ge=0)
    activity_unit: str | None = Field(default=None, min_length=1, max_length=100)
    geography_code: str | None = Field(default=None, min_length=2, max_length=20)
    factor_level_1: str | None = Field(default=None, max_length=250)
    factor_level_2: str | None = Field(default=None, max_length=250)
    factor_level_3: str | None = Field(default=None, max_length=250)
    factor_level_4: str | None = Field(default=None, max_length=250)
    factor_column_text: str | None = Field(default=None, max_length=500)
    lifecycle_boundary: str | None = Field(default=None, max_length=150)
    allocation_percentage: Decimal | None = Field(default=None, ge=0, le=100)
    data_quality_level: DataQualityLevel | None = None
    data_quality_score: int | None = Field(default=None, ge=0, le=100)
    evidence_reference: str | None = Field(default=None, max_length=1000)
    metadata_json: dict[str, object] | None = None


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    inventory_id: UUID
    organisation_id: UUID
    legal_entity_id: UUID | None
    site_id: UUID | None
    activity_type: ActivityType
    status: ActivityStatus
    scope: EmissionScope
    scope_3_category: int | None
    scope_2_method: Scope2Method
    activity_date: date
    description: str
    activity_value: Decimal
    activity_unit: str
    normalized_value: Decimal | None
    normalized_unit: str | None
    geography_code: str
    factor_level_1: str | None
    factor_level_2: str | None
    factor_level_3: str | None
    factor_level_4: str | None
    factor_column_text: str | None
    lifecycle_boundary: str | None
    allocation_percentage: Decimal
    data_quality_level: DataQualityLevel
    data_quality_score: int
    source_system: str
    source_record_id: str
    source_record_hash: str | None
    evidence_reference: str | None
    metadata_json: dict[str, object]
    version: int
    is_current: bool
    superseded_by_id: UUID | None
    validation_message: str | None
    created_at: datetime
    updated_at: datetime


class ActivityListResponse(BaseModel):
    items: list[ActivityResponse]
    total: int
    limit: int
    offset: int
