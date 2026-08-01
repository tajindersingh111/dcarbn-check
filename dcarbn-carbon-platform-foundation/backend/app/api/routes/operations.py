from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import require_roles
from app.services.release_evidence import (
    evidence_summary,
    list_evidence,
    list_gitops_evidence,
    latest_release_gate,
    list_supply_chain_evidence,
    slo_definitions,
    supply_chain_summary,
    gitops_summary,
)

router = APIRouter(
    dependencies=[Depends(require_roles("tenant_admin", "auditor"))]
)


@router.get("/operations/slo-definitions")
async def get_slo_definitions() -> dict[str, Any]:
    return slo_definitions()


@router.get("/operations/evidence")
async def get_evidence(
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    items = list_evidence(limit=limit)
    return {"items": items, "total": len(items)}


@router.get("/operations/evidence-summary")
async def get_evidence_summary() -> dict[str, Any]:
    return evidence_summary()


@router.get("/operations/supply-chain-evidence")
async def get_supply_chain_evidence(
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    items = list_supply_chain_evidence(limit=limit)
    return {"items": items, "total": len(items)}


@router.get("/operations/supply-chain-summary")
async def get_supply_chain_summary() -> dict[str, Any]:
    return supply_chain_summary()



@router.get("/operations/gitops-evidence")
async def get_gitops_evidence(
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    items = list_gitops_evidence(limit=limit)
    return {"items": items, "total": len(items)}


@router.get("/operations/gitops-summary")
async def get_gitops_summary() -> dict[str, Any]:
    return gitops_summary()



@router.get("/operations/release-gate/latest")
async def get_latest_release_gate() -> dict[str, Any]:
    item = latest_release_gate()
    if item is None:
        return {"decision": "blocked", "detail": "No release-gate evidence exists."}
    payload = item.get("payload", {})
    return payload if isinstance(payload, dict) else {"decision": "blocked"}
