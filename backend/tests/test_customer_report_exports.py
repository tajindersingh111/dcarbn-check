from io import BytesIO

from app.reports.customer_exports import (
    build_audit_report_csv,
    build_audit_report_pdf,
)
from pypdf import PdfReader


def report_payload() -> dict[str, object]:
    return {
        "report_schema_version": "1.6",
        "assurance_readiness": {
            "status": "assurance_ready",
            "claim_wording": "Assurance-ready reporting pack",
            "ready": True,
            "checks": [],
            "blockers": [],
            "external_assurance_required": True,
        },
        "inventory": {"name": "Northstar 2026"},
        "reporting_period": {
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        },
        "organisational_boundary": {
            "consolidation_approach": "operational_control",
            "status": "approved",
        },
        "approval": {
            "reviewer_id": "independent-reviewer",
            "decided_at": "2026-08-05T12:00:00Z",
        },
        "totals": {
            "scope_1_kg_co2e": "100",
            "scope_2_location_based_kg_co2e": "50",
            "scope_2_market_based_kg_co2e": "30",
            "scope_3_kg_co2e": "200",
            "scope_2_headline_basis": "location_based",
            "total_t_co2e": "0.35",
        },
        "defensibility_statement": {
            "preparation_basis": "Prepared from governed calculation records.",
            "assurance_limitation": "Not independently verified.",
        },
        "data_quality": {
            "activity_count": 1,
            "average_score": 90,
            "evidence_coverage_percent": "100",
            "level_distribution": {
                "primary": 1,
                "secondary": 0,
                "estimated": 0,
                "unknown": 0,
            },
        },
        "uncertainty": {
            "quantitative_status": "not_quantified",
            "confidence_interval": None,
            "qualitative_sources": ["No estimated activity data."],
        },
        "calculation_comparisons": [
            {
                "comparison_id": "comparison-1",
                "comparison_group_key": "dcarbn:route-199:2026",
                "status": "ready",
                "reporting_basis": "dcarbn_operational",
                "basis_reason": "DcarbN is the approved headline basis.",
                "comparison_unavailable_reason": None,
                "absolute_delta_kg_co2e": "5",
                "percentage_delta": "11.11111111",
                "dcarbn_result": {
                    "result_id": "result-1",
                    "allocated_kg_co2e": "50",
                    "methodology_version": "approved-exact-v1",
                    "factor_id": "factor-1",
                    "lineage": {"source": "DcarbN"},
                },
                "uk_government_comparator": {
                    "result_id": "government-result-1",
                    "allocated_kg_co2e": "45",
                    "methodology_version": "UK-Government-comparator-v1",
                    "factor_id": "government-factor-1",
                    "lineage": {"governed_method_id": "uk-2026-v1"},
                },
                "disclosure": (
                    "The UK Government result is a disclosure-only comparator "
                    "and is excluded from inventory totals. This comparison does "
                    "not imply UK Government endorsement of the DcarbN methodology."
                ),
            }
        ],
        "scope_3_category_dispositions": [
            {
                "category": 1,
                "disposition": "included",
                "rationale": "Material purchased goods are calculated.",
            }
        ],
        "bioenergy_disclosures": [
            {
                "method": "UK Government 2024 Biodiesel HVO",
                "reporting_year": 2024,
                "hvo_litres": "976227",
                "scope_3_hvo_litres": "976227",
                "complete": True,
                "reconciliation_note": ("Scope 1 and Scope 3 Category 3 HVO litres reconcile."),
                "scope_1_kg_co2e": "34734.15666",
                "scope_3_category_3_wtt_kg_co2e": "545710.893",
                "biogenic_co2_outside_scopes_kg": "2372231.61",
                "note": ("HVO combustion CO2 is biogenic and disclosed outside Scopes 1, 2 and 3."),
            }
        ],
        "results": [
            {
                "id": "result-1",
                "activity_id": "activity-1",
                "activity_date": "2026-06-30",
                "description": "Purchased electricity",
                "scope": "scope_2",
                "scope_2_method": "location_based",
                "scope_3_category": None,
                "original_activity_value": "1000",
                "original_activity_unit": "kWh",
                "selected_factor_id": "factor-1",
                "factor_value": "0.05",
                "factor_activity_unit": "kWh",
                "gross_kg_co2e": "50",
                "allocated_kg_co2e": "50",
                "allocation_percentage": "100",
                "calculation_formula": "activity x factor",
                "methodology_version": "approved-exact-v1",
                "evidence_reference": "invoice-1",
                "warnings": [],
            }
        ],
    }


