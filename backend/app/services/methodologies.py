from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.calculations.formula_language import (
    FormulaValidationError,
    evaluate_formula,
)
from app.models.methodology import MethodologyStatus, MethodologyVersion
from app.schemas.methodology import MethodologyVersionCreate
from app.services.audit import record_audit_event


def execute_golden_tests(
    *,
    expression: str,
    golden_tests: list[dict[str, object]],
) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for test in golden_tests:
        name = str(test["name"])
        raw_inputs = test["inputs"]
        if not isinstance(raw_inputs, dict):
            raise FormulaValidationError(f"Golden test {name!r} inputs are invalid.")
        inputs = {
            str(key): Decimal(str(value))
            for key, value in raw_inputs.items()
        }
        actual = evaluate_formula(expression, inputs)
        expected = Decimal(str(test["expected_output"]))
        tolerance = Decimal(str(test.get("tolerance", "0")))
        difference = abs(actual - expected)
        if difference > tolerance:
            raise FormulaValidationError(
                f"Golden test {name!r} failed: expected {expected}, got {actual}."
            )
        results.append(
            {
                "name": name,
                "actual": str(actual),
                "expected": str(expected),
                "tolerance": str(tolerance),
            }
        )
    return results


async def create_methodology_version(
    db: AsyncSession,
    principal: CurrentPrincipal,
    payload: MethodologyVersionCreate,
) -> MethodologyVersion:
    latest = await db.scalar(
        select(func.coalesce(func.max(MethodologyVersion.version), 0)).where(
            MethodologyVersion.method_key == payload.method_key
        )
    )
    next_version = int(latest or 0) + 1
    golden_tests = payload.model_dump(mode="json")["golden_tests"]
    assert isinstance(golden_tests, list)
    execute_golden_tests(
        expression=payload.expression,
        golden_tests=golden_tests,
    )
    method = MethodologyVersion(
        method_key=payload.method_key,
        version=next_version,
        name=payload.name,
        status=MethodologyStatus.DRAFT,
        scope=payload.scope,
        scope_3_category=payload.scope_3_category,
        jurisdiction=payload.jurisdiction,
        reporting_year=payload.reporting_year,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        expression=payload.expression,
        output_unit=payload.output_unit,
        input_schema={
            "inputs": [
                item.model_dump(mode="json")
                for item in payload.inputs
            ]
        },
        validation_rules=payload.validation_rules,
        golden_tests=golden_tests,
        source_reference=payload.source_reference,
        change_reason=payload.change_reason,
        created_by=principal.subject,
        supersedes_version_id=payload.supersedes_version_id,
    )
    db.add(method)
    await db.flush()
    await record_audit_event(
        db,
        principal,
        action="methodology_version.created",
        entity_type="methodology_version",
        entity_id=method.id,
        event_data={
            "method_key": method.method_key,
            "version": method.version,
        },
    )
    await db.commit()
    await db.refresh(method)
    return method


async def list_methodology_versions(
    db: AsyncSession,
    *,
    method_key: str | None = None,
    status_filter: MethodologyStatus | None = None,
) -> list[MethodologyVersion]:
    query = select(MethodologyVersion)
    if method_key is not None:
        query = query.where(MethodologyVersion.method_key == method_key)
    if status_filter is not None:
        query = query.where(MethodologyVersion.status == status_filter)
    query = query.order_by(
        MethodologyVersion.method_key,
        MethodologyVersion.version.desc(),
    )
    return list((await db.scalars(query)).all())


async def get_methodology_version(
    db: AsyncSession,
    methodology_id: UUID,
) -> MethodologyVersion | None:
    return await db.get(MethodologyVersion, methodology_id)


async def submit_methodology_version(
    db: AsyncSession,
    principal: CurrentPrincipal,
    method: MethodologyVersion,
) -> MethodologyVersion:
    _require_status(method, MethodologyStatus.DRAFT)
    method.status = MethodologyStatus.IN_REVIEW
    method.submitted_at = datetime.now(UTC)
    return await _commit_transition(
        db,
        principal,
        method,
        "methodology_version.submitted",
    )


async def review_methodology_version(
    db: AsyncSession,
    principal: CurrentPrincipal,
    method: MethodologyVersion,
) -> MethodologyVersion:
    _require_status(method, MethodologyStatus.IN_REVIEW)
    if method.created_by == principal.subject:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The methodology creator cannot review their own version.",
        )
    if method.reviewed_by is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The methodology version has already been reviewed.",
        )
    execute_golden_tests(
        expression=method.expression,
        golden_tests=method.golden_tests,
    )
    method.reviewed_by = principal.subject
    method.reviewed_at = datetime.now(UTC)
    return await _commit_transition(
        db,
        principal,
        method,
        "methodology_version.reviewed",
    )


async def approve_methodology_version(
    db: AsyncSession,
    principal: CurrentPrincipal,
    method: MethodologyVersion,
) -> MethodologyVersion:
    _require_status(method, MethodologyStatus.IN_REVIEW)
    if method.created_by == principal.subject:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The methodology creator cannot approve their own version.",
        )
    if method.reviewed_by is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The methodology version must be reviewed before approval.",
        )
    if method.reviewed_by == principal.subject:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The methodology reviewer cannot approve the same version.",
        )
    execute_golden_tests(
        expression=method.expression,
        golden_tests=method.golden_tests,
    )
    method.status = MethodologyStatus.APPROVED
    method.approved_by = principal.subject
    method.approved_at = datetime.now(UTC)
    return await _commit_transition(
        db,
        principal,
        method,
        "methodology_version.approved",
    )


async def activate_methodology_version(
    db: AsyncSession,
    principal: CurrentPrincipal,
    method: MethodologyVersion,
) -> MethodologyVersion:
    _require_status(method, MethodologyStatus.APPROVED)
    execute_golden_tests(
        expression=method.expression,
        golden_tests=method.golden_tests,
    )
    active = await db.scalar(
        select(MethodologyVersion).where(
            MethodologyVersion.method_key == method.method_key,
            MethodologyVersion.status == MethodologyStatus.ACTIVE,
        )
    )
    now = datetime.now(UTC)
    if active is not None:
        active.status = MethodologyStatus.SUPERSEDED
        active.retired_at = now
        method.supersedes_version_id = active.id
    method.status = MethodologyStatus.ACTIVE
    method.activated_by = principal.subject
    method.activated_at = now
    return await _commit_transition(
        db,
        principal,
        method,
        "methodology_version.activated",
        {"superseded_version_id": str(active.id) if active else None},
    )


def _require_status(
    method: MethodologyVersion,
    expected: MethodologyStatus,
) -> None:
    if method.status != expected:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Methodology version must be {expected.value}.",
        )


async def _commit_transition(
    db: AsyncSession,
    principal: CurrentPrincipal,
    method: MethodologyVersion,
    action: str,
    extra: dict[str, object] | None = None,
) -> MethodologyVersion:
    await record_audit_event(
        db,
        principal,
        action=action,
        entity_type="methodology_version",
        entity_id=method.id,
        event_data={
            "method_key": method.method_key,
            "version": method.version,
            "status": method.status.value,
            **(extra or {}),
        },
    )
    await db.commit()
    await db.refresh(method)
    return method
