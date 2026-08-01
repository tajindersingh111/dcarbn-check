from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.boundary import (
    BoundaryStatus,
    ConsolidationApproach,
    MembershipDecision,
)


class BoundaryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    consolidation_approach: ConsolidationApproach
    control_threshold_percentage: Decimal = Field(
        default=Decimal("50.00"),
        ge=0,
        le=100,
        decimal_places=2,
    )
    effective_from: date
    effective_to: date
    rationale: str = Field(min_length=10, max_length=5000)

    @model_validator(mode="after")
    def validate_dates(self) -> "BoundaryCreate":
        if self.effective_to < self.effective_from:
            raise ValueError("effective_to must be on or after effective_from")
        return self


class BoundaryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    consolidation_approach: ConsolidationApproach | None = None
    control_threshold_percentage: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
        decimal_places=2,
    )
    effective_from: date | None = None
    effective_to: date | None = None
    rationale: str | None = Field(default=None, min_length=10, max_length=5000)


class BoundaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    reporting_period_id: UUID
    name: str
    consolidation_approach: ConsolidationApproach
    status: BoundaryStatus
    version: int
    control_threshold_percentage: Decimal
    effective_from: date
    effective_to: date
    rationale: str
    approved_at: datetime | None
    approved_by: str | None
    locked_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BoundaryListResponse(BaseModel):
    items: list[BoundaryResponse]
    total: int


class MembershipCreate(BaseModel):
    legal_entity_id: UUID
    decision: MembershipDecision = MembershipDecision.AUTO
    ownership_percentage: Decimal = Field(ge=0, le=100, decimal_places=2)
    has_operational_control: bool
    has_financial_control: bool
    effective_from: date
    effective_to: date
    decision_reason: str | None = Field(default=None, max_length=5000)
    evidence_reference: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_membership(self) -> "MembershipCreate":
        if self.effective_to < self.effective_from:
            raise ValueError("effective_to must be on or after effective_from")
        if self.decision != MembershipDecision.AUTO and not self.decision_reason:
            raise ValueError("decision_reason is required for manual decisions")
        return self


class MembershipUpdate(BaseModel):
    decision: MembershipDecision | None = None
    ownership_percentage: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
        decimal_places=2,
    )
    has_operational_control: bool | None = None
    has_financial_control: bool | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    decision_reason: str | None = Field(default=None, max_length=5000)
    evidence_reference: str | None = Field(default=None, max_length=500)


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    boundary_id: UUID
    legal_entity_id: UUID
    decision: MembershipDecision
    ownership_percentage: Decimal
    has_operational_control: bool
    has_financial_control: bool
    is_included: bool
    allocation_percentage: Decimal
    effective_from: date
    effective_to: date
    decision_reason: str | None
    evidence_reference: str | None
    created_at: datetime
    updated_at: datetime


class MembershipListResponse(BaseModel):
    items: list[MembershipResponse]
    total: int
