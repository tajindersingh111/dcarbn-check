from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.integrations.data.hashing import canonical_json_sha256
from app.models.activity import ActivityRecord
from app.models.boundary import BoundaryStatus, OrganisationalBoundary
from app.models.calculation import (
    CalculationResult,
    CalculationRun,
    CalculationRunStatus,
)
from app.models.emission_factor import EmissionFactor, EmissionFactorSet
from app.models.inventory import Inventory, InventoryStatus, ReportingPeriod
from app.models.inventory_governance import (
    ApprovalStatus,
    AuditReport,
    InventoryApproval,
    InventoryLock,
    InventoryRestatement,
    ReportStatus,
    RestatementStatus,
)
from app.schemas.inventory_governance import (
    ApprovalDecision,
    RestatementDecision,
    RestatementRequestCreate,
)
from app.services.audit import record_audit_event


async def _get_inventory(
    db: AsyncSession,
    tenant_id: UUID,
    inventory_id: UUID,
) -> Inventory:
    inventory = await db.scalar(
        select(Inventory).where(
            Inventory.id == inventory_id,
            Inventory.tenant_id == tenant_id,
        )
    )
    if inventory is None:
        raise HTTPException(status_code=404, detail="Inventory not found.")
    return inventory


async def _get_run(
    db: AsyncSession,
    tenant_id: UUID,
    run_id: UUID,
) -> CalculationRun:
    run = await db.scalar(
        select(CalculationRun).where(
            CalculationRun.id == run_id,
            CalculationRun.tenant_id == tenant_id,
        )
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Calculation run not found.")
    return run


async def create_approval_request(
    db: AsyncSession,
    principal: CurrentPrincipal,
    inventory_id: UUID,
    calculation_run_id: UUID,
) -> InventoryApproval:
    inventory = await _get_inventory(db, principal.tenant_id, inventory_id)
    run = await _get_run(db, principal.tenant_id, calculation_run_id)

    if run.inventory_id != inventory.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Calculation run does not belong to the inventory.",
        )
    if run.status != CalculationRunStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only completed calculation runs can be submitted.",
        )
    if inventory.status not in {
        InventoryStatus.REVIEW_REQUIRED,
        InventoryStatus.READY_FOR_CALCULATION,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inventory is not ready for approval.",
        )

    existing = await db.scalar(
        select(InventoryApproval).where(
            InventoryApproval.inventory_id == inventory.id,
            InventoryApproval.calculation_run_id == run.id,
            InventoryApproval.status.in_(
                [ApprovalStatus.PENDING, ApprovalStatus.IN_REVIEW]
            ),
        )
    )
    if existing is not None:
        return existing

    next_version = int(
        (
            await db.scalar(
                select(func.coalesce(func.max(InventoryApproval.version), 0)).where(
                    InventoryApproval.inventory_id == inventory.id
                )
            )
        )
        or 0
    ) + 1

    checks = await _approval_checks(db, inventory, run)
    approval = InventoryApproval(
        tenant_id=principal.tenant_id,
        inventory_id=inventory.id,
        calculation_run_id=run.id,
        version=next_version,
        status=ApprovalStatus.PENDING,
        requested_by=principal.subject,
        requested_at=datetime.now(UTC),
        **checks,
        review_snapshot=await _approval_snapshot(db, inventory, run),
    )
    db.add(approval)

    await record_audit_event(
        db,
        principal,
        action="inventory.approval.requested",
        entity_type="inventory_approval",
        entity_id=approval.id,
        event_data={
            "inventory_id": str(inventory.id),
            "calculation_run_id": str(run.id),
            "version": next_version,
            **checks,
        },
    )
    await db.commit()
    await db.refresh(approval)
    return approval


async def start_approval_review(
    db: AsyncSession,
    principal: CurrentPrincipal,
    approval_id: UUID,
) -> InventoryApproval:
    approval = await get_approval(db, principal.tenant_id, approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval request not found.")
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending approvals can enter review.",
        )
    if approval.requested_by == principal.subject:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The requester cannot review their own approval request.",
        )

    approval.status = ApprovalStatus.IN_REVIEW
    approval.reviewer_id = principal.subject
    approval.review_started_at = datetime.now(UTC)

    await record_audit_event(
        db,
        principal,
        action="inventory.approval.review_started",
        entity_type="inventory_approval",
        entity_id=approval.id,
        event_data={},
    )
    await db.commit()
    await db.refresh(approval)
    return approval


