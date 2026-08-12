from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.models.boundary import (
    BoundaryMembership,
    BoundaryStatus,
    ConsolidationApproach,
    MembershipDecision,
    OrganisationalBoundary,
)
from app.models.inventory import ReportingPeriod
from app.models.organisation import LegalEntity
from app.schemas.boundary import (
    BoundaryCreate,
    BoundaryUpdate,
    MembershipCreate,
    MembershipUpdate,
)
from app.services.audit import record_audit_event


ZERO = Decimal("0.00")
ONE_HUNDRED = Decimal("100.00")


def calculate_membership_outcome(
    *,
    approach: ConsolidationApproach,
    decision: MembershipDecision,
    ownership_percentage: Decimal,
    has_operational_control: bool,
    has_financial_control: bool,
) -> tuple[bool, Decimal]:
    if decision == MembershipDecision.EXCLUDED:
        return False, ZERO

    if approach == ConsolidationApproach.OPERATIONAL_CONTROL:
        automatic_inclusion = has_operational_control
        automatic_allocation = ONE_HUNDRED if automatic_inclusion else ZERO
    elif approach == ConsolidationApproach.FINANCIAL_CONTROL:
        automatic_inclusion = has_financial_control
        automatic_allocation = ONE_HUNDRED if automatic_inclusion else ZERO
    else:
        automatic_inclusion = ownership_percentage > ZERO
        automatic_allocation = ownership_percentage if automatic_inclusion else ZERO

    if decision == MembershipDecision.INCLUDED:
        if approach == ConsolidationApproach.EQUITY_SHARE:
            return True, ownership_percentage
        return True, ONE_HUNDRED

    return automatic_inclusion, automatic_allocation


async def _get_reporting_period(
    db: AsyncSession,
    tenant_id: UUID,
    reporting_period_id: UUID,
) -> ReportingPeriod:
    query = select(ReportingPeriod).where(
        ReportingPeriod.id == reporting_period_id,
        ReportingPeriod.tenant_id == tenant_id,
    )
    reporting_period = await db.scalar(query)
    if reporting_period is None:
        raise HTTPException(status_code=404, detail="Reporting period not found.")
    return reporting_period


async def get_boundary(
    db: AsyncSession,
    tenant_id: UUID,
    boundary_id: UUID,
) -> OrganisationalBoundary | None:
    query = select(OrganisationalBoundary).where(
        OrganisationalBoundary.id == boundary_id,
        OrganisationalBoundary.tenant_id == tenant_id,
    )
    boundary: OrganisationalBoundary | None = await db.scalar(query)
    return boundary


async def create_boundary(
    db: AsyncSession,
    principal: CurrentPrincipal,
    reporting_period_id: UUID,
    payload: BoundaryCreate,
) -> OrganisationalBoundary:
    period = await _get_reporting_period(
        db,
        principal.tenant_id,
        reporting_period_id,
    )
    if payload.effective_from < period.start_date or payload.effective_to > period.end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Boundary effective dates must fall within the reporting period.",
        )

    version_query = select(
        func.coalesce(func.max(OrganisationalBoundary.version), 0)
    ).where(
        OrganisationalBoundary.reporting_period_id == reporting_period_id,
        OrganisationalBoundary.tenant_id == principal.tenant_id,
    )
    next_version = int((await db.scalar(version_query)) or 0) + 1

    boundary = OrganisationalBoundary(
        tenant_id=principal.tenant_id,
        reporting_period_id=reporting_period_id,
        version=next_version,
        **payload.model_dump(),
    )
    db.add(boundary)
    await db.flush()

    await record_audit_event(
        db,
        principal,
        action="organisational_boundary.created",
        entity_type="organisational_boundary",
        entity_id=boundary.id,
        event_data=payload.model_dump(mode="json") | {"version": next_version},
    )
    await db.commit()
    await db.refresh(boundary)
    return boundary


async def list_boundaries(
    db: AsyncSession,
    tenant_id: UUID,
    reporting_period_id: UUID,
) -> list[OrganisationalBoundary]:
    await _get_reporting_period(db, tenant_id, reporting_period_id)
    query = (
        select(OrganisationalBoundary)
        .where(
            OrganisationalBoundary.tenant_id == tenant_id,
            OrganisationalBoundary.reporting_period_id == reporting_period_id,
        )
        .order_by(OrganisationalBoundary.version.desc())
    )
    return list((await db.scalars(query)).all())


def ensure_boundary_editable(boundary: OrganisationalBoundary) -> None:
    if boundary.status != BoundaryStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft boundaries can be changed.",
        )


async def update_boundary(
    db: AsyncSession,
    principal: CurrentPrincipal,
    boundary: OrganisationalBoundary,
    payload: BoundaryUpdate,
) -> OrganisationalBoundary:
    ensure_boundary_editable(boundary)
    changes = payload.model_dump(exclude_unset=True)

    effective_from = changes.get("effective_from", boundary.effective_from)
    effective_to = changes.get("effective_to", boundary.effective_to)
    if effective_to < effective_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="effective_to must be on or after effective_from.",
        )

    previous = {
        field: str(getattr(boundary, field))
        for field in changes
    }
    for field, value in changes.items():
        setattr(boundary, field, value)

    if "consolidation_approach" in changes:
        await recalculate_all_memberships(db, boundary)

    await record_audit_event(
        db,
        principal,
        action="organisational_boundary.updated",
        entity_type="organisational_boundary",
        entity_id=boundary.id,
        event_data={
            "previous": previous,
            "updated": payload.model_dump(exclude_unset=True, mode="json"),
        },
    )
    await db.commit()
    await db.refresh(boundary)
    return boundary


