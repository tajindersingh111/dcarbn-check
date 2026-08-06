from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.data_review import DataReviewStatus


class DataReviewStartRequest(BaseModel):
    inventory_id: UUID
    reviewer_comment: str | None = Field(default=None, max_length=5000)


class DataReviewDecisionRequest(BaseModel):
    decision: DataReviewStatus
    reviewer_comment: str | None = Field(default=None, max_length=5000)
    rejection_reason: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def validate_decision(self) -> "DataReviewDecisionRequest":
        if self.decision not in {
            DataReviewStatus.APPROVED,
            DataReviewStatus.REJECTED,
        }:
            raise ValueError("decision must be approved or rejected")
        if (
            self.decision == DataReviewStatus.REJECTED
            and not self.rejection_reason
        ):
            raise ValueError("rejection_reason is required when rejecting")
        return self


class DataReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    operational_emission_id: UUID
    inventory_id: UUID | None
    status: DataReviewStatus
    reviewer_id: str | None
    review_started_at: datetime | None
    reviewed_at: datetime | None
    converted_at: datetime | None
    reviewer_comment: str | None
    rejection_reason: str | None
    conversion_failure: str | None
    calculation_run_id: UUID | None
    calculation_result_id: UUID | None
    activity_id: UUID | None
    review_snapshot: dict[str, object]
    created_at: datetime
    updated_at: datetime


class DataReviewQueueItem(BaseModel):
    review: DataReviewResponse
    external_calculation_id: str
    external_customer_id: str | None
    organisation_id: UUID
    suggested_scope: str | None
    suggested_scope_3_category: int | None
    confirmed_scope: str | None
    confirmed_scope_3_category: int | None
    methodology_version: str
    total_kg_co2e: str
    data_quality_level: str | None
    data_quality_score: int | None
    calculated_at: datetime


class DataReviewQueueResponse(BaseModel):
    items: list[DataReviewQueueItem]
    total: int
    limit: int
    offset: int


class DataConversionResponse(BaseModel):
    review: DataReviewResponse
    activity_id: UUID
    calculation_run_id: UUID
    calculation_result_id: UUID
    comparison_id: UUID
