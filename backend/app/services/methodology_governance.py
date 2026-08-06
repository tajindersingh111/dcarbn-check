from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.calculations.formula_language import evaluate_formula
from app.models.methodology import MethodologyStatus, MethodologyVersion
from app.schemas.methodology import MethodologyComparisonResponse, MethodologyImpactPreviewResponse
from app.services.audit import record_audit_event
from app.services.methodologies import execute_golden_tests

COMPARABLE_FIELDS = (
    "name", "scope", "scope_3_category", "jurisdiction", "reporting_year",
    "effective_from", "effective_to", "expression", "output_unit", "input_schema",
    "validation_rules", "golden_tests", "source_reference", "change_reason",
)


def run_methodology_golden_tests(method: MethodologyVersion) -> list[dict[str, str]]:
    return execute_golden_tests(expression=method.expression, golden_tests=method.golden_tests)


def compare_methodology_versions(baseline: MethodologyVersion, candidate: MethodologyVersion) -> MethodologyComparisonResponse:
    changes: dict[str, dict[str, object]] = {}
    for field in COMPARABLE_FIELDS:
        before, after = getattr(baseline, field), getattr(candidate, field)
        if before != after:
            changes[field] = {"baseline": before, "candidate": after}
    return MethodologyComparisonResponse(
        baseline_id=baseline.id, candidate_id=candidate.id,
        same_method_key=baseline.method_key == candidate.method_key,
        changed_fields=changes,
    )


def preview_methodology_impact(
    baseline: MethodologyVersion, candidate: MethodologyVersion, inputs: dict[str, Decimal]
) -> MethodologyImpactPreviewResponse:
    if baseline.method_key != candidate.method_key:
        raise HTTPException(status_code=409, detail="Impact preview requires versions of the same method key.")
    if baseline.output_unit != candidate.output_unit:
        raise HTTPException(status_code=409, detail="Impact preview requires matching output units.")
    required = {
        str(item["name"])
        for method in (baseline, candidate)
        for item in method.input_schema.get("inputs", [])
        if isinstance(item, dict) and item.get("required", True)
    }
    if set(inputs) != required:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Inputs must exactly match: {', '.join(sorted(required))}.",
        )
    baseline_output = evaluate_formula(baseline.expression, inputs)
    candidate_output = evaluate_formula(candidate.expression, inputs)
    absolute_change = candidate_output - baseline_output
    percentage_change = None if baseline_output == 0 else absolute_change / baseline_output * Decimal("100")
    return MethodologyImpactPreviewResponse(
        baseline_id=baseline.id, candidate_id=candidate.id,
        baseline_output=str(baseline_output), candidate_output=str(candidate_output),
        absolute_change=str(absolute_change),
        percentage_change=None if percentage_change is None else str(percentage_change),
        output_unit=baseline.output_unit,
    )


async def retire_methodology_version(
    db: AsyncSession, principal: CurrentPrincipal, method: MethodologyVersion
) -> MethodologyVersion:
    if method.status != MethodologyStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Methodology version must be active.")
    method.status = MethodologyStatus.RETIRED
    method.retired_at = datetime.now(UTC)
    await record_audit_event(
        db, principal, action="methodology_version.retired",
        entity_type="methodology_version", entity_id=method.id,
        event_data={"method_key": method.method_key, "version": method.version, "status": method.status.value},
    )
    await db.commit()
    await db.refresh(method)
    return method
