from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.calculations.operators import OPERATORS, execute_operator
from app.models.methodology_pack import MethodologyPack, MethodologyPackStatus

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")
_FORBIDDEN_KEYS = {"code", "expression", "formula", "function", "import", "script"}


def _canonical_content(definition: dict[str, Any]) -> str:
    return json.dumps(definition, sort_keys=True, separators=(",", ":"), default=str)


def content_sha256(definition: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_content(definition).encode("utf-8")).hexdigest()


def _reject_executable_configuration(value: Any, *, path: str = "pack") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).casefold() in _FORBIDDEN_KEYS:
                raise ValueError(f"{path}.{key} is not permitted in a methodology pack.")
            _reject_executable_configuration(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_executable_configuration(item, path=f"{path}[{index}]")


def validate_pack_definition(definition: dict[str, Any]) -> None:
    version = str(definition.get("semantic_version", ""))
    if not _SEMVER.fullmatch(version):
        raise ValueError("semantic_version must use semantic versioning.")
    if definition.get("operator_identifier") not in OPERATORS:
        raise ValueError("operator_identifier is not in the reviewed operator library.")
    effective_from = definition.get("effective_from")
    effective_to = definition.get("effective_to")
    if not isinstance(effective_from, date):
        raise ValueError("effective_from is required.")
    if effective_to is not None and effective_to < effective_from:
        raise ValueError("effective_to must not precede effective_from.")
    scopes = set(definition.get("supported_scopes") or [])
    if not scopes or not scopes.issubset({"scope_1", "scope_2", "scope_3"}):
        raise ValueError("supported_scopes must contain recognised scope identifiers.")
    categories = definition.get("scope_3_categories") or []
    if any(not isinstance(item, int) or item < 1 or item > 15 for item in categories):
        raise ValueError("Scope 3 categories must be integers from 1 to 15.")
    if "scope_3" not in scopes and categories:
        raise ValueError("Scope 3 categories require scope_3 support.")
    if not definition.get("activity_types"):
        raise ValueError("At least one activity type is required.")
    if not definition.get("golden_examples"):
        raise ValueError("At least one golden example is required.")
    if not definition.get("evidence_references"):
        raise ValueError("At least one evidence reference is required.")
    _reject_executable_configuration(definition.get("operator_configuration") or {})


def run_golden_examples(definition: dict[str, Any]) -> list[Decimal]:
    validate_pack_definition(definition)
    results: list[Decimal] = []
    for example in definition["golden_examples"]:
        inputs = {
            key: Decimal(str(value))
            for key, value in (example.get("inputs") or {}).items()
        }
        expected = Decimal(str(example["expected_kg_co2e"]))
        actual = execute_operator(
            definition["operator_identifier"],
            inputs=inputs,
            configuration=definition.get("operator_configuration") or {},
        )
        if actual != expected:
            raise ValueError(
                f"Golden example {example.get('name', '<unnamed>')} failed: "
                f"expected {expected}, received {actual}."
            )
        results.append(actual)
    return results


def _definition_from_pack(pack: MethodologyPack) -> dict[str, Any]:
    return {
        "pack_key": pack.pack_key,
        "semantic_version": pack.semantic_version,
        "selection_owner": pack.selection_owner,
        "owner_tenant_id": pack.owner_tenant_id,
        "jurisdiction": pack.jurisdiction,
        "framework": pack.framework,
        "effective_from": pack.effective_from,
        "effective_to": pack.effective_to,
        "supported_scopes": pack.supported_scopes,
        "scope_3_categories": pack.scope_3_categories,
        "activity_types": pack.activity_types,
        "required_inputs": pack.required_inputs,
        "validation_rules": pack.validation_rules,
        "operator_identifier": pack.operator_identifier,
        "operator_configuration": pack.operator_configuration,
        "factor_resolution": pack.factor_resolution,
        "lifecycle_boundary": pack.lifecycle_boundary,
        "reporting_disclosures": pack.reporting_disclosures,
        "evidence_references": pack.evidence_references,
        "change_rationale": pack.change_rationale,
        "compatibility_notes": pack.compatibility_notes,
        "golden_examples": pack.golden_examples,
        "supersedes_pack_id": pack.supersedes_pack_id,
    }


async def create_pack_draft(
    db: AsyncSession,
    *,
    definition: dict[str, Any],
    created_by: str,
) -> MethodologyPack:
    validate_pack_definition(definition)
    pack = MethodologyPack(**definition, content_sha256="", created_by=created_by)
    pack.content_sha256 = content_sha256(_definition_from_pack(pack))
    db.add(pack)
    await db.commit()
    await db.refresh(pack)
    return pack


async def mark_pack_reviewed(
    db: AsyncSession,
    pack: MethodologyPack,
    *,
    reviewed_by: str,
) -> None:
    if pack.status != MethodologyPackStatus.DRAFT:
        raise ValueError("Only draft packs can be reviewed.")
    if reviewed_by == pack.created_by:
        raise ValueError("The preparer cannot review the same methodology pack.")
    run_golden_examples(_definition_from_pack(pack))
    pack.status = MethodologyPackStatus.REVIEWED
    pack.reviewed_by = reviewed_by
    pack.reviewed_at = datetime.now(UTC)
    await db.commit()


async def approve_pack(
    db: AsyncSession,
    pack: MethodologyPack,
    *,
    approved_by: str,
) -> None:
    if pack.status != MethodologyPackStatus.REVIEWED:
        raise ValueError("Only reviewed packs can be approved.")
    if approved_by in {pack.created_by, pack.reviewed_by}:
        raise ValueError("Approval requires an independent approver.")
    definition = _definition_from_pack(pack)
    run_golden_examples(definition)
    if pack.content_sha256 != content_sha256(definition):
        raise ValueError("Methodology pack content changed after its controlled draft.")
    overlap = await db.scalar(
        select(MethodologyPack.id).where(
            MethodologyPack.id != pack.id,
            MethodologyPack.selection_owner == pack.selection_owner,
            MethodologyPack.pack_key == pack.pack_key,
            MethodologyPack.jurisdiction == pack.jurisdiction,
            MethodologyPack.framework == pack.framework,
            MethodologyPack.status == MethodologyPackStatus.APPROVED,
            MethodologyPack.effective_from <= (pack.effective_to or date.max),
            or_(
                MethodologyPack.effective_to.is_(None),
                MethodologyPack.effective_to >= pack.effective_from,
            ),
        )
    )
    if overlap is not None:
        raise ValueError("An approved methodology pack overlaps this effective period.")
    pack.status = MethodologyPackStatus.APPROVED
    pack.approved_by = approved_by
    pack.approved_at = datetime.now(UTC)
    await db.commit()


async def select_approved_pack(
    db: AsyncSession,
    *,
    reporting_date: date,
    jurisdiction: str,
    framework: str,
    pack_key: str,
    tenant_id: UUID | None = None,
) -> MethodologyPack | None:
    owner_candidates = ["platform"]
    if tenant_id is not None:
        owner_candidates.insert(0, str(tenant_id))
    rows = list(
        (
            await db.scalars(
                select(MethodologyPack)
                .where(
                    MethodologyPack.selection_owner.in_(owner_candidates),
                    MethodologyPack.pack_key == pack_key,
                    MethodologyPack.jurisdiction == jurisdiction,
                    MethodologyPack.framework == framework,
                    MethodologyPack.status == MethodologyPackStatus.APPROVED,
                    MethodologyPack.effective_from <= reporting_date,
                    or_(
                        MethodologyPack.effective_to.is_(None),
                        MethodologyPack.effective_to >= reporting_date,
                    ),
                )
                .order_by(MethodologyPack.effective_from.desc())
            )
        ).all()
    )
    if not rows:
        return None
    if tenant_id is not None:
        for pack in rows:
            if pack.selection_owner == str(tenant_id):
                return pack
    return rows[0]