async def decide_approval(
    db: AsyncSession,
    principal: CurrentPrincipal,
    approval_id: UUID,
    payload: ApprovalDecision,
) -> InventoryApproval:
    approval = await get_approval(db, principal.tenant_id, approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval request not found.")
    if approval.status != ApprovalStatus.IN_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only approvals in review can be decided.",
        )
    if approval.reviewer_id != principal.subject:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned reviewer can decide this request.",
        )

    inventory = await _get_inventory(
        db,
        principal.tenant_id,
        approval.inventory_id,
    )

    if payload.decision == ApprovalStatus.APPROVED:
        if not all(
            (
                approval.evidence_complete,
                approval.boundary_complete,
                approval.factor_lineage_complete,
                approval.calculation_complete,
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Approval controls are incomplete.",
            )
        inventory.status = InventoryStatus.APPROVED
        inventory.approved_at = datetime.now(UTC)

    approval.status = payload.decision
    approval.decided_at = datetime.now(UTC)
    approval.decision_reason = payload.decision_reason

    await record_audit_event(
        db,
        principal,
        action=f"inventory.approval.{payload.decision.value}",
        entity_type="inventory_approval",
        entity_id=approval.id,
        event_data={"decision_reason": payload.decision_reason},
    )
    await db.commit()
    await db.refresh(approval)
    return approval


async def lock_inventory(
    db: AsyncSession,
    principal: CurrentPrincipal,
    inventory_id: UUID,
    lock_reason: str,
) -> InventoryLock:
    inventory = await _get_inventory(db, principal.tenant_id, inventory_id)
    if inventory.status != InventoryStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only approved inventories can be locked.",
        )

    existing = await db.scalar(
        select(InventoryLock).where(InventoryLock.inventory_id == inventory.id)
    )
    if existing is not None:
        return existing

    approval = await db.scalar(
        select(InventoryApproval)
        .where(
            InventoryApproval.inventory_id == inventory.id,
            InventoryApproval.status == ApprovalStatus.APPROVED,
        )
        .order_by(InventoryApproval.version.desc())
    )
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approved inventory does not have an approved request.",
        )

    now = datetime.now(UTC)
    lock = InventoryLock(
        tenant_id=principal.tenant_id,
        inventory_id=inventory.id,
        approval_id=approval.id,
        calculation_run_id=approval.calculation_run_id,
        locked_by=principal.subject,
        locked_at=now,
        lock_reason=lock_reason,
        lock_snapshot=await _lock_snapshot(db, inventory, approval),
    )
    db.add(lock)
    inventory.status = InventoryStatus.LOCKED
    inventory.locked_at = now

    await record_audit_event(
        db,
        principal,
        action="inventory.locked",
        entity_type="inventory",
        entity_id=inventory.id,
        event_data={
            "approval_id": str(approval.id),
            "calculation_run_id": str(approval.calculation_run_id),
            "lock_reason": lock_reason,
        },
    )
    await db.commit()
    await db.refresh(lock)
    return lock


async def request_restatement(
    db: AsyncSession,
    principal: CurrentPrincipal,
    inventory_id: UUID,
    payload: RestatementRequestCreate,
) -> InventoryRestatement:
    inventory = await _get_inventory(db, principal.tenant_id, inventory_id)
    if inventory.status not in {
        InventoryStatus.APPROVED,
        InventoryStatus.LOCKED,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only approved or locked inventories can be restated.",
        )

    open_request = await db.scalar(
        select(InventoryRestatement).where(
            InventoryRestatement.original_inventory_id == inventory.id,
            InventoryRestatement.status.in_(
                [
                    RestatementStatus.REQUESTED,
                    RestatementStatus.UNDER_REVIEW,
                    RestatementStatus.APPROVED,
                ]
            ),
        )
    )
    if open_request is not None:
        return open_request

    restatement = InventoryRestatement(
        tenant_id=principal.tenant_id,
        original_inventory_id=inventory.id,
        status=RestatementStatus.REQUESTED,
        requested_by=principal.subject,
        requested_at=datetime.now(UTC),
        reason=payload.reason,
        materiality_assessment=payload.materiality_assessment,
        requested_changes=payload.requested_changes,
    )
    db.add(restatement)
    inventory.status = InventoryStatus.RESTATEMENT_REQUIRED

    await record_audit_event(
        db,
        principal,
        action="inventory.restatement.requested",
        entity_type="inventory_restatement",
        entity_id=restatement.id,
        event_data={
            "inventory_id": str(inventory.id),
            "reason": payload.reason,
            "materiality_assessment": payload.materiality_assessment,
        },
    )
    await db.commit()
    await db.refresh(restatement)
    return restatement


