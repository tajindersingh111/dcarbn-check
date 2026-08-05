from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum


class Scope2InstrumentType(StrEnum):
    SUPPLIER_SPECIFIC = "supplier_specific"
    ENERGY_ATTRIBUTE_CERTIFICATE = "energy_attribute_certificate"
    DIRECT_CONTRACT = "direct_contract"
    RESIDUAL_MIX = "residual_mix"


_REQUIRED_MARKET_EVIDENCE = (
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
)


def validate_market_based_evidence(
    metadata: dict[str, object],
    *,
    evidence_reference: str | None,
    activity_date: date,
    geography_code: str,
) -> dict[str, object]:
    missing = [
        field
        for field in _REQUIRED_MARKET_EVIDENCE
        if metadata.get(field) in (None, "")
    ]
    if not evidence_reference:
        missing.append("evidence_reference")
    if missing:
        raise ValueError(
            "Market-based Scope 2 requires contractual-instrument evidence: "
            + ", ".join(sorted(missing))
        )

    try:
        instrument_type = Scope2InstrumentType(str(metadata["instrument_type"]))
    except ValueError as exc:
        raise ValueError("Unsupported Scope 2 contractual instrument type") from exc
    try:
        factor_value = Decimal(str(metadata["factor_value"]))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Market-based factor_value must be numeric") from exc
    if factor_value < 0:
        raise ValueError("Market-based factor_value cannot be negative")
    if str(metadata["factor_unit"]) != "kg CO2e/kWh":
        raise ValueError("Market-based factor_unit must be kg CO2e/kWh")
    try:
        valid_from = date.fromisoformat(str(metadata["valid_from"]))
        valid_to = date.fromisoformat(str(metadata["valid_to"]))
    except ValueError as exc:
        raise ValueError("Market-based instrument validity dates are invalid") from exc
    if valid_from > activity_date or valid_to < activity_date:
        raise ValueError("Market-based instrument does not cover the activity date")
    if str(metadata["geography_code"]).upper() != geography_code.upper():
        raise ValueError("Market-based instrument geography must match the activity")
    if metadata["quality_criteria_attested"] is not True:
        raise ValueError("Market-based instrument quality criteria must be attested")

    return {
        "instrument_type": instrument_type.value,
        "supplier_or_issuer": str(metadata["supplier_or_issuer"]),
        "instrument_reference": str(metadata["instrument_reference"]),
        "factor_source": str(metadata["factor_source"]),
        "factor_value": str(factor_value),
        "factor_unit": "kg CO2e/kWh",
        "valid_from": valid_from.isoformat(),
        "valid_to": valid_to.isoformat(),
        "geography_code": geography_code.upper(),
        "evidence_reference": evidence_reference,
        "quality_criteria_attested": True,
    }
