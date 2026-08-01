from decimal import Decimal

import pytest

from app.units.registry import Dimension, UnitConversionError, get_unit_registry


def test_converts_miles_to_kilometres() -> None:
    registry = get_unit_registry()

    result = registry.convert(Decimal("10"), "miles", "km")

    assert result == Decimal("16.093440")


def test_converts_tonnes_to_kilograms() -> None:
    registry = get_unit_registry()

    result = registry.convert(Decimal("2.5"), "tonnes", "kg")

    assert result == Decimal("2500.0")


def test_converts_mass_distance() -> None:
    registry = get_unit_registry()

    result = registry.convert(Decimal("5000"), "kg-km", "tonne-km")

    assert result == Decimal("5.000")


def test_normalizes_energy_to_kwh() -> None:
    registry = get_unit_registry()

    result = registry.normalize(Decimal("2"), "MWh")

    assert result.normalized_value == Decimal("2000")
    assert result.normalized_unit == "kWh"
    assert result.dimension == Dimension.ENERGY


def test_rejects_incompatible_dimensions() -> None:
    registry = get_unit_registry()

    with pytest.raises(UnitConversionError):
        registry.convert(Decimal("1"), "litres", "kg")
