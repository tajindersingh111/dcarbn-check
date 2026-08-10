from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.calculations.governed_methods import GovernedCalculationMethod
from app.methodology_packs.uk_2026 import (
    STATIONARY_DIESEL_PACK_KEY,
    stationary_diesel_pack_definition,
)
from app.models.methodology_pack import MethodologyPackStatus
from app.models.workload import DurableWorkload, WorkloadType
from app.services.methodology_dual_run import (
    compare_activity_factor_method,
    handle_methodology_dual_run,
)
from app.services.methodology_packs import (
    approve_pack,
    create_pack_draft,
    mark_pack_reviewed,
    run_golden_examples,
)
from app.workers.registry import build_default_registry

TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
METHOD_ID = GovernedCalculationMethod.SCOPE1_STATIONARY_DIESEL_LITRES_2026.value


@pytest.mark.asyncio
async def test_stationary_diesel_pack_matches_existing_engine(
    db_session: AsyncSession,
) -> None:
    definition = stationary_diesel_pack_definition()
    assert definition["pack_key"] == STATIONARY_DIESEL_PACK_KEY
    assert run_golden_examples(definition) == [Decimal("2583.54000")]

    pack = await create_pack_draft(
        db_session,
        definition=definition,
        created_by="preparer@example.com",
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
    assert pack.status == MethodologyPackStatus.APPROVED

    comparison = compare_activity_factor_method(
        pack,
        activity_value=Decimal("1000"),
        factor_value=Decimal("2.58354"),
        allocation_percentage=Decimal("80"),
    )
    assert comparison.equivalent is True
    assert comparison.legacy_allocated_kg_co2e == Decimal("2066.832000")
    assert comparison.pack_allocated_kg_co2e == Decimal("2066.832000")
    assert comparison.allocated_delta_kg_co2e == 0


@pytest.mark.asyncio
async def test_registered_worker_returns_lineage_without_writing_results(
    db_session: AsyncSession,
) -> None:
    pack = await create_pack_draft(
        db_session,
        definition=stationary_diesel_pack_definition(),
        created_by="preparer@example.com",
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
    workload = DurableWorkload(
        tenant_id=TENANT_ID,
        workload_type=WorkloadType.CALCULATION,
        idempotency_key="dual-run-test",
        requested_by="tester@example.com",
        payload_json={
            "operation": "methodology_dual_run",
            "governed_method_id": METHOD_ID,
            "methodology_pack_id": str(pack.id),
            "activity_value": "1000",
            "factor_value": "2.58354",
            "allocation_percentage": "80",
            "source_reference": "fictional-activity-001",
        },
        scheduled_at=datetime.now(UTC),
    )

    result = await handle_methodology_dual_run(db_session, workload)

    assert result["methodology_pack_id"] == str(pack.id)
    assert result["methodology_pack_version"] == "1.0.0"
    assert result["operator_identifier"] == "activity_times_factor.v1"
    assert result["comparison"]["equivalent"] is True
    assert result["comparison"]["allocated_delta_kg_co2e"] == "0.000000"


def test_default_registry_exposes_only_reviewed_calculation_handler() -> None:
    registry = build_default_registry()
    assert registry.resolve(WorkloadType.CALCULATION) is handle_methodology_dual_run
    with pytest.raises(LookupError):
        registry.resolve(WorkloadType.DATA_IMPORT)
