from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from app.auth.dependencies import CurrentPrincipal
from app.calculations.engine import calculate_activity_factor_emissions, kg_to_tonnes
from app.calculations.governed_methods import (
    METHODS,
    GovernedCalculationMethod,
)
from app.factors.resolution import (
    FactorResolutionCriteria,
    ResolutionOutcome,
    resolve_factor,
)
from app.models.activity import (
    ActivityRecord,
    ActivityStatus,
    EmissionScope,
    Scope2Method,
)
from app.models.calculation import (
    CalculationMethod,
    CalculationResult,
    CalculationRun,
    CalculationRunStatus,
)
from app.models.emission_factor import (
    EmissionFactor,
    EmissionFactorSet,
    FactorSetStatus,
    GreenhouseGasComponent,
)
from app.models.factor_resolution import (
    FactorResolutionRecord,
    ResolutionSource,
)
from app.models.inventory import InventoryStatus
from app.schemas.calculation import (
    CalculationRunCreate,
    InventoryCalculationSummary,
    InventoryScopeSummaryItem,
    Scope2HeadlineBasis,
)
from app.services.activities import get_inventory
from app.services.audit import record_audit_event
from app.units.registry import get_unit_registry
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def create_and_execute_calculation_run(
    db: AsyncSession,
    principal: CurrentPrincipal,
    inventory_id: UUID,
    payload: CalculationRunCreate,
) -> CalculationRun:
    inventory = await get_inventory(db, principal.tenant_id, inventory_id)
    if inventory.status in {
        InventoryStatus.APPROVED,
        InventoryStatus.LOCKED,
        InventoryStatus.SUPERSEDED,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The inventory cannot be recalculated in its current state.",
        )

    version_query = select(func.coalesce(func.max(CalculationRun.version), 0)).where(
        CalculationRun.inventory_id == inventory_id
    )
    next_version = int((await db.scalar(version_query)) or 0) + 1

    activities = list(
        (
            await db.scalars(
                select(ActivityRecord).where(
                    ActivityRecord.inventory_id == inventory_id,
                    ActivityRecord.tenant_id == principal.tenant_id,
                    ActivityRecord.is_current.is_(True),
                    ActivityRecord.status.in_(
                        [ActivityStatus.VALIDATED, ActivityStatus.CALCULATED]
                    ),
                )
            )
        ).all()
    )
    if not activities:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No validated activities are available for calculation.",
        )

    run = CalculationRun(
        tenant_id=principal.tenant_id,
        inventory_id=inventory_id,
        version=next_version,
        status=CalculationRunStatus.RUNNING,
        software_version=payload.software_version,
        factor_policy_version=payload.factor_policy_version,
        started_at=datetime.now(UTC),
        activity_count=len(activities),
    )
    db.add(run)
    inventory.status = InventoryStatus.CALCULATING
    await db.flush()

    failed_messages: list[str] = []
    for activity in activities:
        try:
            await calculate_activity(
                db,
                principal,
                run,
                activity,
                allow_previous_year=payload.allow_previous_year,
                allow_geography_fallback=payload.allow_geography_fallback,
            )
            activity.status = ActivityStatus.CALCULATED
            run.result_count += 1
        except ValueError as exc:
            run.failed_count += 1
            failed_messages.append(f"{activity.id}: {exc}")

    run.completed_at = datetime.now(UTC)
    if run.failed_count:
        run.status = CalculationRunStatus.FAILED
        run.failure_message = "\n".join(failed_messages)
        inventory.status = InventoryStatus.CALCULATION_FAILED
    else:
        run.status = CalculationRunStatus.COMPLETED
        inventory.status = InventoryStatus.REVIEW_REQUIRED

    await record_audit_event(
        db,
        principal,
        action="calculation_run.completed",
        entity_type="calculation_run",
        entity_id=run.id,
        event_data={
            "version": run.version,
            "activity_count": run.activity_count,
            "result_count": run.result_count,
            "failed_count": run.failed_count,
            "status": run.status.value,
        },
    )
    await db.commit()
    await db.refresh(run)
    return run


