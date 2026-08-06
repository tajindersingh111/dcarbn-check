from inspect import signature

import pytest
from pydantic import ValidationError

from app.models.inventory_governance import (
    ApprovalStatus,
    RestatementStatus,
)
from app.services.inventory_governance import _lock_snapshot
from app.schemas.inventory_governance import (
    ApprovalDecision,
    ReportGenerateRequest,
    RestatementDecision,
)


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
