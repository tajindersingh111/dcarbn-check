from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from app.calculations.governed_methods import GovernedCalculationMethod
from app.services.data_comparisons import (
    COMPARISON_WARNING,
    _comparison_inputs,
    calculate_comparison_delta,
)


@pytest.mark.parametrize(
    ("dcarbn", "government", "absolute", "percentage"),
    [
        ("100", "100", "0", "0"),
        ("120", "100", "20", "20"),
        ("80", "100", "-20", "-20"),
    ],
)
def test_calculation_comparison_delta(
    dcarbn: str,
    government: str,
    absolute: str,
    percentage: str,
) -> None:
    actual_absolute, actual_percentage = calculate_comparison_delta(
        Decimal(dcarbn),
        Decimal(government),
    )

    assert actual_absolute == Decimal(absolute)
    assert actual_percentage == Decimal(percentage)


def test_calculation_comparison_delta_handles_zero_government_baseline() -> None:
    absolute, percentage = calculate_comparison_delta(
        Decimal("12.5"),
        Decimal("0"),
    )

    assert absolute == Decimal("12.5")
    assert percentage is None


def test_comparison_inputs_require_governed_method_and_classification() -> None:
    emission: Any = SimpleNamespace(
        confirmed_scope="scope_3",
        confirmed_scope_3_category=9,
        comparison_inputs_json={
            "government_method_id":
                "scope3.category9.average_diesel_van.tonne_km.uk_2026.v1",
            "activity_value": "1250",
            "activity_unit": "tonne.km",
        },
    )

    method, value, unit = _comparison_inputs(emission)

    assert method == (
        GovernedCalculationMethod
        .SCOPE3_CATEGORY9_AVERAGE_DIESEL_VAN_TONNE_KM_2026
    )
    assert value == Decimal("1250")
    assert unit == "tonne.km"


def test_comparison_inputs_reject_category_mismatch() -> None:
    emission: Any = SimpleNamespace(
        confirmed_scope="scope_3",
        confirmed_scope_3_category=4,
        comparison_inputs_json={
            "government_method_id":
                "scope3.category9.average_diesel_van.tonne_km.uk_2026.v1",
            "activity_value": "1250",
            "activity_unit": "tonne.km",
        },
    )

    with pytest.raises(ValueError, match="Scope 3 category"):
        _comparison_inputs(emission)


def test_comparator_result_is_explicitly_excluded_from_totals() -> None:
    assert COMPARISON_WARNING == (
        "comparison_only_not_included_in_inventory_totals"
    )



def test_scope1_mobile_comparison_inputs_route_to_governed_method() -> None:
    emission: Any = SimpleNamespace(
        confirmed_scope="scope_1",
        confirmed_scope_3_category=None,
        comparison_inputs_json={
            "government_method_id":
                "scope1.mobile_combustion.delivery_van.class1.diesel.km.uk_2026.v1",
            "activity_value": "1000",
            "activity_unit": "km",
        },
    )

    method, value, unit = _comparison_inputs(emission)

    assert method == (
        GovernedCalculationMethod.SCOPE1_CLASS1_DIESEL_VAN_KM_2026
    )
    assert value == Decimal("1000")
    assert unit == "km"