async def calculate_activity(
    db: AsyncSession,
    principal: CurrentPrincipal,
    run: CalculationRun,
    activity: ActivityRecord,
    *,
    allow_previous_year: bool,
    allow_geography_fallback: bool,
) -> CalculationResult:
    raw_method = activity.metadata_json.get("calculation_method_id")
    if isinstance(raw_method, str):
        try:
            governed_method = GovernedCalculationMethod(raw_method)
        except ValueError:
            governed_method = None
        if (
            governed_method is not None
            and METHODS[governed_method].direct_reported_result
        ):
            return _record_supplier_specific_result(
                db, principal, run, activity, governed_method
            )

    factor_query = (
        select(EmissionFactor)
        .join(EmissionFactorSet)
        .where(
            EmissionFactorSet.status == FactorSetStatus.APPROVED,
            EmissionFactor.scope == _factor_scope_label(activity.scope),
            EmissionFactor.greenhouse_gas_component
            == GreenhouseGasComponent.TOTAL_CO2E,
            EmissionFactor.is_active.is_(True),
        )
    )
    if not allow_previous_year:
        factor_query = factor_query.where(
            EmissionFactor.reporting_year == _reporting_year(activity)
        )
    else:
        factor_query = factor_query.where(
            EmissionFactor.reporting_year <= _reporting_year(activity)
        )
    if not allow_geography_fallback:
        factor_query = factor_query.where(
            EmissionFactor.geography_code == activity.geography_code
        )

    candidates = list((await db.scalars(factor_query.limit(5000))).all())
    criteria = FactorResolutionCriteria(
        reporting_year=_reporting_year(activity),
        geography_code=activity.geography_code,
        scope=_factor_scope_label(activity.scope),
        activity_unit=activity.activity_unit,
        level_1=activity.factor_level_1,
        level_2=activity.factor_level_2,
        level_3=activity.factor_level_3,
        level_4=activity.factor_level_4,
        column_text=activity.factor_column_text,
        lifecycle_boundary=activity.lifecycle_boundary,
        greenhouse_gas_component=GreenhouseGasComponent.TOTAL_CO2E,
        allow_previous_year=allow_previous_year,
        allow_geography_fallback=allow_geography_fallback,
    )
    resolution = resolve_factor(
        candidates,
        criteria,
        activity.activity_value,
        get_unit_registry(),
    )
    if resolution.outcome != ResolutionOutcome.RESOLVED or resolution.selected is None:
        raise ValueError(
            f"Factor resolution failed with outcome {resolution.outcome.value}."
        )

    selected = resolution.selected
    resolution_record = FactorResolutionRecord(
        tenant_id=principal.tenant_id,
        inventory_id=activity.inventory_id,
        selected_factor_id=selected.factor.id,
        outcome=resolution.outcome,
        match_strength=selected.strength,
        source=ResolutionSource.CALCULATION_ENGINE,
        original_activity_value=activity.activity_value,
        original_activity_unit=activity.activity_unit,
        normalized_activity_value=activity.normalized_value,
        normalized_activity_unit=activity.normalized_unit,
        selected_factor_activity_value=selected.converted_activity_value,
        selected_factor_activity_unit=selected.factor_activity_unit,
        selected_factor_value=selected.factor.factor_value,
        resulting_kg_co2e=(
            selected.converted_activity_value * selected.factor.factor_value
        ),
        selected_score=selected.score,
        criteria={
            "reporting_year": criteria.reporting_year,
            "geography_code": criteria.geography_code,
            "scope": criteria.scope,
            "activity_unit": criteria.activity_unit,
            "level_1": criteria.level_1,
            "level_2": criteria.level_2,
            "level_3": criteria.level_3,
            "level_4": criteria.level_4,
            "column_text": criteria.column_text,
            "lifecycle_boundary": criteria.lifecycle_boundary,
        },
        candidate_summary=[
            {
                "factor_id": str(candidate.factor.id),
                "score": candidate.score,
                "source_factor_id": candidate.factor.source_factor_id,
            }
            for candidate in resolution.candidates[:20]
        ],
        warnings=list(resolution.warnings),
        resolution_reason="Deterministic highest-scoring approved factor.",
        resolved_by=principal.subject,
    )
    db.add(resolution_record)
    await db.flush()

    calculation = calculate_activity_factor_emissions(
        factor_activity_value=selected.converted_activity_value,
        factor_value=selected.factor.factor_value,
        allocation_percentage=activity.allocation_percentage,
    )

    result = CalculationResult(
        tenant_id=principal.tenant_id,
        calculation_run_id=run.id,
        activity_id=activity.id,
        factor_resolution_record_id=resolution_record.id,
        selected_factor_id=selected.factor.id,
        method=CalculationMethod.ACTIVITY_FACTOR,
        scope=activity.scope,
        scope_3_category=activity.scope_3_category,
        scope_2_method=activity.scope_2_method,
        original_activity_value=activity.activity_value,
        original_activity_unit=activity.activity_unit,
        factor_activity_value=calculation.factor_activity_value,
        factor_activity_unit=selected.factor_activity_unit,
        factor_value=calculation.factor_value,
        allocation_percentage=calculation.allocation_percentage,
        allocation_multiplier=calculation.allocation_multiplier,
        gross_kg_co2e=calculation.gross_kg_co2e,
        allocated_kg_co2e=calculation.allocated_kg_co2e,
        calculation_formula=calculation.formula,
        intermediate_values={
            "factor_score": selected.score,
            "factor_source_id": selected.factor.source_factor_id,
            "factor_reporting_year": selected.factor.reporting_year,
            "factor_geography": selected.factor.geography_code,
        },
        warnings=list(resolution.warnings),
        methodology_version=run.factor_policy_version,
    )
    db.add(result)
    return result


