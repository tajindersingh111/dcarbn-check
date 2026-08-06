from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.calculations.engine import HUNDRED
from app.models.activity import (
    ActivityRecord,
    ActivityStatus,
    ActivityType,
    DataQualityLevel,
    EmissionScope,
    Scope2Method,
)
from app.models.calculation import (
    CalculationMethod,
    CalculationResult,
    CalculationRun,
    CalculationRunStatus,
)
from app.models.data_integration import (
    DataCalculationComparison,
    DataClassificationStatus,
    DataComparisonStatus,
    DataOperationalEmission,
    DataOrganisationMapping,
    DataReportingBasis,
)
from app.models.data_review import (
    DataOperationalEmissionReview,
    DataReviewStatus,
)
from app.models.inventory import Inventory, InventoryStatus, ReportingPeriod
from app.schemas.data_review import (
    DataReviewDecisionRequest,
    DataReviewStartRequest,
)
from app.services.audit import record_audit_event


def _parse_scope(value: str) -> EmissionScope:
    normalized = value.strip().lower().replace(" ", "_")
    mapping = {
        "scope_1": EmissionScope.SCOPE_1,
        "scope1": EmissionScope.SCOPE_1,
        "scope_2": EmissionScope.SCOPE_2,
        "scope2": EmissionScope.SCOPE_2,
        "scope_3": EmissionScope.SCOPE_3,
        "scope3": EmissionScope.SCOPE_3,
    }
    try:
        return mapping[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported confirmed scope: {value!r}.") from exc


def _map_data_quality(value: str | None) -> DataQualityLevel:
    if not value:
        return DataQualityLevel.UNKNOWN
    normalized = value.strip().lower()
    return {
        "primary": DataQualityLevel.PRIMARY,
        "secondary": DataQualityLevel.SECONDARY,
        "estimated": DataQualityLevel.ESTIMATED,
        "unknown": DataQualityLevel.UNKNOWN,
    }.get(normalized, DataQualityLevel.UNKNOWN)


async def _get_emission(
    db: AsyncSession,
    tenant_id: UUID,
    emission_id: UUID,
) -> DataOperationalEmission:
    emission = await db.scalar(
        select(DataOperationalEmission).where(
            DataOperationalEmission.id == emission_id,
            DataOperationalEmission.tenant_id == tenant_id,
        )
    )
    if emission is None:
        raise HTTPException(
            status_code=404,
            detail="DATa operational-emission record not found.",
        )
    return emission


async def _get_inventory(
    db: AsyncSession,
    tenant_id: UUID,
    inventory_id: UUID,
) -> tuple[Inventory, ReportingPeriod]:
    inventory = await db.scalar(
        select(Inventory).where(
            Inventory.id == inventory_id,
            Inventory.tenant_id == tenant_id,
        )
    )
    if inventory is None:
        raise HTTPException(status_code=404, detail="Inventory not found.")
    if inventory.status in {
        InventoryStatus.APPROVED,
        InventoryStatus.LOCKED,
        InventoryStatus.SUPERSEDED,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The selected inventory is not editable.",
        )

    period = await db.get(ReportingPeriod, inventory.reporting_period_id)
    if period is None or period.tenant_id != tenant_id:
        raise HTTPException(
            status_code=404,
            detail="Reporting period not found.",
        )
    return inventory, period


async def get_or_create_review(
    db: AsyncSession,
    principal: CurrentPrincipal,
    emission_id: UUID,
) -> DataOperationalEmissionReview:
    emission = await _get_emission(db, principal.tenant_id, emission_id)
    review = await db.scalar(
        select(DataOperationalEmissionReview).where(
            DataOperationalEmissionReview.tenant_id == principal.tenant_id,
            DataOperationalEmissionReview.operational_emission_id == emission.id,
        )
    )
    if review is not None:
        return review

    review = DataOperationalEmissionReview(
        tenant_id=principal.tenant_id,
        operational_emission_id=emission.id,
        status=DataReviewStatus.PENDING,
        review_snapshot={},
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


async def start_review(
    db: AsyncSession,
    principal: CurrentPrincipal,
    emission_id: UUID,
    payload: DataReviewStartRequest,
) -> DataOperationalEmissionReview:
    emission = await _get_emission(db, principal.tenant_id, emission_id)
    inventory, period = await _get_inventory(
        db,
        principal.tenant_id,
        payload.inventory_id,
    )

    if not period.start_date <= emission.calculated_at.date() <= period.end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "The DATa calculation date does not fall within the "
                "inventory reporting period."
            ),
        )

    if emission.classification_status != DataClassificationStatus.CONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The operational-emission classification must be confirmed "
                "before review begins."
            ),
        )

    review = await get_or_create_review(db, principal, emission.id)
    if review.status in {
        DataReviewStatus.CONVERTED,
        DataReviewStatus.REJECTED,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A {review.status.value} review cannot be restarted.",
        )

    review.inventory_id = inventory.id
    review.status = DataReviewStatus.IN_REVIEW
    review.reviewer_id = principal.subject
    review.review_started_at = datetime.now(UTC)
    review.reviewer_comment = payload.reviewer_comment
    review.rejection_reason = None
    review.conversion_failure = None
    review.review_snapshot = _build_review_snapshot(emission, inventory, period)

    await record_audit_event(
        db,
        principal,
        action="data.review.started",
        entity_type="data_operational_emission_review",
        entity_id=review.id,
        event_data={
            "operational_emission_id": str(emission.id),
            "inventory_id": str(inventory.id),
        },
    )
    await db.commit()
    await db.refresh(review)
    return review


