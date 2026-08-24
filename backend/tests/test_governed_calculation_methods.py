from datetime import date
from decimal import Decimal

import pytest
from app.calculations.engine import calculate_activity_factor_emissions
from app.calculations.governed_methods import (
    HVO_2023_BIOGENIC_CO2_KG_PER_LITRE,
    HVO_2023_SCOPE1_FACTOR_KG_CO2E_PER_LITRE,
    HVO_2023_WTT_FACTOR_KG_CO2E_PER_LITRE,
    HVO_2024_BIOGENIC_CO2_KG_PER_LITRE,
    HVO_2024_SCOPE1_FACTOR_KG_CO2E_PER_LITRE,
    HVO_2024_WTT_FACTOR_KG_CO2E_PER_LITRE,
    HVO_2025_BIOGENIC_CO2_KG_PER_LITRE,
    HVO_2025_SCOPE1_FACTOR_KG_CO2E_PER_LITRE,
    HVO_2025_WTT_FACTOR_KG_CO2E_PER_LITRE,
    GovernedCalculationMethod,
    validate_governed_method,
)
from app.models.activity import ActivityType, EmissionScope, Scope2Method


@pytest.mark.parametrize(
    ("method_id", "scope", "category", "level_1", "level_2", "boundary", "factor", "expected"),
    [
        (
            "scope1.mobile_combustion.hvo.litres.uk_2023.v1",
            EmissionScope.SCOPE_1,
            None,
            "Bioenergy",
            "Biofuel",
            "direct",
            HVO_2023_SCOPE1_FACTOR_KG_CO2E_PER_LITRE,
            Decimal("35.58000"),
        ),
        (
            "scope3.category3.hvo_wtt.litres.uk_2023.v1",
            EmissionScope.SCOPE_3,
            3,
            "WTT- bioenergy",
            "WTT- biofuel",
            "well_to_tank",
            HVO_2023_WTT_FACTOR_KG_CO2E_PER_LITRE,
            Decimal("278.44000"),
        ),
    ],
)
def test_uk_2023_hvo_contract_and_golden_result(
    method_id: str,
    scope: EmissionScope,
    category: int | None,
    level_1: str,
    level_2: str,
    boundary: str,
    factor: Decimal,
    expected: Decimal,
) -> None:
    method = validate_governed_method(
        activity_type=ActivityType.MOBILE_COMBUSTION,
        scope=scope,
        scope_3_category=category,
        activity_unit="litres",
        factor_level_1=level_1,
        factor_level_2=level_2,
        factor_level_3="Biodiesel HVO",
        factor_level_4=None,
        factor_column_text=None,
        metadata_json={"calculation_method_id": method_id},
        lifecycle_boundary=boundary,
        evidence_reference="new-era-hvo-delivery-notes-2023.pdf",
        activity_date=date(2023, 12, 31),
    )
    result = calculate_activity_factor_emissions(
        factor_activity_value=Decimal("1000"),
        factor_value=factor,
        allocation_percentage=Decimal(100),
    )

    assert method.value == method_id
    assert result.allocated_kg_co2e == expected
    assert Decimal("1000") * HVO_2023_BIOGENIC_CO2_KG_PER_LITRE == Decimal("2430.00")


@pytest.mark.parametrize("activity_date", [date(2023, 1, 1), date(2023, 12, 31)])
def test_uk_2023_hvo_accepts_calendar_year_boundaries(activity_date: date) -> None:
    method = validate_governed_method(
        activity_type=ActivityType.MOBILE_COMBUSTION,
        scope=EmissionScope.SCOPE_1,
        scope_3_category=None,
        activity_unit="litres",
        factor_level_1="Bioenergy",
        factor_level_2="Biofuel",
        factor_level_3="Biodiesel HVO",
        factor_level_4=None,
        factor_column_text=None,
        metadata_json={"calculation_method_id": "scope1.mobile_combustion.hvo.litres.uk_2023.v1"},
        lifecycle_boundary="direct",
        evidence_reference="hvo-delivery-notes.pdf",
        activity_date=activity_date,
    )

    assert method == GovernedCalculationMethod.SCOPE1_MOBILE_HVO_LITRES_2023


