from decimal import Decimal

import pytest

from app.calculations.engine import (
    CalculationError,
    calculate_activity_factor_emissions,
    kg_to_tonnes,
)


def test_calculates_allocated_emissions() -> None:
    result = calculate_activity_factor_emissions(
        factor_activity_value=Decimal("100"),
        factor_value=Decimal("2.51"),
        allocation_percentage=Decimal("80"),
    )

    assert result.gross_kg_co2e == Decimal("251.00")
    assert result.allocation_multiplier == Decimal("0.8")
    assert result.allocated_kg_co2e == Decimal("200.800")


def test_converts_kg_to_tonnes() -> None:
    assert kg_to_tonnes(Decimal("1250")) == Decimal("1.25")


@pytest.mark.parametrize(
    ("activity_value", "factor_value", "allocation"),
    [
        (Decimal("-1"), Decimal("1"), Decimal("100")),
        (Decimal("1"), Decimal("-1"), Decimal("100")),
        (Decimal("1"), Decimal("1"), Decimal("101")),
    ],
)
def test_rejects_invalid_inputs(
    activity_value: Decimal,
    factor_value: Decimal,
    allocation: Decimal,
) -> None:
    with pytest.raises(CalculationError):
        calculate_activity_factor_emissions(
            factor_activity_value=activity_value,
            factor_value=factor_value,
            allocation_percentage=allocation,
        )