async def decide_review(
    db: AsyncSession,
    principal: CurrentPrincipal,
    review_id: UUID,
    payload: DataReviewDecisionRequest,
) -> DataOperationalEmissionReview:
    review = await get_review(db, principal.tenant_id, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found.")
    if review.status != DataReviewStatus.IN_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only reviews in progress can be decided.",
        )

    review.status = payload.decision
    review.reviewer_id = principal.subject
    review.reviewed_at = datetime.now(UTC)
    review.reviewer_comment = payload.reviewer_comment
    review.rejection_reason = payload.rejection_reason

    await record_audit_event(
        db,
        principal,
        action=f"data.review.{payload.decision.value}",
        entity_type="data_operational_emission_review",
        entity_id=review.id,
        event_data={
            "decision": payload.decision.value,
            "rejection_reason": payload.rejection_reason,
        },
    )
    await db.commit()
    await db.refresh(review)
    return review


async def convert_review(
    db: AsyncSession,
    principal: CurrentPrincipal,
    review_id: UUID,
) -> DataOperationalEmissionReview:
    review = await get_review(db, principal.tenant_id, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found.")

    if review.status == DataReviewStatus.CONVERTED:
        return review
    if review.status != DataReviewStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only approved reviews can be converted.",
        )
    if review.inventory_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The review is not linked to an inventory.",
        )

    emission = await _get_emission(
        db,
        principal.tenant_id,
        review.operational_emission_id,
    )
    inventory, period = await _get_inventory(
        db,
        principal.tenant_id,
        review.inventory_id,
    )

    try:
        scope = _parse_scope(emission.confirmed_scope or "")
        _validate_confirmed_classification(
            scope,
            emission.confirmed_scope_3_category,
        )
        if not period.start_date <= emission.calculated_at.date() <= period.end_date:
            raise ValueError(
                "DATa calculation date is outside the inventory reporting period."
            )
        comparison_group_key = await _ensure_comparison_group_available(
            db,
            principal.tenant_id,
            emission,
            period,
        )

        activity = await _create_external_activity(
            db,
            principal,
            inventory,
            emission,
            scope,
        )
        run = await _create_external_calculation_run(
            db,
            principal,
            inventory,
        )
        result = _create_external_calculation_result(
            principal,
            run,
            activity,
            emission,
            scope,
        )
        db.add(result)
        await db.flush()

        comparison = DataCalculationComparison(
            tenant_id=principal.tenant_id,
            operational_emission_id=emission.id,
            comparison_group_key=comparison_group_key,
            dcarbn_result_id=result.id,
            government_result_id=None,
            status=DataComparisonStatus.PENDING,
            reporting_basis=DataReportingBasis.DCRBN_OPERATIONAL,
            basis_reason=(
                "DcarbN operational result selected pending a defensible "
                "UK Government comparator."
            ),
            basis_selected_by=principal.subject,
            basis_selected_at=datetime.now(UTC),
        )
        db.add(comparison)
        await db.flush()

        review.status = DataReviewStatus.CONVERTED
        review.converted_at = datetime.now(UTC)
        review.activity_id = activity.id
        review.calculation_run_id = run.id
        review.calculation_result_id = result.id
        review.conversion_failure = None

        emission.activity_id = activity.id
        inventory.status = InventoryStatus.REVIEW_REQUIRED

        await record_audit_event(
            db,
            principal,
            action="data.review.converted",
            entity_type="data_operational_emission_review",
            entity_id=review.id,
            event_data={
                "activity_id": str(activity.id),
                "calculation_run_id": str(run.id),
                "calculation_result_id": str(result.id),
                "external_calculation_id": emission.external_calculation_id,
                "total_kg_co2e": str(emission.total_kg_co2e),
                "comparison_id": str(comparison.id),
                "comparison_group_key": comparison_group_key,
                "reporting_basis": comparison.reporting_basis.value,
            },
        )
        await db.commit()
        await db.refresh(review)
        return review
    except ValueError as exc:
        review.conversion_failure = str(exc)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