def test_csv_export_contains_full_lineage() -> None:
    content = build_audit_report_csv(report_payload(), "abc123").decode("utf-8-sig")

    assert "report_sha256,assurance_readiness_status,assurance_claim" in content
    assert "abc123,assurance_ready,Assurance-ready reporting pack,result-1" in content
    assert "factor-1,0.05,kWh" in content
    assert "invoice-1" in content
    assert "dcarbn_kg_co2e" in content
    assert "50,approved-exact-v1,45,UK-Government-comparator-v1" in content
    assert "disclosure-only comparator" in content
    assert "hvo_biogenic_co2_outside_scopes_kg" in content
    assert "2372231.61" in content


def test_csv_export_preserves_year_specific_hvo_disclosures() -> None:
    payload = report_payload()
    disclosures = payload["bioenergy_disclosures"]
    assert isinstance(disclosures, list)
    disclosures.insert(
        0,
        {
            "method": "UK Government 2023 Biodiesel HVO",
            "reporting_year": 2023,
            "scope_1_kg_co2e": "35.58",
            "scope_3_category_3_wtt_kg_co2e": "278.44",
            "biogenic_co2_outside_scopes_kg": "2430.00",
            "reconciliation_note": "2023 litres reconcile.",
            "note": "2023 governed disclosure.",
        },
    )

    content = build_audit_report_csv(payload, "abc123").decode("utf-8-sig")

    assert "hvo_reporting_years" in content
    assert "2023 | 2024" in content
    assert "2023: 2430.00 | 2024: 2372231.61" in content


def test_pdf_export_is_deterministic_and_valid() -> None:
    first = build_audit_report_pdf(report_payload(), "abc123")
    second = build_audit_report_pdf(report_payload(), "abc123")

    assert first == second
    assert first.startswith(b"%PDF-")
    reader = PdfReader(BytesIO(first))
    extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    normalized_text = " ".join(extracted_text.split())
    assert "DcarbN Analytics" in normalized_text
    assert "Assurance-ready reporting pack" in normalized_text
    assert "DcarbN and UK Government comparison" in normalized_text
    assert "50 kg CO2e" in normalized_text
    assert "45 kg CO2e" in normalized_text
    assert "UK-Government-comparator-v1" in normalized_text
    assert "excluded from inventory totals" in normalized_text
    assert "does not imply UK Government endorsement" in normalized_text
    assert "HVO bioenergy disclosure" in normalized_text
    assert "2372231.61 kg CO2" in normalized_text
    assert "Scope 1 and Scope 3 Category 3 HVO litres reconcile" in normalized_text
    assert reader.metadata is not None
    assert reader.metadata.title == "DcarbN Analytics GHG Inventory Report"
    assert len(first) > 2000


def test_pdf_export_discloses_draft_blockers() -> None:
    payload = report_payload()
    payload["assurance_readiness"] = {
        "status": "draft_calculation_not_fully_validated",
        "claim_wording": "Draft — calculation not fully validated",
        "ready": False,
        "checks": [],
        "blockers": ["Every current activity has a supporting evidence reference."],
        "external_assurance_required": True,
    }

    reader = PdfReader(BytesIO(build_audit_report_pdf(payload, "abc123")))
    text = " ".join(" ".join(page.extract_text() or "" for page in reader.pages).split())

    assert "Draft — calculation not fully validated" in text
    assert "Every current activity has a supporting evidence reference" in text


def test_pdf_repeats_header_across_paginated_disclosures() -> None:
    payload = report_payload()
    payload["scope_3_category_dispositions"] = [
        {
            "category": category,
            "disposition": "excluded",
            "rationale": "Assessed against the approved organisational boundary.",
        }
        for category in range(1, 16)
    ]
    result = dict(report_payload()["results"][0])  # type: ignore[index]
    payload["results"] = [
        {**result, "id": f"result-{index}", "activity_id": f"activity-{index}"}
        for index in range(1, 7)
    ]

    reader = PdfReader(BytesIO(build_audit_report_pdf(payload, "abc123")))

    assert len(reader.pages) >= 2
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        assert "DcarbN Analytics" in text
        assert "GHG Inventory Report" in text
        assert f"Page {page_number}" in text