async def decide_restatement(
    db: AsyncSession,
    principal: CurrentPrincipal,
    restatement_id: UUID,
    payload: RestatementDecision,
) -> InventoryRestatement:
    restatement = await get_restatement(
        db,
        principal.tenant_id,
        restatement_id,
    )
    if restatement is None:
        raise HTTPException(status_code=404, detail="Restatement not found.")
    if restatement.requested_by == principal.subject:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The requester cannot decide their own restatement.",
        )
    if restatement.status not in {
        RestatementStatus.REQUESTED,
        RestatementStatus.UNDER_REVIEW,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Restatement cannot be decided in its current state.",
        )

    original = await _get_inventory(
        db,
        principal.tenant_id,
        restatement.original_inventory_id,
    )
    restatement.status = payload.decision
    restatement.reviewed_by = principal.subject
    restatement.reviewed_at = datetime.now(UTC)
    restatement.decision_reason = payload.decision_reason

    if payload.decision == RestatementStatus.APPROVED:
        replacement = Inventory(
            tenant_id=original.tenant_id,
            reporting_period_id=original.reporting_period_id,
            name=f"{original.name} - Restatement",
            status=InventoryStatus.DRAFT,
            version=original.version + 1,
        )
        db.add(replacement)
        await db.flush()
        restatement.replacement_inventory_id = replacement.id
        original.status = InventoryStatus.SUPERSEDED
    else:
        original.status = (
            InventoryStatus.LOCKED
            if original.locked_at is not None
            else InventoryStatus.APPROVED
        )

    await record_audit_event(
        db,
        principal,
        action=f"inventory.restatement.{payload.decision.value}",
        entity_type="inventory_restatement",
        entity_id=restatement.id,
        event_data={
            "decision_reason": payload.decision_reason,
            "replacement_inventory_id": (
                str(restatement.replacement_inventory_id)
                if restatement.replacement_inventory_id
                else None
            ),
        },
    )
    await db.commit()
    await db.refresh(restatement)
    return restatement


async def complete_restatement(
    db: AsyncSession,
    principal: CurrentPrincipal,
    restatement_id: UUID,
) -> InventoryRestatement:
    restatement = await get_restatement(
        db,
        principal.tenant_id,
        restatement_id,
    )
    if restatement is None:
        raise HTTPException(status_code=404, detail="Restatement not found.")
    if restatement.status != RestatementStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only approved restatements can be completed.",
        )
    if restatement.replacement_inventory_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Restatement does not have a replacement inventory.",
        )

    replacement = await _get_inventory(
        db,
        principal.tenant_id,
        restatement.replacement_inventory_id,
    )
    if replacement.status not in {
        InventoryStatus.APPROVED,
        InventoryStatus.LOCKED,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Replacement inventory must be approved or locked.",
        )

    restatement.status = RestatementStatus.COMPLETED
    restatement.completed_at = datetime.now(UTC)

    await record_audit_event(
        db,
        principal,
        action="inventory.restatement.completed",
        entity_type="inventory_restatement",
        entity_id=restatement.id,
        event_data={
            "replacement_inventory_id": str(replacement.id),
        },
    )
    await db.commit()
    await db.refresh(restatement)
    return restatement


