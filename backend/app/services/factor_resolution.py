from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.factors.resolution import (
    FactorResolutionCriteria,
    FactorResolutionResult,
    ResolutionOutcome,
    ScoredFactor,
    resolve_factor,
)
from app.models.emission_factor import (
    EmissionFactor,
    EmissionFactorSet,
    FactorSetStatus,
)
from app.models.factor_resolution import FactorResolutionRecord
from app.models.inventory import Inventory
from app.schemas.factor_resolution import (
    FactorCandidateResponse,
    FactorResolutionRequest,
    FactorResolutionResponse,
)
from app.services.audit import record_audit_event
from app.units.registry import UnitConversionError, get_unit_registry


MAX_DATABASE_CANDIDATES = 5000


async def _verify_inventory_tenant(
    db: AsyncSession,
    tenant_id: UUID,
    inventory_id: UUID | None,
) -> None:
    if inventory_id is None:
        return
    query = select(Inventory.id).where(
        Inventory.id == inventory_id,
        Inventory.tenant_id == tenant_id,
    )
    if await db.scalar(query) is None:
        raise HTTPException(status_code=404, detail="Inventory not found.")


async def load_candidate_factors(
    db: AsyncSession,
    request: FactorResolutionRequest,
) -> list[EmissionFactor]:
    query = (
        select(EmissionFactor)
        .join(EmissionFactorSet)
        .where(
            EmissionFactorSet.status == FactorSetStatus.APPROVED,
            EmissionFactor.greenhouse_gas_component
            == request.greenhouse_gas_component,
            EmissionFactor.scope == request.scope,
            EmissionFactor.is_active.is_(True),
        )
    )

    if request.factor_set_id is not None:
        query = query.where(
            EmissionFactor.factor_set_id == request.factor_set_id
        )
    if request.level_1 is not None:
        query = query.where(EmissionFactor.level_1.ilike(request.level_1))
    if not request.allow_previous_year:
        query = query.where(EmissionFactor.reporting_year == request.reporting_year)
    else:
        query = query.where(EmissionFactor.reporting_year <= request.reporting_year)
    if not request.allow_geography_fallback:
        query = query.where(
            EmissionFactor.geography_code == request.geography_code
        )

    query = query.limit(MAX_DATABASE_CANDIDATES)
    return list((await db.scalars(query)).all())


def build_criteria(request: FactorResolutionRequest) -> FactorResolutionCriteria:
    return FactorResolutionCriteria(
        reporting_year=request.reporting_year,
        geography_code=request.geography_code,
        scope=request.scope,
        activity_unit=request.activity_unit,
        level_1=request.level_1,
        level_2=request.level_2,
        level_3=request.level_3,
        level_4=request.level_4,
        column_text=request.column_text,
        lifecycle_boundary=request.lifecycle_boundary,
        greenhouse_gas_component=request.greenhouse_gas_component,
        factor_set_id=request.factor_set_id,
        allow_previous_year=request.allow_previous_year,
        allow_geography_fallback=request.allow_geography_fallback,
    )


def candidate_response(scored: ScoredFactor) -> FactorCandidateResponse:
    resulting_kg_co2e = (
        scored.converted_activity_value * scored.factor.factor_value
    )
    return FactorCandidateResponse(
        factor_id=scored.factor.id,
        source_factor_id=scored.factor.source_factor_id,
        score=scored.score,
        strength=scored.strength,
        reasons=list(scored.reasons),
        warnings=list(scored.warnings),
        factor_value=scored.factor.factor_value,
        factor_activity_unit=scored.factor_activity_unit,
        converted_activity_value=scored.converted_activity_value,
        resulting_kg_co2e=resulting_kg_co2e,
    )


async def resolve_emission_factor(
    db: AsyncSession,
    principal: CurrentPrincipal,
    request: FactorResolutionRequest,
) -> FactorResolutionResponse:
    await _verify_inventory_tenant(
        db,
        principal.tenant_id,
        request.inventory_id,
    )

    registry = get_unit_registry()
    try:
        normalized = registry.normalize(
            request.activity_value,
            request.activity_unit,
        )
    except UnitConversionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    candidates = await load_candidate_factors(db, request)
    result = resolve_factor(
        candidates,
        build_criteria(request),
        request.activity_value,
        registry,
    )

    selected_response = (
        candidate_response(result.selected)
        if result.selected is not None
        else None
    )
    candidate_responses = [
        candidate_response(candidate)
        for candidate in result.candidates
    ]

    record_id = None
    if request.persist:
        record = await persist_resolution(
            db,
            principal,
            request,
            result,
            normalized.normalized_value,
            normalized.normalized_unit,
            candidate_responses,
        )
        record_id = record.id

    return FactorResolutionResponse(
        outcome=result.outcome,
        selected=selected_response,
        candidates=candidate_responses,
        warnings=list(result.warnings),
        normalized_activity_value=normalized.normalized_value,
        normalized_activity_unit=normalized.normalized_unit,
        resolution_record_id=record_id,
    )


async def persist_resolution(
    db: AsyncSession,
    principal: CurrentPrincipal,
    request: FactorResolutionRequest,
    result: FactorResolutionResult,
    normalized_activity_value: Decimal,
    normalized_activity_unit: str,
    candidate_responses: list[FactorCandidateResponse],
) -> FactorResolutionRecord:
    selected = result.selected
    resulting_kg_co2e = (
        selected.converted_activity_value * selected.factor.factor_value
        if selected is not None
        else None
    )

    record = FactorResolutionRecord(
        tenant_id=principal.tenant_id,
        inventory_id=request.inventory_id,
        selected_factor_id=selected.factor.id if selected else None,
        outcome=result.outcome,
        match_strength=selected.strength if selected else None,
        source=request.source,
        original_activity_value=request.activity_value,
        original_activity_unit=request.activity_unit,
        normalized_activity_value=normalized_activity_value,
        normalized_activity_unit=normalized_activity_unit,
        selected_factor_activity_value=(
            selected.converted_activity_value if selected else None
        ),
        selected_factor_activity_unit=(
            selected.factor_activity_unit if selected else None
        ),
        selected_factor_value=(
            selected.factor.factor_value if selected else None
        ),
        resulting_kg_co2e=resulting_kg_co2e,
        selected_score=selected.score if selected else None,
        criteria=request.model_dump(mode="json", exclude={"persist"}),
        candidate_summary=[
            candidate.model_dump(mode="json")
            for candidate in candidate_responses[:20]
        ],
        warnings=list(result.warnings),
        resolution_reason=(
            "Deterministic highest-scoring approved factor."
            if result.outcome == ResolutionOutcome.RESOLVED
            else None
        ),
        resolved_by=principal.subject,
    )
    db.add(record)
    await db.flush()

    await record_audit_event(
        db,
        principal,
        action="emission_factor.resolved",
        entity_type="factor_resolution_record",
        entity_id=record.id,
        event_data={
            "outcome": result.outcome.value,
            "selected_factor_id": (
                str(selected.factor.id) if selected is not None else None
            ),
            "warnings": list(result.warnings),
        },
    )
    await db.commit()
    await db.refresh(record)
    return record


async def get_resolution_record(
    db: AsyncSession,
    tenant_id: UUID,
    resolution_record_id: UUID,
) -> FactorResolutionRecord | None:
    query = select(FactorResolutionRecord).where(
        FactorResolutionRecord.id == resolution_record_id,
        FactorResolutionRecord.tenant_id == tenant_id,
    )
    record: FactorResolutionRecord | None = await db.scalar(query)
    return record
