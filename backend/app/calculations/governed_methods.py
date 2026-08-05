from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.models.activity import ActivityType, EmissionScope


class GovernedCalculationMethod(StrEnum):
    SCOPE1_STATIONARY_DIESEL_LITRES_2026 = "scope1.stationary_diesel.litres.uk_2026.v1"
    SCOPE3_CATEGORY4_DIESEL_VAN_TONNE_KM_2026 = (
        "scope3.category4.diesel_van.tonne_km.uk_2026.v1"
    )
    SCOPE3_CATEGORY6_DOMESTIC_AIR_WITH_RF_2026 = (
        "scope3.category6.domestic_air.with_rf.passenger_km.uk_2026.v1"
    )


@dataclass(frozen=True, slots=True)
class GovernedMethodSpecification:
    activity_type: ActivityType
    scope: EmissionScope
    scope_3_category: int | None
    activity_unit: str
    factor_level_1: str
    factor_level_2: str
    factor_level_3: str
    factor_level_4: str | None = None
    factor_column_text: str | None = None


METHODS: dict[GovernedCalculationMethod, GovernedMethodSpecification] = {
    GovernedCalculationMethod.SCOPE1_STATIONARY_DIESEL_LITRES_2026:
        GovernedMethodSpecification(
            activity_type=ActivityType.STATIONARY_COMBUSTION,
            scope=EmissionScope.SCOPE_1,
            scope_3_category=None,
            activity_unit="litres",
            factor_level_1="Fuels",
            factor_level_2="Liquid fuels",
            factor_level_3="Diesel (average biofuel blend)",
        ),
    GovernedCalculationMethod.SCOPE3_CATEGORY4_DIESEL_VAN_TONNE_KM_2026:
        GovernedMethodSpecification(
            activity_type=ActivityType.FREIGHT_TRANSPORT,
            scope=EmissionScope.SCOPE_3,
            scope_3_category=4,
            activity_unit="tonne.km",
            factor_level_1="Freighting goods",
            factor_level_2="Vans",
            factor_level_3="Class I (up to 1.305 tonnes)",
            factor_column_text="Diesel",
        ),
    GovernedCalculationMethod.SCOPE3_CATEGORY6_DOMESTIC_AIR_WITH_RF_2026:
        GovernedMethodSpecification(
            activity_type=ActivityType.BUSINESS_TRAVEL,
            scope=EmissionScope.SCOPE_3,
            scope_3_category=6,
            activity_unit="passenger.km",
            factor_level_1="Business travel- air",
            factor_level_2="Flights",
            factor_level_3="Domestic, to/from UK",
            factor_level_4="Average passenger",
            factor_column_text="With RF",
        ),
}

GOVERNED_ACTIVITY_TYPES = {
    ActivityType.STATIONARY_COMBUSTION,
    ActivityType.FREIGHT_TRANSPORT,
    ActivityType.BUSINESS_TRAVEL,
}


def validate_governed_method(
    *,
    activity_type: ActivityType,
    scope: EmissionScope,
    scope_3_category: int | None,
    activity_unit: str,
    factor_level_1: str | None,
    factor_level_2: str | None,
    factor_level_3: str | None,
    factor_level_4: str | None,
    factor_column_text: str | None,
    metadata_json: dict[str, object],
) -> GovernedCalculationMethod | None:
    """Fail closed for activity types covered by the governed-method rollout."""
    if activity_type not in GOVERNED_ACTIVITY_TYPES:
        return None

    raw_method = metadata_json.get("calculation_method_id")
    if not isinstance(raw_method, str):
        raise ValueError(
            "metadata_json.calculation_method_id is required for this activity type"
        )
    try:
        method = GovernedCalculationMethod(raw_method)
    except ValueError as exc:
        raise ValueError("Unsupported governed calculation method") from exc

    expected = METHODS[method]
    actual = {
        "activity_type": activity_type,
        "scope": scope,
        "scope_3_category": scope_3_category,
        "activity_unit": activity_unit,
        "factor_level_1": factor_level_1,
        "factor_level_2": factor_level_2,
        "factor_level_3": factor_level_3,
        "factor_level_4": factor_level_4,
        "factor_column_text": factor_column_text,
    }
    for field, required in {
        "activity_type": expected.activity_type,
        "scope": expected.scope,
        "scope_3_category": expected.scope_3_category,
        "activity_unit": expected.activity_unit,
        "factor_level_1": expected.factor_level_1,
        "factor_level_2": expected.factor_level_2,
        "factor_level_3": expected.factor_level_3,
        "factor_level_4": expected.factor_level_4,
        "factor_column_text": expected.factor_column_text,
    }.items():
        if actual[field] != required:
            raise ValueError(
                f"{field} must be {required!s} for calculation method {method.value}"
            )
    return method