async def generate_audit_report(
    db: AsyncSession,
    principal: CurrentPrincipal,
    inventory_id: UUID,
    *,
    finalize: bool,
) -> AuditReport:
    inventory = await _get_inventory(db, principal.tenant_id, inventory_id)
    if inventory.status not in {
        InventoryStatus.APPROVED,
        InventoryStatus.LOCKED,
        InventoryStatus.SUPERSEDED,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inventory must be approved before report generation.",
        )

    approval = await db.scalar(
        select(InventoryApproval)
        .where(
            InventoryApproval.inventory_id == inventory.id,
            InventoryApproval.status == ApprovalStatus.APPROVED,
        )
        .order_by(InventoryApproval.version.desc())
    )
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No approved inventory approval was found.",
        )

    payload = await _build_audit_report_payload(
        db,
        inventory,
        approval,
    )
    report_hash = canonical_json_sha256(payload)
    existing = await db.scalar(
        select(AuditReport).where(AuditReport.report_sha256 == report_hash)
    )
    if existing is not None:
        return existing

    next_version = int(
        (
            await db.scalar(
                select(func.coalesce(func.max(AuditReport.version), 0)).where(
                    AuditReport.inventory_id == inventory.id
                )
            )
        )
        or 0
    ) + 1

    now = datetime.now(UTC)
    report = AuditReport(
        tenant_id=principal.tenant_id,
        inventory_id=inventory.id,
        calculation_run_id=approval.calculation_run_id,
        approval_id=approval.id,
        version=next_version,
        status=ReportStatus.FINAL if finalize else ReportStatus.DRAFT,
        generated_by=principal.subject,
        generated_at=now,
        finalized_by=principal.subject if finalize else None,
        finalized_at=now if finalize else None,
        report_sha256=report_hash,
        report_payload=payload,
    )
    db.add(report)

    if finalize:
        previous_reports = list(
            (
                await db.scalars(
                    select(AuditReport).where(
                        AuditReport.inventory_id == inventory.id,
                        AuditReport.status == ReportStatus.FINAL,
                    )
                )
            ).all()
        )
        for previous in previous_reports:
            previous.status = ReportStatus.SUPERSEDED
            previous.superseded_by_report_id = report.id

    await record_audit_event(
        db,
        principal,
        action="audit_report.generated",
        entity_type="audit_report",
        entity_id=report.id,
        event_data={
            "inventory_id": str(inventory.id),
            "version": next_version,
            "status": report.status.value,
            "report_sha256": report_hash,
        },
    )
    await db.commit()
    await db.refresh(report)
    return report


async def get_approval(
    db: AsyncSession,
    tenant_id: UUID,
    approval_id: UUID,
) -> InventoryApproval | None:
    return await db.scalar(
        select(InventoryApproval).where(
            InventoryApproval.id == approval_id,
            InventoryApproval.tenant_id == tenant_id,
        )
    )


async def get_restatement(
    db: AsyncSession,
    tenant_id: UUID,
    restatement_id: UUID,
) -> InventoryRestatement | None:
    return await db.scalar(
        select(InventoryRestatement).where(
            InventoryRestatement.id == restatement_id,
            InventoryRestatement.tenant_id == tenant_id,
        )
    )


async def get_audit_report(
    db: AsyncSession,
    tenant_id: UUID,
    report_id: UUID,
) -> AuditReport | None:
    return await db.scalar(
        select(AuditReport).where(
            AuditReport.id == report_id,
            AuditReport.tenant_id == tenant_id,
        )
    )