def _comparison_group_key(
    emission: DataOperationalEmission,
    period: ReportingPeriod,
) -> str:
    activity_key = (
        emission.external_activity_key
        or emission.external_calculation_id
    )
    start = emission.reporting_period_start or period.start_date
    end = emission.reporting_period_end or period.end_date
    return f"dcarbn:{activity_key}:{start.isoformat()}:{end.isoformat()}"


async def _ensure_comparison_group_available(
    db: AsyncSession,
    tenant_id: UUID,
    emission: DataOperationalEmission,
    period: ReportingPeriod,
) -> str:
    comparison_group_key = _comparison_group_key(emission, period)
    existing = await db.scalar(
        select(DataCalculationComparison.id).where(
            DataCalculationComparison.tenant_id == tenant_id,
            DataCalculationComparison.comparison_group_key
            == comparison_group_key,
        )
    )
    if existing is not None:
        raise ValueError(
            "A DcarbN comparison already exists for this activity and "
            "reporting period."
        )
    return comparison_group_key


def _external_activity_type(scope: EmissionScope) -> ActivityType:
    if scope == EmissionScope.SCOPE_1:
        return ActivityType.MOBILE_COMBUSTION
    if scope == EmissionScope.SCOPE_3:
        return ActivityType.FREIGHT_TRANSPORT
    raise ValueError(
        "DcarbN operational transport results may only map to Scope 1 or Scope 3."
    )


async def _create_external_activity(
    db: AsyncSession,
    principal: CurrentPrincipal,
    inventory: Inventory,
    emission: DataOperationalEmission,
    scope: EmissionScope,
) -> ActivityRecord:
    existing = await db.scalar(
        select(ActivityRecord).where(
            ActivityRecord.tenant_id == principal.tenant_id,
            ActivityRecord.source_system == "DATa",
            ActivityRecord.source_record_id
            == emission.external_calculation_id,
            ActivityRecord.is_current.is_(True),
        )
    )
    if existing is not None:
        raise ValueError(
            "A current activity already exists for this DATa calculation."
        )

    activity = ActivityRecord(
        tenant_id=principal.tenant_id,
        inventory_id=inventory.id,
        organisation_id=emission.organisation_id,
        activity_type=_external_activity_type(scope),
        status=ActivityStatus.CALCULATED,
        scope=scope,
        scope_3_category=emission.confirmed_scope_3_category,
        scope_2_method=Scope2Method.NOT_APPLICABLE,
        activity_date=emission.calculated_at.date(),
        description=(
            "DATa operational transport result "
            f"{emission.external_calculation_id}"
        ),
        activity_value=emission.total_kg_co2e,
        activity_unit="kg",
        normalized_value=emission.total_kg_co2e,
        normalized_unit="kg",
        geography_code="GB",
        allocation_percentage=Decimal("100.00"),
        data_quality_level=_map_data_quality(emission.data_quality_level),
        data_quality_score=emission.data_quality_score or 0,
        source_system="DATa",
        source_record_id=emission.external_calculation_id,
        source_record_hash=emission.source_record_hash,
        metadata_json={
            "data_operational_emission_id": str(emission.id),
            "external_journey_id": await _external_journey_id(db, emission),
            "external_shipment_id": await _external_shipment_id(db, emission),
            "external_vehicle_id": await _external_vehicle_id(db, emission),
            "methodology_version": emission.methodology_version,
            "method_identifier": emission.method_identifier,
            "calculation_software_version": emission.calculation_software_version,
            "external_activity_key": emission.external_activity_key,
            "reporting_period_start": (
                emission.reporting_period_start.isoformat()
                if emission.reporting_period_start
                else None
            ),
            "reporting_period_end": (
                emission.reporting_period_end.isoformat()
                if emission.reporting_period_end
                else None
            ),
            "uncertainty_percentage": (
                str(emission.uncertainty_percentage)
                if emission.uncertainty_percentage is not None
                else None
            ),
            "comparison_inputs": emission.comparison_inputs_json,
            "lineage": emission.lineage_json,
            "source_record_version": emission.source_record_version,
        },
        version=1,
        is_current=True,
    )
    db.add(activity)
    await db.flush()
    return activity


