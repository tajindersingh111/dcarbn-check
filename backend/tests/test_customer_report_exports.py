from io import BytesIO

from pypdf import PdfReader

from app.reports.customer_exports import (
    build_audit_report_csv,
    build_audit_report_pdf,
)


def report_payload() -> dict[str, object]:
    return {
        "report_schema_version": "1.2",
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
        "scope_3_category_dispositions": [
            {
                "category": 1,
                "disposition": "included",
                "rationale": "Material purchased goods are calculated.",
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

    assert "report_sha256,result_id,activity_id" in content
    assert "abc123,result-1,activity-1" in content
    assert "factor-1,0.05,kWh" in content
    assert "invoice-1" in content


def test_pdf_export_is_deterministic_and_valid() -> None:
    first = build_audit_report_pdf(report_payload(), "abc123")
    second = build_audit_report_pdf(report_payload(), "abc123")

    assert first == second
    assert first.startswith(b"%PDF-")
    reader = PdfReader(BytesIO(first))
    extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "DcarbN Analytics" in extracted_text
    assert reader.metadata is not None
    assert reader.metadata.title == "DcarbN Analytics GHG Inventory Report"
    assert len(first) > 2000


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
