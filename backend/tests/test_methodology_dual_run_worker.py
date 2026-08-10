from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.calculations.governed_methods import GovernedCalculationMethod
from app.methodology_packs.uk_2026 import (
    STATIONARY_DIESEL_PACK_KEY,
    stationary_diesel_pack_definition,
)
from app.models.emission_factor import (
    EmissionFactor,
    EmissionFactorSet,
    FactorSetStatus,
    GreenhouseGasComponent,
)
from app.models.methodology_pack import MethodologyPackStatus
from app.models.workload import WorkloadType
from app.services.methodology_dual_run import (
    compare_activity_factor_method,
    enqueue_methodology_dual_run,
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


async def _approved_pack(db_session: AsyncSession):
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
    return pack


async def _approved_factor(db_session: AsyncSession) -> EmissionFactor:
    factor_set = EmissionFactorSet(
        publisher="DESNZ",
        dataset_name="UK conversion factors",
        dataset_version="2026.1",
        reporting_year=2026,
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        source_filename="factors.xlsx",
        source_sha256="a" * 64,
        status=FactorSetStatus.APPROVED,
        imported_at=datetime.now(UTC),
        imported_by="importer@example.com",
        approved_at=datetime.now(UTC),
        approved_by="approver@example.com",
    )
    db_session.add(factor_set)
    await db_session.flush()
    factor = EmissionFactor(
        factor_set_id=factor_set.id,
        source_factor_id="diesel-stationary-2026",
        scope="scope_1",
        level_1="Fuels",
        activity_unit="litres",
        factor_unit_text="kg CO2e per litre",
        greenhouse_gas_component=GreenhouseGasComponent.TOTAL_CO2E,
        greenhouse_gas_label="kg CO2e",
        factor_value=Decimal("2.58354"),
        factor_denominator_unit="litre",
        reporting_year=2026,
        source_row_number=1,
        raw_source_data={"source": "test"},
        is_active=True,
    )
    db_session.add(factor)
    await db_session.commit()
    await db_session.refresh(factor)
    return factor


@pytest.mark.asyncio
async def test_stationary_diesel_pack_matches_existing_engine(
    db_session: AsyncSession,
) -> None:
    definition = stationary_diesel_pack_definition()
    assert definition["pack_key"] == STATIONARY_DIESEL_PACK_KEY
    assert run_golden_examples(definition) == [Decimal("2583.54000")]

    pack = await _approved_pack(db_session)
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
async def test_queued_dual_run_snapshots_factor_lineage(
    db_session: AsyncSession,
) -> None:
    pack = await _approved_pack(db_session)
    factor = await _approved_factor(db_session)

    workload, created = await enqueue_methodology_dual_run(
        db_session,
        tenant_id=TENANT_ID,
        requested_by="tester@example.com",
        governed_method_id=METHOD_ID,
        methodology_pack_id=pack.id,
        emission_factor_id=factor.id,
        activity_value=Decimal("1000"),
        allocation_percentage=Decimal("80"),
        source_reference="fictional-activity-001",
    )

    assert created is True
    assert workload.payload_json["emission_factor_id"] == str(factor.id)
    assert workload.payload_json["factor_set_version"] == "2026.1"
    assert workload.payload_json["factor_set_source_sha256"] == "a" * 64
    assert "factor_value" in workload.payload_json

    result = await handle_methodology_dual_run(db_session, workload)
    assert result["methodology_pack_id"] == str(pack.id)
    assert result["methodology_pack_version"] == "1.0.0"
    assert result["operator_identifier"] == "activity_times_factor.v1"
    assert result["emission_factor_lineage"]["emission_factor_id"] == str(factor.id)
    assert result["emission_factor_lineage"]["dataset_version"] == "2026.1"
    assert result["emission_factor_lineage"]["source_sha256"] == "a" * 64
    assert result["comparison"]["equivalent"] is True
    assert Decimal(result["comparison"]["allocated_delta_kg_co2e"]) == 0


def test_default_registry_exposes_only_reviewed_calculation_handler() -> None:
    registry = build_default_registry()
    assert registry.resolve(WorkloadType.CALCULATION) is handle_methodology_dual_run
    with pytest.raises(LookupError):
        registry.resolve(WorkloadType.DATA_IMPORT)
