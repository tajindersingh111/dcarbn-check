from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Iterable
from uuid import UUID

from app.models.emission_factor import (
    EmissionFactor,
    GreenhouseGasComponent,
)
from app.units.registry import UnitConversionError, UnitRegistry


class ResolutionOutcome(StrEnum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    NO_MATCH = "no_match"
    INCOMPATIBLE_UNIT = "incompatible_unit"


class MatchStrength(StrEnum):
    EXACT = "exact"
    STRONG = "strong"
    FALLBACK = "fallback"


@dataclass(frozen=True, slots=True)
class FactorResolutionCriteria:
    reporting_year: int
    geography_code: str
    scope: str
    activity_unit: str
    level_1: str | None = None
    level_2: str | None = None
    level_3: str | None = None
    level_4: str | None = None
    column_text: str | None = None
    lifecycle_boundary: str | None = None
    greenhouse_gas_component: GreenhouseGasComponent = (
        GreenhouseGasComponent.TOTAL_CO2E
    )
    factor_set_id: UUID | None = None
    allow_previous_year: bool = False
    allow_geography_fallback: bool = False


@dataclass(frozen=True, slots=True)
class ScoredFactor:
    factor: EmissionFactor
    score: int
    strength: MatchStrength
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    converted_activity_value: Decimal
    factor_activity_unit: str


@dataclass(frozen=True, slots=True)
class FactorResolutionResult:
    outcome: ResolutionOutcome
    selected: ScoredFactor | None
    candidates: tuple[ScoredFactor, ...]
    warnings: tuple[str, ...]


def _equal_text(first: str | None, second: str | None) -> bool:
    if first is None or second is None:
        return False
    return " ".join(first.casefold().split()) == " ".join(second.casefold().split())


def _contains_text(value: str | None, query: str | None) -> bool:
    if not value or not query:
        return False
    return " ".join(query.casefold().split()) in " ".join(
        value.casefold().split()
    )


def _score_optional_level(
    *,
    criterion: str | None,
    actual: str | None,
    exact_points: int,
    contains_points: int,
    reasons: list[str],
    label: str,
) -> int:
    if criterion is None:
        return 0
    if _equal_text(criterion, actual):
        reasons.append(f"{label} exact")
        return exact_points
    if _contains_text(actual, criterion):
        reasons.append(f"{label} partial")
        return contains_points
    return -exact_points


def score_factor(
    factor: EmissionFactor,
    criteria: FactorResolutionCriteria,
    activity_value: Decimal,
    unit_registry: UnitRegistry,
) -> ScoredFactor | None:
    reasons: list[str] = []
    warnings: list[str] = []
    score = 0

    if factor.greenhouse_gas_component != criteria.greenhouse_gas_component:
        return None

    if criteria.factor_set_id is not None and factor.factor_set_id != criteria.factor_set_id:
        return None

    if _equal_text(factor.scope, criteria.scope):
        score += 120
        reasons.append("scope exact")
    else:
        return None

    if factor.reporting_year == criteria.reporting_year:
        score += 100
        reasons.append("reporting year exact")
    elif (
        criteria.allow_previous_year
        and factor.reporting_year < criteria.reporting_year
    ):
        year_gap = criteria.reporting_year - factor.reporting_year
        score += max(10, 70 - year_gap * 10)
        warnings.append(
            f"Previous-year factor used: {factor.reporting_year} "
            f"for reporting year {criteria.reporting_year}."
        )
        reasons.append("previous reporting year")
    else:
        return None

    if factor.geography_code.casefold() == criteria.geography_code.casefold():
        score += 80
        reasons.append("geography exact")
    elif criteria.allow_geography_fallback:
        score += 10
        warnings.append(
            f"Geography fallback used: factor {factor.geography_code}, "
            f"requested {criteria.geography_code}."
        )
        reasons.append("geography fallback")
    else:
        return None

    try:
        converted_activity_value = unit_registry.convert(
            activity_value,
            criteria.activity_unit,
            factor.activity_unit,
        )
        score += 100
        reasons.append("activity unit compatible")
        if unit_registry.canonical_name(criteria.activity_unit) == unit_registry.canonical_name(
            factor.activity_unit
        ):
            score += 20
            reasons.append("activity unit exact")
    except UnitConversionError:
        return None

    score += _score_optional_level(
        criterion=criteria.level_1,
        actual=factor.level_1,
        exact_points=80,
        contains_points=40,
        reasons=reasons,
        label="level 1",
    )
    score += _score_optional_level(
        criterion=criteria.level_2,
        actual=factor.level_2,
        exact_points=60,
        contains_points=30,
        reasons=reasons,
        label="level 2",
    )
    score += _score_optional_level(
        criterion=criteria.level_3,
        actual=factor.level_3,
        exact_points=50,
        contains_points=25,
        reasons=reasons,
        label="level 3",
    )
    score += _score_optional_level(
        criterion=criteria.level_4,
        actual=factor.level_4,
        exact_points=40,
        contains_points=20,
        reasons=reasons,
        label="level 4",
    )
    score += _score_optional_level(
        criterion=criteria.column_text,
        actual=factor.column_text,
        exact_points=35,
        contains_points=15,
        reasons=reasons,
        label="column text",
    )

    if criteria.lifecycle_boundary:
        if _equal_text(criteria.lifecycle_boundary, factor.lifecycle_boundary):
            score += 60
            reasons.append("lifecycle boundary exact")
        else:
            score -= 60

    if warnings:
        strength = MatchStrength.FALLBACK
    elif score >= 600:
        strength = MatchStrength.EXACT
    else:
        strength = MatchStrength.STRONG

    return ScoredFactor(
        factor=factor,
        score=score,
        strength=strength,
        reasons=tuple(reasons),
        warnings=tuple(warnings),
        converted_activity_value=converted_activity_value,
        factor_activity_unit=factor.activity_unit,
    )


def resolve_factor(
    factors: Iterable[EmissionFactor],
    criteria: FactorResolutionCriteria,
    activity_value: Decimal,
    unit_registry: UnitRegistry,
) -> FactorResolutionResult:
    scored = [
        candidate
        for factor in factors
        if (
            candidate := score_factor(
                factor,
                criteria,
                activity_value,
                unit_registry,
            )
        )
        is not None
    ]
    scored.sort(
        key=lambda candidate: (
            -candidate.score,
            candidate.factor.source_factor_id,
        )
    )

    if not scored:
        try:
            unit_registry.resolve(criteria.activity_unit)
        except UnitConversionError as exc:
            return FactorResolutionResult(
                outcome=ResolutionOutcome.INCOMPATIBLE_UNIT,
                selected=None,
                candidates=(),
                warnings=(str(exc),),
            )
        return FactorResolutionResult(
            outcome=ResolutionOutcome.NO_MATCH,
            selected=None,
            candidates=(),
            warnings=("No approved factor matched the supplied criteria.",),
        )

    top_score = scored[0].score
    top_matches = [
        candidate for candidate in scored if candidate.score == top_score
    ]
    if len(top_matches) > 1:
        return FactorResolutionResult(
            outcome=ResolutionOutcome.AMBIGUOUS,
            selected=None,
            candidates=tuple(scored[:20]),
            warnings=(
                f"{len(top_matches)} factors share the highest score "
                f"of {top_score}; manual selection is required.",
            ),
        )

    selected = scored[0]
    return FactorResolutionResult(
        outcome=ResolutionOutcome.RESOLVED,
        selected=selected,
        candidates=tuple(scored[:20]),
        warnings=selected.warnings,
    )
