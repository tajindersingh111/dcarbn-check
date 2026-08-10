from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.methodology_pack import MethodologyPackStatus
from app.services.methodology_packs import (
    approve_pack,
    create_pack_draft,
    mark_pack_reviewed,
    run_golden_examples,
    select_approved_pack,
    validate_pack_definition,
)


def _definition(**overrides: object) -> dict[str, object]:
    definition: dict[str, object] = {
        "pack_key": "uk.scope1.stationary_diesel",
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
            "activity_value": {"type": "decimal", "unit": "litre"},
            "factor_value": {"type": "decimal", "unit": "kg_co2e/litre"},
        },
        "validation_rules": [{"field": "activity_value", "minimum": "0"}],
        "operator_identifier": "activity_times_factor.v1",
        "operator_configuration": {},
        "factor_resolution": {"factor_set": "uk-government-2026"},
        "lifecycle_boundary": "Direct fuel combustion.",
        "reporting_disclosures": ["Uses the approved UK factor set."],
        "evidence_references": [{"title": "UK factors", "reference": "2026"}],
        "change_rationale": "Initial equivalent pack for the governed method.",
        "compatibility_notes": None,
        "golden_examples": [
            {
                "name": "one thousand litres",
                "inputs": {"activity_value": "1000", "factor_value": "2.58354"},
                "expected_kg_co2e": "2583.54000",
            }
        ],
        "supersedes_pack_id": None,
    }
    definition.update(overrides)
    return definition


def test_pack_rejects_executable_formula_configuration() -> None:
    with pytest.raises(ValueError, match="not permitted"):
        validate_pack_definition(
            _definition(operator_configuration={"formula": "activity_value * factor"})
        )


def test_pack_golden_examples_use_reviewed_operator() -> None:
    assert run_golden_examples(_definition()) == [Decimal("2583.54000")]


@pytest.mark.asyncio
async def test_only_approved_pack_is_selected_and_historical_version_is_stable(
    db_session: AsyncSession,
) -> None:
    pack = await create_pack_draft(
        db_session,
        definition=_definition(),
        created_by="preparer@example.com",
    )
    assert pack.status == MethodologyPackStatus.DRAFT
    assert (
        await select_approved_pack(
            db_session,
            reporting_date=date(2026, 6, 30),
            jurisdiction="GB",
            framework="ghg_protocol",
            pack_key=pack.pack_key,
        )
        is None
    )

    await mark_pack_reviewed(
        db_session,
        pack,
        reviewed_by="reviewer@example.com",
    )
    await approve_pack(
        db_session,
        pack,
        approved_by="approver@example.com",
    )

    selected = await select_approved_pack(
        db_session,
        reporting_date=date(2026, 6, 30),
        jurisdiction="GB",
        framework="ghg_protocol",
        pack_key=pack.pack_key,
    )
    assert selected is not None
    assert selected.id == pack.id
    assert selected.semantic_version == "1.0.0"
