from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.calculations.governed_methods import validate_governed_method
from app.calculations.scope2_reporting import validate_market_based_evidence
from app.models.activity import ActivityRecord, ActivityStatus, Scope2Method
from app.models.inventory import Inventory, InventoryStatus, ReportingPeriod
from app.models.organisation import LegalEntity, Organisation, Site
from app.schemas.activity import ActivityCreate, ActivityUpdate
from app.services.audit import record_audit_event
from app.units.registry import UnitConversionError, get_unit_registry


async def get_inventory(
    db: AsyncSession,
    tenant_id: UUID,
    inventory_id: UUID,
) -> Inventory:
    query = select(Inventory).where(
        Inventory.id == inventory_id,
        Inventory.tenant_id == tenant_id,
    )
    inventory = await db.scalar(query)
    if inventory is None:
        raise HTTPException(status_code=404, detail="Inventory not found.")
    return inventory


def ensure_inventory_editable(inventory: Inventory) -> None:
    if inventory.status in {
        InventoryStatus.APPROVED,
        InventoryStatus.LOCKED,
        InventoryStatus.SUPERSEDED,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The inventory is not editable.",
        )


async def _validate_links(
    db: AsyncSession,
    principal: CurrentPrincipal,
    inventory: Inventory,
    payload: ActivityCreate,
) -> None:
    period = await db.get(ReportingPeriod, inventory.reporting_period_id)
    if period is None or period.tenant_id != principal.tenant_id:
        raise HTTPException(status_code=404, detail="Reporting period not found.")

    if not period.start_date <= payload.activity_date <= period.end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Activity date must fall within the reporting period.",
        )

    if period.organisation_id != payload.organisation_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Activity organisation must match the inventory reporting period.",
        )

    organisation = await db.scalar(
        select(Organisation).where(
            Organisation.id == payload.organisation_id,
            Organisation.tenant_id == principal.tenant_id,
        )
    )
    if organisation is None:
        raise HTTPException(status_code=404, detail="Organisation not found.")

    if payload.legal_entity_id is not None:
        entity = await db.scalar(
            select(LegalEntity).where(
                LegalEntity.id == payload.legal_entity_id,
                LegalEntity.tenant_id == principal.tenant_id,
                LegalEntity.organisation_id == payload.organisation_id,
            )
        )
        if entity is None:
            raise HTTPException(status_code=404, detail="Legal entity not found.")

    if payload.site_id is not None:
        site = await db.scalar(
            select(Site).where(
                Site.id == payload.site_id,
                Site.tenant_id == principal.tenant_id,
                Site.organisation_id == payload.organisation_id,
            )
        )
        if site is None:
            raise HTTPException(status_code=404, detail="Site not found.")


async def create_activity(
    db: AsyncSession,
    principal: CurrentPrincipal,
    inventory_id: UUID,
    payload: ActivityCreate,
) -> ActivityRecord:
    inventory = await get_inventory(db, principal.tenant_id, inventory_id)
    ensure_inventory_editable(inventory)
    activity = await _stage_activity(db, principal, inventory, payload)
    await db.commit()
    await db.refresh(activity)
    return activity


async def _stage_activity(
    db: AsyncSession,
    principal: CurrentPrincipal,
    inventory: Inventory,
    payload: ActivityCreate,
) -> ActivityRecord:
    await _validate_links(db, principal, inventory, payload)

    registry = get_unit_registry()
    try:
        normalized = registry.normalize(
            payload.activity_value,
            payload.activity_unit,
        )
    except UnitConversionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    version_query = select(func.coalesce(func.max(ActivityRecord.version), 0)).where(
        ActivityRecord.tenant_id == principal.tenant_id,
        ActivityRecord.source_system == payload.source_system,
        ActivityRecord.source_record_id == payload.source_record_id,
    )
    next_version = int((await db.scalar(version_query)) or 0) + 1

    existing_query = select(ActivityRecord).where(
        ActivityRecord.tenant_id == principal.tenant_id,
        ActivityRecord.source_system == payload.source_system,
        ActivityRecord.source_record_id == payload.source_record_id,
        ActivityRecord.is_current.is_(True),
    )
    existing = await db.scalar(existing_query)
    if existing is not None and (
        existing.inventory_id != inventory.id or existing.organisation_id != payload.organisation_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "source_record_id already belongs to another inventory or organisation "
                "for this source system."
            ),
        )

    activity = ActivityRecord(
        tenant_id=principal.tenant_id,
        inventory_id=inventory.id,
        normalized_value=normalized.normalized_value,
        normalized_unit=normalized.normalized_unit,
        version=next_version,
        status=ActivityStatus.VALIDATED,
        **payload.model_dump(),
    )
    db.add(activity)
    await db.flush()

    if existing is not None:
        existing.is_current = False
        existing.status = ActivityStatus.SUPERSEDED
        existing.superseded_by_id = activity.id

    await record_audit_event(
        db,
        principal,
        action="activity.created",
        entity_type="activity_record",
        entity_id=activity.id,
        event_data={
            "inventory_id": str(inventory.id),
            "activity_type": activity.activity_type.value,
            "scope": activity.scope.value,
            "version": next_version,
        },
    )
    return activity


