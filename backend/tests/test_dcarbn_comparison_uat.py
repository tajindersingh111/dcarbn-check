from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.integrations.data.hashing import canonical_json_sha256
from app.schemas.data_integration import (
    DataBatchRequest,
    DataOperationalEmissionPayload,
)
from app.services.data_comparisons import (
    _comparison_inputs,
    calculate_comparison_delta,
)
from app.services.data_review import (
    _parse_scope,
    _validate_confirmed_classification,
)

FIXTURE = (
    Path(__file__).parents[2]
    / "docs"
    / "uat"
    / "fixtures"
    / "dcarbn-operational-emissions-v2.json"
)


def _batch() -> DataBatchRequest[DataOperationalEmissionPayload]:
    return DataBatchRequest[DataOperationalEmissionPayload].model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )


def _confirmed(record: DataOperationalEmissionPayload) -> Any:
    return SimpleNamespace(
        confirmed_scope=record.suggested_scope,
        confirmed_scope_3_category=record.suggested_scope_3_category,
        comparison_inputs_json=record.comparison_inputs,
    )


def test_uat_contract_is_versioned_idempotent_and_uniquely_grouped() -> None:
    batch = _batch()

    assert batch.schema_version == "2.0"
    assert batch.idempotency_key == "uat-comparison"
    assert len(batch.records) == 4
    activity_keys = [record.external_activity_key for record in batch.records]
    source_hashes = [record.source_hash for record in batch.records]
    assert len(set(activity_keys)) == len(activity_keys)
    assert len(set(source_hashes)) == len(source_hashes)


@pytest.mark.parametrize(
    ("calculation_id", "scope", "category", "unit"),
    [
        ("UAT-S1-FLEET-001", "scope_1", None, "km"),
        ("UAT-S3-CAT4-001", "scope_3", 4, "tonne.km"),
        ("UAT-S3-CAT9-001", "scope_3", 9, "tonne.km"),
    ],
)
def test_uat_reviewer_routes_each_customer_journey_to_governed_method(
    calculation_id: str,
    scope: str,
    category: int | None,
    unit: str,
) -> None:
    record = next(
        item for item in _batch().records
        if item.external_calculation_id == calculation_id
    )
    confirmed_scope = _parse_scope(record.suggested_scope)
    _validate_confirmed_classification(
        confirmed_scope,
        record.suggested_scope_3_category,
    )
    method, value, activity_unit = _comparison_inputs(_confirmed(record))

    assert confirmed_scope.value == scope
    assert record.suggested_scope_3_category == category
    assert method.value == record.comparison_inputs["government_method_id"]
    assert value == Decimal(str(record.comparison_inputs["activity_value"]))
    assert activity_unit == unit


@pytest.mark.parametrize(
    ("calculation_id", "expected_relation"),
    [
        ("UAT-S1-FLEET-001", "higher"),
        ("UAT-S3-CAT4-001", "lower"),
        ("UAT-S3-CAT9-001", "equal"),
    ],
)
def test_uat_golden_comparison_relations(
    calculation_id: str,
    expected_relation: str,
) -> None:
    record = next(
        item for item in _batch().records
        if item.external_calculation_id == calculation_id
    )
    baseline = Decimal(
        str(record.metadata["uat_government_baseline_kg_co2e"])
    )
    absolute, percentage = calculate_comparison_delta(
        record.total_kg_co2e,
        baseline,
    )

    relation = "equal"
    if absolute > 0:
        relation = "higher"
    elif absolute < 0:
        relation = "lower"
    assert relation == expected_relation
    assert percentage is not None


def test_uat_zero_baseline_is_explicitly_non_percentage() -> None:
    absolute, percentage = calculate_comparison_delta(
        Decimal("75"),
        Decimal("0"),
    )

    assert absolute == Decimal("75")
    assert percentage is None


def test_uat_missing_comparison_inputs_produce_unavailable_path() -> None:
    record = next(
        item for item in _batch().records
        if item.external_calculation_id == "UAT-S3-UNAVAILABLE-001"
    )

    with pytest.raises(
        ValueError,
        match="comparison_inputs.government_method_id is required",
    ):
        _comparison_inputs(_confirmed(record))
    assert record.metadata["uat_expected_status"] == "comparison_unavailable"


def test_locked_comparison_snapshot_is_reproducible_and_change_sensitive() -> None:
    batch = _batch()
    snapshot = {
        "report_schema_version": "1.3",
        "idempotency_key": batch.idempotency_key,
        "records": [
            record.model_dump(mode="json")
            for record in batch.records
        ],
        "reporting_basis": "dcarbn_operational",
        "comparison_only_included_in_totals": False,
    }

    first_hash = canonical_json_sha256(snapshot)
    second_hash = canonical_json_sha256(
        {
            "comparison_only_included_in_totals": False,
            "reporting_basis": "dcarbn_operational",
            "records": snapshot["records"],
            "idempotency_key": batch.idempotency_key,
            "report_schema_version": "1.3",
        }
    )
    changed_snapshot = dict(snapshot)
    changed_records = [
        dict(item) for item in snapshot["records"]  # type: ignore[arg-type]
    ]
    changed_records[0]["source_hash"] = "changed-source-hash"
    changed_snapshot["records"] = changed_records

    assert first_hash == second_hash
    assert canonical_json_sha256(changed_snapshot) != first_hash
