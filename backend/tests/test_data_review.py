from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from app.models.activity import (
    ActivityType,
    DataQualityLevel,
    EmissionScope,
)
from app.services.data_review import (
    _comparison_group_key,
    _external_activity_type,
    _map_data_quality,
    _parse_scope,
    _validate_confirmed_classification,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("scope_1", EmissionScope.SCOPE_1),
        ("Scope 1", EmissionScope.SCOPE_1),
        ("scope2", EmissionScope.SCOPE_2),
        ("Scope 3", EmissionScope.SCOPE_3),
    ],
)
def test_parse_scope(value: str, expected: EmissionScope) -> None:
    assert _parse_scope(value) == expected


def test_scope_3_requires_category() -> None:
    with pytest.raises(ValueError):
        _validate_confirmed_classification(
            EmissionScope.SCOPE_3,
            None,
        )


def test_non_scope_3_rejects_category() -> None:
    with pytest.raises(ValueError):
        _validate_confirmed_classification(
            EmissionScope.SCOPE_1,
            4,
        )


@pytest.mark.parametrize("category", [4, 9])
def test_dcarbn_scope_3_accepts_transport_categories(category: int) -> None:
    _validate_confirmed_classification(
        EmissionScope.SCOPE_3,
        category,
    )


@pytest.mark.parametrize("category", [1, 3, 5, 6, 7, 15])
def test_dcarbn_scope_3_rejects_non_transport_categories(category: int) -> None:
    with pytest.raises(
        ValueError,
        match="Category 4 or Category 9",
    ):
        _validate_confirmed_classification(
            EmissionScope.SCOPE_3,
            category,
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("primary", DataQualityLevel.PRIMARY),
        ("secondary", DataQualityLevel.SECONDARY),
        ("estimated", DataQualityLevel.ESTIMATED),
        (None, DataQualityLevel.UNKNOWN),
        ("custom", DataQualityLevel.UNKNOWN),
    ],
)
def test_maps_data_quality(
    value: str | None,
    expected: DataQualityLevel,
) -> None:
    assert _map_data_quality(value) == expected



def test_comparison_group_key_uses_dcarbn_activity_and_source_period() -> None:
    emission: Any = SimpleNamespace(
        external_activity_key="route-44",
        external_calculation_id="calc-44",
        reporting_period_start=date(2026, 2, 1),
        reporting_period_end=date(2026, 2, 28),
    )
    inventory_period: Any = SimpleNamespace(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    assert _comparison_group_key(emission, inventory_period) == (
        "dcarbn:route-44:2026-02-01:2026-02-28"
    )


def test_comparison_group_key_has_legacy_fallback() -> None:
    emission: Any = SimpleNamespace(
        external_activity_key=None,
        external_calculation_id="legacy-calc-1",
        reporting_period_start=None,
        reporting_period_end=None,
    )
    inventory_period: Any = SimpleNamespace(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    assert _comparison_group_key(emission, inventory_period) == (
        "dcarbn:legacy-calc-1:2026-01-01:2026-12-31"
    )



def test_dcarbn_scope1_routes_to_mobile_combustion() -> None:
    assert _external_activity_type(
        EmissionScope.SCOPE_1
    ) == ActivityType.MOBILE_COMBUSTION


def test_dcarbn_scope3_routes_to_freight_transport() -> None:
    assert _external_activity_type(
        EmissionScope.SCOPE_3
    ) == ActivityType.FREIGHT_TRANSPORT
