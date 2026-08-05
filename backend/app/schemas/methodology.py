from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.calculations.formula_language import validate_formula
from app.models.methodology import MethodologyStatus


class MethodologyInputDefinition(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=100)
    unit: str = Field(min_length=1, max_length=100)
    required: bool = True
    minimum: Decimal | None = None
    maximum: Decimal | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "MethodologyInputDefinition":
        if (
            self.minimum is not None
            and self.maximum is not None
            and self.maximum < self.minimum
        ):
            raise ValueError("maximum must be greater than or equal to minimum")
        return self


class MethodologyGoldenTest(BaseModel):
    name: str = Field(min_length=1, max_length=250)
    inputs: dict[str, Decimal]
    expected_output: Decimal
    tolerance: Decimal = Field(default=Decimal("0"), ge=0)


class MethodologyVersionCreate(BaseModel):
    method_key: str = Field(pattern=r"^[a-z0-9_.-]+$", max_length=250)
    name: str = Field(min_length=1, max_length=300)
    scope: str = Field(pattern=r"^scope_[123]$")
    scope_3_category: int | None = Field(default=None, ge=1, le=15)
    jurisdiction: str = Field(default="GB", min_length=2, max_length=20)
    reporting_year: int | None = Field(default=None, ge=1990, le=2200)
    effective_from: date
    effective_to: date | None = None
    expression: str = Field(min_length=1, max_length=5000)
    output_unit: str = Field(min_length=1, max_length=100)
    inputs: list[MethodologyInputDefinition] = Field(min_length=1, max_length=50)
    validation_rules: list[dict[str, object]] = Field(default_factory=list)
    golden_tests: list[MethodologyGoldenTest] = Field(min_length=1, max_length=100)
    source_reference: str = Field(min_length=1, max_length=1000)
    change_reason: str = Field(min_length=20, max_length=5000)
    supersedes_version_id: UUID | None = None

    @model_validator(mode="after")
    def validate_methodology(self) -> "MethodologyVersionCreate":
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be on or after effective_from")
        if self.scope == "scope_3" and self.scope_3_category is None:
            raise ValueError("scope_3_category is required for Scope 3")
        if self.scope != "scope_3" and self.scope_3_category is not None:
            raise ValueError("scope_3_category is only valid for Scope 3")
        names = [item.name for item in self.inputs]
        if len(names) != len(set(names)):
            raise ValueError("input names must be unique")
        validate_formula(self.expression, set(names))
        for test in self.golden_tests:
            if set(test.inputs) != set(names):
                raise ValueError(
                    "each golden test must provide exactly the declared inputs"
                )
        return self


class MethodologyVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    method_key: str
    version: int
    name: str
    status: MethodologyStatus
    scope: str
    scope_3_category: int | None
    jurisdiction: str
    reporting_year: int | None
    effective_from: date
    effective_to: date | None
    expression: str
    output_unit: str
    input_schema: dict[str, object]
    validation_rules: list[dict[str, object]]
    golden_tests: list[dict[str, object]]
    source_reference: str
    change_reason: str
    created_by: str
    submitted_at: datetime | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    approved_by: str | None
    approved_at: datetime | None
    activated_by: str | None
    activated_at: datetime | None
    retired_at: datetime | None
    supersedes_version_id: UUID | None
    created_at: datetime
    updated_at: datetime


class MethodologyVersionListResponse(BaseModel):
    items: list[MethodologyVersionResponse]
    total: int
