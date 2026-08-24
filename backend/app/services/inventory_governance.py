from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

from app.auth.dependencies import CurrentPrincipal
from app.calculations.governed_methods import (
    HVO_2024_BIOGENIC_CO2_KG_PER_LITRE,
    HVO_2024_SCOPE1_FACTOR_KG_CO2E_PER_LITRE,
    HVO_2024_WTT_FACTOR_KG_CO2E_PER_LITRE,
    GovernedCalculationMethod,
)
from app.calculations.scope2_reporting import validate_market_based_evidence
from app.integrations.data.hashing import canonical_json_sha256
from app.models.activity import ActivityRecord, EmissionScope, Scope2Method
from app.models.boundary import BoundaryStatus, OrganisationalBoundary
from app.models.calculation import (
    CalculationMethod,
    CalculationResult,
    CalculationRun,
    CalculationRunStatus,
)
from app.models.data_integration import DataCalculationComparison
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
from app.schemas.calculation import Scope2HeadlineBasis
from app.schemas.inventory_governance import (
    ApprovalDecision,
    RestatementDecision,
    RestatementRequestCreate,
)
from app.services.audit import record_audit_event
from app.services.scope3_governance import (
    list_scope3_dispositions,
    scope3_disposition_payload,
    scope3_dispositions_are_approved,
)
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession


def _build_hvo_2024_disclosure(
    results: list[CalculationResult],
    activity_by_id: dict[UUID, ActivityRecord],
) -> dict[str, object] | None:
    scope1_method = GovernedCalculationMethod.SCOPE1_MOBILE_HVO_LITRES_2024.value
    wtt_method = GovernedCalculationMethod.SCOPE3_CATEGORY3_HVO_WTT_LITRES_2024.value
    scope1_results = [
        result
        for result in results
        if (
            activity_by_id.get(result.activity_id)
            and activity_by_id[result.activity_id].metadata_json.get("calculation_method_id")
            == scope1_method
        )
    ]
    wtt_results = [
        result
        for result in results
        if (
            activity_by_id.get(result.activity_id)
            and activity_by_id[result.activity_id].metadata_json.get("calculation_method_id")
            == wtt_method
        )
    ]
    if not scope1_results and not wtt_results:
        return None

    scope1_litres = sum(
        (result.factor_activity_value * result.allocation_multiplier for result in scope1_results),
        Decimal(0),
    )
    wtt_litres = sum(
        (result.factor_activity_value * result.allocation_multiplier for result in wtt_results),
        Decimal(0),
    )
    scope1_kg = sum(
        (result.allocated_kg_co2e for result in scope1_results),
        Decimal(0),
    )
    wtt_kg = sum(
        (result.allocated_kg_co2e for result in wtt_results),
        Decimal(0),
    )
    biogenic_co2_kg = scope1_litres * HVO_2024_BIOGENIC_CO2_KG_PER_LITRE
    complete = bool(scope1_results and wtt_results and scope1_litres == wtt_litres)
    reconciliation_note = (
        "Scope 1 and Scope 3 Category 3 HVO litres reconcile."
        if complete
        else (
            "HVO reporting is incomplete: the Scope 1 and Scope 3 Category 3 "
            "well-to-tank entries must both be present and use matching litres."
        )
    )
    return {
        "method": "UK Government 2024 Biodiesel HVO",
        "reporting_year": 2024,
        "hvo_litres": str(scope1_litres),
        "scope_3_hvo_litres": str(wtt_litres),
        "complete": complete,
        "reconciliation_note": reconciliation_note,
        "scope_1_kg_co2e": str(scope1_kg),
        "scope_3_category_3_wtt_kg_co2e": str(wtt_kg),
        "biogenic_co2_outside_scopes_kg": str(biogenic_co2_kg),
        "scope_1_factor_kg_co2e_per_litre": str(HVO_2024_SCOPE1_FACTOR_KG_CO2E_PER_LITRE),
        "scope_3_wtt_factor_kg_co2e_per_litre": str(HVO_2024_WTT_FACTOR_KG_CO2E_PER_LITRE),
        "biogenic_co2_factor_kg_per_litre": str(HVO_2024_BIOGENIC_CO2_KG_PER_LITRE),
        "source_factor_ids": {
            "scope_1": "2_103_1036_8_1",
            "scope_3_category_3_wtt": "12_900_1036_8_1",
            "biogenic_co2_outside_scopes": "99_103_1036_8_2",
        },
        "note": (
            "HVO is reported only where the customer supplied evidence confirming "
            "the fuel type. UK Government 2024 factors report direct CH4 and N2O "
            "in Scope 1 and upstream well-to-tank emissions in Scope 3 Category 3. "
            "Combustion CO2 is biogenic and disclosed outside Scopes 1, 2 and 3; "
            "it is excluded from the headline inventory total. The Government "
            "well-to-tank factor is a UK average; supplier- and feedstock-specific "
            "evidence should be used when available."
        ),
        "source_reference": (
            "https://www.gov.uk/government/publications/"
            "greenhouse-gas-reporting-conversion-factors-2024"
        ),
        "methodology_reference": (
            "https://assets.publishing.service.gov.uk/media/"
            "66a9fe4ca3c2a28abb50da4a/"
            "2024-greenhouse-gas-conversion-factors-methodology.pdf"
        ),
    }


