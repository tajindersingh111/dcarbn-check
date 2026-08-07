from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from app.models.activity import ActivityType, EmissionScope


class GovernedCalculationMethod(StrEnum):
    SCOPE1_CLASS1_DIESEL_VAN_KM_2026 = (
        "scope1.mobile_combustion.delivery_van.class1.diesel.km.uk_2026.v1"
    )
    SCOPE1_STATIONARY_DIESEL_LITRES_2026 = "scope1.stationary_diesel.litres.uk_2026.v1"
    SCOPE2_LOCATION_ELECTRICITY_KWH_2026 = "scope2.location_electricity.kwh.uk_2026.v1"
    SCOPE1_HFC134A_MASS_BALANCE_KG_2026 = (
        "scope1.refrigerant.hfc134a.mass_balance.kg.uk_2026.v1"
    )
    SCOPE3_CATEGORY3_DIESEL_WTT_LITRES_2026 = (
        "scope3.category3.diesel_wtt.litres.uk_2026.v1"
    )
    SCOPE3_CATEGORY5_COMMERCIAL_WASTE_LANDFILL_TONNES_2026 = (
        "scope3.category5.commercial_waste.landfill.tonnes.uk_2026.v1"
    )
    SCOPE3_CATEGORY7_AVERAGE_CAR_COMMUTING_KM_2026 = (
        "scope3.category7.average_car.unknown_fuel.km.uk_2026.v1"
    )
    SCOPE3_CATEGORY9_AVERAGE_DIESEL_VAN_TONNE_KM_2026 = (
        "scope3.category9.average_diesel_van.tonne_km.uk_2026.v1"
    )
    SCOPE3_CATEGORY9_AVERAGE_HGV_TONNE_KM_2026 = "scope3.category9.average_non_refrigerated_hgv.average_laden.tonne_km.uk_2026.v1"
    SCOPE3_CATEGORY9_RAIL_FREIGHT_TONNE_KM_2026 = (
        "scope3.category9.rail_freight.tonne_km.uk_2026.v1"
    )
    SCOPE3_CATEGORY4_DIESEL_VAN_TONNE_KM_2026 = (
        "scope3.category4.diesel_van.tonne_km.uk_2026.v1"
    )
    SCOPE3_CATEGORY6_DOMESTIC_AIR_WITH_RF_2026 = (
        "scope3.category6.domestic_air.with_rf.passenger_km.uk_2026.v1"
    )

    SCOPE3_CATEGORY1_SUPPLIER_SPECIFIC = (
        "scope3.category1.supplier_specific.reported_kgco2e.ghgp.v1"
    )
    SCOPE3_CATEGORY2_SUPPLIER_SPECIFIC = (
        "scope3.category2.supplier_specific.reported_kgco2e.ghgp.v1"
    )
    SCOPE3_CATEGORY8_SUPPLIER_SPECIFIC = (
        "scope3.category8.supplier_specific.reported_kgco2e.ghgp.v1"
    )
    SCOPE3_CATEGORY10_SUPPLIER_SPECIFIC = (
        "scope3.category10.supplier_specific.reported_kgco2e.ghgp.v1"
    )
    SCOPE3_CATEGORY11_SUPPLIER_SPECIFIC = (
        "scope3.category11.supplier_specific.reported_kgco2e.ghgp.v1"
    )
    SCOPE3_CATEGORY12_SUPPLIER_SPECIFIC = (
        "scope3.category12.supplier_specific.reported_kgco2e.ghgp.v1"
    )
    SCOPE3_CATEGORY13_SUPPLIER_SPECIFIC = (
        "scope3.category13.supplier_specific.reported_kgco2e.ghgp.v1"
    )
    SCOPE3_CATEGORY14_SUPPLIER_SPECIFIC = (
        "scope3.category14.supplier_specific.reported_kgco2e.ghgp.v1"
    )
    SCOPE3_CATEGORY15_SUPPLIER_SPECIFIC = (
        "scope3.category15.supplier_specific.reported_kgco2e.ghgp.v1"
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
    lifecycle_boundary: str | None = None
    direct_reported_result: bool = False


METHODS: dict[GovernedCalculationMethod, GovernedMethodSpecification] = {
    GovernedCalculationMethod.SCOPE1_CLASS1_DIESEL_VAN_KM_2026: GovernedMethodSpecification(
        activity_type=ActivityType.MOBILE_COMBUSTION,
        scope=EmissionScope.SCOPE_1,
        scope_3_category=None,
        activity_unit="km",
        factor_level_1="Delivery vehicles",
        factor_level_2="Vans",
        factor_level_3="Class I (up to 1.305 tonnes)",
        factor_column_text="Diesel",
    ),
    GovernedCalculationMethod.SCOPE1_STATIONARY_DIESEL_LITRES_2026: GovernedMethodSpecification(
        activity_type=ActivityType.STATIONARY_COMBUSTION,
        scope=EmissionScope.SCOPE_1,
        scope_3_category=None,
        activity_unit="litres",
        factor_level_1="Fuels",
        factor_level_2="Liquid fuels",
        factor_level_3="Diesel (average biofuel blend)",
    ),
    GovernedCalculationMethod.SCOPE2_LOCATION_ELECTRICITY_KWH_2026: GovernedMethodSpecification(
        activity_type=ActivityType.PURCHASED_ELECTRICITY,
        scope=EmissionScope.SCOPE_2,
        scope_3_category=None,
        activity_unit="kWh",
        factor_level_1="UK electricity",
        factor_level_2="Electricity generated",
        factor_level_3="Electricity: UK",
    ),
    GovernedCalculationMethod.SCOPE1_HFC134A_MASS_BALANCE_KG_2026: GovernedMethodSpecification(
        activity_type=ActivityType.REFRIGERANT,
        scope=EmissionScope.SCOPE_1,
        scope_3_category=None,
        activity_unit="kg",
        factor_level_1="Refrigerant & other",
        factor_level_2="Kyoto protocol products",
        factor_level_3="HFC-134a",
        factor_column_text="Emissions including only Kyoto products",
    ),
    GovernedCalculationMethod.SCOPE3_CATEGORY3_DIESEL_WTT_LITRES_2026: GovernedMethodSpecification(
        activity_type=ActivityType.STATIONARY_COMBUSTION,
        scope=EmissionScope.SCOPE_3,
        scope_3_category=3,
        activity_unit="litres",
        factor_level_1="WTT- fuels",
        factor_level_2="Liquid fuels",
        factor_level_3="Diesel (average biofuel blend)",
        lifecycle_boundary="well_to_tank",
    ),
    GovernedCalculationMethod.SCOPE3_CATEGORY5_COMMERCIAL_WASTE_LANDFILL_TONNES_2026: GovernedMethodSpecification(
        activity_type=ActivityType.WASTE_GENERATED,
        scope=EmissionScope.SCOPE_3,
        scope_3_category=5,
        activity_unit="tonnes",
        factor_level_1="Waste disposal",
        factor_level_2="Refuse",
        factor_level_3="Commercial and industrial waste",
        factor_column_text="Landfill",
        lifecycle_boundary="indirect_value_chain",
    ),
    GovernedCalculationMethod.SCOPE3_CATEGORY7_AVERAGE_CAR_COMMUTING_KM_2026: GovernedMethodSpecification(
        activity_type=ActivityType.EMPLOYEE_COMMUTING,
        scope=EmissionScope.SCOPE_3,
        scope_3_category=7,
        activity_unit="km",
        factor_level_1="Business travel- land",
        factor_level_2="Cars (by size)",
        factor_level_3="Average car",
        factor_column_text="Unknown",
        lifecycle_boundary="indirect_value_chain",
    ),
    GovernedCalculationMethod.SCOPE3_CATEGORY9_AVERAGE_DIESEL_VAN_TONNE_KM_2026: GovernedMethodSpecification(
        activity_type=ActivityType.FREIGHT_TRANSPORT,
        scope=EmissionScope.SCOPE_3,
        scope_3_category=9,
        activity_unit="tonne.km",
        factor_level_1="Freighting goods",
        factor_level_2="Vans",
        factor_level_3="Average (up to 3.5 tonnes)",
        factor_column_text="Diesel",
        lifecycle_boundary="indirect_value_chain",
    ),
    GovernedCalculationMethod.SCOPE3_CATEGORY9_AVERAGE_HGV_TONNE_KM_2026: GovernedMethodSpecification(
        activity_type=ActivityType.FREIGHT_TRANSPORT,
        scope=EmissionScope.SCOPE_3,
        scope_3_category=9,
        activity_unit="tonne.km",
        factor_level_1="Freighting goods",
        factor_level_2="HGV (non-refrigerated, all diesel)",
        factor_level_3="Average non-refrigerated HGVs",
        factor_column_text="Average laden",
        lifecycle_boundary="indirect_value_chain",
    ),
    GovernedCalculationMethod.SCOPE3_CATEGORY9_RAIL_FREIGHT_TONNE_KM_2026: GovernedMethodSpecification(
        activity_type=ActivityType.FREIGHT_TRANSPORT,
        scope=EmissionScope.SCOPE_3,
        scope_3_category=9,
        activity_unit="tonne.km",
        factor_level_1="Freighting goods",
        factor_level_2="Rail",
        factor_level_3="Freight train",
        lifecycle_boundary="indirect_value_chain",
    ),
    GovernedCalculationMethod.SCOPE3_CATEGORY4_DIESEL_VAN_TONNE_KM_2026: GovernedMethodSpecification(
        activity_type=ActivityType.FREIGHT_TRANSPORT,
        scope=EmissionScope.SCOPE_3,
        scope_3_category=4,
        activity_unit="tonne.km",
        factor_level_1="Freighting goods",
        factor_level_2="Vans",
        factor_level_3="Class I (up to 1.305 tonnes)",
        factor_column_text="Diesel",
    ),
    GovernedCalculationMethod.SCOPE3_CATEGORY6_DOMESTIC_AIR_WITH_RF_2026: GovernedMethodSpecification(
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

_REMAINING_SCOPE3_CATEGORY_LABELS = {
    1: "Purchased goods and services",
    2: "Capital goods",
    8: "Upstream leased assets",
    10: "Processing of sold products",
    11: "Use of sold products",
    12: "End-of-life treatment of sold products",
    13: "Downstream leased assets",
    14: "Franchises",
    15: "Investments",
}

for _category, _label in _REMAINING_SCOPE3_CATEGORY_LABELS.items():
    _method = GovernedCalculationMethod(
        f"scope3.category{_category}.supplier_specific.reported_kgco2e.ghgp.v1"
    )
    METHODS[_method] = GovernedMethodSpecification(
        activity_type=ActivityType.VALUE_CHAIN_RESULT,
        scope=EmissionScope.SCOPE_3,
        scope_3_category=_category,
        activity_unit="kgCO2e",
        factor_level_1="Supplier-specific lifecycle result",
        factor_level_2=f"Category {_category}",
        factor_level_3=_label,
        lifecycle_boundary="indirect_value_chain",
        direct_reported_result=True,
    )

GOVERNED_ACTIVITY_TYPES = {
    ActivityType.MOBILE_COMBUSTION,
    ActivityType.STATIONARY_COMBUSTION,
    ActivityType.PURCHASED_ELECTRICITY,
    ActivityType.REFRIGERANT,
    ActivityType.FREIGHT_TRANSPORT,
    ActivityType.BUSINESS_TRAVEL,
    ActivityType.EMPLOYEE_COMMUTING,
    ActivityType.WASTE_GENERATED,
    ActivityType.VALUE_CHAIN_RESULT,
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
    activity_value: Decimal | None = None,
    scope_2_method: object | None = None,
    lifecycle_boundary: str | None = None,
    evidence_reference: str | None = None,
) -> GovernedCalculationMethod | None:
    """Fail closed for activity types covered by the governed-method rollout."""
    if activity_type not in GOVERNED_ACTIVITY_TYPES:
        return None

    raw_method = metadata_json.get("calculation_method_id")
    if not isinstance(raw_method, str):
        raise ValueError(  # noqa: TRY004 - schema surfaces governed input errors uniformly
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
        "lifecycle_boundary": lifecycle_boundary,
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
        "lifecycle_boundary": expected.lifecycle_boundary,
    }.items():
        if field == "lifecycle_boundary" and required is None:
            continue
        if actual[field] != required:
            raise ValueError(
                f"{field} must be {required!s} for calculation method {method.value}"
            )
    if expected.direct_reported_result:
        required_metadata = (
            "supplier_name",
            "supplier_methodology",
            "supplier_methodology_version",
            "supplier_reporting_period",
            "boundary_description",
            "assurance_status",
        )
        missing = [
            field
            for field in required_metadata
            if not isinstance(metadata_json.get(field), str)
            or not str(metadata_json[field]).strip()
        ]
        if missing:
            raise ValueError(
                "Supplier-specific Scope 3 results require metadata fields: "
                + ", ".join(missing)
            )
        if not evidence_reference or not evidence_reference.strip():
            raise ValueError(
                "Supplier-specific Scope 3 results require an evidence_reference"
            )
    if method == GovernedCalculationMethod.SCOPE2_LOCATION_ELECTRICITY_KWH_2026:
        method_value = getattr(scope_2_method, "value", scope_2_method)
        if method_value != "location_based":
            raise ValueError(
                "scope_2_method must be location_based for this calculation method"
            )
    if method == GovernedCalculationMethod.SCOPE1_HFC134A_MASS_BALANCE_KG_2026:
        if activity_value is None:
            raise ValueError("activity_value is required for refrigerant mass balance")
        required_fields = (
            "opening_stock_kg",
            "purchases_kg",
            "closing_stock_kg",
            "recovered_kg",
        )
        try:
            values = {
                field: Decimal(str(metadata_json[field])) for field in required_fields
            }
        except (KeyError, InvalidOperation, ValueError) as exc:
            raise ValueError(
                "Refrigerant mass balance requires valid opening_stock_kg, "
                "purchases_kg, closing_stock_kg and recovered_kg"
            ) from exc
        if any(value < 0 for value in values.values()):
            raise ValueError("Refrigerant mass-balance inputs cannot be negative")
        emitted = (
            values["opening_stock_kg"]
            + values["purchases_kg"]
            - values["closing_stock_kg"]
            - values["recovered_kg"]
        )
        if emitted < 0:
            raise ValueError(
                "Refrigerant mass balance cannot produce negative emissions"
            )
        if emitted != activity_value:
            raise ValueError(
                f"activity_value must equal refrigerant mass-balance emissions ({emitted})"
            )
    return method
