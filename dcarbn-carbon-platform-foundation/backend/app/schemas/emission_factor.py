from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.emission_factor import (
    FactorImportStatus,
    FactorSetStatus,
    GreenhouseGasComponent,
)


class FactorSetImportMetadata(BaseModel):
    dataset_version: str = Field(min_length=1, max_length=100)
    reporting_year: int = Field(ge=1990, le=2200)
    publication_date: date | None = None
    effective_from: date
    effective_to: date
    source_reference: str | None = Field(default=None, max_length=1000)
    methodology_reference: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=5000)


class FactorSetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    publisher: str
    dataset_name: str
    dataset_version: str
    reporting_year: int
    publication_date: date | None
    effective_from: date
    effective_to: date
    geography_code: str
    source_filename: str
    source_sha256: str
    source_reference: str | None
    methodology_reference: str | None
    licence_name: str | None
    licence_reference: str | None
    status: FactorSetStatus
    is_authoritative: bool
    imported_at: datetime
    imported_by: str
    approved_at: datetime | None
    approved_by: str | None
    superseded_at: datetime | None
    superseded_by_set_id: UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class FactorSetListResponse(BaseModel):
    items: list[FactorSetResponse]
    total: int


class EmissionFactorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    factor_set_id: UUID
    source_factor_id: str
    scope: str
    level_1: str
    level_2: str | None
    level_3: str | None
    level_4: str | None
    column_text: str | None
    activity_unit: str
    factor_unit_text: str
    greenhouse_gas_component: GreenhouseGasComponent
    greenhouse_gas_label: str
    factor_value: Decimal
    factor_numerator_unit: str
    factor_denominator_unit: str
    geography_code: str
    reporting_year: int
    lifecycle_boundary: str | None
    source_row_number: int
    is_active: bool


class EmissionFactorListResponse(BaseModel):
    items: list[EmissionFactorResponse]
    total: int
    limit: int
    offset: int


class FactorImportErrorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    import_job_id: UUID
    worksheet_name: str
    row_number: int | None
    error_code: str
    error_message: str
    raw_row_data: dict[str, object] | None
    created_at: datetime


class FactorImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    factor_set_id: UUID | None
    status: FactorImportStatus
    source_filename: str
    source_sha256: str
    dataset_version: str
    reporting_year: int
    total_rows: int
    imported_rows: int
    rejected_rows: int
    started_at: datetime | None
    completed_at: datetime | None
    requested_by: str
    failure_message: str | None
    created_at: datetime
    updated_at: datetime


class FactorSetApprovalRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=5000)


class FactorSetSupersedeRequest(BaseModel):
    replacement_factor_set_id: UUID
    reason: str = Field(min_length=10, max_length=5000)