async def _approval_checks(
    db: AsyncSession,
    inventory: Inventory,
    run: CalculationRun,
) -> dict[str, bool]:
    activity_count = int(
        (
            await db.scalar(
                select(func.count())
                .select_from(ActivityRecord)
                .where(
                    ActivityRecord.inventory_id == inventory.id,
                    ActivityRecord.is_current.is_(True),
                )
            )
        )
        or 0
    )
    result_count = int(
        (
            await db.scalar(
                select(func.count())
                .select_from(CalculationResult)
                .where(CalculationResult.calculation_run_id == run.id)
            )
        )
        or 0
    )
    missing_factor_lineage = int(
        (
            await db.scalar(
                select(func.count())
                .select_from(CalculationResult)
                .where(
                    CalculationResult.calculation_run_id == run.id,
                    CalculationResult.selected_factor_id.is_(None),
                    CalculationResult.method
                    != "external_operational_result",
                )
            )
        )
        or 0
    )
    boundary_count = int(
        (
            await db.scalar(
                select(func.count())
                .select_from(OrganisationalBoundary)
                .join(
                    ReportingPeriod,
                    ReportingPeriod.id
                    == OrganisationalBoundary.reporting_period_id,
                )
                .where(
                    ReportingPeriod.id == inventory.reporting_period_id,
                    OrganisationalBoundary.status.in_(
                        [BoundaryStatus.APPROVED, BoundaryStatus.LOCKED]
                    ),
                )
            )
        )
        or 0
    )
    evidence_count = int(
        (
            await db.scalar(
                select(func.count())
                .select_from(ActivityRecord)
                .where(
                    ActivityRecord.inventory_id == inventory.id,
                    ActivityRecord.is_current.is_(True),
                    ActivityRecord.evidence_reference.is_not(None),
                )
            )
        )
        or 0
    )

    return {
        "evidence_complete": activity_count > 0 and evidence_count == activity_count,
        "boundary_complete": boundary_count > 0,
        "factor_lineage_complete": missing_factor_lineage == 0,
        "calculation_complete": (
            run.status == CalculationRunStatus.COMPLETED
            and result_count == activity_count
            and activity_count > 0
        ),
    }


async def _approval_snapshot(
    db: AsyncSession,
    inventory: Inventory,
    run: CalculationRun,
) -> dict[str, object]:
    period = await db.get(ReportingPeriod, inventory.reporting_period_id)
    return {
        "inventory_id": str(inventory.id),
        "inventory_version": inventory.version,
        "calculation_run_id": str(run.id),
        "calculation_run_version": run.version,
        "reporting_period": {
            "id": str(period.id) if period else None,
            "start_date": period.start_date.isoformat() if period else None,
            "end_date": period.end_date.isoformat() if period else None,
        },
        "activity_count": run.activity_count,
        "result_count": run.result_count,
        "failed_count": run.failed_count,
        "factor_policy_version": run.factor_policy_version,
        "software_version": run.software_version,
    }


async def _lock_snapshot(
    db: AsyncSession,
    inventory: Inventory,
    approval: InventoryApproval,
) -> dict[str, object]:
    result_count = int(
        (
            await db.scalar(
                select(func.count())
                .select_from(CalculationResult)
                .where(
                    CalculationResult.calculation_run_id
                    == approval.calculation_run_id
                )
            )
        )
        or 0
    )
    return {
        "inventory_id": str(inventory.id),
        "inventory_version": inventory.version,
        "approval_id": str(approval.id),
        "approval_version": approval.version,
        "calculation_run_id": str(approval.calculation_run_id),
        "result_count": result_count,
        "approval_snapshot": approval.review_snapshot,
    }