@pytest.mark.parametrize("activity_date", [date(2022, 12, 31), date(2024, 1, 1)])
def test_uk_2023_hvo_rejects_dates_outside_calendar_year(activity_date: date) -> None:
    with pytest.raises(ValueError, match="only valid for activity dated in 2023"):
        validate_governed_method(
            activity_type=ActivityType.MOBILE_COMBUSTION,
            scope=EmissionScope.SCOPE_1,
            scope_3_category=None,
            activity_unit="litres",
            factor_level_1="Bioenergy",
            factor_level_2="Biofuel",
            factor_level_3="Biodiesel HVO",
            factor_level_4=None,
            factor_column_text=None,
            metadata_json={
                "calculation_method_id": "scope1.mobile_combustion.hvo.litres.uk_2023.v1"
            },
            lifecycle_boundary="direct",
            evidence_reference="hvo-delivery-notes.pdf",
            activity_date=activity_date,
        )


@pytest.mark.parametrize(
    ("method_id", "scope", "category", "level_1", "level_2", "boundary", "factor", "expected"),
    [
        (
            "scope1.mobile_combustion.hvo.litres.uk_2025.v1",
            EmissionScope.SCOPE_1,
            None,
            "Bioenergy",
            "Biofuel",
            "direct",
            HVO_2025_SCOPE1_FACTOR_KG_CO2E_PER_LITRE,
            Decimal("35.58000"),
        ),
        (
            "scope3.category3.hvo_wtt.litres.uk_2025.v1",
            EmissionScope.SCOPE_3,
            3,
            "WTT- bioenergy",
            "WTT- biofuel",
            "well_to_tank",
            HVO_2025_WTT_FACTOR_KG_CO2E_PER_LITRE,
            Decimal("564.39000"),
        ),
    ],
)
def test_uk_2025_hvo_contract_and_golden_result(
    method_id: str,
    scope: EmissionScope,
    category: int | None,
    level_1: str,
    level_2: str,
    boundary: str,
    factor: Decimal,
    expected: Decimal,
) -> None:
    method = validate_governed_method(
        activity_type=ActivityType.MOBILE_COMBUSTION,
        scope=scope,
        scope_3_category=category,
        activity_unit="litres",
        factor_level_1=level_1,
        factor_level_2=level_2,
        factor_level_3="Biodiesel HVO",
        factor_level_4=None,
        factor_column_text=None,
        metadata_json={"calculation_method_id": method_id},
        lifecycle_boundary=boundary,
        evidence_reference="hvo-delivery-notes-2025.pdf",
        activity_date=date(2025, 12, 31),
    )
    result = calculate_activity_factor_emissions(
        factor_activity_value=Decimal("1000"),
        factor_value=factor,
        allocation_percentage=Decimal(100),
    )

    assert method.value == method_id
    assert result.allocated_kg_co2e == expected
    assert Decimal("1000") * HVO_2025_BIOGENIC_CO2_KG_PER_LITRE == Decimal("2430.00")


def test_uk_2025_hvo_rejects_activity_outside_calendar_year() -> None:
    with pytest.raises(ValueError, match="only valid for activity dated in 2025"):
        validate_governed_method(
            activity_type=ActivityType.MOBILE_COMBUSTION,
            scope=EmissionScope.SCOPE_1,
            scope_3_category=None,
            activity_unit="litres",
            factor_level_1="Bioenergy",
            factor_level_2="Biofuel",
            factor_level_3="Biodiesel HVO",
            factor_level_4=None,
            factor_column_text=None,
            metadata_json={
                "calculation_method_id": "scope1.mobile_combustion.hvo.litres.uk_2025.v1"
            },
            lifecycle_boundary="direct",
            evidence_reference="hvo-delivery-notes.pdf",
            activity_date=date(2024, 12, 31),
        )


def test_scope1_stationary_diesel_contract_and_golden_result() -> None:
    method = validate_governed_method(
        activity_type=ActivityType.STATIONARY_COMBUSTION,
        scope=EmissionScope.SCOPE_1,
        scope_3_category=None,
        activity_unit="litres",
        factor_level_1="Fuels",
        factor_level_2="Liquid fuels",
        factor_level_3="Diesel (average biofuel blend)",
        factor_level_4=None,
        factor_column_text=None,
        metadata_json={"calculation_method_id": "scope1.stationary_diesel.litres.uk_2026.v1"},
    )
    result = calculate_activity_factor_emissions(
        factor_activity_value=Decimal(1000),
        factor_value=Decimal("2.58354"),
        allocation_percentage=Decimal(100),
    )

    assert method == (GovernedCalculationMethod.SCOPE1_STATIONARY_DIESEL_LITRES_2026)
    assert result.allocated_kg_co2e == Decimal("2583.54000")