def _record_supplier_specific_result(
    db: AsyncSession,
    principal: CurrentPrincipal,
    run: CalculationRun,
    activity: ActivityRecord,
    governed_method: GovernedCalculationMethod,
) -> CalculationResult:
    """Record an evidence-backed supplier result without inventing a generic factor."""
    calculation = calculate_activity_factor_emissions(
        factor_activity_value=activity.activity_value,
        factor_value=Decimal(1),
        allocation_percentage=activity.allocation_percentage,
    )
    metadata = activity.metadata_json
    result = CalculationResult(
        tenant_id=principal.tenant_id,
        calculation_run_id=run.id,
        activity_id=activity.id,
        factor_resolution_record_id=None,
        selected_factor_id=None,
        method=CalculationMethod.SUPPLIER_SPECIFIC_RESULT,
        scope=activity.scope,
        scope_3_category=activity.scope_3_category,
        scope_2_method=activity.scope_2_method,
        original_activity_value=activity.activity_value,
        original_activity_unit=activity.activity_unit,
        factor_activity_value=calculation.factor_activity_value,
        factor_activity_unit="kgCO2e",
        factor_value=calculation.factor_value,
        allocation_percentage=calculation.allocation_percentage,
        allocation_multiplier=calculation.allocation_multiplier,
        gross_kg_co2e=calculation.gross_kg_co2e,
        allocated_kg_co2e=calculation.allocated_kg_co2e,
        calculation_formula=("supplier_reported_kg_co2e × allocation_percentage / 100"),
        intermediate_values={
            "calculation_method_id": governed_method.value,
            "supplier_name": metadata["supplier_name"],
            "supplier_methodology": metadata["supplier_methodology"],
            "supplier_methodology_version": metadata["supplier_methodology_version"],
            "supplier_reporting_period": metadata["supplier_reporting_period"],
            "boundary_description": metadata["boundary_description"],
            "assurance_status": metadata["assurance_status"],
            "evidence_reference": activity.evidence_reference,
        },
        warnings=(
            []
            if metadata["assurance_status"] == "third_party_verified"
            else ["supplier_specific_result_requires_independent_review"]
        ),
        methodology_version=str(metadata["supplier_methodology_version"]),
    )
    db.add(result)
    return result


async def get_calculation_run(
    db: AsyncSession,
    tenant_id: UUID,
    run_id: UUID,
) -> CalculationRun | None:
    query = select(CalculationRun).where(
        CalculationRun.id == run_id,
        CalculationRun.tenant_id == tenant_id,
    )
    run: CalculationRun | None = await db.scalar(query)
    return run


