from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.calculations.engine import calculate_activity_factor_emissions
from app.calculations.operators import execute_operator
from app.methodology_packs.uk_2026 import GOVERNED_METHOD_TO_PACK_KEY
from app.models.emission_factor import (
    EmissionFactor,
    EmissionFactorSet,
    FactorSetStatus,
)
from app.models.methodology_pack import MethodologyPack, MethodologyPackStatus
from app.models.workload import DurableWorkload, WorkloadType
from app.services.workloads import enqueue_workload
from app.workers.errors import NonRetryableWorkloadError

_DUAL_RUN_OPERATION = "methodology_dual_run"


@dataclass(frozen=True, slots=True)
class DualRunComparison:
    legacy_gross_kg_co2e: Decimal
    pack_gross_kg_co2e: Decimal
    legacy_allocated_kg_co2e: Decimal
    pack_allocated_kg_co2e: Decimal
    gross_delta_kg_co2e: Decimal
    allocated_delta_kg_co2e: Decimal
    equivalent: bool

    def serializable(self) -> dict[str, str | bool]:
        values = asdict(self)
        return {
            key: value if isinstance(value, bool) else str(value)
            for key, value in values.items()
        }


def compare_activity_factor_method(
    pack: MethodologyPack,
    *,
    activity_value: Decimal,
    factor_value: Decimal,
    allocation_percentage: Decimal,
) -> DualRunComparison:
    """Compare the existing engine with one reviewed pack using identical inputs."""
    if pack.operator_identifier != "activity_times_factor.v1":
        raise NonRetryableWorkloadError(
            "This dual-run handler supports activity-factor packs only."
        )

    legacy = calculate_activity_factor_emissions(
        factor_activity_value=activity_value,
        factor_value=factor_value,
        allocation_percentage=allocation_percentage,
    )
    pack_gross = execute_operator(
        pack.operator_identifier,
        inputs={
            "activity_value": activity_value,
            "factor_value": factor_value,
        },
        configuration=pack.operator_configuration,
    )
    pack_allocated = pack_gross * legacy.allocation_multiplier
    gross_delta = pack_gross - legacy.gross_kg_co2e
    allocated_delta = pack_allocated - legacy.allocated_kg_co2e
    return DualRunComparison(
        legacy_gross_kg_co2e=legacy.gross_kg_co2e,
        pack_gross_kg_co2e=pack_gross,
        legacy_allocated_kg_co2e=legacy.allocated_kg_co2e,
        pack_allocated_kg_co2e=pack_allocated,
        gross_delta_kg_co2e=gross_delta,
        allocated_delta_kg_co2e=allocated_delta,
        equivalent=gross_delta == 0 and allocated_delta == 0,
    )


def _decimal(payload: dict[str, Any], field: str) -> Decimal:
    try:
        return Decimal(str(payload[field]))
    except (KeyError, InvalidOperation, ValueError) as exc:
        raise NonRetryableWorkloadError(
            f"{field} must be a valid decimal value."
        ) from exc


def _uuid(payload: dict[str, Any], field: str) -> UUID:
    try:
        return UUID(str(payload[field]))
    except (KeyError, ValueError) as exc:
        raise NonRetryableWorkloadError(f"{field} must be a valid UUID.") from exc


async def _load_factor_snapshot(
    db: AsyncSession,
    *,
    emission_factor_id: UUID,
    require_approved: bool,
) -> tuple[EmissionFactor, EmissionFactorSet]:
    conditions: list[Any] = [
        EmissionFactor.id == emission_factor_id,
        EmissionFactor.is_active.is_(True),
        EmissionFactorSet.id == EmissionFactor.factor_set_id,
    ]
    if require_approved:
        conditions.append(EmissionFactorSet.status == FactorSetStatus.APPROVED)
    row = (
        await db.execute(
            select(EmissionFactor, EmissionFactorSet).where(*conditions)
        )
    ).one_or_none()
    if row is None:
        raise NonRetryableWorkloadError(
            "An active emission factor from an approved factor set was not found."
        )
    return row[0], row[1]