@pytest.mark.parametrize(
    ("method_id", "scope", "category", "level_1", "level_2", "boundary", "factor"),
    [
        (
            "scope1.mobile_combustion.hvo.litres.uk_2024.v1",
            EmissionScope.SCOPE_1,
            None,
            "Bioenergy",
            "Biofuel",
            "direct",
            HVO_2024_SCOPE1_FACTOR_KG_CO2E_PER_LITRE,
        ),
        (
            "scope3.category3.hvo_wtt.litres.uk_2024.v1",
            EmissionScope.SCOPE_3,
            3,
            "WTT- bioenergy",
            "WTT- biofuel",
            "well_to_tank",
            HVO_2024_WTT_FACTOR_KG_CO2E_PER_LITRE,
        ),
    ],
)
def test_uk_2024_hvo_contract_and_new_era_golden_result(
    method_id: str,
    scope: EmissionScope,
    category: int | None,
    level_1: str,
    level_2: str,
    boundary: str,
    factor: Decimal,
) -> None:
    method = validate_governed_method(
        activity_type=ActivityType.MOBILE_COMBUSTION,
        scope=scope,
        scope_3_category=category,
        activity_unit="litres",
        factor_level_1=level_1,
        factor_level_2=level_2,
        factor_level_3="Biodiesel HVO",
        factor_level_4=None,
        factor_column_text=None,
        metadata_json={"calculation_method_id": method_id},
        lifecycle_boundary=boundary,
        evidence_reference="new-era-hvo-delivery-notes-2024.pdf",
        activity_date=date(2024, 10, 31),
    )
    result = calculate_activity_factor_emissions(
        factor_activity_value=Decimal("976227"),
        factor_value=factor,
        allocation_percentage=Decimal(100),
    )

    assert method.value == method_id
    expected = Decimal("34734.15666") if scope == EmissionScope.SCOPE_1 else Decimal("545710.89300")
    assert result.allocated_kg_co2e == expected
    assert Decimal("976227") * HVO_2024_BIOGENIC_CO2_KG_PER_LITRE == Decimal("2372231.61")


def test_uk_2024_hvo_rejects_missing_fuel_evidence() -> None:
    with pytest.raises(ValueError, match="requires evidence confirming"):
        validate_governed_method(
            activity_type=ActivityType.MOBILE_COMBUSTION,
            scope=EmissionScope.SCOPE_1,
            scope_3_category=None,
            activity_unit="litres",
            factor_level_1="Bioenergy",
            factor_level_2="Biofuel",
            factor_level_3="Biodiesel HVO",
            factor_level_4=None,
            factor_column_text=None,
            metadata_json={
                "calculation_method_id": ("scope1.mobile_combustion.hvo.litres.uk_2024.v1")
            },
            lifecycle_boundary="direct",
            activity_date=date(2024, 6, 30),
        )


def test_uk_2024_hvo_rejects_activity_outside_calendar_year() -> None:
    with pytest.raises(ValueError, match="only valid for activity dated in 2024"):
        validate_governed_method(
            activity_type=ActivityType.MOBILE_COMBUSTION,
            scope=EmissionScope.SCOPE_1,
            scope_3_category=None,
            activity_unit="litres",
            factor_level_1="Bioenergy",
            factor_level_2="Biofuel",
            factor_level_3="Biodiesel HVO",
            factor_level_4=None,
            factor_column_text=None,
            metadata_json={
                "calculation_method_id": ("scope1.mobile_combustion.hvo.litres.uk_2024.v1")
            },
            lifecycle_boundary="direct",
            evidence_reference="hvo-delivery-notes.pdf",
            activity_date=date(2023, 12, 31),
        )


