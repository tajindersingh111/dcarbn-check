from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.data_integration import (
    DataBatchRequest,
    DataJourneyPayload,
    DataOperationalEmissionPayload,
    DataVehiclePayload,
)


def test_vehicle_batch_validates() -> None:
    request = DataBatchRequest[DataVehiclePayload](
        idempotency_key="vehicles-2026-08-01",
        records=[
            DataVehiclePayload(
                external_customer_id="customer-1",
                external_vehicle_id="vehicle-1",
                vehicle_type="rigid_hgv",
                fuel_type="diesel",
            )
        ],
    )

    assert request.schema_version == "1.0"
    assert len(request.records) == 1


def test_journey_requires_distance_unit_with_value() -> None:
    with pytest.raises(ValidationError):
        DataJourneyPayload(
            external_customer_id="customer-1",
            external_journey_id="journey-1",
            distance_value=Decimal("10"),
        )


def test_operational_emission_preserves_lineage() -> None:
    payload = DataOperationalEmissionPayload(
        external_customer_id="customer-1",
        external_calculation_id="calc-1",
        methodology_version="DATa-2026.1",
        total_kg_co2e=Decimal("326.745"),
        calculated_at=datetime.now(UTC),
        source_hash="1234567890abcdef",
        lineage={"distance_source": "telematics"},
    )

    assert payload.total_kg_co2e == Decimal("326.745")
    assert payload.lineage["distance_source"] == "telematics"



def test_operational_emission_accepts_governed_comparison_contract() -> None:
    payload = DataOperationalEmissionPayload(
        external_customer_id="customer-1",
        external_calculation_id="calc-compare-1",
        external_activity_key="fleet-route-44-2026",
        method_identifier="dcarbn.route.vehicle.v3",
        methodology_version="DATa-2026.1",
        calculation_software_version="data-engine-3.4.0",
        reporting_period_start=date(2026, 1, 1),
        reporting_period_end=date(2026, 12, 31),
        uncertainty_percentage=Decimal("3.5"),
        comparison_inputs={
            "activity_value": "1250",
            "activity_unit": "tonne.km",
            "government_method_id":
                "scope3.category9.average_diesel_van.tonne_km.uk_2026.v1",
        },
        total_kg_co2e=Decimal("712.20"),
        calculated_at=datetime.now(UTC),
        source_hash="compare12345678",
    )

    assert payload.external_activity_key == "fleet-route-44-2026"
    assert payload.comparison_inputs["activity_unit"] == "tonne.km"
    assert payload.uncertainty_percentage == Decimal("3.5")


def test_operational_emission_requires_complete_comparison_identity() -> None:
    with pytest.raises(
        ValidationError,
        match="external_activity_key, method_identifier",
    ):
        DataOperationalEmissionPayload(
            external_customer_id="customer-1",
            external_calculation_id="calc-incomplete",
            external_activity_key="route-1",
            methodology_version="DATa-2026.1",
            total_kg_co2e=Decimal("10"),
            calculated_at=datetime.now(UTC),
            source_hash="incomplete123",
        )


def test_operational_emission_rejects_reversed_reporting_period() -> None:
    with pytest.raises(
        ValidationError,
        match="reporting_period_end must not precede",
    ):
        DataOperationalEmissionPayload(
            external_customer_id="customer-1",
            external_calculation_id="calc-period",
            methodology_version="DATa-2026.1",
            reporting_period_start=date(2026, 12, 31),
            reporting_period_end=date(2026, 1, 1),
            total_kg_co2e=Decimal("10"),
            calculated_at=datetime.now(UTC),
            source_hash="period123456",
        )