async def _create_external_calculation_run(
    db: AsyncSession,
    principal: CurrentPrincipal,
    inventory: Inventory,
) -> CalculationRun:
    next_version = int(
        (
            await db.scalar(
                select(func.coalesce(func.max(CalculationRun.version), 0)).where(
                    CalculationRun.inventory_id == inventory.id
                )
            )
        )
        or 0
    ) + 1

    now = datetime.now(UTC)
    run = CalculationRun(
        tenant_id=principal.tenant_id,
        inventory_id=inventory.id,
        version=next_version,
        status=CalculationRunStatus.COMPLETED,
        software_version="0.1.0",
        factor_policy_version="DATa-external-result-v1",
        started_at=now,
        completed_at=now,
        activity_count=1,
        result_count=1,
        failed_count=0,
    )
    db.add(run)
    await db.flush()
    return run


def _create_external_calculation_result(
    principal: CurrentPrincipal,
    run: CalculationRun,
    activity: ActivityRecord,
    emission: DataOperationalEmission,
    scope: EmissionScope,
) -> CalculationResult:
    allocation_percentage = Decimal("100.00")
    allocation_multiplier = allocation_percentage / HUNDRED

    return CalculationResult(
        tenant_id=principal.tenant_id,
        calculation_run_id=run.id,
        activity_id=activity.id,
        factor_resolution_record_id=None,
        selected_factor_id=None,
        method=CalculationMethod.EXTERNAL_OPERATIONAL_RESULT,
        scope=scope,
        scope_3_category=emission.confirmed_scope_3_category,
        scope_2_method=Scope2Method.NOT_APPLICABLE,
        original_activity_value=emission.total_kg_co2e,
        original_activity_unit="kg CO2e",
        factor_activity_value=emission.total_kg_co2e,
        factor_activity_unit="kg CO2e",
        factor_value=None,
        allocation_percentage=allocation_percentage,
        allocation_multiplier=allocation_multiplier,
        gross_kg_co2e=emission.total_kg_co2e,
        allocated_kg_co2e=emission.total_kg_co2e,
        co2_kg=emission.co2_kg,
        ch4_kg_co2e=emission.ch4_kg_co2e,
        n2o_kg_co2e=emission.n2o_kg_co2e,
        calculation_formula=(
            "allocated_kg_co2e = verified DATa operational result; "
            "no emission factor reapplied"
        ),
        intermediate_values={
            "data_operational_emission_id": str(emission.id),
            "external_calculation_id": emission.external_calculation_id,
            "methodology_version": emission.methodology_version,
            "method_identifier": emission.method_identifier,
            "calculation_software_version": emission.calculation_software_version,
            "external_activity_key": emission.external_activity_key,
            "uncertainty_percentage": (
                str(emission.uncertainty_percentage)
                if emission.uncertainty_percentage is not None
                else None
            ),
            "comparison_inputs": emission.comparison_inputs_json,
            "source_record_hash": emission.source_record_hash,
            "source_record_version": emission.source_record_version,
            "calculated_at": emission.calculated_at.isoformat(),
            "lineage": emission.lineage_json,
            "data_quality_level": emission.data_quality_level,
            "data_quality_score": emission.data_quality_score,
        },
        warnings=[],
        methodology_version=emission.methodology_version,
    )


async def get_review(
    db: AsyncSession,
    tenant_id: UUID,
    review_id: UUID,
) -> DataOperationalEmissionReview | None:
    return await db.scalar(
        select(DataOperationalEmissionReview).where(
            DataOperationalEmissionReview.id == review_id,
            DataOperationalEmissionReview.tenant_id == tenant_id,
        )
    )


async def list_reviews(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    status_filter: DataReviewStatus | None,
    limit: int,
    offset: int,
) -> tuple[list[tuple[DataOperationalEmissionReview, DataOperationalEmission]], int]:
    conditions = [
        DataOperationalEmissionReview.tenant_id == tenant_id,
    ]
    if status_filter is not None:
        conditions.append(
            DataOperationalEmissionReview.status == status_filter
        )

    query = (
        select(
            DataOperationalEmissionReview,
            DataOperationalEmission,
        )
        .join(
            DataOperationalEmission,
            DataOperationalEmission.id
            == DataOperationalEmissionReview.operational_emission_id,
        )
        .where(*conditions)
        .order_by(
            DataOperationalEmissionReview.created_at,
            DataOperationalEmission.calculated_at,
        )
        .limit(limit)
        .offset(offset)
    )
    count_query = (
        select(func.count())
        .select_from(DataOperationalEmissionReview)
        .where(*conditions)
    )
    items = list((await db.execute(query)).all())
    total = int((await db.scalar(count_query)) or 0)
    return items, total