def test_scope3_category4_freight_contract_and_golden_result() -> None:
    method = validate_governed_method(
        activity_type=ActivityType.FREIGHT_TRANSPORT,
        scope=EmissionScope.SCOPE_3,
        scope_3_category=4,
        activity_unit="tonne.km",
        factor_level_1="Freighting goods",
        factor_level_2="Vans",
        factor_level_3="Class I (up to 1.305 tonnes)",
        factor_level_4=None,
        factor_column_text="Diesel",
        metadata_json={"calculation_method_id": "scope3.category4.diesel_van.tonne_km.uk_2026.v1"},
    )
    result = calculate_activity_factor_emissions(
        factor_activity_value=Decimal(1000),
        factor_value=Decimal("0.87948"),
        allocation_percentage=Decimal(100),
    )

    assert method == (GovernedCalculationMethod.SCOPE3_CATEGORY4_DIESEL_VAN_TONNE_KM_2026)
    assert result.allocated_kg_co2e == Decimal("879.48000")


def test_scope3_category6_air_contract_and_golden_result() -> None:
    method = validate_governed_method(
        activity_type=ActivityType.BUSINESS_TRAVEL,
        scope=EmissionScope.SCOPE_3,
        scope_3_category=6,
        activity_unit="passenger.km",
        factor_level_1="Business travel- air",
        factor_level_2="Flights",
        factor_level_3="Domestic, to/from UK",
        factor_level_4="Average passenger",
        factor_column_text="With RF",
        metadata_json={
            "calculation_method_id": "scope3.category6.domestic_air.with_rf.passenger_km.uk_2026.v1"
        },
    )
    result = calculate_activity_factor_emissions(
        factor_activity_value=Decimal(1000),
        factor_value=Decimal("0.22928"),
        allocation_percentage=Decimal(100),
    )

    assert method == (GovernedCalculationMethod.SCOPE3_CATEGORY6_DOMESTIC_AIR_WITH_RF_2026)
    assert result.allocated_kg_co2e == Decimal("229.28000")


def test_governed_method_rejects_wrong_scope_3_category() -> None:
    with pytest.raises(
        ValueError,
        match="scope_3_category must be 4",
    ):
        validate_governed_method(
            activity_type=ActivityType.FREIGHT_TRANSPORT,
            scope=EmissionScope.SCOPE_3,
            scope_3_category=9,
            activity_unit="tonne.km",
            factor_level_1="Freighting goods",
            factor_level_2="Vans",
            factor_level_3="Class I (up to 1.305 tonnes)",
            factor_level_4=None,
            factor_column_text="Diesel",
            metadata_json={
                "calculation_method_id": "scope3.category4.diesel_van.tonne_km.uk_2026.v1"
            },
        )


def test_governed_activity_rejects_missing_method_id() -> None:
    with pytest.raises(
        ValueError,
        match="calculation_method_id is required",
    ):
        validate_governed_method(
            activity_type=ActivityType.BUSINESS_TRAVEL,
            scope=EmissionScope.SCOPE_3,
            scope_3_category=6,
            activity_unit="passenger.km",
            factor_level_1="Business travel- air",
            factor_level_2="Flights",
            factor_level_3="Domestic, to/from UK",
            factor_level_4="Average passenger",
            factor_column_text="With RF",
            metadata_json={},
        )


def test_governed_method_rejects_non_matching_unit() -> None:
    with pytest.raises(ValueError, match="activity_unit must be passenger.km"):
        validate_governed_method(
            activity_type=ActivityType.BUSINESS_TRAVEL,
            scope=EmissionScope.SCOPE_3,
            scope_3_category=6,
            activity_unit="km",
            factor_level_1="Business travel- air",
            factor_level_2="Flights",
            factor_level_3="Domestic, to/from UK",
            factor_level_4="Average passenger",
            factor_column_text="With RF",
            metadata_json={
                "calculation_method_id": "scope3.category6.domestic_air.with_rf.passenger_km.uk_2026.v1"
            },
        )


def test_scope2_location_electricity_contract_and_2026_golden_result() -> None:
    method = validate_governed_method(
        activity_type=ActivityType.PURCHASED_ELECTRICITY,
        scope=EmissionScope.SCOPE_2,
        scope_3_category=None,
        activity_unit="kWh",
        factor_level_1="UK electricity",
        factor_level_2="Electricity generated",
        factor_level_3="Electricity: UK",
        factor_level_4=None,
        factor_column_text=None,
        metadata_json={"calculation_method_id": "scope2.location_electricity.kwh.uk_2026.v1"},
        activity_value=Decimal(1000),
        scope_2_method=Scope2Method.LOCATION_BASED,
    )
    result = calculate_activity_factor_emissions(
        factor_activity_value=Decimal(1000),
        factor_value=Decimal("0.13096"),
        allocation_percentage=Decimal(100),
    )

    assert method == GovernedCalculationMethod.SCOPE2_LOCATION_ELECTRICITY_KWH_2026
    assert result.allocated_kg_co2e == Decimal("130.96000")


