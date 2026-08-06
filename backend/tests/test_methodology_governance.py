from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.main import app
from app.services.methodology_governance import compare_methodology_versions, preview_methodology_impact


def method(*, expression: str, version: int = 1, method_key: str = "scope2.location_electricity"):
    return SimpleNamespace(
        id=uuid4(), method_key=method_key, version=version,
        name="Electricity", scope="scope_2", scope_3_category=None,
        jurisdiction="GB", reporting_year=2026, effective_from="2026-01-01",
        effective_to="2026-12-31", expression=expression, output_unit="kg CO2e",
        input_schema={"inputs": [
            {"name": "activity_value", "required": True},
            {"name": "factor_value", "required": True},
        ]}, validation_rules=[], golden_tests=[], source_reference="gov.uk",
        change_reason="Controlled version change.",
    )


def test_compare_versions_reports_only_changed_fields() -> None:
    baseline = method(expression="activity_value * factor_value")
    candidate = method(expression="activity_value * factor_value / 1000", version=2)
    result = compare_methodology_versions(baseline, candidate)
    assert result.same_method_key is True
    assert list(result.changed_fields) == ["expression"]


def test_impact_preview_is_deterministic_and_non_mutating() -> None:
    baseline = method(expression="activity_value * factor_value")
    candidate = method(expression="activity_value * factor_value * 1.1", version=2)
    result = preview_methodology_impact(
        baseline, candidate,
        {"activity_value": Decimal("1000"), "factor_value": Decimal("0.2")},
    )
    assert result.baseline_output == "200.0"
    assert result.candidate_output == "220.00"
    assert result.absolute_change == "20.00"
    assert result.percentage_change == "10.0"


def test_impact_preview_rejects_different_method_keys() -> None:
    with pytest.raises(HTTPException, match="same method key"):
        preview_methodology_impact(
            method(expression="activity_value * factor_value"),
            method(expression="activity_value * factor_value", method_key="scope1.fuel"),
            {"activity_value": Decimal("1"), "factor_value": Decimal("1")},
        )


def test_openapi_exposes_governance_controls() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/methodologies/{methodology_id}/golden-tests" in paths
    assert "/api/v1/methodologies/{baseline_id}/compare/{candidate_id}" in paths
    assert "/api/v1/methodologies/{baseline_id}/impact-preview/{candidate_id}" in paths
    assert "/api/v1/methodologies/{methodology_id}/retire" in paths
