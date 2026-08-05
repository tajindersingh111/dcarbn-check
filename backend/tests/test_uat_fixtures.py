from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.data_integration import (
    DataBatchRequest,
    DataJourneyPayload,
    DataVehiclePayload,
)

FIXTURES = Path(__file__).parents[2] / "docs" / "uat" / "fixtures"


def test_uat_vehicle_fixture_matches_contract() -> None:
    batch = DataBatchRequest[DataVehiclePayload].model_validate_json(
        (FIXTURES / "vehicles.json").read_text(encoding="utf-8")
    )

    assert batch.idempotency_key == "UAT-VEHICLES-001"
    assert len(batch.records) == 2


def test_uat_journey_fixture_matches_contract() -> None:
    batch = DataBatchRequest[DataJourneyPayload].model_validate_json(
        (FIXTURES / "journeys.json").read_text(encoding="utf-8")
    )

    assert batch.idempotency_key == "uat-journeys"
    assert len(batch.records) == 2


def test_invalid_uat_journey_fixture_is_rejected() -> None:
    with pytest.raises(
        ValidationError,
        match="distance_value and distance_unit must be supplied together",
    ):
        DataBatchRequest[DataJourneyPayload].model_validate_json(
            (FIXTURES / "journeys-invalid.json").read_text(encoding="utf-8")
        )
