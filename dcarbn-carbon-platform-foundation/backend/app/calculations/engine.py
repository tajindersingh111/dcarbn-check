from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

HUNDRED = Decimal("100")
THOUSAND = Decimal("1000")


class CalculationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ActivityFactorCalculation:
    factor_activity_value: Decimal
    factor_value: Decimal
    allocation_percentage: Decimal
    allocation_multiplier: Decimal
    gross_kg_co2e: Decimal
    allocated_kg_co2e: Decimal
    formula: str


def calculate_activity_factor_emissions(
    *,
    factor_activity_value: Decimal,
    factor_value: Decimal,
    allocation_percentage: Decimal,
) -> ActivityFactorCalculation:
    if factor_activity_value < 0:
        raise CalculationError("Activity value cannot be negative.")
    if factor_value < 0:
        raise CalculationError("Emission factor cannot be negative.")
    if allocation_percentage < 0 or allocation_percentage > HUNDRED:
        raise CalculationError(
            "Allocation percentage must be between 0 and 100."
        )

    allocation_multiplier = allocation_percentage / HUNDRED
    gross = factor_activity_value * factor_value
    allocated = gross * allocation_multiplier

    return ActivityFactorCalculation(
        factor_activity_value=factor_activity_value,
        factor_value=factor_value,
        allocation_percentage=allocation_percentage,
        allocation_multiplier=allocation_multiplier,
        gross_kg_co2e=gross,
        allocated_kg_co2e=allocated,
        formula=(
            "allocated_kg_co2e = factor_activity_value "
            "× factor_value × (allocation_percentage ÷ 100)"
        ),
    )


def kg_to_tonnes(value: Decimal) -> Decimal:
    return value / THOUSAND