async def create_activity_batch(
    db: AsyncSession,
    principal: CurrentPrincipal,
    inventory_id: UUID,
    payloads: list[ActivityCreate],
) -> list[ActivityRecord]:
    if not payloads or len(payloads) > 500:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="An activity import must contain between 1 and 500 records.",
        )
    identities = [
        (payload.source_system, payload.source_record_id)
        for payload in payloads
    ]
    if len(identities) != len(set(identities)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Each source_system and source_record_id pair must be unique "
                "within an import."
            ),
        )

    inventory = await get_inventory(db, principal.tenant_id, inventory_id)
    ensure_inventory_editable(inventory)

    activities: list[ActivityRecord] = []
    try:
        for payload in payloads:
            activities.append(
                await _stage_activity(db, principal, inventory, payload)
            )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    for activity in activities:
        await db.refresh(activity)
    return activities


async def get_activity(
    db: AsyncSession,
    tenant_id: UUID,
    activity_id: UUID,
) -> ActivityRecord | None:
    query = select(ActivityRecord).where(
        ActivityRecord.id == activity_id,
        ActivityRecord.tenant_id == tenant_id,
    )
    activity: ActivityRecord | None = await db.scalar(query)
    return activity


async def list_activities(
    db: AsyncSession,
    tenant_id: UUID,
    inventory_id: UUID,
    limit: int,
    offset: int,
) -> tuple[list[ActivityRecord], int]:
    await get_inventory(db, tenant_id, inventory_id)
    conditions = (
        ActivityRecord.tenant_id == tenant_id,
        ActivityRecord.inventory_id == inventory_id,
        ActivityRecord.is_current.is_(True),
    )
    query = (
        select(ActivityRecord)
        .where(*conditions)
        .order_by(ActivityRecord.activity_date, ActivityRecord.created_at)
        .limit(limit)
        .offset(offset)
    )
    count_query = select(func.count()).select_from(ActivityRecord).where(*conditions)
    items = list((await db.scalars(query)).all())
    total = int((await db.scalar(count_query)) or 0)
    return items, total


async def update_activity(
    db: AsyncSession,
    principal: CurrentPrincipal,
    activity: ActivityRecord,
    payload: ActivityUpdate,
) -> ActivityRecord:
    inventory = await get_inventory(
        db,
        principal.tenant_id,
        activity.inventory_id,
    )
    ensure_inventory_editable(inventory)
    if not activity.is_current:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only the current activity version can be updated.",
        )

    changes = payload.model_dump(exclude_unset=True)
    original = {key: str(getattr(activity, key)) for key in changes}
    for field, value in changes.items():
        setattr(activity, field, value)

    try:
        validate_governed_method(
            activity_type=activity.activity_type,
            scope=activity.scope,
            scope_3_category=activity.scope_3_category,
            activity_unit=activity.activity_unit,
            factor_level_1=activity.factor_level_1,
            factor_level_2=activity.factor_level_2,
            factor_level_3=activity.factor_level_3,
            factor_level_4=activity.factor_level_4,
            factor_column_text=activity.factor_column_text,
            metadata_json=activity.metadata_json,
            activity_value=activity.activity_value,
            scope_2_method=activity.scope_2_method,
            lifecycle_boundary=activity.lifecycle_boundary,
            evidence_reference=activity.evidence_reference,
            activity_date=activity.activity_date,
        )
        if activity.scope_2_method == Scope2Method.MARKET_BASED:
            validate_market_based_evidence(
                activity.metadata_json,
                evidence_reference=activity.evidence_reference,
                activity_date=activity.activity_date,
                geography_code=activity.geography_code,
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if "activity_value" in changes or "activity_unit" in changes:
        registry = get_unit_registry()
        try:
            normalized = registry.normalize(
                activity.activity_value,
                activity.activity_unit,
            )
        except UnitConversionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        activity.normalized_value = normalized.normalized_value
        activity.normalized_unit = normalized.normalized_unit

    activity.status = ActivityStatus.VALIDATED
    await record_audit_event(
        db,
        principal,
        action="activity.updated",
        entity_type="activity_record",
        entity_id=activity.id,
        event_data={
            "previous": original,
            "updated": payload.model_dump(exclude_unset=True, mode="json"),
        },
    )
    await db.commit()
    await db.refresh(activity)
    return activity