async def _build_audit_report_payload(
    db: AsyncSession,
    inventory: Inventory,
    approval: InventoryApproval,
) -> dict[str, object]:
    period = await db.get(ReportingPeriod, inventory.reporting_period_id)
    run = await db.get(CalculationRun, approval.calculation_run_id)
    if period is None or run is None:
        raise HTTPException(
            status_code=500,
            detail="Inventory reporting context is incomplete.",
        )

    results = list(
        (
            await db.scalars(
                select(CalculationResult).where(
                    CalculationResult.calculation_run_id == run.id
                )
            )
        ).all()
    )

    total_kg = sum(
        (result.allocated_kg_co2e for result in results),
        Decimal("0"),
    )
    grouped: dict[str, Decimal] = {}
    for result in results:
        key = result.scope.value
        if result.scope_3_category is not None:
            key = f"{key}:category_{result.scope_3_category}"
        if result.scope_2_method.value != "not_applicable":
            key = f"{key}:{result.scope_2_method.value}"
        grouped[key] = grouped.get(key, Decimal("0")) + result.allocated_kg_co2e

    factor_ids = {
        result.selected_factor_id
        for result in results
        if result.selected_factor_id is not None
    }
    factor_set_ids: set[UUID] = set()
    if factor_ids:
        factor_set_ids = set(
            (
                await db.scalars(
                    select(EmissionFactor.factor_set_id).where(
                        EmissionFactor.id.in_(factor_ids)
                    )
                )
            ).all()
        )
    factor_sets = []
    if factor_set_ids:
        sets = list(
            (
                await db.scalars(
                    select(EmissionFactorSet).where(
                        EmissionFactorSet.id.in_(factor_set_ids)
                    )
                )
            ).all()
        )
        factor_sets = [
            {
                "id": str(item.id),
                "publisher": item.publisher,
                "dataset_name": item.dataset_name,
                "dataset_version": item.dataset_version,
                "reporting_year": item.reporting_year,
                "source_sha256": item.source_sha256,
            }
            for item in sets
        ]

    boundary = await db.scalar(
        select(OrganisationalBoundary)
        .where(
            OrganisationalBoundary.reporting_period_id == period.id,
            OrganisationalBoundary.status.in_(
                [BoundaryStatus.APPROVED, BoundaryStatus.LOCKED]
            ),
        )
        .order_by(OrganisationalBoundary.version.desc())
    )

    quality_scores = [
        activity.data_quality_score
        for activity in (
            await db.scalars(
                select(ActivityRecord).where(
                    ActivityRecord.inventory_id == inventory.id,
                    ActivityRecord.is_current.is_(True),
                )
            )
        ).all()
    ]
    average_quality = (
        sum(quality_scores) / len(quality_scores)
        if quality_scores
        else None
    )

    return {
        "report_schema_version": "1.0",
        "inventory": {
            "id": str(inventory.id),
            "name": inventory.name,
            "version": inventory.version,
            "status": inventory.status.value,
            "approved_at": (
                inventory.approved_at.isoformat()
                if inventory.approved_at
                else None
            ),
            "locked_at": (
                inventory.locked_at.isoformat()
                if inventory.locked_at
                else None
            ),
        },
        "reporting_period": {
            "id": str(period.id),
            "name": period.name,
            "start_date": period.start_date.isoformat(),
            "end_date": period.end_date.isoformat(),
            "is_base_year": period.is_base_year,
        },
        "organisational_boundary": (
            {
                "id": str(boundary.id),
                "version": boundary.version,
                "consolidation_approach": (
                    boundary.consolidation_approach.value
                ),
                "status": boundary.status.value,
                "effective_from": boundary.effective_from.isoformat(),
                "effective_to": boundary.effective_to.isoformat(),
            }
            if boundary
            else None
        ),
        "approval": {
            "id": str(approval.id),
            "version": approval.version,
            "requested_by": approval.requested_by,
            "reviewer_id": approval.reviewer_id,
            "decided_at": (
                approval.decided_at.isoformat()
                if approval.decided_at
                else None
            ),
            "decision_reason": approval.decision_reason,
        },
        "calculation_run": {
            "id": str(run.id),
            "version": run.version,
            "software_version": run.software_version,
            "factor_policy_version": run.factor_policy_version,
            "activity_count": run.activity_count,
            "result_count": run.result_count,
            "failed_count": run.failed_count,
            "completed_at": (
                run.completed_at.isoformat()
                if run.completed_at
                else None
            ),
        },
        "totals": {
            "total_kg_co2e": str(total_kg),
            "total_t_co2e": str(total_kg / Decimal("1000")),
            "by_scope_and_category": {
                key: str(value)
                for key, value in sorted(grouped.items())
            },
        },
        "factor_sets": factor_sets,
        "data_quality": {
            "activity_count": len(quality_scores),
            "average_score": average_quality,
        },
        "results": [
            {
                "id": str(result.id),
                "activity_id": str(result.activity_id),
                "method": result.method.value,
                "scope": result.scope.value,
                "scope_3_category": result.scope_3_category,
                "scope_2_method": result.scope_2_method.value,
                "selected_factor_id": (
                    str(result.selected_factor_id)
                    if result.selected_factor_id
                    else None
                ),
                "gross_kg_co2e": str(result.gross_kg_co2e),
                "allocated_kg_co2e": str(result.allocated_kg_co2e),
                "methodology_version": result.methodology_version,
                "warnings": result.warnings,
                "intermediate_values": result.intermediate_values,
            }
            for result in results
        ],
    }
