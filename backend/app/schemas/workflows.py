from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.inventory import InventoryStatus
from app.models.inventory_governance import ApprovalStatus, ReportStatus


class ReportingPeriodCreate(BaseModel):
    organisation_id: UUID
    name: str = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date
    is_base_year: bool = False

    @model_validator(mode="after")
    def validate_dates(self) -> "ReportingPeriodCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class ReportingPeriodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    organisation_id: UUID
    name: str
    start_date: date
    end_date: date
    is_base_year: bool
    created_at: datetime
    updated_at: datetime


class ReportingPeriodListResponse(BaseModel):
    items: list[ReportingPeriodResponse]
    total: int


class InventoryCreate(BaseModel):
    reporting_period_id: UUID
    name: str = Field(min_length=1, max_length=200)


class InventoryResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    reporting_period_id: UUID
    organisation_id: UUID
    organisation_name: str
    reporting_period_name: str
    reporting_period_start: date
    reporting_period_end: date
    name: str
    status: InventoryStatus
    version: int
    locked_at: datetime | None
    approved_at: datetime | None
    latest_calculation_run_id: UUID | None
    total_kg_co2e: Decimal | None
    scope_1_kg_co2e: Decimal | None
    scope_2_kg_co2e: Decimal | None
    scope_3_kg_co2e: Decimal | None
    created_at: datetime
    updated_at: datetime


class InventoryListResponse(BaseModel):
    items: list[InventoryResponse]
    total: int
    limit: int
    offset: int


class CalculationRunOption(BaseModel):
    id: UUID
    inventory_id: UUID
    version: int
    status: str
    completed_at: datetime | None
    activity_count: int
    result_count: int


class CalculationRunOptionList(BaseModel):
    items: list[CalculationRunOption]
    total: int


class ApprovalQueueItem(BaseModel):
    id: UUID
    inventory_id: UUID
    inventory_name: str
    calculation_run_id: UUID
    version: int
    status: ApprovalStatus
    requested_by: str
    requested_at: datetime
    reviewer_id: str | None
    evidence_complete: bool
    boundary_complete: bool
    factor_lineage_complete: bool
    calculation_complete: bool


class ApprovalQueueResponse(BaseModel):
    items: list[ApprovalQueueItem]
    total: int
    limit: int
    offset: int


class AuditReportListItem(BaseModel):
    id: UUID
    inventory_id: UUID
    inventory_name: str
    version: int
    status: ReportStatus
    generated_by: str
    generated_at: datetime
    finalized_at: datetime | None
    report_sha256: str
    total_kg_co2e: Decimal
    total_t_co2e: Decimal


class AuditReportListResponse(BaseModel):
    items: list[AuditReportListItem]
    total: int
    limit: int
    offset: int


class DashboardSummaryResponse(BaseModel):
    total_kg_co2e: Decimal
    total_t_co2e: Decimal
    inventory_count: int
    locked_inventory_count: int
    open_data_review_count: int
    open_approval_count: int
    organisation_count: int