async def list_calculation_results(
    db: AsyncSession,
    tenant_id: UUID,
    run_id: UUID,
    *,
    limit: int | None = None,
    offset: int = 0,
) -> list[CalculationResult]:
    query = (
        select(CalculationResult)
        .where(
            CalculationResult.calculation_run_id == run_id,
            CalculationResult.tenant_id == tenant_id,
        )
        .order_by(
            CalculationResult.created_at,
            CalculationResult.id,
        )
        .offset(offset)
    )
    if limit is not None:
        query = query.limit(limit)
    return list((await db.scalars(query)).all())


async def count_calculation_results(
    db: AsyncSession,
    tenant_id: UUID,
    run_id: UUID,
) -> int:
    count = await db.scalar(
        select(func.count(CalculationResult.id)).where(
            CalculationResult.calculation_run_id == run_id,
            CalculationResult.tenant_id == tenant_id,
        )
    )
    return int(count or 0)


async def summarize_calculation_run(
    db: AsyncSession,
    tenant_id: UUID,
    run_id: UUID,
    scope_2_headline_basis: Scope2HeadlineBasis,
) -> InventoryCalculationSummary:
    run = await get_calculation_run(db, tenant_id, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Calculation run not found.")

    results = await list_calculation_results(db, tenant_id, run_id)
    grouped: dict[tuple[EmissionScope, int | None, Scope2Method], Decimal] = {}
    for result in results:
        key = (result.scope, result.scope_3_category, result.scope_2_method)
        grouped[key] = grouped.get(key, Decimal(0)) + result.allocated_kg_co2e

    items = [
        InventoryScopeSummaryItem(
            scope=scope,
            scope_3_category=category,
            scope_2_method=scope_2_method,
            kg_co2e=value,
            t_co2e=kg_to_tonnes(value),
        )
        for (scope, category, scope_2_method), value in sorted(
            grouped.items(),
            key=lambda item: (
                item[0][0].value,
                item[0][1] or 0,
                item[0][2].value,
            ),
        )
    ]
    totals = calculate_inventory_totals(items, scope_2_headline_basis)
    return InventoryCalculationSummary(
        calculation_run_id=run.id,
        inventory_id=run.inventory_id,
        scope_2_headline_basis=scope_2_headline_basis,
        scope_1_kg_co2e=totals["scope_1"],
        scope_2_location_based_kg_co2e=totals["scope_2_location_based"],
        scope_2_market_based_kg_co2e=totals["scope_2_market_based"],
        scope_3_kg_co2e=totals["scope_3"],
        total_kg_co2e=totals["headline_total"],
        total_t_co2e=kg_to_tonnes(totals["headline_total"]),
        items=items,
    )


def calculate_inventory_totals(
    items: list[InventoryScopeSummaryItem],
    scope_2_headline_basis: Scope2HeadlineBasis,
) -> dict[str, Decimal]:
    """Return disclosed scope totals and one non-double-counted corporate total."""
    zero = Decimal(0)
    scope_1 = sum(
        (item.kg_co2e for item in items if item.scope == EmissionScope.SCOPE_1),
        zero,
    )
    scope_2_location_based = sum(
        (
            item.kg_co2e
            for item in items
            if item.scope == EmissionScope.SCOPE_2
            and item.scope_2_method == Scope2Method.LOCATION_BASED
        ),
        zero,
    )
    scope_2_market_based = sum(
        (
            item.kg_co2e
            for item in items
            if item.scope == EmissionScope.SCOPE_2
            and item.scope_2_method == Scope2Method.MARKET_BASED
        ),
        zero,
    )
    scope_3 = sum(
        (item.kg_co2e for item in items if item.scope == EmissionScope.SCOPE_3),
        zero,
    )
    selected_scope_2 = (
        scope_2_location_based
        if scope_2_headline_basis == Scope2HeadlineBasis.LOCATION_BASED
        else scope_2_market_based
    )
    return {
        "scope_1": scope_1,
        "scope_2_location_based": scope_2_location_based,
        "scope_2_market_based": scope_2_market_based,
        "scope_3": scope_3,
        "headline_total": scope_1 + selected_scope_2 + scope_3,
    }


def _factor_scope_label(scope: EmissionScope) -> str:
    return {
        EmissionScope.SCOPE_1: "Scope 1",
        EmissionScope.SCOPE_2: "Scope 2",
        EmissionScope.SCOPE_3: "Scope 3",
    }[scope]


def _reporting_year(activity: ActivityRecord) -> int:
    return activity.activity_date.year
