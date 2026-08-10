from __future__ import annotations

from datetime import date
from typing import Any

from app.calculations.governed_methods import GovernedCalculationMethod

STATIONARY_DIESEL_PACK_KEY = "uk.scope1.stationary_diesel.litres"
STATIONARY_DIESEL_METHOD_ID = (
    GovernedCalculationMethod.SCOPE1_STATIONARY_DIESEL_LITRES_2026.value
)

GOVERNED_METHOD_TO_PACK_KEY: dict[str, str] = {
    STATIONARY_DIESEL_METHOD_ID: STATIONARY_DIESEL_PACK_KEY,
}


def stationary_diesel_pack_definition() -> dict[str, Any]:
    """Return the reviewed configuration equivalent to the existing 2026 method."""
    return {
        "pack_key": STATIONARY_DIESEL_PACK_KEY,
        "semantic_version": "1.0.0",
        "selection_owner": "platform",
        "owner_tenant_id": None,
        "jurisdiction": "GB",
        "framework": "ghg_protocol",
        "effective_from": date(2026, 1, 1),
        "effective_to": date(2026, 12, 31),
        "supported_scopes": ["scope_1"],
        "scope_3_categories": [],
        "activity_types": ["stationary_combustion"],
        "required_inputs": {
            "activity_value": {"type": "decimal", "unit": "litres"},
            "factor_value": {"type": "decimal", "unit": "kg_co2e/litre"},
        },
        "validation_rules": [
            {"field": "activity_value", "minimum": "0"},
            {"field": "factor_value", "minimum": "0"},
        ],
        "operator_identifier": "activity_times_factor.v1",
        "operator_configuration": {},
        "factor_resolution": {
            "source": "approved_factor_resolution",
            "reporting_year": 2026,
            "level_1": "Fuels",
            "level_2": "Liquid fuels",
            "level_3": "Diesel (average biofuel blend)",
            "greenhouse_gas_component": "total_co2e",
        },
        "lifecycle_boundary": "Direct stationary combustion of diesel fuel.",
        "reporting_disclosures": [
            "Uses the approved UK Government factor selected for the reporting year.",
            (
                "Allocation is applied after the pack operator and remains part of "
                "calculation lineage."
            ),
        ],
        "evidence_references": [
            {
                "title": "UK Government GHG Conversion Factors for Company Reporting",
                "reference": "2026 factor set imported and approved in D-carbN",
            }
        ],
        "change_rationale": (
            "Configuration equivalent of the existing governed stationary-diesel method "
            "for controlled dual-run validation."
        ),
        "compatibility_notes": (
            "Does not replace the existing synchronous calculation path. Enable only "
            "after dual-run evidence is accepted."
        ),
        "golden_examples": [
            {
                "name": "one thousand litres",
                "inputs": {
                    "activity_value": "1000",
                    "factor_value": "2.58354",
                },
                "expected_kg_co2e": "2583.54000",
            }
        ],
        "supersedes_pack_id": None,
    }
