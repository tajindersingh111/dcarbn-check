from decimal import Decimal
from inspect import signature

import pytest
from app.models.inventory_governance import (
    ApprovalStatus,
    RestatementStatus,
    RestatementTrigger,
)
from app.schemas.inventory_governance import (
    ApprovalDecision,
    ReportGenerateRequest,
    RestatementDecision,
    RestatementRequestCreate,
)
from app.services.inventory_governance import (
    _assess_assurance_readiness,
    _lock_snapshot,
)
from pydantic import ValidationError


def test_approval_decision_accepts_approved() -> None:
    payload = ApprovalDecision(
        decision=ApprovalStatus.APPROVED,
        decision_reason="All approval controls and supporting evidence are complete.",
    )

    assert payload.decision == ApprovalStatus.APPROVED


def test_approval_decision_rejects_pending() -> None:
    with pytest.raises(ValidationError):
        ApprovalDecision(
            decision=ApprovalStatus.PENDING,
            decision_reason="This is not a valid final decision.",
        )


def test_restatement_decision_accepts_rejected() -> None:
    payload = RestatementDecision(
        decision=RestatementStatus.REJECTED,
        decision_reason="The identified variance is not material to the inventory.",
    )

    assert payload.decision == RestatementStatus.REJECTED


def test_restatement_request_accepts_quantified_materiality() -> None:
    payload = RestatementRequestCreate(
        trigger=RestatementTrigger.MATERIAL_ERROR,
        reason="A material source-data error was identified after approval.",
        materiality_assessment="The estimated change is material to reported emissions.",
        estimated_impact_percent="6.25",
    )

    assert payload.estimated_impact_percent is not None
    assert payload.estimated_impact_percent.as_tuple().exponent == -2


def test_restatement_request_requires_override_rationale() -> None:
    with pytest.raises(ValidationError):
        RestatementRequestCreate(
            trigger=RestatementTrigger.METHODOLOGY_CHANGE,
            reason="The governed calculation methodology has changed.",
            materiality_assessment="Impact cannot yet be quantified reliably.",
            qualitative_override=True,
        )


def test_boundary_restatement_requires_change_summary() -> None:
    with pytest.raises(ValidationError):
        RestatementRequestCreate(
            trigger=RestatementTrigger.ACQUISITION,
            reason="A controlled business was acquired during the period.",
            materiality_assessment="The acquisition changes the inventory boundary.",
            estimated_impact_percent="8.0",
        )


def test_report_generation_requires_explicit_scope2_headline_basis() -> None:
    with pytest.raises(ValidationError):
        ReportGenerateRequest(finalize=False)


def test_report_generation_accepts_market_based_headline_basis() -> None:
    payload = ReportGenerateRequest(
        finalize=True,
        scope_2_headline_basis="market_based",
    )

    assert payload.scope_2_headline_basis.value == "market_based"


def test_lock_snapshot_keeps_runtime_call_contract() -> None:
    assert list(signature(_lock_snapshot).parameters) == [
        "db",
        "inventory",
        "approval",
    ]


def test_assurance_readiness_passes_only_complete_controls() -> None:
    assessment = _assess_assurance_readiness(
        boundary_approved=True,
        approval_separated=True,
        result_count=3,
        result_lineage_complete=True,
        evidence_coverage_percent=Decimal(100),
        included_scope3_categories={4},
        calculated_scope3_categories={4},
        scope2_present=True,
        scope2_dual_reporting_complete=True,
        unresolved_warning_count=0,
        open_restatement_count=0,
    )

    assert assessment["ready"] is True
    assert assessment["status"] == "assurance_ready"
    assert assessment["blockers"] == []


def test_assurance_readiness_returns_specific_blockers() -> None:
    assessment = _assess_assurance_readiness(
        boundary_approved=True,
        approval_separated=True,
        result_count=2,
        result_lineage_complete=True,
        evidence_coverage_percent=Decimal(50),
        included_scope3_categories={1, 4},
        calculated_scope3_categories={4},
        scope2_present=False,
        scope2_dual_reporting_complete=False,
        unresolved_warning_count=1,
        open_restatement_count=0,
    )

    assert assessment["ready"] is False
    assert assessment["status"] == "draft_calculation_not_fully_validated"
    failed = {item["code"] for item in assessment["checks"] if not item["passed"]}
    assert failed == {
        "evidence_coverage",
        "scope3_included_category_results",
        "unresolved_calculation_warnings",
    }
