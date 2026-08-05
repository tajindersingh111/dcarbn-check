from decimal import Decimal

import pytest

from app.calculations.engine import calculate_activity_factor_emissions
from app.calculations.governed_methods import (
    GovernedCalculationMethod,
    validate_governed_method,
)
from app.models.activity import ActivityType, EmissionScope, Scope2Method


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
        metadata_json={
            "calculation_method_id":
                "scope1.stationary_diesel.litres.uk_2026.v1"
        },
    )
    result = calculate_activity_factor_emissions(
        factor_activity_value=Decimal("1000"),
        factor_value=Decimal("2.58354"),
        allocation_percentage=Decimal("100"),
    )

    assert method == (
        GovernedCalculationMethod.SCOPE1_STATIONARY_DIESEL_LITRES_2026
    )
    assert result.allocated_kg_co2e == Decimal("2583.54000")


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
        metadata_json={
            "calculation_method_id":
                "scope3.category4.diesel_van.tonne_km.uk_2026.v1"
        },
    )
    result = calculate_activity_factor_emissions(
        factor_activity_value=Decimal("1000"),
        factor_value=Decimal("0.87948"),
        allocation_percentage=Decimal("100"),
    )

    assert method == (
        GovernedCalculationMethod
        .SCOPE3_CATEGORY4_DIESEL_VAN_TONNE_KM_2026
    )
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
            "calculation_method_id":
                "scope3.category6.domestic_air.with_rf.passenger_km.uk_2026.v1"
        },
    )
    result = calculate_activity_factor_emissions(
        factor_activity_value=Decimal("1000"),
        factor_value=Decimal("0.22928"),
        allocation_percentage=Decimal("100"),
    )

    assert method == (
        GovernedCalculationMethod
        .SCOPE3_CATEGORY6_DOMESTIC_AIR_WITH_RF_2026
    )
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
                "calculation_method_id":
                    "scope3.category4.diesel_van.tonne_km.uk_2026.v1"
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
                "calculation_method_id":
                    "scope3.category6.domestic_air.with_rf.passenger_km.uk_2026.v1"
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
        metadata_json={
            "calculation_method_id":
                "scope2.location_electricity.kwh.uk_2026.v1"
        },
        activity_value=Decimal("1000"),
        scope_2_method=Scope2Method.LOCATION_BASED,
    )
    result = calculate_activity_factor_emissions(
        factor_activity_value=Decimal("1000"),
        factor_value=Decimal("0.13096"),
        allocation_percentage=Decimal("100"),
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
            metadata_json={
                "calculation_method_id":
                    "scope2.location_electricity.kwh.uk_2026.v1"
            },
            activity_value=Decimal("1000"),
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
            "calculation_method_id":
                "scope1.refrigerant.hfc134a.mass_balance.kg.uk_2026.v1",
            "opening_stock_kg": "100",
            "purchases_kg": "25",
            "closing_stock_kg": "110",
            "recovered_kg": "5",
        },
        activity_value=Decimal("10"),
    )
    result = calculate_activity_factor_emissions(
        factor_activity_value=Decimal("10"),
        factor_value=Decimal("1300"),
        allocation_percentage=Decimal("100"),
    )

    assert method == GovernedCalculationMethod.SCOPE1_HFC134A_MASS_BALANCE_KG_2026
    assert result.allocated_kg_co2e == Decimal("13000")


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
                "calculation_method_id":
                    "scope1.refrigerant.hfc134a.mass_balance.kg.uk_2026.v1",
                "opening_stock_kg": "100",
                "purchases_kg": "25",
                "closing_stock_kg": "110",
                "recovered_kg": "5",
            },
            activity_value=Decimal("11"),
        )
