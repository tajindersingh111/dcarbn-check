from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.inventory_governance import (
    ApprovalStatus,
    ReportStatus,
    RestatementStatus,
)


class ApprovalRequestCreate(BaseModel):
    calculation_run_id: UUID


class ApprovalReviewStart(BaseModel):
    reviewer_comment: str | None = Field(default=None, max_length=5000)


class ApprovalDecision(BaseModel):
    decision: ApprovalStatus
    decision_reason: str = Field(min_length=10, max_length=5000)

    @model_validator(mode="after")
    def validate_decision(self) -> "ApprovalDecision":
        if self.decision not in {
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
        }:
            raise ValueError("decision must be approved or rejected")
        return self


class InventoryApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    inventory_id: UUID
    calculation_run_id: UUID
    version: int
    status: ApprovalStatus
    requested_by: str
    requested_at: datetime
    reviewer_id: str | None
    review_started_at: datetime | None
    decided_at: datetime | None
    decision_reason: str | None
    evidence_complete: bool
    boundary_complete: bool
    factor_lineage_complete: bool
    calculation_complete: bool
    review_snapshot: dict[str, object]
    created_at: datetime
    updated_at: datetime


class InventoryLockRequest(BaseModel):
    lock_reason: str = Field(min_length=10, max_length=5000)


class InventoryLockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    inventory_id: UUID
    approval_id: UUID
    calculation_run_id: UUID
    locked_by: str
    locked_at: datetime
    lock_reason: str
    lock_snapshot: dict[str, object]


class RestatementRequestCreate(BaseModel):
    reason: str = Field(min_length=10, max_length=5000)
    materiality_assessment: str = Field(min_length=10, max_length=5000)
    requested_changes: dict[str, object] = Field(default_factory=dict)


class RestatementDecision(BaseModel):
    decision: RestatementStatus
    decision_reason: str = Field(min_length=10, max_length=5000)

    @model_validator(mode="after")
    def validate_decision(self) -> "RestatementDecision":
        if self.decision not in {
            RestatementStatus.APPROVED,
            RestatementStatus.REJECTED,
        }:
            raise ValueError("decision must be approved or rejected")
        return self


class InventoryRestatementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    original_inventory_id: UUID
    replacement_inventory_id: UUID | None
    status: RestatementStatus
    requested_by: str
    requested_at: datetime
    reviewed_by: str | None
    reviewed_at: datetime | None
    completed_at: datetime | None
    reason: str
    materiality_assessment: str
    decision_reason: str | None
    requested_changes: dict[str, object]
    created_at: datetime
    updated_at: datetime


class ReportGenerateRequest(BaseModel):
    finalize: bool = False


class AuditReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    inventory_id: UUID
    calculation_run_id: UUID
    approval_id: UUID
    version: int
    status: ReportStatus
    generated_by: str
    generated_at: datetime
    finalized_by: str | None
    finalized_at: datetime | None
    report_sha256: str
    report_payload: dict[str, object]
    superseded_by_report_id: UUID | None
    created_at: datetime
    updated_at: datetime
