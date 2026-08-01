from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from functools import lru_cache


class Dimension(StrEnum):
    MASS = "mass"
    DISTANCE = "distance"
    VOLUME = "volume"
    ENERGY = "energy"
    CURRENCY = "currency"
    VEHICLE_DISTANCE = "vehicle_distance"
    MASS_DISTANCE = "mass_distance"
    PASSENGER_DISTANCE = "passenger_distance"
    TIME = "time"
    COUNT = "count"


class UnitConversionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class UnitDefinition:
    canonical_name: str
    dimension: Dimension
    to_base_multiplier: Decimal
    aliases: frozenset[str]


@dataclass(frozen=True, slots=True)
class NormalizedQuantity:
    original_value: Decimal
    original_unit: str
    normalized_value: Decimal
    normalized_unit: str
    dimension: Dimension
    conversion_multiplier: Decimal


class UnitRegistry:
    def __init__(self, definitions: tuple[UnitDefinition, ...]) -> None:
        self._definitions = definitions
        self._by_alias: dict[str, UnitDefinition] = {}
        self._by_canonical: dict[str, UnitDefinition] = {}

        for definition in definitions:
            canonical_key = self._normalize_key(definition.canonical_name)
            if canonical_key in self._by_canonical:
                raise ValueError(
                    f"Duplicate canonical unit: {definition.canonical_name}"
                )
            self._by_canonical[canonical_key] = definition

            for alias in definition.aliases | {definition.canonical_name}:
                key = self._normalize_key(alias)
                if key in self._by_alias:
                    existing = self._by_alias[key]
                    if existing.canonical_name == definition.canonical_name:
                        continue
                    raise ValueError(
                        f"Unit alias '{alias}' is already assigned to "
                        f"'{existing.canonical_name}'."
                    )
                self._by_alias[key] = definition

    @staticmethod
    def _normalize_key(unit: str) -> str:
        return (
            unit.strip()
            .lower()
            .replace("₂", "2")
            .replace("³", "3")
            .replace("·", "-")
            .replace("_", "-")
            .replace(" ", "")
            .replace("/", "-per-")
            .replace("--", "-")
        )

    def resolve(self, unit: str) -> UnitDefinition:
        if not unit or not unit.strip():
            raise UnitConversionError("A unit is required.")

        definition = self._by_alias.get(self._normalize_key(unit))
        if definition is None:
            raise UnitConversionError(f"Unsupported unit: {unit!r}.")
        return definition

    def convert(
        self,
        value: Decimal | str | int,
        from_unit: str,
        to_unit: str,
    ) -> Decimal:
        decimal_value = self._to_decimal(value)
        source = self.resolve(from_unit)
        target = self.resolve(to_unit)

        if source.dimension != target.dimension:
            raise UnitConversionError(
                f"Cannot convert {source.dimension.value} unit "
                f"'{source.canonical_name}' to {target.dimension.value} unit "
                f"'{target.canonical_name}'."
            )

        value_in_base = decimal_value * source.to_base_multiplier
        return value_in_base / target.to_base_multiplier

    def normalize(
        self,
        value: Decimal | str | int,
        unit: str,
    ) -> NormalizedQuantity:
        decimal_value = self._to_decimal(value)
        source = self.resolve(unit)
        base = self.base_unit(source.dimension)
        normalized_value = self.convert(
            decimal_value,
            source.canonical_name,
            base.canonical_name,
        )
        return NormalizedQuantity(
            original_value=decimal_value,
            original_unit=unit,
            normalized_value=normalized_value,
            normalized_unit=base.canonical_name,
            dimension=source.dimension,
            conversion_multiplier=source.to_base_multiplier,
        )

    def base_unit(self, dimension: Dimension) -> UnitDefinition:
        matches = [
            definition
            for definition in self._definitions
            if definition.dimension == dimension
            and definition.to_base_multiplier == Decimal("1")
        ]
        if len(matches) != 1:
            raise UnitConversionError(
                f"Dimension '{dimension.value}' does not have exactly one base unit."
            )
        return matches[0]

    def canonical_name(self, unit: str) -> str:
        return self.resolve(unit).canonical_name

    def compatible(self, first_unit: str, second_unit: str) -> bool:
        return self.resolve(first_unit).dimension == self.resolve(
            second_unit
        ).dimension

    @staticmethod
    def _to_decimal(value: Decimal | str | int) -> Decimal:
        try:
            decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise UnitConversionError(f"Invalid numeric quantity: {value!r}.") from exc

        if not decimal_value.is_finite():
            raise UnitConversionError("Quantity must be a finite decimal.")
        return decimal_value


