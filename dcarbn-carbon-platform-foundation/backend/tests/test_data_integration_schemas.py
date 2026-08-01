from datetime import UTC, datetime
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
