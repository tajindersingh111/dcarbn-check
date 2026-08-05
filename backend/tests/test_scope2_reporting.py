from datetime import date

import pytest

from app.calculations.scope2_reporting import validate_market_based_evidence


def complete_evidence() -> dict[str, object]:
    return {
        "instrument_type": "supplier_specific",
        "supplier_or_issuer": "Example Energy Ltd",
        "instrument_reference": "SUPPLY-2026-001",
        "factor_source": "Supplier disclosure 2026",
        "factor_value": "0.045",
        "factor_unit": "kg CO2e/kWh",
        "valid_from": "2026-01-01",
        "valid_to": "2026-12-31",
        "geography_code": "GB",
        "quality_criteria_attested": True,
    }


def test_market_based_evidence_accepts_complete_contract() -> None:
    evidence = validate_market_based_evidence(
        complete_evidence(),
        evidence_reference="supplier-contract-2026.pdf",
        activity_date=date(2026, 6, 30),
        geography_code="GB",
    )

    assert evidence["instrument_type"] == "supplier_specific"
    assert evidence["factor_value"] == "0.045"
    assert evidence["quality_criteria_attested"] is True


@pytest.mark.parametrize(
    "field",
    [
        "instrument_type",
        "supplier_or_issuer",
        "instrument_reference",
        "factor_source",
        "factor_value",
        "factor_unit",
        "valid_from",
        "valid_to",
        "geography_code",
        "quality_criteria_attested",
    ],
)
def test_market_based_evidence_rejects_missing_control(field: str) -> None:
    evidence = complete_evidence()
    evidence.pop(field)

    with pytest.raises(ValueError, match="contractual-instrument evidence"):
        validate_market_based_evidence(
            evidence,
            evidence_reference="supplier-contract-2026.pdf",
            activity_date=date(2026, 6, 30),
            geography_code="GB",
        )


def test_market_based_evidence_rejects_expired_instrument() -> None:
    evidence = complete_evidence()
    evidence["valid_to"] = "2026-05-31"

    with pytest.raises(ValueError, match="does not cover"):
        validate_market_based_evidence(
            evidence,
            evidence_reference="supplier-contract-2026.pdf",
            activity_date=date(2026, 6, 30),
            geography_code="GB",
        )


def test_market_based_evidence_rejects_unattested_quality_criteria() -> None:
    evidence = complete_evidence()
    evidence["quality_criteria_attested"] = False

    with pytest.raises(ValueError, match="quality criteria"):
        validate_market_based_evidence(
            evidence,
            evidence_reference="supplier-contract-2026.pdf",
            activity_date=date(2026, 6, 30),
            geography_code="GB",
        )