def _assess_assurance_readiness(
    *,
    boundary_approved: bool,
    approval_separated: bool,
    result_count: int,
    result_lineage_complete: bool,
    evidence_coverage_percent: Decimal,
    included_scope3_categories: set[int],
    calculated_scope3_categories: set[int],
    scope2_present: bool,
    scope2_dual_reporting_complete: bool,
    bioenergy_reporting_complete: bool,
    unresolved_warning_count: int,
    open_restatement_count: int,
) -> dict[str, object]:
    """Return deterministic claim wording and the controls supporting it."""
    missing_scope3_categories = sorted(included_scope3_categories - calculated_scope3_categories)
    checks = [
        {
            "code": "approved_boundary",
            "passed": boundary_approved,
            "summary": "An approved or locked organisational boundary is recorded.",
        },
        {
            "code": "independent_approval",
            "passed": approval_separated,
            "summary": "The inventory preparer and approver are independently identified.",
        },
        {
            "code": "calculation_lineage",
            "passed": result_count > 0 and result_lineage_complete,
            "summary": (
                "Every result retains its activity, exact factor, formula and methodology version."
            ),
        },
        {
            "code": "evidence_coverage",
            "passed": evidence_coverage_percent == Decimal(100),
            "summary": "Every current activity has a supporting evidence reference.",
        },
        {
            "code": "scope3_included_category_results",
            "passed": not missing_scope3_categories,
            "summary": (
                "Every Scope 3 category marked included has a calculated result "
                "or must be returned to data collection."
            ),
            "missing_categories": missing_scope3_categories,
        },
        {
            "code": "scope2_dual_reporting",
            "passed": not scope2_present or scope2_dual_reporting_complete,
            "summary": (
                "Scope 2 location- and market-based totals are both disclosed "
                "when Scope 2 activity is reported."
            ),
        },
        {
            "code": "bioenergy_scope_coverage",
            "passed": bioenergy_reporting_complete,
            "summary": (
                "HVO Scope 1 and Scope 3 Category 3 well-to-tank entries are both "
                "present and use matching allocated litres."
            ),
        },
        {
            "code": "unresolved_calculation_warnings",
            "passed": unresolved_warning_count == 0,
            "summary": "No unresolved calculation or factor-resolution warnings remain.",
            "warning_count": unresolved_warning_count,
        },
        {
            "code": "open_restatements",
            "passed": open_restatement_count == 0,
            "summary": "No requested, under-review or approved restatement remains open.",
            "open_restatement_count": open_restatement_count,
        },
    ]
    blockers = [str(item["summary"]) for item in checks if not item["passed"]]
    ready = not blockers
    return {
        "status": ("assurance_ready" if ready else "draft_calculation_not_fully_validated"),
        "claim_wording": (
            "Assurance-ready reporting pack" if ready else "Draft — calculation not fully validated"
        ),
        "ready": ready,
        "checks": checks,
        "blockers": blockers,
        "external_assurance_required": True,
    }


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

    if not await scope3_dispositions_are_approved(
        db,
        principal.tenant_id,
        inventory.id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "All 15 Scope 3 category dispositions must be prepared and independently approved."
            ),
        )

    existing = await db.scalar(
        select(InventoryApproval).where(
            InventoryApproval.inventory_id == inventory.id,
            InventoryApproval.calculation_run_id == run.id,
            InventoryApproval.status.in_([ApprovalStatus.PENDING, ApprovalStatus.IN_REVIEW]),
        )
    )
    if existing is not None:
        return existing

    next_version = (
        int(
            (
                await db.scalar(
                    select(func.coalesce(func.max(InventoryApproval.version), 0)).where(
                        InventoryApproval.inventory_id == inventory.id
                    )
                )
            )
            or 0
        )
        + 1
    )

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

    period = await db.get(ReportingPeriod, inventory.reporting_period_id)
    if period is None:
        raise HTTPException(status_code=404, detail="Reporting period not found.")
    threshold = period.recalculation_significance_threshold_percent
    threshold_exceeded = (
        payload.estimated_impact_percent is not None
        and payload.estimated_impact_percent >= threshold
    )
    if not threshold_exceeded and not payload.qualitative_override:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Restatement impact does not meet the reporting-period significance "
                "threshold. Record a justified qualitative override to continue."
            ),
        )

    restatement = InventoryRestatement(
        tenant_id=principal.tenant_id,
        original_inventory_id=inventory.id,
        status=RestatementStatus.REQUESTED,
        requested_by=principal.subject,
        requested_at=datetime.now(UTC),
        reason=payload.reason,
        materiality_assessment=payload.materiality_assessment,
        trigger=payload.trigger,
        estimated_impact_percent=payload.estimated_impact_percent,
        significance_threshold_percent=threshold,
        threshold_exceeded=threshold_exceeded,
        qualitative_override=payload.qualitative_override,
        qualitative_override_rationale=payload.qualitative_override_rationale,
        boundary_change_summary=payload.boundary_change_summary,
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
            "trigger": payload.trigger.value,
            "estimated_impact_percent": (
                str(payload.estimated_impact_percent)
                if payload.estimated_impact_percent is not None
                else None
            ),
            "significance_threshold_percent": str(threshold),
            "threshold_exceeded": threshold_exceeded,
            "qualitative_override": payload.qualitative_override,
            "qualitative_override_rationale": (payload.qualitative_override_rationale),
            "boundary_change_summary": payload.boundary_change_summary,
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
            InventoryStatus.LOCKED if original.locked_at is not None else InventoryStatus.APPROVED
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
    scope_2_headline_basis: Scope2HeadlineBasis,
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

    if not await scope3_dispositions_are_approved(
        db,
        principal.tenant_id,
        inventory.id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approved Scope 3 category dispositions are required.",
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
        scope_2_headline_basis,
    )
    report_hash = canonical_json_sha256(payload)
    existing = await db.scalar(select(AuditReport).where(AuditReport.report_sha256 == report_hash))
    if existing is not None:
        return existing

    next_version = (
        int(
            (
                await db.scalar(
                    select(func.coalesce(func.max(AuditReport.version), 0)).where(
                        AuditReport.inventory_id == inventory.id
                    )
                )
            )
            or 0
        )
        + 1
    )

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
    return cast(
        InventoryApproval | None,
        await db.scalar(
            select(InventoryApproval).where(
                InventoryApproval.id == approval_id,
                InventoryApproval.tenant_id == tenant_id,
            )
        ),
    )


async def get_restatement(
    db: AsyncSession,
    tenant_id: UUID,
    restatement_id: UUID,
) -> InventoryRestatement | None:
    return cast(
        InventoryRestatement | None,
        await db.scalar(
            select(InventoryRestatement).where(
                InventoryRestatement.id == restatement_id,
                InventoryRestatement.tenant_id == tenant_id,
            )
        ),
    )


async def get_audit_report(
    db: AsyncSession,
    tenant_id: UUID,
    report_id: UUID,
) -> AuditReport | None:
    return cast(
        AuditReport | None,
        await db.scalar(
            select(AuditReport).where(
                AuditReport.id == report_id,
                AuditReport.tenant_id == tenant_id,
            )
        ),
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
                    CalculationResult.method != "external_operational_result",
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
                    ReportingPeriod.id == OrganisationalBoundary.reporting_period_id,
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
                .where(CalculationResult.calculation_run_id == approval.calculation_run_id)
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
    scope_2_headline_basis: Scope2HeadlineBasis,
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
                select(CalculationResult).where(CalculationResult.calculation_run_id == run.id)
            )
        ).all()
    )

    activities = list(
        (
            await db.scalars(
                select(ActivityRecord).where(
                    ActivityRecord.inventory_id == inventory.id,
                    ActivityRecord.is_current.is_(True),
                )
            )
        ).all()
    )
    activity_by_id = {activity.id: activity for activity in activities}
    hvo_2024_disclosure = _build_hvo_2024_disclosure(results, activity_by_id)

    market_evidence: list[dict[str, object]] = []
    market_results = [
        result
        for result in results
        if result.scope == EmissionScope.SCOPE_2
        and result.scope_2_method == Scope2Method.MARKET_BASED
    ]
    if scope_2_headline_basis == Scope2HeadlineBasis.MARKET_BASED:
        if not market_results:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Market-based Scope 2 cannot be the headline basis "
                    "without market-based calculation results."
                ),
            )
        for result in market_results:
            activity = activity_by_id.get(result.activity_id)
            if activity is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Market-based result is missing its source activity.",
                )
            try:
                evidence = validate_market_based_evidence(
                    activity.metadata_json,
                    evidence_reference=activity.evidence_reference,
                    activity_date=activity.activity_date,
                    geography_code=activity.geography_code,
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=str(exc),
                ) from exc
            if (
                result.factor_value is None
                or Decimal(str(evidence["factor_value"])) != result.factor_value
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Market-based contractual factor does not match "
                        "the factor used by the calculation result."
                    ),
                )
            market_evidence.append(
                {
                    "activity_id": str(activity.id),
                    **evidence,
                }
            )

    zero = Decimal(0)
    scope_1_kg = sum(
        (r.allocated_kg_co2e for r in results if r.scope == EmissionScope.SCOPE_1),
        zero,
    )
    scope_2_location_kg = sum(
        (
            r.allocated_kg_co2e
            for r in results
            if r.scope == EmissionScope.SCOPE_2 and r.scope_2_method == Scope2Method.LOCATION_BASED
        ),
        zero,
    )
    scope_2_market_kg = sum(
        (
            r.allocated_kg_co2e
            for r in results
            if r.scope == EmissionScope.SCOPE_2 and r.scope_2_method == Scope2Method.MARKET_BASED
        ),
        zero,
    )
    scope_3_kg = sum(
        (r.allocated_kg_co2e for r in results if r.scope == EmissionScope.SCOPE_3),
        zero,
    )
    selected_scope_2_kg = (
        scope_2_location_kg
        if scope_2_headline_basis == Scope2HeadlineBasis.LOCATION_BASED
        else scope_2_market_kg
    )
    total_kg = scope_1_kg + selected_scope_2_kg + scope_3_kg

    grouped: dict[str, Decimal] = {}
    for result in results:
        key = result.scope.value
        if result.scope_3_category is not None:
            key = f"{key}:category_{result.scope_3_category}"
        if result.scope_2_method.value != "not_applicable":
            key = f"{key}:{result.scope_2_method.value}"
        grouped[key] = grouped.get(key, Decimal(0)) + result.allocated_kg_co2e

    factor_ids = {
        result.selected_factor_id for result in results if result.selected_factor_id is not None
    }
    factor_set_ids: set[UUID] = set()
    if factor_ids:
        factor_set_ids = set(
            (
                await db.scalars(
                    select(EmissionFactor.factor_set_id).where(EmissionFactor.id.in_(factor_ids))
                )
            ).all()
        )
    factor_sets = []
    if factor_set_ids:
        sets = list(
            (
                await db.scalars(
                    select(EmissionFactorSet).where(EmissionFactorSet.id.in_(factor_set_ids))
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
            OrganisationalBoundary.status.in_([BoundaryStatus.APPROVED, BoundaryStatus.LOCKED]),
        )
        .order_by(OrganisationalBoundary.version.desc())
    )

    quality_scores = [activity.data_quality_score for activity in activities]
    average_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
    quality_distribution = Counter(activity.data_quality_level.value for activity in activities)
    evidenced_count = sum(1 for activity in activities if activity.evidence_reference)
    evidence_coverage = (
        Decimal(evidenced_count) * Decimal(100) / Decimal(len(activities))
        if activities
        else Decimal(0)
    )
    estimated_count = quality_distribution.get("estimated", 0)
    warning_count = sum(len(result.warnings) for result in results)
    uncertainty_sources = [
        (
            f"{estimated_count} activity record(s) use estimated data."
            if estimated_count
            else "No activity records are classified as estimated."
        ),
        (
            f"{warning_count} factor-resolution or calculation warning(s) "
            "require reviewer consideration."
        ),
        (f"Evidence is attached to {evidenced_count} of {len(activities)} activity record(s)."),
        (
            "Scenario uncertainty includes the selected organisational boundary, "
            "Scope 2 headline basis and approved Scope 3 category dispositions."
        ),
    ]
    scope3_dispositions = await list_scope3_dispositions(
        db,
        inventory.tenant_id,
        inventory.id,
    )

    result_ids = [result.id for result in results]
    comparisons = (
        list(
            (
                await db.scalars(
                    select(DataCalculationComparison).where(
                        DataCalculationComparison.tenant_id == inventory.tenant_id,
                        DataCalculationComparison.dcarbn_result_id.in_(result_ids),
                    )
                )
            ).all()
        )
        if result_ids
        else []
    )
    comparison_result_ids = {
        comparison.government_result_id
        for comparison in comparisons
        if comparison.government_result_id is not None
    }
    comparison_results = (
        list(
            (
                await db.scalars(
                    select(CalculationResult).where(CalculationResult.id.in_(comparison_result_ids))
                )
            ).all()
        )
        if comparison_result_ids
        else []
    )
    comparison_result_by_id = {result.id: result for result in [*results, *comparison_results]}
    calculation_comparisons = []
    for comparison in sorted(
        comparisons,
        key=lambda item: item.comparison_group_key,
    ):
        dcarbn_result = (
            comparison_result_by_id.get(comparison.dcarbn_result_id)
            if comparison.dcarbn_result_id is not None
            else None
        )
        government_result = (
            comparison_result_by_id.get(comparison.government_result_id)
            if comparison.government_result_id is not None
            else None
        )
        calculation_comparisons.append(
            {
                "comparison_id": str(comparison.id),
                "comparison_group_key": comparison.comparison_group_key,
                "status": comparison.status.value,
                "reporting_basis": comparison.reporting_basis.value,
                "basis_reason": comparison.basis_reason,
                "comparison_unavailable_reason": (comparison.comparison_unavailable_reason),
                "absolute_delta_kg_co2e": (
                    str(comparison.absolute_delta_kg_co2e)
                    if comparison.absolute_delta_kg_co2e is not None
                    else None
                ),
                "percentage_delta": (
                    str(comparison.percentage_delta)
                    if comparison.percentage_delta is not None
                    else None
                ),
                "dcarbn_result": (
                    {
                        "result_id": str(dcarbn_result.id),
                        "allocated_kg_co2e": str(dcarbn_result.allocated_kg_co2e),
                        "methodology_version": (dcarbn_result.methodology_version),
                        "factor_id": (
                            str(dcarbn_result.selected_factor_id)
                            if dcarbn_result.selected_factor_id
                            else None
                        ),
                        "lineage": dcarbn_result.intermediate_values,
                    }
                    if dcarbn_result
                    else None
                ),
                "uk_government_comparator": (
                    {
                        "result_id": str(government_result.id),
                        "allocated_kg_co2e": str(government_result.allocated_kg_co2e),
                        "methodology_version": (government_result.methodology_version),
                        "factor_id": (
                            str(government_result.selected_factor_id)
                            if government_result.selected_factor_id
                            else None
                        ),
                        "lineage": government_result.intermediate_values,
                    }
                    if government_result
                    else None
                ),
                "disclosure": (
                    "The UK Government result is a disclosure-only comparator "
                    "and is excluded from inventory totals. This comparison does "
                    "not imply UK Government endorsement of the DcarbN methodology."
                ),
            }
        )

    restatements = list(
        (
            await db.scalars(
                select(InventoryRestatement)
                .where(
                    InventoryRestatement.tenant_id == inventory.tenant_id,
                    or_(
                        InventoryRestatement.original_inventory_id == inventory.id,
                        InventoryRestatement.replacement_inventory_id == inventory.id,
                    ),
                )
                .order_by(InventoryRestatement.requested_at.asc())
            )
        ).all()
    )
    restatement_history = [
        {
            "id": str(item.id),
            "status": item.status.value,
            "trigger": item.trigger.value,
            "original_inventory_id": str(item.original_inventory_id),
            "replacement_inventory_id": (
                str(item.replacement_inventory_id) if item.replacement_inventory_id else None
            ),
            "reason": item.reason,
            "materiality_assessment": item.materiality_assessment,
            "estimated_impact_percent": (
                str(item.estimated_impact_percent)
                if item.estimated_impact_percent is not None
                else None
            ),
            "significance_threshold_percent": str(item.significance_threshold_percent),
            "threshold_exceeded": item.threshold_exceeded,
            "qualitative_override": item.qualitative_override,
            "qualitative_override_rationale": (item.qualitative_override_rationale),
            "boundary_change_summary": item.boundary_change_summary,
            "requested_changes": item.requested_changes,
            "requested_by": item.requested_by,
            "requested_at": item.requested_at.isoformat(),
            "reviewed_by": item.reviewed_by,
            "reviewed_at": (item.reviewed_at.isoformat() if item.reviewed_at else None),
            "decision_reason": item.decision_reason,
            "completed_at": (item.completed_at.isoformat() if item.completed_at else None),
        }
        for item in restatements
    ]
    included_scope3_categories = {
        item.category for item in scope3_dispositions if item.disposition.value == "included"
    }
    calculated_scope3_categories = {
        result.scope_3_category
        for result in results
        if result.scope == EmissionScope.SCOPE_3 and result.scope_3_category is not None
    }
    scope2_location_present = any(
        result.scope == EmissionScope.SCOPE_2
        and result.scope_2_method == Scope2Method.LOCATION_BASED
        for result in results
    )
    scope2_market_present = any(
        result.scope == EmissionScope.SCOPE_2 and result.scope_2_method == Scope2Method.MARKET_BASED
        for result in results
    )
    result_lineage_complete = all(
        (
            result.selected_factor_id is not None
            or (
                result.method == CalculationMethod.SUPPLIER_SPECIFIC_RESULT
                and bool(result.intermediate_values.get("evidence_reference"))
                and bool(result.intermediate_values.get("supplier_methodology"))
                and bool(result.intermediate_values.get("boundary_description"))
            )
        )
        and result.factor_value is not None
        and bool(result.calculation_formula)
        and bool(result.methodology_version)
        for result in results
    )
    open_restatement_count = sum(
        item.status
        in {
            RestatementStatus.REQUESTED,
            RestatementStatus.UNDER_REVIEW,
            RestatementStatus.APPROVED,
        }
        for item in restatements
    )
    assurance_readiness = _assess_assurance_readiness(
        boundary_approved=boundary is not None,
        approval_separated=(
            approval.reviewer_id is not None and approval.requested_by != approval.reviewer_id
        ),
        result_count=len(results),
        result_lineage_complete=result_lineage_complete,
        evidence_coverage_percent=evidence_coverage,
        included_scope3_categories=included_scope3_categories,
        calculated_scope3_categories=calculated_scope3_categories,
        scope2_present=scope2_location_present or scope2_market_present,
        scope2_dual_reporting_complete=(scope2_location_present and scope2_market_present),
        bioenergy_reporting_complete=(
            hvo_2024_disclosure is None or bool(hvo_2024_disclosure.get("complete"))
        ),
        unresolved_warning_count=warning_count,
        open_restatement_count=open_restatement_count,
    )

    return {
        "report_schema_version": "1.6",
        "assurance_readiness": assurance_readiness,
        "defensibility_statement": {
            "preparation_basis": (
                "Prepared from approved organisational boundaries, current activity "
                "records, deterministic factor resolution and versioned calculation "
                "methods. Every reported result retains activity, factor, formula, "
                "evidence and approval lineage."
            ),
            "assurance_limitation": (
                "This report is assurance-ready but is not an independent verification "
                "or assurance opinion. External assurance status must be evidenced "
                "separately."
            ),
        },
        "inventory": {
            "id": str(inventory.id),
            "name": inventory.name,
            "version": inventory.version,
            "status": inventory.status.value,
            "approved_at": (inventory.approved_at.isoformat() if inventory.approved_at else None),
            "locked_at": (inventory.locked_at.isoformat() if inventory.locked_at else None),
        },
        "reporting_period": {
            "id": str(period.id),
            "name": period.name,
            "start_date": period.start_date.isoformat(),
            "end_date": period.end_date.isoformat(),
            "is_base_year": period.is_base_year,
            "base_year_reason": period.base_year_reason,
            "recalculation_policy": period.recalculation_policy,
            "recalculation_significance_threshold_percent": str(
                period.recalculation_significance_threshold_percent
            ),
            "comparative_reporting_period_id": (
                str(period.comparative_reporting_period_id)
                if period.comparative_reporting_period_id
                else None
            ),
        },
        "restatement_history": restatement_history,
        "organisational_boundary": (
            {
                "id": str(boundary.id),
                "version": boundary.version,
                "consolidation_approach": (boundary.consolidation_approach.value),
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
            "decided_at": (approval.decided_at.isoformat() if approval.decided_at else None),
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
            "completed_at": (run.completed_at.isoformat() if run.completed_at else None),
        },
        "totals": {
            "scope_2_headline_basis": scope_2_headline_basis.value,
            "scope_1_kg_co2e": str(scope_1_kg),
            "scope_2_location_based_kg_co2e": str(scope_2_location_kg),
            "scope_2_market_based_kg_co2e": str(scope_2_market_kg),
            "scope_3_kg_co2e": str(scope_3_kg),
            "total_kg_co2e": str(total_kg),
            "total_t_co2e": str(total_kg / Decimal(1000)),
            "dual_reporting_complete": (scope_2_location_kg > zero and scope_2_market_kg > zero),
            "by_scope_and_category": {key: str(value) for key, value in sorted(grouped.items())},
        },
        "calculation_comparisons": calculation_comparisons,
        "scope_2_market_based_evidence": market_evidence,
        "scope_3_category_dispositions": scope3_disposition_payload(scope3_dispositions),
        "factor_sets": factor_sets,
        "bioenergy_disclosures": ([hvo_2024_disclosure] if hvo_2024_disclosure is not None else []),
        "data_quality": {
            "activity_count": len(quality_scores),
            "average_score": average_quality,
            "minimum_score": min(quality_scores) if quality_scores else None,
            "maximum_score": max(quality_scores) if quality_scores else None,
            "evidenced_activity_count": evidenced_count,
            "evidence_coverage_percent": str(evidence_coverage),
            "level_distribution": {
                key: quality_distribution.get(key, 0)
                for key in ("primary", "secondary", "estimated", "unknown")
            },
        },
        "uncertainty": {
            "quantitative_status": "not_quantified",
            "confidence_interval": None,
            "reason": (
                "A confidence interval is not reported because activity- and "
                "factor-level uncertainty distributions have not been supplied "
                "for every calculation. No unsupported precision is inferred."
            ),
            "qualitative_sources": uncertainty_sources,
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
                    str(result.selected_factor_id) if result.selected_factor_id else None
                ),
                "activity_date": (
                    activity_by_id[result.activity_id].activity_date.isoformat()
                    if result.activity_id in activity_by_id
                    else None
                ),
                "description": (
                    activity_by_id[result.activity_id].description
                    if result.activity_id in activity_by_id
                    else None
                ),
                "original_activity_value": str(result.original_activity_value),
                "original_activity_unit": result.original_activity_unit,
                "factor_activity_value": str(result.factor_activity_value),
                "factor_activity_unit": result.factor_activity_unit,
                "factor_value": (
                    str(result.factor_value) if result.factor_value is not None else None
                ),
                "allocation_percentage": str(result.allocation_percentage),
                "gross_kg_co2e": str(result.gross_kg_co2e),
                "allocated_kg_co2e": str(result.allocated_kg_co2e),
                "calculation_formula": result.calculation_formula,
                "methodology_version": result.methodology_version,
                "calculation_method_id": (
                    activity_by_id[result.activity_id].metadata_json.get("calculation_method_id")
                    if result.activity_id in activity_by_id
                    else None
                ),
                "evidence_reference": (
                    activity_by_id[result.activity_id].evidence_reference
                    if result.activity_id in activity_by_id
                    else None
                ),
                "warnings": result.warnings,
                "intermediate_values": result.intermediate_values,
            }
            for result in results
        ],
    }