def test_scope2_location_method_rejects_market_based_classification() -> None:
    with pytest.raises(ValueError, match="scope_2_method must be location_based"):
        validate_governed_method(
            activity_type=ActivityType.PURCHASED_ELECTRICITY,
            scope=EmissionScope.SCOPE_2,
            scope_3_category=None,
            activity_unit="kWh",
            factor_level_1="UK electricity",
            factor_level_2="Electricity generated",
            factor_level_3="Electricity: UK",
            factor_level_4=None,
            factor_column_text=None,
            metadata_json={"calculation_method_id": "scope2.location_electricity.kwh.uk_2026.v1"},
            activity_value=Decimal(1000),
            scope_2_method=Scope2Method.MARKET_BASED,
        )


def test_scope1_hfc134a_mass_balance_contract_and_2026_golden_result() -> None:
    method = validate_governed_method(
        activity_type=ActivityType.REFRIGERANT,
        scope=EmissionScope.SCOPE_1,
        scope_3_category=None,
        activity_unit="kg",
        factor_level_1="Refrigerant & other",
        factor_level_2="Kyoto protocol products",
        factor_level_3="HFC-134a",
        factor_level_4=None,
        factor_column_text="Emissions including only Kyoto products",
        metadata_json={
            "calculation_method_id": "scope1.refrigerant.hfc134a.mass_balance.kg.uk_2026.v1",
            "opening_stock_kg": "100",
            "purchases_kg": "25",
            "closing_stock_kg": "110",
            "recovered_kg": "5",
        },
        activity_value=Decimal(10),
    )
    result = calculate_activity_factor_emissions(
        factor_activity_value=Decimal(10),
        factor_value=Decimal(1300),
        allocation_percentage=Decimal(100),
    )

    assert method == GovernedCalculationMethod.SCOPE1_HFC134A_MASS_BALANCE_KG_2026
    assert result.allocated_kg_co2e == Decimal(13000)


def test_refrigerant_mass_balance_rejects_activity_value_mismatch() -> None:
    with pytest.raises(ValueError, match="activity_value must equal"):
        validate_governed_method(
            activity_type=ActivityType.REFRIGERANT,
            scope=EmissionScope.SCOPE_1,
            scope_3_category=None,
            activity_unit="kg",
            factor_level_1="Refrigerant & other",
            factor_level_2="Kyoto protocol products",
            factor_level_3="HFC-134a",
            factor_level_4=None,
            factor_column_text="Emissions including only Kyoto products",
            metadata_json={
                "calculation_method_id": "scope1.refrigerant.hfc134a.mass_balance.kg.uk_2026.v1",
                "opening_stock_kg": "100",
                "purchases_kg": "25",
                "closing_stock_kg": "110",
                "recovered_kg": "5",
            },
            activity_value=Decimal(11),
        )


