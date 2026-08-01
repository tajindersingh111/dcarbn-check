from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.models.calculation import CalculationResult, CalculationRun
from app.models.data_review import DataOperationalEmissionReview, DataReviewStatus
from app.models.inventory import Inventory, InventoryStatus, ReportingPeriod
from app.models.inventory_governance import (
    ApprovalStatus,
    AuditReport,
    InventoryApproval,
)
from app.models.organisation import Organisation
from app.schemas.workflows import (
    ApprovalQueueItem,
    AuditReportListItem,
    DashboardSummaryResponse,
    InventoryCreate,
    InventoryResponse,
    ReportingPeriodCreate,
)
from app.services.audit import record_audit_event


async def create_reporting_period(
    db: AsyncSession,
    principal: CurrentPrincipal,
    payload: ReportingPeriodCreate,
) -> ReportingPeriod:
    organisation = await db.scalar(
        select(Organisation).where(
            Organisation.id == payload.organisation_id,
            Organisation.tenant_id == principal.tenant_id,
        )
    )
    if organisation is None:
        raise HTTPException(status_code=404, detail="Organisation not found.")

    period = ReportingPeriod(
        tenant_id=principal.tenant_id,
        **payload.model_dump(),
    )
    db.add(period)
    await db.flush()
    await record_audit_event(
        db,
        principal,
        action="reporting_period.created",
        entity_type="reporting_period",
        entity_id=period.id,
        event_data=payload.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(period)
    return period


async def list_reporting_periods(
    db: AsyncSession,
    tenant_id: UUID,
) -> list[ReportingPeriod]:
    query = (
        select(ReportingPeriod)
        .where(ReportingPeriod.tenant_id == tenant_id)
        .order_by(ReportingPeriod.start_date.desc(), ReportingPeriod.name)
    )
    return list((await db.scalars(query)).all())


async def create_inventory(
    db: AsyncSession,
    principal: CurrentPrincipal,
    payload: InventoryCreate,
) -> Inventory:
    period = await db.scalar(
        select(ReportingPeriod).where(
            ReportingPeriod.id == payload.reporting_period_id,
            ReportingPeriod.tenant_id == principal.tenant_id,
        )
    )
    if period is None:
        raise HTTPException(status_code=404, detail="Reporting period not found.")

    next_version = int(
        (
            await db.scalar(
                select(func.coalesce(func.max(Inventory.version), 0)).where(
                    Inventory.reporting_period_id == period.id,
                    Inventory.tenant_id == principal.tenant_id,
                )
            )
        )
        or 0
    ) + 1

    inventory = Inventory(
        tenant_id=principal.tenant_id,
        reporting_period_id=period.id,
        name=payload.name,
        status=InventoryStatus.DRAFT,
        version=next_version,
    )
    db.add(inventory)
    await db.flush()
    await record_audit_event(
        db,
        principal,
        action="inventory.created",
        entity_type="inventory",
        entity_id=inventory.id,
        event_data={
            "reporting_period_id": str(period.id),
            "name": inventory.name,
            "version": inventory.version,
        },
    )
    await db.commit()
    await db.refresh(inventory)
    return inventory


async def list_inventories(
    db: AsyncSession,
    tenant_id: UUID,
    limit: int,
    offset: int,
) -> tuple[list[InventoryResponse], int]:
    query = (
        select(Inventory, ReportingPeriod, Organisation)
        .join(ReportingPeriod, ReportingPeriod.id == Inventory.reporting_period_id)
        .join(Organisation, Organisation.id == ReportingPeriod.organisation_id)
        .where(Inventory.tenant_id == tenant_id)
        .order_by(ReportingPeriod.start_date.desc(), Inventory.version.desc())
        .limit(limit)
        .offset(offset)
    )
    count_query = (
        select(func.count())
        .select_from(Inventory)
        .where(Inventory.tenant_id == tenant_id)
    )
    rows = list((await db.execute(query)).all())
    total = int((await db.scalar(count_query)) or 0)

    items: list[InventoryResponse] = []
    for inventory, period, organisation in rows:
        latest_run = await db.scalar(
            select(CalculationRun)
            .where(CalculationRun.inventory_id == inventory.id)
            .order_by(CalculationRun.version.desc())
        )
        totals = await _calculation_totals(
            db,
            latest_run.id if latest_run else None,
        )
        items.append(
            InventoryResponse(
                id=inventory.id,
                tenant_id=inventory.tenant_id,
                reporting_period_id=period.id,
                organisation_id=organisation.id,
                organisation_name=organisation.name,
                reporting_period_name=period.name,
                reporting_period_start=period.start_date,
                reporting_period_end=period.end_date,
                name=inventory.name,
                status=inventory.status,
                version=inventory.version,
                locked_at=inventory.locked_at,
                approved_at=inventory.approved_at,
                latest_calculation_run_id=latest_run.id if latest_run else None,
                total_kg_co2e=totals["total"],
                scope_1_kg_co2e=totals["scope_1"],
                scope_2_kg_co2e=totals["scope_2"],
                scope_3_kg_co2e=totals["scope_3"],
                created_at=inventory.created_at,
                updated_at=inventory.updated_at,
            )
        )
    return items, total


async def get_inventory_response(
    db: AsyncSession,
    tenant_id: UUID,
    inventory_id: UUID,
) -> InventoryResponse | None:
    items, _ = await list_inventories(db, tenant_id, 200, 0)
    return next((item for item in items if item.id == inventory_id), None)


async def list_calculation_run_options(
    db: AsyncSession,
    tenant_id: UUID,
    inventory_id: UUID,
) -> list[CalculationRun]:
    inventory = await db.scalar(
        select(Inventory.id).where(
            Inventory.id == inventory_id,
            Inventory.tenant_id == tenant_id,
        )
    )
    if inventory is None:
        raise HTTPException(status_code=404, detail="Inventory not found.")
    query = (
        select(CalculationRun)
        .where(
            CalculationRun.inventory_id == inventory_id,
            CalculationRun.tenant_id == tenant_id,
        )
        .order_by(CalculationRun.version.desc())
    )
    return list((await db.scalars(query)).all())


async def list_approval_queue(
    db: AsyncSession,
    tenant_id: UUID,
    limit: int,
    offset: int,
) -> tuple[list[ApprovalQueueItem], int]:
    query = (
        select(InventoryApproval, Inventory)
        .join(Inventory, Inventory.id == InventoryApproval.inventory_id)
        .where(InventoryApproval.tenant_id == tenant_id)
        .order_by(InventoryApproval.requested_at.desc())
        .limit(limit)
        .offset(offset)
    )
    count_query = (
        select(func.count())
        .select_from(InventoryApproval)
        .where(InventoryApproval.tenant_id == tenant_id)
    )
    rows = list((await db.execute(query)).all())
    total = int((await db.scalar(count_query)) or 0)
    return [
        ApprovalQueueItem(
            id=approval.id,
            inventory_id=inventory.id,
            inventory_name=inventory.name,
            calculation_run_id=approval.calculation_run_id,
            version=approval.version,
            status=approval.status,
            requested_by=approval.requested_by,
            requested_at=approval.requested_at,
            reviewer_id=approval.reviewer_id,
            evidence_complete=approval.evidence_complete,
            boundary_complete=approval.boundary_complete,
            factor_lineage_complete=approval.factor_lineage_complete,
            calculation_complete=approval.calculation_complete,
        )
        for approval, inventory in rows
    ], total


async def list_audit_reports(
    db: AsyncSession,
    tenant_id: UUID,
    limit: int,
    offset: int,
) -> tuple[list[AuditReportListItem], int]:
    query = (
        select(AuditReport, Inventory)
        .join(Inventory, Inventory.id == AuditReport.inventory_id)
        .where(AuditReport.tenant_id == tenant_id)
        .order_by(AuditReport.generated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    count_query = (
        select(func.count())
        .select_from(AuditReport)
        .where(AuditReport.tenant_id == tenant_id)
    )
    rows = list((await db.execute(query)).all())
    total = int((await db.scalar(count_query)) or 0)
    items = []
    for report, inventory in rows:
        totals = report.report_payload.get("totals", {})
        total_kg = Decimal(str(totals.get("total_kg_co2e", "0")))
        total_t = Decimal(str(totals.get("total_t_co2e", "0")))
        items.append(
            AuditReportListItem(
                id=report.id,
                inventory_id=inventory.id,
                inventory_name=inventory.name,
                version=report.version,
                status=report.status,
                generated_by=report.generated_by,
                generated_at=report.generated_at,
                finalized_at=report.finalized_at,
                report_sha256=report.report_sha256,
                total_kg_co2e=total_kg,
                total_t_co2e=total_t,
            )
        )
    return items, total


async def dashboard_summary(
    db: AsyncSession,
    tenant_id: UUID,
) -> DashboardSummaryResponse:
    inventories, inventory_count = await list_inventories(db, tenant_id, 200, 0)
    total_kg = sum(
        (
            item.total_kg_co2e
            for item in inventories
            if item.total_kg_co2e is not None
        ),
        Decimal("0"),
    )
    locked_count = sum(
        1 for item in inventories if item.status == InventoryStatus.LOCKED
    )
    open_reviews = int(
        (
            await db.scalar(
                select(func.count())
                .select_from(DataOperationalEmissionReview)
                .where(
                    DataOperationalEmissionReview.tenant_id == tenant_id,
                    DataOperationalEmissionReview.status.in_(
                        [DataReviewStatus.PENDING, DataReviewStatus.IN_REVIEW]
                    ),
                )
            )
        )
        or 0
    )
    open_approvals = int(
        (
            await db.scalar(
                select(func.count())
                .select_from(InventoryApproval)
                .where(
                    InventoryApproval.tenant_id == tenant_id,
                    InventoryApproval.status.in_(
                        [ApprovalStatus.PENDING, ApprovalStatus.IN_REVIEW]
                    ),
                )
            )
        )
        or 0
    )
    organisation_count = int(
        (
            await db.scalar(
                select(func.count())
                .select_from(Organisation)
                .where(Organisation.tenant_id == tenant_id)
            )
        )
        or 0
    )
    return DashboardSummaryResponse(
        total_kg_co2e=total_kg,
        total_t_co2e=total_kg / Decimal("1000"),
        inventory_count=inventory_count,
        locked_inventory_count=locked_count,
        open_data_review_count=open_reviews,
        open_approval_count=open_approvals,
        organisation_count=organisation_count,
    )


async def _calculation_totals(
    db: AsyncSession,
    run_id: UUID | None,
) -> dict[str, Decimal | None]:
    if run_id is None:
        return {
            "total": None,
            "scope_1": None,
            "scope_2": None,
            "scope_3": None,
        }
    rows = list(
        (
            await db.execute(
                select(
                    CalculationResult.scope,
                    func.sum(CalculationResult.allocated_kg_co2e),
                )
                .where(CalculationResult.calculation_run_id == run_id)
                .group_by(CalculationResult.scope)
            )
        ).all()
    )
    by_scope = {
        scope.value: Decimal(str(value))
        for scope, value in rows
    }
    total = sum(by_scope.values(), Decimal("0"))
    return {
        "total": total,
        "scope_1": by_scope.get("scope_1", Decimal("0")),
        "scope_2": by_scope.get("scope_2", Decimal("0")),
        "scope_3": by_scope.get("scope_3", Decimal("0")),
    }
