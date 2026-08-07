from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.models.inventory_governance import (
    ApprovalStatus,
    ReportStatus,
    RestatementStatus,
    RestatementTrigger,
)
from app.schemas.calculation import Scope2HeadlineBasis
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ApprovalRequestCreate(BaseModel):
    calculation_run_id: UUID


class ApprovalReviewStart(BaseModel):
    reviewer_comment: str | None = Field(default=None, max_length=5000)


class ApprovalDecision(BaseModel):
    decision: ApprovalStatus
    decision_reason: str = Field(min_length=10, max_length=5000)

    @model_validator(mode="after")
    def validate_decision(self) -> ApprovalDecision:
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
    trigger: RestatementTrigger
    reason: str = Field(min_length=10, max_length=5000)
    materiality_assessment: str = Field(min_length=10, max_length=5000)
    estimated_impact_percent: Decimal | None = Field(default=None, ge=0, le=1000)
    qualitative_override: bool = False
    qualitative_override_rationale: str | None = Field(default=None, max_length=5000)
    boundary_change_summary: str | None = Field(default=None, max_length=5000)
    requested_changes: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_materiality_evidence(self) -> RestatementRequestCreate:
        if self.qualitative_override and not (
            self.qualitative_override_rationale
            and len(self.qualitative_override_rationale.strip()) >= 10
        ):
            raise ValueError(
                "qualitative_override_rationale is required for a qualitative override"
            )
        boundary_triggers = {
            RestatementTrigger.ACQUISITION,
            RestatementTrigger.DIVESTMENT,
            RestatementTrigger.OUTSOURCING_INSOURCING,
            RestatementTrigger.ORGANISATIONAL_BOUNDARY_CHANGE,
            RestatementTrigger.OPERATIONAL_BOUNDARY_CHANGE,
        }
        if self.trigger in boundary_triggers and not (
            self.boundary_change_summary
            and len(self.boundary_change_summary.strip()) >= 10
        ):
            raise ValueError(
                "boundary_change_summary is required for boundary-related triggers"
            )
        return self


class RestatementDecision(BaseModel):
    decision: RestatementStatus
    decision_reason: str = Field(min_length=10, max_length=5000)

    @model_validator(mode="after")
    def validate_decision(self) -> RestatementDecision:
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
    trigger: RestatementTrigger
    estimated_impact_percent: Decimal | None
    significance_threshold_percent: Decimal
    threshold_exceeded: bool
    qualitative_override: bool
    qualitative_override_rationale: str | None
    boundary_change_summary: str | None
    decision_reason: str | None
    requested_changes: dict[str, object]
    created_at: datetime
    updated_at: datetime


class ReportGenerateRequest(BaseModel):
    finalize: bool = False
    scope_2_headline_basis: Scope2HeadlineBasis


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
