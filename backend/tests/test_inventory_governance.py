from decimal import Decimal
from inspect import signature
from types import SimpleNamespace
from uuid import UUID

import pytest
from app.models.inventory_governance import (
    ApprovalStatus,
    RestatementStatus,
    RestatementTrigger,
)
from app.schemas.inventory_governance import (
    ApprovalDecision,
    ReportGenerateRequest,
    RestatementDecision,
    RestatementRequestCreate,
)
from app.services.inventory_governance import (
    _assess_assurance_readiness,
    _build_hvo_2023_disclosure,
    _build_hvo_2024_disclosure,
    _build_hvo_disclosures,
    _lock_snapshot,
)
from pydantic import ValidationError


def test_approval_decision_accepts_approved() -> None:
    payload = ApprovalDecision(
        decision=ApprovalStatus.APPROVED,
        decision_reason="All approval controls and supporting evidence are complete.",
    )

    assert payload.decision == ApprovalStatus.APPROVED


def test_approval_decision_rejects_pending() -> None:
    with pytest.raises(ValidationError):
        ApprovalDecision(
            decision=ApprovalStatus.PENDING,
            decision_reason="This is not a valid final decision.",
        )


def test_restatement_decision_accepts_rejected() -> None:
    payload = RestatementDecision(
        decision=RestatementStatus.REJECTED,
        decision_reason="The identified variance is not material to the inventory.",
    )

    assert payload.decision == RestatementStatus.REJECTED


def test_restatement_request_accepts_quantified_materiality() -> None:
    payload = RestatementRequestCreate(
        trigger=RestatementTrigger.MATERIAL_ERROR,
        reason="A material source-data error was identified after approval.",
        materiality_assessment="The estimated change is material to reported emissions.",
        estimated_impact_percent="6.25",
    )

    assert payload.estimated_impact_percent is not None
    assert payload.estimated_impact_percent.as_tuple().exponent == -2


def test_restatement_request_requires_override_rationale() -> None:
    with pytest.raises(ValidationError):
        RestatementRequestCreate(
            trigger=RestatementTrigger.METHODOLOGY_CHANGE,
            reason="The governed calculation methodology has changed.",
            materiality_assessment="Impact cannot yet be quantified reliably.",
            qualitative_override=True,
        )


def test_boundary_restatement_requires_change_summary() -> None:
    with pytest.raises(ValidationError):
        RestatementRequestCreate(
            trigger=RestatementTrigger.ACQUISITION,
            reason="A controlled business was acquired during the period.",
            materiality_assessment="The acquisition changes the inventory boundary.",
            estimated_impact_percent="8.0",
        )


def test_report_generation_requires_explicit_scope2_headline_basis() -> None:
    with pytest.raises(ValidationError):
        ReportGenerateRequest(finalize=False)


def test_report_generation_accepts_market_based_headline_basis() -> None:
    payload = ReportGenerateRequest(
        finalize=True,
        scope_2_headline_basis="market_based",
    )

    assert payload.scope_2_headline_basis.value == "market_based"


def test_lock_snapshot_keeps_runtime_call_contract() -> None:
    assert list(signature(_lock_snapshot).parameters) == [
        "db",
        "inventory",
        "approval",
    ]


def test_hvo_disclosure_reconciles_matching_scope_entries() -> None:
    scope1_id = UUID("11111111-1111-1111-1111-111111111111")
    wtt_id = UUID("22222222-2222-2222-2222-222222222222")
    activities = {
        scope1_id: SimpleNamespace(
            metadata_json={
                "calculation_method_id": ("scope1.mobile_combustion.hvo.litres.uk_2024.v1")
            }
        ),
        wtt_id: SimpleNamespace(
            metadata_json={"calculation_method_id": ("scope3.category3.hvo_wtt.litres.uk_2024.v1")}
        ),
    }
    results = [
        SimpleNamespace(
            activity_id=scope1_id,
            factor_activity_value=Decimal("976227"),
            allocation_multiplier=Decimal(1),
            allocated_kg_co2e=Decimal("34734.15666"),
        ),
        SimpleNamespace(
            activity_id=wtt_id,
            factor_activity_value=Decimal("976227"),
            allocation_multiplier=Decimal(1),
            allocated_kg_co2e=Decimal("545710.893"),
        ),
    ]

    disclosure = _build_hvo_2024_disclosure(results, activities)  # type: ignore[arg-type]

    assert disclosure is not None
    assert disclosure["complete"] is True
    assert disclosure["biogenic_co2_outside_scopes_kg"] == "2372231.61"
    assert disclosure["scope_3_hvo_litres"] == "976227"


def test_uk_2023_hvo_disclosure_uses_year_specific_factors() -> None:
    scope1_id = UUID("33333333-3333-3333-3333-333333333333")
    wtt_id = UUID("44444444-4444-4444-4444-444444444444")
    activities = {
        scope1_id: SimpleNamespace(
            metadata_json={
                "calculation_method_id": "scope1.mobile_combustion.hvo.litres.uk_2023.v1"
            }
        ),
        wtt_id: SimpleNamespace(
            metadata_json={"calculation_method_id": "scope3.category3.hvo_wtt.litres.uk_2023.v1"}
        ),
    }
    results = [
        SimpleNamespace(
            activity_id=scope1_id,
            factor_activity_value=Decimal("1000"),
            allocation_multiplier=Decimal(1),
            allocated_kg_co2e=Decimal("35.58"),
        ),
        SimpleNamespace(
            activity_id=wtt_id,
            factor_activity_value=Decimal("1000"),
            allocation_multiplier=Decimal(1),
            allocated_kg_co2e=Decimal("278.44"),
        ),
    ]

    disclosure = _build_hvo_2023_disclosure(results, activities)  # type: ignore[arg-type]

    assert disclosure is not None
    assert disclosure["reporting_year"] == 2023
    assert disclosure["complete"] is True
    assert disclosure["scope_3_wtt_factor_kg_co2e_per_litre"] == "0.27844"
    assert disclosure["biogenic_co2_outside_scopes_kg"] == "2430.00"