async def handle_methodology_dual_run(
    db: AsyncSession,
    workload: DurableWorkload,
) -> dict[str, Any]:
    """Execute an evidence-only comparison; never write customer calculation results."""
    payload = workload.payload_json
    if payload.get("operation") != _DUAL_RUN_OPERATION:
        raise NonRetryableWorkloadError("Unsupported calculation workload operation.")

    raw_method = payload.get("governed_method_id")
    if not isinstance(raw_method, str) or raw_method not in GOVERNED_METHOD_TO_PACK_KEY:
        raise NonRetryableWorkloadError(
            "governed_method_id is not registered for methodology dual-run validation."
        )

    pack_id = _uuid(payload, "methodology_pack_id")
    pack = await db.scalar(
        select(MethodologyPack).where(
            MethodologyPack.id == pack_id,
            MethodologyPack.status == MethodologyPackStatus.APPROVED,
            or_(
                MethodologyPack.selection_owner == "platform",
                MethodologyPack.owner_tenant_id == workload.tenant_id,
            ),
        )
    )
    if pack is None:
        raise NonRetryableWorkloadError(
            "Approved methodology pack was not found for this tenant."
        )
    if pack.pack_key != GOVERNED_METHOD_TO_PACK_KEY[raw_method]:
        raise NonRetryableWorkloadError(
            "Methodology pack does not match the governed calculation method."
        )

    factor, factor_set = await _load_factor_snapshot(
        db,
        emission_factor_id=_uuid(payload, "emission_factor_id"),
        require_approved=False,
    )
    expected = {
        "factor_set_id": str(factor_set.id),
        "factor_set_version": factor_set.dataset_version,
        "factor_set_source_sha256": factor_set.source_sha256,
        "factor_reporting_year": factor.reporting_year,
        "factor_value": str(factor.factor_value),
    }
    if any(str(payload.get(key)) != str(value) for key, value in expected.items()):
        raise NonRetryableWorkloadError(
            "Emission-factor lineage no longer matches the immutable queued snapshot."
        )

    comparison = compare_activity_factor_method(
        pack,
        activity_value=_decimal(payload, "activity_value"),
        factor_value=_decimal(payload, "factor_value"),
        allocation_percentage=_decimal(payload, "allocation_percentage"),
    )
    return {
        "operation": _DUAL_RUN_OPERATION,
        "governed_method_id": raw_method,
        "methodology_pack_id": str(pack.id),
        "methodology_pack_key": pack.pack_key,
        "methodology_pack_version": pack.semantic_version,
        "operator_identifier": pack.operator_identifier,
        "source_reference": str(payload.get("source_reference", ""))[:200],
        "emission_factor_lineage": {
            "emission_factor_id": str(factor.id),
            "factor_set_id": str(factor_set.id),
            "dataset_version": factor_set.dataset_version,
            "source_sha256": factor_set.source_sha256,
            "reporting_year": factor.reporting_year,
            "factor_value": str(factor.factor_value),
        },
        "comparison": comparison.serializable(),
    }


async def enqueue_methodology_dual_run(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    requested_by: str,
    governed_method_id: str,
    methodology_pack_id: UUID,
    emission_factor_id: UUID,
    activity_value: Decimal,
    allocation_percentage: Decimal,
    source_reference: str,
    inventory_id: UUID | None = None,
) -> tuple[DurableWorkload, bool]:
    """Enqueue one idempotent comparison with an immutable factor snapshot."""
    if governed_method_id not in GOVERNED_METHOD_TO_PACK_KEY:
        raise NonRetryableWorkloadError(
            "governed_method_id is not registered for methodology dual-run validation."
        )
    factor, factor_set = await _load_factor_snapshot(
        db,
        emission_factor_id=emission_factor_id,
        require_approved=True,
    )
    snapshot = {
        "emission_factor_id": str(factor.id),
        "factor_set_id": str(factor_set.id),
        "factor_set_version": factor_set.dataset_version,
        "factor_set_source_sha256": factor_set.source_sha256,
        "factor_reporting_year": factor.reporting_year,
        "factor_value": str(factor.factor_value),
    }
    identity = "|".join(
        (
            str(tenant_id),
            governed_method_id,
            str(methodology_pack_id),
            source_reference,
            str(activity_value),
            str(allocation_percentage),
            *[str(snapshot[key]) for key in sorted(snapshot)],
        )
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return await enqueue_workload(
        db,
        tenant_id=tenant_id,
        inventory_id=inventory_id,
        workload_type=WorkloadType.CALCULATION,
        idempotency_key=f"methodology-dual-run:{digest}",
        requested_by=requested_by,
        payload={
            "operation": _DUAL_RUN_OPERATION,
            "governed_method_id": governed_method_id,
            "methodology_pack_id": str(methodology_pack_id),
            "activity_value": str(activity_value),
            "allocation_percentage": str(allocation_percentage),
            "source_reference": source_reference[:200],
            **snapshot,
        },
    )
