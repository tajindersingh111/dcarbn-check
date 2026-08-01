from decimal import Decimal

import pytest

from app.models.boundary import ConsolidationApproach, MembershipDecision
from app.services.boundaries import calculate_membership_outcome


@pytest.mark.parametrize(
    (
        "approach",
        "decision",
        "ownership",
        "operational_control",
        "financial_control",
        "expected_included",
        "expected_allocation",
    ),
    [
        (
            ConsolidationApproach.OPERATIONAL_CONTROL,
            MembershipDecision.AUTO,
            Decimal("25.00"),
            True,
            False,
            True,
            Decimal("100.00"),
        ),
        (
            ConsolidationApproach.OPERATIONAL_CONTROL,
            MembershipDecision.AUTO,
            Decimal("100.00"),
            False,
            True,
            False,
            Decimal("0.00"),
        ),
        (
            ConsolidationApproach.FINANCIAL_CONTROL,
            MembershipDecision.AUTO,
            Decimal("10.00"),
            False,
            True,
            True,
            Decimal("100.00"),
        ),
        (
            ConsolidationApproach.EQUITY_SHARE,
            MembershipDecision.AUTO,
            Decimal("37.50"),
            False,
            False,
            True,
            Decimal("37.50"),
        ),
        (
            ConsolidationApproach.EQUITY_SHARE,
            MembershipDecision.EXCLUDED,
            Decimal("37.50"),
            False,
            False,
            False,
            Decimal("0.00"),
        ),
        (
            ConsolidationApproach.OPERATIONAL_CONTROL,
            MembershipDecision.INCLUDED,
            Decimal("0.00"),
            False,
            False,
            True,
            Decimal("100.00"),
        ),
    ],
)
def test_calculate_membership_outcome(
    approach: ConsolidationApproach,
    decision: MembershipDecision,
    ownership: Decimal,
    operational_control: bool,
    financial_control: bool,
    expected_included: bool,
    expected_allocation: Decimal,
) -> None:
    included, allocation = calculate_membership_outcome(
        approach=approach,
        decision=decision,
        ownership_percentage=ownership,
        has_operational_control=operational_control,
        has_financial_control=financial_control,
    )

    assert included is expected_included
    assert allocation == expected_allocation
