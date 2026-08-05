from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.inventory_governance import Scope3CategoryDispositionStatus


class Scope3CategoryDispositionInput(BaseModel):
    category: int = Field(ge=1, le=15)
    disposition: Scope3CategoryDispositionStatus
    rationale: str = Field(min_length=20, max_length=5000)
    evidence_reference: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def require_exclusion_evidence(self) -> "Scope3CategoryDispositionInput":
        if (
            self.disposition == Scope3CategoryDispositionStatus.EXCLUDED
            and not self.evidence_reference
        ):
            raise ValueError("excluded categories require an evidence reference")
        return self


class Scope3CategoryDispositionSet(BaseModel):
    items: list[Scope3CategoryDispositionInput] = Field(min_length=15, max_length=15)

    @model_validator(mode="after")
    def require_all_categories(self) -> "Scope3CategoryDispositionSet":
        categories = [item.category for item in self.items]
        if sorted(categories) != list(range(1, 16)):
            raise ValueError("exactly one decision is required for each category 1-15")
        return self


class Scope3CategoryDispositionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    inventory_id: UUID
    category: int
    disposition: Scope3CategoryDispositionStatus
    rationale: str
    evidence_reference: str | None
    prepared_by: str
    prepared_at: datetime
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class Scope3CategoryDispositionListResponse(BaseModel):
    items: list[Scope3CategoryDispositionResponse]
    total: int
    complete: bool
    approved: bool
