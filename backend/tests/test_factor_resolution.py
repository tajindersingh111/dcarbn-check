from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from app.factors.resolution import (
    FactorResolutionCriteria,
    ResolutionOutcome,
    resolve_factor,
)
from app.models.emission_factor import GreenhouseGasComponent
from app.units.registry import get_unit_registry


def factor(
    *,
    factor_id: str,
    source_factor_id: str,
    reporting_year: int = 2026,
    geography_code: str = "GB",
    scope: str = "Scope 1",
    level_1: str = "Fuels",
    level_2: str = "Liquid fuels",
    level_3: str = "Diesel",
    activity_unit: str = "litre",
    value: str = "2.51",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=UUID(factor_id),
        factor_set_id=UUID("99999999-9999-9999-9999-999999999999"),
        source_factor_id=source_factor_id,
        reporting_year=reporting_year,
        geography_code=geography_code,
        scope=scope,
        level_1=level_1,
        level_2=level_2,
        level_3=level_3,
        level_4=None,
        column_text=None,
        activity_unit=activity_unit,
        lifecycle_boundary="direct",
        greenhouse_gas_component=GreenhouseGasComponent.TOTAL_CO2E,
        factor_value=Decimal(value),
    )


def criteria(**overrides: object) -> FactorResolutionCriteria:
    values = {
        "reporting_year": 2026,
        "geography_code": "GB",
        "scope": "Scope 1",
        "activity_unit": "litres",
        "level_1": "Fuels",
        "level_2": "Liquid fuels",
        "level_3": "Diesel",
        "lifecycle_boundary": "direct",
    }
    values.update(overrides)
    return FactorResolutionCriteria(**values)


def test_resolves_single_exact_factor() -> None:
    result = resolve_factor(
        [
            factor(
                factor_id="11111111-1111-1111-1111-111111111111",
                source_factor_id="diesel-litres",
            )
        ],
        criteria(),
        Decimal("100"),
        get_unit_registry(),
    )

    assert result.outcome == ResolutionOutcome.RESOLVED
    assert result.selected is not None
    assert result.selected.factor.source_factor_id == "diesel-litres"
    assert result.selected.converted_activity_value == Decimal("100")


def test_returns_ambiguous_when_top_scores_are_equal() -> None:
    result = resolve_factor(
        [
            factor(
                factor_id="11111111-1111-1111-1111-111111111111",
                source_factor_id="diesel-a",
            ),
            factor(
                factor_id="22222222-2222-2222-2222-222222222222",
                source_factor_id="diesel-b",
            ),
        ],
        criteria(),
        Decimal("100"),
        get_unit_registry(),
    )

    assert result.outcome == ResolutionOutcome.AMBIGUOUS
    assert result.selected is None


def test_previous_year_requires_explicit_fallback() -> None:
    previous = factor(
        factor_id="11111111-1111-1111-1111-111111111111",
        source_factor_id="diesel-2025",
        reporting_year=2025,
    )

    strict_result = resolve_factor(
        [previous],
        criteria(),
        Decimal("100"),
        get_unit_registry(),
    )
    fallback_result = resolve_factor(
        [previous],
        criteria(allow_previous_year=True),
        Decimal("100"),
        get_unit_registry(),
    )

    assert strict_result.outcome == ResolutionOutcome.NO_MATCH
    assert fallback_result.outcome == ResolutionOutcome.RESOLVED
    assert fallback_result.warnings
