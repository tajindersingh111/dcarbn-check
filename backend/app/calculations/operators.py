from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any

Operator = Callable[[dict[str, Decimal], dict[str, Any]], Decimal]


def _activity_times_factor(inputs: dict[str, Decimal], _: dict[str, Any]) -> Decimal:
    return inputs["activity_value"] * inputs["factor_value"]


def _mass_balance_times_factor(inputs: dict[str, Decimal], _: dict[str, Any]) -> Decimal:
    emitted = (
        inputs["opening_stock"]
        + inputs["purchases"]
        - inputs["closing_stock"]
        - inputs["recovered"]
    )
    if emitted < 0:
        raise ValueError("Mass-balance result cannot be negative.")
    return emitted * inputs["factor_value"]


def _allocated_reported_result(inputs: dict[str, Decimal], _: dict[str, Any]) -> Decimal:
    percentage = inputs.get("allocation_percentage", Decimal("100"))
    if percentage < 0 or percentage > 100:
        raise ValueError("Allocation percentage must be between 0 and 100.")
    return inputs["reported_kg_co2e"] * percentage / Decimal("100")


def _identity_reported_result(inputs: dict[str, Decimal], _: dict[str, Any]) -> Decimal:
    return inputs["reported_kg_co2e"]


OPERATORS: dict[str, Operator] = {
    "activity_times_factor.v1": _activity_times_factor,
    "mass_balance_times_factor.v1": _mass_balance_times_factor,
    "allocated_reported_result.v1": _allocated_reported_result,
    "identity_reported_result.v1": _identity_reported_result,
}


def execute_operator(
    operator_identifier: str,
    *,
    inputs: dict[str, Decimal],
    configuration: dict[str, Any] | None = None,
) -> Decimal:
    try:
        operator = OPERATORS[operator_identifier]
    except KeyError as exc:
        raise ValueError("Methodology pack references an unapproved operator.") from exc
    return operator(inputs, configuration or {})