async def approve_boundary(
    db: AsyncSession,
    principal: CurrentPrincipal,
    boundary: OrganisationalBoundary,
) -> OrganisationalBoundary:
    ensure_boundary_editable(boundary)

    member_count = int(
        (
            await db.scalar(
                select(func.count())
                .select_from(BoundaryMembership)
                .where(BoundaryMembership.boundary_id == boundary.id)
            )
        )
        or 0
    )
    if member_count == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A boundary must contain at least one legal entity before approval.",
        )

    boundary.status = BoundaryStatus.APPROVED
    boundary.approved_at = datetime.now(UTC)
    boundary.approved_by = principal.subject

    await record_audit_event(
        db,
        principal,
        action="organisational_boundary.approved",
        entity_type="organisational_boundary",
        entity_id=boundary.id,
        event_data={"membership_count": member_count},
    )
    await db.commit()
    await db.refresh(boundary)
    return boundary


async def get_membership(
    db: AsyncSession,
    tenant_id: UUID,
    boundary_id: UUID,
    membership_id: UUID,
) -> BoundaryMembership | None:
    query = select(BoundaryMembership).where(
        BoundaryMembership.id == membership_id,
        BoundaryMembership.boundary_id == boundary_id,
        BoundaryMembership.tenant_id == tenant_id,
    )
    membership: BoundaryMembership | None = await db.scalar(query)
    return membership


async def create_membership(
    db: AsyncSession,
    principal: CurrentPrincipal,
    boundary: OrganisationalBoundary,
    payload: MembershipCreate,
) -> BoundaryMembership:
    ensure_boundary_editable(boundary)

    legal_entity_query = select(LegalEntity).where(
        LegalEntity.id == payload.legal_entity_id,
        LegalEntity.tenant_id == principal.tenant_id,
    )
    legal_entity = await db.scalar(legal_entity_query)
    if legal_entity is None:
        raise HTTPException(status_code=404, detail="Legal entity not found.")

    if (
        payload.effective_from < boundary.effective_from
        or payload.effective_to > boundary.effective_to
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Membership dates must fall within the boundary effective dates.",
        )

    is_included, allocation_percentage = calculate_membership_outcome(
        approach=boundary.consolidation_approach,
        decision=payload.decision,
        ownership_percentage=payload.ownership_percentage,
        has_operational_control=payload.has_operational_control,
        has_financial_control=payload.has_financial_control,
    )

    membership = BoundaryMembership(
        tenant_id=principal.tenant_id,
        boundary_id=boundary.id,
        is_included=is_included,
        allocation_percentage=allocation_percentage,
        **payload.model_dump(),
    )
    db.add(membership)
    await db.flush()

    await record_audit_event(
        db,
        principal,
        action="boundary_membership.created",
        entity_type="boundary_membership",
        entity_id=membership.id,
        event_data=payload.model_dump(mode="json")
        | {
            "is_included": is_included,
            "allocation_percentage": str(allocation_percentage),
        },
    )
    await db.commit()
    await db.refresh(membership)
    return membership


async def list_memberships(
    db: AsyncSession,
    tenant_id: UUID,
    boundary_id: UUID,
) -> list[BoundaryMembership]:
    query = (
        select(BoundaryMembership)
        .where(
            BoundaryMembership.tenant_id == tenant_id,
            BoundaryMembership.boundary_id == boundary_id,
        )
        .order_by(BoundaryMembership.created_at)
    )
    return list((await db.scalars(query)).all())


async def update_membership(
    db: AsyncSession,
    principal: CurrentPrincipal,
    boundary: OrganisationalBoundary,
    membership: BoundaryMembership,
    payload: MembershipUpdate,
) -> BoundaryMembership:
    ensure_boundary_editable(boundary)
    changes = payload.model_dump(exclude_unset=True)

    decision = changes.get("decision", membership.decision)
    decision_reason = changes.get("decision_reason", membership.decision_reason)
    if decision != MembershipDecision.AUTO and not decision_reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="decision_reason is required for manual decisions.",
        )

    effective_from = changes.get("effective_from", membership.effective_from)
    effective_to = changes.get("effective_to", membership.effective_to)
    if effective_to < effective_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="effective_to must be on or after effective_from.",
        )
    if effective_from < boundary.effective_from or effective_to > boundary.effective_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Membership dates must fall within the boundary effective dates.",
        )

    previous = {
        field: str(getattr(membership, field))
        for field in changes
    }
    for field, value in changes.items():
        setattr(membership, field, value)

    membership.is_included, membership.allocation_percentage = (
        calculate_membership_outcome(
            approach=boundary.consolidation_approach,
            decision=membership.decision,
            ownership_percentage=membership.ownership_percentage,
            has_operational_control=membership.has_operational_control,
            has_financial_control=membership.has_financial_control,
        )
    )

    await record_audit_event(
        db,
        principal,
        action="boundary_membership.updated",
        entity_type="boundary_membership",
        entity_id=membership.id,
        event_data={
            "previous": previous,
            "updated": payload.model_dump(exclude_unset=True, mode="json"),
            "is_included": membership.is_included,
            "allocation_percentage": str(membership.allocation_percentage),
        },
    )
    await db.commit()
    await db.refresh(membership)
    return membership


async def recalculate_all_memberships(
    db: AsyncSession,
    boundary: OrganisationalBoundary,
) -> None:
    memberships = await list_memberships(db, boundary.tenant_id, boundary.id)
    for membership in memberships:
        membership.is_included, membership.allocation_percentage = (
            calculate_membership_outcome(
                approach=boundary.consolidation_approach,
                decision=membership.decision,
                ownership_percentage=membership.ownership_percentage,
                has_operational_control=membership.has_operational_control,
                has_financial_control=membership.has_financial_control,
            )
        )
