from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.calculations.engine import calculate_activity_factor_emissions
from app.calculations.governed_methods import (
    METHODS,
    GovernedCalculationMethod,
)
from app.factors.resolution import (
    FactorResolutionCriteria,
    ResolutionOutcome,
    resolve_factor,
)
from app.models.activity import EmissionScope, Scope2Method
from app.models.calculation import (
    CalculationMethod,
    CalculationResult,
    CalculationRun,
    CalculationRunStatus,
)
from app.models.data_integration import (
    DataCalculationComparison,
    DataComparisonStatus,
    DataOperationalEmission,
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
from app.services.audit import record_audit_event
from app.units.registry import get_unit_registry


COMPARISON_WARNING = "comparison_only_not_included_in_inventory_totals"


def calculate_comparison_delta(
    dcarbn_kg_co2e: Decimal,
    government_kg_co2e: Decimal,
) -> tuple[Decimal, Decimal | None]:
    absolute = dcarbn_kg_co2e - government_kg_co2e
    percentage = (
        (absolute / government_kg_co2e) * Decimal("100")
        if government_kg_co2e != 0
        else None
    )
    return absolute, percentage


def _scope_label(scope: EmissionScope) -> str:
    return {
        EmissionScope.SCOPE_1: "Scope 1",
        EmissionScope.SCOPE_2: "Scope 2",
        EmissionScope.SCOPE_3: "Scope 3",
    }[scope]


def _parse_scope(value: str | None) -> EmissionScope:
    normalized = (value or "").strip().lower().replace(" ", "_")
    try:
        return {
            "scope_1": EmissionScope.SCOPE_1,
            "scope1": EmissionScope.SCOPE_1,
            "scope_2": EmissionScope.SCOPE_2,
            "scope2": EmissionScope.SCOPE_2,
            "scope_3": EmissionScope.SCOPE_3,
            "scope3": EmissionScope.SCOPE_3,
        }[normalized]
    except KeyError as exc:
        raise ValueError("The DcarbN result has no supported confirmed scope.") from exc


def _comparison_inputs(
    emission: DataOperationalEmission,
) -> tuple[GovernedCalculationMethod, Decimal, str]:
    raw = emission.comparison_inputs_json
    method_id = raw.get("government_method_id")
    activity_value = raw.get("activity_value")
    activity_unit = raw.get("activity_unit")
    if not isinstance(method_id, str):
        raise ValueError("comparison_inputs.government_method_id is required.")
    if not isinstance(activity_unit, str):
        raise ValueError("comparison_inputs.activity_unit is required.")
    try:
        method = GovernedCalculationMethod(method_id)
        value = Decimal(str(activity_value))
    except (ValueError, InvalidOperation) as exc:
        raise ValueError("The Government comparison method or activity value is invalid.") from exc
    if value < 0:
        raise ValueError("The Government comparison activity value cannot be negative.")
    specification = METHODS[method]
    if activity_unit != specification.activity_unit:
        raise ValueError(
            f"comparison activity_unit must be {specification.activity_unit}."
        )
    scope = _parse_scope(emission.confirmed_scope)
    if scope != specification.scope:
        raise ValueError("The Government method does not match the confirmed scope.")
    if emission.confirmed_scope_3_category != specification.scope_3_category:
        raise ValueError(
            "The Government method does not match the confirmed Scope 3 category."
        )
    return method, value, activity_unit


async def generate_government_comparator(
    db: AsyncSession,
    principal: CurrentPrincipal,
    comparison_id: UUID,
) -> DataCalculationComparison:
    comparison = await db.scalar(
        select(DataCalculationComparison).where(
            DataCalculationComparison.id == comparison_id,
            DataCalculationComparison.tenant_id == principal.tenant_id,
        )
    )
    if comparison is None:
        raise HTTPException(status_code=404, detail="Calculation comparison not found.")
    if comparison.status == DataComparisonStatus.READY:
        return comparison

    emission = await db.scalar(
        select(DataOperationalEmission).where(
            DataOperationalEmission.id == comparison.operational_emission_id,
            DataOperationalEmission.tenant_id == principal.tenant_id,
        )
    )
    if emission is None or comparison.dcarbn_result_id is None:
        return await _mark_unavailable(
            db,
            principal,
            comparison,
            "The comparison is missing its DcarbN source result.",
        )
    dcarbn_result = await db.scalar(
        select(CalculationResult).where(
            CalculationResult.id == comparison.dcarbn_result_id,
            CalculationResult.tenant_id == principal.tenant_id,
        )
    )
    if dcarbn_result is None:
        return await _mark_unavailable(
            db,
            principal,
            comparison,
            "The linked DcarbN calculation result was not found.",
        )
    dcarbn_run = await db.scalar(
        select(CalculationRun).where(
            CalculationRun.id == dcarbn_result.calculation_run_id,
            CalculationRun.tenant_id == principal.tenant_id,
        )
    )
    if dcarbn_run is None:
        return await _mark_unavailable(
            db,
            principal,
            comparison,
            "The linked DcarbN calculation run was not found.",
        )

    try:
        method, activity_value, activity_unit = _comparison_inputs(emission)
        specification = METHODS[method]
        reporting_year = emission.calculated_at.year
        query = (
            select(EmissionFactor)
            .join(EmissionFactorSet)
            .where(
                EmissionFactorSet.status == FactorSetStatus.APPROVED,
                EmissionFactor.scope == _scope_label(specification.scope),
                EmissionFactor.reporting_year == reporting_year,
                EmissionFactor.geography_code == "GB",
                EmissionFactor.greenhouse_gas_component
                == GreenhouseGasComponent.TOTAL_CO2E,
                EmissionFactor.is_active.is_(True),
            )
        )
        candidates = list((await db.scalars(query.limit(5000))).all())
        criteria = FactorResolutionCriteria(
            reporting_year=reporting_year,
            geography_code="GB",
            scope=_scope_label(specification.scope),
            activity_unit=activity_unit,
            level_1=specification.factor_level_1,
            level_2=specification.factor_level_2,
            level_3=specification.factor_level_3,
            level_4=specification.factor_level_4,
            column_text=specification.factor_column_text,
            lifecycle_boundary=specification.lifecycle_boundary,
            greenhouse_gas_component=GreenhouseGasComponent.TOTAL_CO2E,
            allow_previous_year=False,
            allow_geography_fallback=False,
        )
        resolution = resolve_factor(
            candidates,
            criteria,
            activity_value,
            get_unit_registry(),
        )
        if (
            resolution.outcome != ResolutionOutcome.RESOLVED
            or resolution.selected is None
        ):
            raise ValueError(
                "No unique approved UK Government factor matches the supplied "
                f"activity ({resolution.outcome.value})."
            )
        selected = resolution.selected
        calculation = calculate_activity_factor_emissions(
            factor_activity_value=selected.converted_activity_value,
            factor_value=selected.factor.factor_value,
            allocation_percentage=Decimal("100"),
        )

        next_version = int(
            (
                await db.scalar(
                    select(func.coalesce(func.max(CalculationRun.version), 0)).where(
                        CalculationRun.inventory_id == dcarbn_run.inventory_id
                    )
                )
            )
            or 0
        ) + 1
        now = datetime.now(UTC)
        comparator_run = CalculationRun(
            tenant_id=principal.tenant_id,
            inventory_id=dcarbn_run.inventory_id,
            version=next_version,
            status=CalculationRunStatus.SUPERSEDED,
            software_version="0.1.0",
            factor_policy_version="UK-Government-comparator-v1",
            started_at=now,
            completed_at=now,
            activity_count=1,
            result_count=1,
            failed_count=0,
        )
        db.add(comparator_run)
        await db.flush()

        resolution_record = FactorResolutionRecord(
            tenant_id=principal.tenant_id,
            inventory_id=dcarbn_run.inventory_id,
            selected_factor_id=selected.factor.id,
            outcome=resolution.outcome,
            match_strength=selected.strength,
            source=ResolutionSource.CALCULATION_ENGINE,
            original_activity_value=activity_value,
            original_activity_unit=activity_unit,
            normalized_activity_value=activity_value,
            normalized_activity_unit=activity_unit,
            selected_factor_activity_value=selected.converted_activity_value,
            selected_factor_activity_unit=selected.factor_activity_unit,
            selected_factor_value=selected.factor.factor_value,
            resulting_kg_co2e=calculation.allocated_kg_co2e,
            selected_score=selected.score,
            criteria={
                "governed_method_id": method.value,
                "reporting_year": reporting_year,
                "geography_code": "GB",
                "scope": criteria.scope,
                "activity_unit": activity_unit,
                "level_1": specification.factor_level_1,
                "level_2": specification.factor_level_2,
                "level_3": specification.factor_level_3,
                "level_4": specification.factor_level_4,
                "column_text": specification.factor_column_text,
                "lifecycle_boundary": specification.lifecycle_boundary,
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
            resolution_reason=(
                "Exact governed UK Government method resolved against an "
                "approved factor set."
            ),
            resolved_by=principal.subject,
        )
        db.add(resolution_record)
        await db.flush()

        government_result = CalculationResult(
            tenant_id=principal.tenant_id,
            calculation_run_id=comparator_run.id,
            activity_id=dcarbn_result.activity_id,
            factor_resolution_record_id=resolution_record.id,
            selected_factor_id=selected.factor.id,
            method=CalculationMethod.ACTIVITY_FACTOR,
            scope=specification.scope,
            scope_3_category=specification.scope_3_category,
            scope_2_method=Scope2Method.NOT_APPLICABLE,
            original_activity_value=activity_value,
            original_activity_unit=activity_unit,
            factor_activity_value=calculation.factor_activity_value,
            factor_activity_unit=selected.factor_activity_unit,
            factor_value=calculation.factor_value,
            allocation_percentage=calculation.allocation_percentage,
            allocation_multiplier=calculation.allocation_multiplier,
            gross_kg_co2e=calculation.gross_kg_co2e,
            allocated_kg_co2e=calculation.allocated_kg_co2e,
            calculation_formula=calculation.formula,
            intermediate_values={
                "comparison_id": str(comparison.id),
                "governed_method_id": method.value,
                "factor_source_id": selected.factor.source_factor_id,
                "factor_reporting_year": selected.factor.reporting_year,
                "comparison_only": True,
            },
            warnings=[*resolution.warnings, COMPARISON_WARNING],
            methodology_version=comparator_run.factor_policy_version,
        )
        db.add(government_result)
        await db.flush()

        absolute, percentage = calculate_comparison_delta(
            dcarbn_result.allocated_kg_co2e,
            government_result.allocated_kg_co2e,
        )
        comparison.government_result_id = government_result.id
        comparison.status = DataComparisonStatus.READY
        comparison.comparison_unavailable_reason = None
        comparison.absolute_delta_kg_co2e = absolute
        comparison.percentage_delta = percentage

        await record_audit_event(
            db,
            principal,
            action="data.comparison.government_generated",
            entity_type="data_calculation_comparison",
            entity_id=comparison.id,
            event_data={
                "dcarbn_result_id": str(dcarbn_result.id),
                "government_result_id": str(government_result.id),
                "governed_method_id": method.value,
                "selected_factor_id": str(selected.factor.id),
                "dcarbn_kg_co2e": str(dcarbn_result.allocated_kg_co2e),
                "government_kg_co2e": str(
                    government_result.allocated_kg_co2e
                ),
                "absolute_delta_kg_co2e": str(absolute),
                "percentage_delta": (
                    str(percentage) if percentage is not None else None
                ),
                "reporting_basis": comparison.reporting_basis.value,
                "comparison_only": True,
            },
        )
        await db.commit()
        await db.refresh(comparison)
        return comparison
    except ValueError as exc:
        return await _mark_unavailable(
            db,
            principal,
            comparison,
            str(exc),
        )


async def _mark_unavailable(
    db: AsyncSession,
    principal: CurrentPrincipal,
    comparison: DataCalculationComparison,
    reason: str,
) -> DataCalculationComparison:
    comparison.status = DataComparisonStatus.UNAVAILABLE
    comparison.comparison_unavailable_reason = reason
    comparison.government_result_id = None
    comparison.absolute_delta_kg_co2e = None
    comparison.percentage_delta = None
    await record_audit_event(
        db,
        principal,
        action="data.comparison.government_unavailable",
        entity_type="data_calculation_comparison",
        entity_id=comparison.id,
        event_data={"reason": reason},
    )
    await db.commit()
    await db.refresh(comparison)
    return comparison