@pytest.mark.parametrize(
    (
        "method_id",
        "activity_type",
        "category",
        "unit",
        "level_1",
        "level_2",
        "level_3",
        "column_text",
        "boundary",
        "factor",
        "expected",
    ),
    [
        (
            "scope3.category3.diesel_wtt.litres.uk_2026.v1",
            ActivityType.STATIONARY_COMBUSTION,
            3,
            "litres",
            "WTT- fuels",
            "Liquid fuels",
            "Diesel (average biofuel blend)",
            None,
            "well_to_tank",
            "0.61101",
            "611.01000",
        ),
        (
            "scope3.category5.commercial_waste.landfill.tonnes.uk_2026.v1",
            ActivityType.WASTE_GENERATED,
            5,
            "tonnes",
            "Waste disposal",
            "Refuse",
            "Commercial and industrial waste",
            "Landfill",
            "indirect_value_chain",
            "520.58023",
            "520580.23000",
        ),
        (
            "scope3.category7.average_car.unknown_fuel.km.uk_2026.v1",
            ActivityType.EMPLOYEE_COMMUTING,
            7,
            "km",
            "Business travel- land",
            "Cars (by size)",
            "Average car",
            "Unknown",
            "indirect_value_chain",
            "0.16591",
            "165.91000",
        ),
    ],
)
def test_scope3_2026_category_contracts_and_golden_results(
    method_id: str,
    activity_type: ActivityType,
    category: int,
    unit: str,
    level_1: str,
    level_2: str,
    level_3: str,
    column_text: str | None,
    boundary: str,
    factor: str,
    expected: str,
) -> None:
    method = validate_governed_method(
        activity_type=activity_type,
        scope=EmissionScope.SCOPE_3,
        scope_3_category=category,
        activity_unit=unit,
        factor_level_1=level_1,
        factor_level_2=level_2,
        factor_level_3=level_3,
        factor_level_4=None,
        factor_column_text=column_text,
        metadata_json={"calculation_method_id": method_id},
        lifecycle_boundary=boundary,
    )
    result = calculate_activity_factor_emissions(
        factor_activity_value=Decimal(1000),
        factor_value=Decimal(factor),
        allocation_percentage=Decimal(100),
    )

    assert method.value == method_id
    assert result.allocated_kg_co2e == Decimal(expected)


def test_scope3_governed_method_rejects_wrong_lifecycle_boundary() -> None:
    with pytest.raises(ValueError, match="lifecycle_boundary must be well_to_tank"):
        validate_governed_method(
            activity_type=ActivityType.STATIONARY_COMBUSTION,
            scope=EmissionScope.SCOPE_3,
            scope_3_category=3,
            activity_unit="litres",
            factor_level_1="WTT- fuels",
            factor_level_2="Liquid fuels",
            factor_level_3="Diesel (average biofuel blend)",
            factor_level_4=None,
            factor_column_text=None,
            metadata_json={
                "calculation_method_id": "scope3.category3.diesel_wtt.litres.uk_2026.v1"
            },
            lifecycle_boundary="direct",
        )


@pytest.mark.parametrize(
    ("method_id", "level_2", "level_3", "column_text", "factor", "expected"),
    [
        (
            "scope3.category9.average_diesel_van.tonne_km.uk_2026.v1",
            "Vans",
            "Average (up to 3.5 tonnes)",
            "Diesel",
            "0.63511",
            "635.11000",
        ),
        (
            "scope3.category9.average_non_refrigerated_hgv.average_laden.tonne_km.uk_2026.v1",
            "HGV (non-refrigerated, all diesel)",
            "Average non-refrigerated HGVs",
            "Average laden",
            "0.10356",
            "103.56000",
        ),
        (
            "scope3.category9.rail_freight.tonne_km.uk_2026.v1",
            "Rail",
            "Freight train",
            None,
            "0.02583",
            "25.83000",
        ),
    ],
)
def test_scope3_category9_downstream_freight_golden_results(
    method_id: str,
    level_2: str,
    level_3: str,
    column_text: str | None,
    factor: str,
    expected: str,
) -> None:
    method = validate_governed_method(
        activity_type=ActivityType.FREIGHT_TRANSPORT,
        scope=EmissionScope.SCOPE_3,
        scope_3_category=9,
        activity_unit="tonne.km",
        factor_level_1="Freighting goods",
        factor_level_2=level_2,
        factor_level_3=level_3,
        factor_level_4=None,
        factor_column_text=column_text,
        metadata_json={"calculation_method_id": method_id},
        lifecycle_boundary="indirect_value_chain",
    )
    result = calculate_activity_factor_emissions(
        factor_activity_value=Decimal(1000),
        factor_value=Decimal(factor),
        allocation_percentage=Decimal(100),
    )

    assert method.value == method_id
    assert result.allocated_kg_co2e == Decimal(expected)


def test_scope3_category9_cannot_be_misclassified_as_upstream_freight() -> None:
    with pytest.raises(ValueError, match="scope_3_category must be 9"):
        validate_governed_method(
            activity_type=ActivityType.FREIGHT_TRANSPORT,
            scope=EmissionScope.SCOPE_3,
            scope_3_category=4,
            activity_unit="tonne.km",
            factor_level_1="Freighting goods",
            factor_level_2="Rail",
            factor_level_3="Freight train",
            factor_level_4=None,
            factor_column_text=None,
            metadata_json={
                "calculation_method_id": "scope3.category9.rail_freight.tonne_km.uk_2026.v1"
            },
            lifecycle_boundary="indirect_value_chain",
        )


