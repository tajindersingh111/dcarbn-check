import pytest
from pydantic import ValidationError

from app.models.inventory_governance import (
    ApprovalStatus,
    RestatementStatus,
)
from app.schemas.inventory_governance import (
    ApprovalDecision,
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
