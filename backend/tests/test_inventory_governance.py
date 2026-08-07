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
from app.services.inventory_governance import _lock_snapshot
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