def test_hvo_reconciliation_is_separate_for_each_calendar_year() -> None:
    scope1_2023 = UUID("11111111-1111-1111-1111-111111111123")
    wtt_2023 = UUID("22222222-2222-2222-2222-222222222123")
    scope1_2024 = UUID("11111111-1111-1111-1111-111111111124")
    wtt_2024 = UUID("22222222-2222-2222-2222-222222222124")
    activities = {
        scope1_2023: SimpleNamespace(
            metadata_json={
                "calculation_method_id": "scope1.mobile_combustion.hvo.litres.uk_2023.v1"
            }
        ),
        wtt_2023: SimpleNamespace(
            metadata_json={"calculation_method_id": "scope3.category3.hvo_wtt.litres.uk_2023.v1"}
        ),
        scope1_2024: SimpleNamespace(
            metadata_json={
                "calculation_method_id": "scope1.mobile_combustion.hvo.litres.uk_2024.v1"
            }
        ),
        wtt_2024: SimpleNamespace(
            metadata_json={"calculation_method_id": "scope3.category3.hvo_wtt.litres.uk_2024.v1"}
        ),
    }
    results = [
        SimpleNamespace(
            activity_id=scope1_2023,
            factor_activity_value=Decimal("100"),
            allocation_multiplier=Decimal(1),
            allocated_kg_co2e=Decimal("3.558"),
        ),
        SimpleNamespace(
            activity_id=wtt_2023,
            factor_activity_value=Decimal("90"),
            allocation_multiplier=Decimal(1),
            allocated_kg_co2e=Decimal("25.0596"),
        ),
        SimpleNamespace(
            activity_id=scope1_2024,
            factor_activity_value=Decimal("50"),
            allocation_multiplier=Decimal(1),
            allocated_kg_co2e=Decimal("1.779"),
        ),
        SimpleNamespace(
            activity_id=wtt_2024,
            factor_activity_value=Decimal("60"),
            allocation_multiplier=Decimal(1),
            allocated_kg_co2e=Decimal("33.54"),
        ),
    ]

    disclosures = _build_hvo_disclosures(results, activities)  # type: ignore[arg-type]

    assert [item["reporting_year"] for item in disclosures] == [2023, 2024]
    assert [item["complete"] for item in disclosures] == [False, False]


def test_hvo_disclosure_marks_mismatched_litres_incomplete() -> None:
    scope1_id = UUID("11111111-1111-1111-1111-111111111111")
    wtt_id = UUID("22222222-2222-2222-2222-222222222222")
    activities = {
        scope1_id: SimpleNamespace(
            metadata_json={
                "calculation_method_id": ("scope1.mobile_combustion.hvo.litres.uk_2024.v1")
            }
        ),
        wtt_id: SimpleNamespace(
            metadata_json={"calculation_method_id": ("scope3.category3.hvo_wtt.litres.uk_2024.v1")}
        ),
    }
    results = [
        SimpleNamespace(
            activity_id=scope1_id,
            factor_activity_value=Decimal("100"),
            allocation_multiplier=Decimal(1),
            allocated_kg_co2e=Decimal("3.558"),
        ),
        SimpleNamespace(
            activity_id=wtt_id,
            factor_activity_value=Decimal("99"),
            allocation_multiplier=Decimal(1),
            allocated_kg_co2e=Decimal("55.341"),
        ),
    ]

    disclosure = _build_hvo_2024_disclosure(results, activities)  # type: ignore[arg-type]

    assert disclosure is not None
    assert disclosure["complete"] is False
    assert "must both be present" in str(disclosure["reconciliation_note"])


def test_assurance_readiness_passes_only_complete_controls() -> None:
    assessment = _assess_assurance_readiness(
        boundary_approved=True,
        approval_separated=True,
        result_count=3,
        result_lineage_complete=True,
        evidence_coverage_percent=Decimal(100),
        included_scope3_categories={4},
        calculated_scope3_categories={4},
        scope2_present=True,
        scope2_dual_reporting_complete=True,
        bioenergy_reporting_complete=True,
        unresolved_warning_count=0,
        open_restatement_count=0,
    )

    assert assessment["ready"] is True
    assert assessment["status"] == "assurance_ready"
    assert assessment["blockers"] == []


def test_assurance_readiness_returns_specific_blockers() -> None:
    assessment = _assess_assurance_readiness(
        boundary_approved=True,
        approval_separated=True,
        result_count=2,
        result_lineage_complete=True,
        evidence_coverage_percent=Decimal(50),
        included_scope3_categories={1, 4},
        calculated_scope3_categories={4},
        scope2_present=False,
        scope2_dual_reporting_complete=False,
        bioenergy_reporting_complete=False,
        unresolved_warning_count=1,
        open_restatement_count=0,
    )

    assert assessment["ready"] is False
    assert assessment["status"] == "draft_calculation_not_fully_validated"
    failed = {item["code"] for item in assessment["checks"] if not item["passed"]}
    assert failed == {
        "evidence_coverage",
        "scope3_included_category_results",
        "bioenergy_scope_coverage",
        "unresolved_calculation_warnings",
    }