async def ensure_pending_reviews_for_confirmed_emissions(
    db: AsyncSession,
    principal: CurrentPrincipal,
) -> int:
    emissions = list(
        (
            await db.scalars(
                select(DataOperationalEmission).where(
                    DataOperationalEmission.tenant_id == principal.tenant_id,
                    DataOperationalEmission.classification_status
                    == DataClassificationStatus.CONFIRMED,
                )
            )
        ).all()
    )
    created = 0
    for emission in emissions:
        existing = await db.scalar(
            select(DataOperationalEmissionReview.id).where(
                DataOperationalEmissionReview.tenant_id
                == principal.tenant_id,
                DataOperationalEmissionReview.operational_emission_id
                == emission.id,
            )
        )
        if existing is None:
            db.add(
                DataOperationalEmissionReview(
                    tenant_id=principal.tenant_id,
                    operational_emission_id=emission.id,
                    status=DataReviewStatus.PENDING,
                    review_snapshot={},
                )
            )
            created += 1

    if created:
        await db.commit()
    return created


def _validate_confirmed_classification(
    scope: EmissionScope,
    category: int | None,
) -> None:
    if scope == EmissionScope.SCOPE_3:
        if category is None:
            raise ValueError("Confirmed Scope 3 classification requires a category.")
        if category not in {4, 9}:
            raise ValueError(
                "DcarbN operational transport results may only map to "
                "Scope 3 Category 4 or Category 9."
            )
    elif category is not None:
        raise ValueError(
            "A Scope 3 category cannot be used outside confirmed Scope 3."
        )


def _build_review_snapshot(
    emission: DataOperationalEmission,
    inventory: Inventory,
    period: ReportingPeriod,
) -> dict[str, object]:
    return {
        "operational_emission": {
            "id": str(emission.id),
            "external_calculation_id": emission.external_calculation_id,
            "organisation_id": str(emission.organisation_id),
            "confirmed_scope": emission.confirmed_scope,
            "confirmed_scope_3_category": (
                emission.confirmed_scope_3_category
            ),
            "methodology_version": emission.methodology_version,
            "method_identifier": emission.method_identifier,
            "calculation_software_version": emission.calculation_software_version,
            "external_activity_key": emission.external_activity_key,
            "reporting_period_start": (
                emission.reporting_period_start.isoformat()
                if emission.reporting_period_start
                else None
            ),
            "reporting_period_end": (
                emission.reporting_period_end.isoformat()
                if emission.reporting_period_end
                else None
            ),
            "uncertainty_percentage": (
                str(emission.uncertainty_percentage)
                if emission.uncertainty_percentage is not None
                else None
            ),
            "comparison_inputs": emission.comparison_inputs_json,
            "total_kg_co2e": str(emission.total_kg_co2e),
            "co2_kg": str(emission.co2_kg) if emission.co2_kg is not None else None,
            "ch4_kg_co2e": (
                str(emission.ch4_kg_co2e)
                if emission.ch4_kg_co2e is not None
                else None
            ),
            "n2o_kg_co2e": (
                str(emission.n2o_kg_co2e)
                if emission.n2o_kg_co2e is not None
                else None
            ),
            "source_record_hash": emission.source_record_hash,
            "calculated_at": emission.calculated_at.isoformat(),
            "lineage": emission.lineage_json,
        },
        "inventory": {
            "id": str(inventory.id),
            "version": inventory.version,
            "reporting_period_id": str(inventory.reporting_period_id),
            "reporting_period_start": period.start_date.isoformat(),
            "reporting_period_end": period.end_date.isoformat(),
        },
    }


async def _external_journey_id(
    db: AsyncSession,
    emission: DataOperationalEmission,
) -> str | None:
    if emission.journey_id is None:
        return None
    from app.models.data_integration import DataJourney

    return await db.scalar(
        select(DataJourney.external_journey_id).where(
            DataJourney.id == emission.journey_id
        )
    )


async def _external_shipment_id(
    db: AsyncSession,
    emission: DataOperationalEmission,
) -> str | None:
    if emission.shipment_id is None:
        return None
    from app.models.data_integration import DataShipment

    return await db.scalar(
        select(DataShipment.external_shipment_id).where(
            DataShipment.id == emission.shipment_id
        )
    )


async def _external_vehicle_id(
    db: AsyncSession,
    emission: DataOperationalEmission,
) -> str | None:
    if emission.vehicle_id is None:
        return None
    from app.models.data_integration import DataVehicle

    return await db.scalar(
        select(DataVehicle.external_vehicle_id).where(
            DataVehicle.id == emission.vehicle_id
        )
    )
