from decimal import Decimal

import pytest

from app.models.activity import (
    DataQualityLevel,
    EmissionScope,
)
from app.services.data_review import (
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