DEFINITIONS = (
    UnitDefinition(
        canonical_name="kg",
        dimension=Dimension.MASS,
        to_base_multiplier=Decimal("1"),
        aliases=frozenset({"kilogram", "kilograms", "kgs"}),
    ),
    UnitDefinition(
        canonical_name="g",
        dimension=Dimension.MASS,
        to_base_multiplier=Decimal("0.001"),
        aliases=frozenset({"gram", "grams"}),
    ),
    UnitDefinition(
        canonical_name="tonne",
        dimension=Dimension.MASS,
        to_base_multiplier=Decimal("1000"),
        aliases=frozenset(
            {"tonnes", "metric tonne", "metric tonnes", "t", "te"}
        ),
    ),
    UnitDefinition(
        canonical_name="lb",
        dimension=Dimension.MASS,
        to_base_multiplier=Decimal("0.45359237"),
        aliases=frozenset({"lbs", "pound", "pounds"}),
    ),
    UnitDefinition(
        canonical_name="km",
        dimension=Dimension.DISTANCE,
        to_base_multiplier=Decimal("1"),
        aliases=frozenset({"kilometre", "kilometres", "kilometer", "kilometers"}),
    ),
    UnitDefinition(
        canonical_name="m",
        dimension=Dimension.DISTANCE,
        to_base_multiplier=Decimal("0.001"),
        aliases=frozenset({"metre", "metres", "meter", "meters"}),
    ),
    UnitDefinition(
        canonical_name="mile",
        dimension=Dimension.DISTANCE,
        to_base_multiplier=Decimal("1.609344"),
        aliases=frozenset({"miles", "mi"}),
    ),
    UnitDefinition(
        canonical_name="litre",
        dimension=Dimension.VOLUME,
        to_base_multiplier=Decimal("1"),
        aliases=frozenset({"litres", "liter", "liters", "l", "ltr", "ltrs"}),
    ),
    UnitDefinition(
        canonical_name="m3",
        dimension=Dimension.VOLUME,
        to_base_multiplier=Decimal("1000"),
        aliases=frozenset(
            {
                "cubic metre",
                "cubic metres",
                "cubic meter",
                "cubic meters",
                "m^3",
                "m³",
            }
        ),
    ),
    UnitDefinition(
        canonical_name="gallon-uk",
        dimension=Dimension.VOLUME,
        to_base_multiplier=Decimal("4.54609"),
        aliases=frozenset(
            {
                "uk gallon",
                "uk gallons",
                "imperial gallon",
                "imperial gallons",
            }
        ),
    ),
    UnitDefinition(
        canonical_name="kWh",
        dimension=Dimension.ENERGY,
        to_base_multiplier=Decimal("1"),
        aliases=frozenset({"kilowatt hour", "kilowatt hours", "kilowatt-hour"}),
    ),
    UnitDefinition(
        canonical_name="MWh",
        dimension=Dimension.ENERGY,
        to_base_multiplier=Decimal("1000"),
        aliases=frozenset({"megawatt hour", "megawatt hours", "megawatt-hour"}),
    ),
    UnitDefinition(
        canonical_name="GJ",
        dimension=Dimension.ENERGY,
        to_base_multiplier=Decimal("277.777777777777777778"),
        aliases=frozenset({"gigajoule", "gigajoules"}),
    ),
    UnitDefinition(
        canonical_name="MJ",
        dimension=Dimension.ENERGY,
        to_base_multiplier=Decimal("0.277777777777777778"),
        aliases=frozenset({"megajoule", "megajoules"}),
    ),
    UnitDefinition(
        canonical_name="GBP",
        dimension=Dimension.CURRENCY,
        to_base_multiplier=Decimal("1"),
        aliases=frozenset({"£", "pound sterling", "pounds sterling"}),
    ),
    UnitDefinition(
        canonical_name="vehicle-km",
        dimension=Dimension.VEHICLE_DISTANCE,
        to_base_multiplier=Decimal("1"),
        aliases=frozenset(
            {
                "vehicle kilometre",
                "vehicle kilometres",
                "vehicle kilometer",
                "vehicle kilometers",
                "vkm",
            }
        ),
    ),
    UnitDefinition(
        canonical_name="vehicle-mile",
        dimension=Dimension.VEHICLE_DISTANCE,
        to_base_multiplier=Decimal("1.609344"),
        aliases=frozenset({"vehicle miles", "vehicle mile"}),
    ),
    UnitDefinition(
        canonical_name="tonne-km",
        dimension=Dimension.MASS_DISTANCE,
        to_base_multiplier=Decimal("1"),
        aliases=frozenset(
            {
                "tonne kilometre",
                "tonne kilometres",
                "tonne kilometer",
                "tonne kilometers",
                "tonne-kilometre",
                "tonne-kilometres",
                "tkm",
            }
        ),
    ),
    UnitDefinition(
        canonical_name="kg-km",
        dimension=Dimension.MASS_DISTANCE,
        to_base_multiplier=Decimal("0.001"),
        aliases=frozenset(
            {
                "kilogram kilometre",
                "kilogram kilometres",
                "kilogram-kilometre",
            }
        ),
    ),
    UnitDefinition(
        canonical_name="tonne-mile",
        dimension=Dimension.MASS_DISTANCE,
        to_base_multiplier=Decimal("1.609344"),
        aliases=frozenset({"tonne miles", "ton-mile", "ton-miles"}),
    ),
    UnitDefinition(
        canonical_name="passenger-km",
        dimension=Dimension.PASSENGER_DISTANCE,
        to_base_multiplier=Decimal("1"),
        aliases=frozenset(
            {
                "passenger kilometre",
                "passenger kilometres",
                "passenger-kilometre",
                "pkm",
            }
        ),
    ),
    UnitDefinition(
        canonical_name="passenger-mile",
        dimension=Dimension.PASSENGER_DISTANCE,
        to_base_multiplier=Decimal("1.609344"),
        aliases=frozenset({"passenger mile", "passenger miles"}),
    ),
    UnitDefinition(
        canonical_name="hour",
        dimension=Dimension.TIME,
        to_base_multiplier=Decimal("1"),
        aliases=frozenset({"hours", "hr", "hrs"}),
    ),
    UnitDefinition(
        canonical_name="day",
        dimension=Dimension.TIME,
        to_base_multiplier=Decimal("24"),
        aliases=frozenset({"days"}),
    ),
    UnitDefinition(
        canonical_name="unit",
        dimension=Dimension.COUNT,
        to_base_multiplier=Decimal("1"),
        aliases=frozenset({"units", "item", "items", "each", "number"}),
    ),
)


@lru_cache
def get_unit_registry() -> UnitRegistry:
    return UnitRegistry(DEFINITIONS)