@pytest.mark.parametrize("category", [1, 2, 8, 10, 11, 12, 13, 14, 15])
def test_remaining_scope3_categories_accept_evidence_backed_supplier_results(
    category: int,
) -> None:
    labels = {
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
    method_id = f"scope3.category{category}.supplier_specific.reported_kgco2e.ghgp.v1"
    method = validate_governed_method(
        activity_type=ActivityType.VALUE_CHAIN_RESULT,
        scope=EmissionScope.SCOPE_3,
        scope_3_category=category,
        activity_unit="kgCO2e",
        factor_level_1="Supplier-specific lifecycle result",
        factor_level_2=f"Category {category}",
        factor_level_3=labels[category],
        factor_level_4=None,
        factor_column_text=None,
        metadata_json={
            "calculation_method_id": method_id,
            "supplier_name": "Example supplier",
            "supplier_methodology": "GHG Protocol Scope 3 supplier-specific method",
            "supplier_methodology_version": "2026.1",
            "supplier_reporting_period": "2026",
            "boundary_description": "Cradle-to-gate emissions attributable to customer",
            "assurance_status": "third_party_verified",
        },
        lifecycle_boundary="indirect_value_chain",
        evidence_reference="supplier-inventory-2026.pdf",
    )
    result = calculate_activity_factor_emissions(
        factor_activity_value=Decimal(1000),
        factor_value=Decimal(1),
        allocation_percentage=Decimal(75),
    )

    assert method.value == method_id
    assert result.allocated_kg_co2e == Decimal("750.00000")


def test_supplier_specific_scope3_result_rejects_missing_lineage() -> None:
    with pytest.raises(ValueError, match="supplier_methodology_version"):
        validate_governed_method(
            activity_type=ActivityType.VALUE_CHAIN_RESULT,
            scope=EmissionScope.SCOPE_3,
            scope_3_category=1,
            activity_unit="kgCO2e",
            factor_level_1="Supplier-specific lifecycle result",
            factor_level_2="Category 1",
            factor_level_3="Purchased goods and services",
            factor_level_4=None,
            factor_column_text=None,
            metadata_json={
                "calculation_method_id": (
                    "scope3.category1.supplier_specific.reported_kgco2e.ghgp.v1"
                ),
                "supplier_name": "Example supplier",
                "supplier_methodology": "GHG Protocol supplier-specific method",
            },
            lifecycle_boundary="indirect_value_chain",
            evidence_reference="supplier-inventory-2026.pdf",
        )


def test_scope1_class1_diesel_van_km_2026_golden_result() -> None:
    method = validate_governed_method(
        activity_type=ActivityType.MOBILE_COMBUSTION,
        scope=EmissionScope.SCOPE_1,
        scope_3_category=None,
        activity_unit="km",
        factor_level_1="Delivery vehicles",
        factor_level_2="Vans",
        factor_level_3="Class I (up to 1.305 tonnes)",
        factor_level_4=None,
        factor_column_text="Diesel",
        metadata_json={
            "calculation_method_id": "scope1.mobile_combustion.delivery_van.class1.diesel.km.uk_2026.v1"
        },
    )
    result = calculate_activity_factor_emissions(
        factor_activity_value=Decimal(1000),
        factor_value=Decimal("0.15833"),
        allocation_percentage=Decimal(100),
    )

    assert method == GovernedCalculationMethod.SCOPE1_CLASS1_DIESEL_VAN_KM_2026
    assert result.allocated_kg_co2e == Decimal("158.33000")


def test_scope1_mobile_method_rejects_scope3_classification() -> None:
    with pytest.raises(ValueError, match="scope must be scope_1"):
        validate_governed_method(
            activity_type=ActivityType.MOBILE_COMBUSTION,
            scope=EmissionScope.SCOPE_3,
            scope_3_category=4,
            activity_unit="km",
            factor_level_1="Delivery vehicles",
            factor_level_2="Vans",
            factor_level_3="Class I (up to 1.305 tonnes)",
            factor_level_4=None,
            factor_column_text="Diesel",
            metadata_json={
                "calculation_method_id": "scope1.mobile_combustion.delivery_van.class1.diesel.km.uk_2026.v1"
            },
        )
