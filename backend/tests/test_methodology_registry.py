from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.calculations.formula_language import (
    FormulaValidationError,
    evaluate_formula,
)
from app.main import app
from app.schemas.methodology import MethodologyVersionCreate
from app.services.methodologies import execute_golden_tests


def valid_methodology() -> dict[str, object]:
    return {
        "method_key": "scope2.location_electricity",
        "name": "Scope 2 location-based electricity",
        "scope": "scope_2",
        "jurisdiction": "GB",
        "reporting_year": 2026,
        "effective_from": date(2026, 1, 1),
        "effective_to": date(2026, 12, 31),
        "expression": "activity_value * factor_value * allocation_percentage / 100",
        "output_unit": "kg CO2e",
        "inputs": [
            {"name": "activity_value", "unit": "kWh", "minimum": "0"},
            {"name": "factor_value", "unit": "kg CO2e/kWh", "minimum": "0"},
            {
                "name": "allocation_percentage",
                "unit": "percent",
                "minimum": "0",
                "maximum": "100",
            },
        ],
        "golden_tests": [
            {
                "name": "full allocation",
                "inputs": {
                    "activity_value": "1000",
                    "factor_value": "0.2",
                    "allocation_percentage": "100",
                },
                "expected_output": "200",
                "tolerance": "0",
            }
        ],
        "source_reference": "https://www.gov.uk/government/publications/",
        "change_reason": "Initial controlled methodology registry version.",
    }


def test_evaluates_decimal_formula_without_binary_float_drift() -> None:
    result = evaluate_formula(
        "activity_value * factor_value * allocation_percentage / 100",
        {
            "activity_value": Decimal("1000"),
            "factor_value": Decimal("0.22928"),
            "allocation_percentage": Decimal("100"),
        },
    )

    assert result == Decimal("229.28000")


def test_rejects_function_calls_and_arbitrary_code() -> None:
    with pytest.raises(FormulaValidationError, match="unsupported syntax"):
        evaluate_formula(
            "__import__('os').system('whoami')",
            {},
        )


def test_rejects_undeclared_variables() -> None:
    with pytest.raises(ValidationError, match="undeclared variable"):
        MethodologyVersionCreate.model_validate(
            {**valid_methodology(), "expression": "activity_value * secret_factor"}
        )


def test_rejects_incomplete_golden_test_inputs() -> None:
    payload = valid_methodology()
    payload["golden_tests"] = [
        {
            "name": "missing allocation",
            "inputs": {
                "activity_value": "1000",
                "factor_value": "0.2",
            },
            "expected_output": "200",
        }
    ]

    with pytest.raises(ValidationError, match="exactly the declared inputs"):
        MethodologyVersionCreate.model_validate(payload)


def test_scope3_method_requires_category() -> None:
    with pytest.raises(ValidationError, match="scope_3_category is required"):
        MethodologyVersionCreate.model_validate(
            {**valid_methodology(), "scope": "scope_3"}
        )


def test_golden_test_runner_rejects_changed_formula_output() -> None:
    with pytest.raises(FormulaValidationError, match="Golden test.*failed"):
        execute_golden_tests(
            expression="activity_value * factor_value",
            golden_tests=[
                {
                    "name": "published control",
                    "inputs": {
                        "activity_value": "1000",
                        "factor_value": "0.22928",
                    },
                    "expected_output": "200",
                    "tolerance": "0",
                }
            ],
        )


def test_openapi_exposes_controlled_methodology_lifecycle() -> None:
    paths = app.openapi()["paths"]

    assert "/api/v1/methodologies" in paths
    for action in ("submit", "review", "approve", "activate"):
        path = f"/api/v1/methodologies/{{methodology_id}}/{action}"
        assert path in paths
        assert "post" in paths[path]
