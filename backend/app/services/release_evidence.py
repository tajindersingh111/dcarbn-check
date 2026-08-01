from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from app.core.config import get_settings


def list_evidence(limit: int = 50) -> list[dict[str, Any]]:
    settings = get_settings()
    directory = Path(settings.release_evidence_directory)
    if not directory.is_dir():
        return []

    items: list[dict[str, Any]] = []
    for path in sorted(
        directory.glob("*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    ):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        evidence = payload.get("evidence", payload)
        if not isinstance(evidence, dict):
            continue

        items.append(
            {
                "filename": path.name,
                "signed": "signature" in payload,
                "sha256": payload.get("sha256"),
                "evidence_type": evidence.get("evidence_type", "unknown"),
                "result": evidence.get("result"),
                "decision": evidence.get("decision"),
                "exercise_id": evidence.get("exercise_id"),
                "generated_at": (
                    evidence.get("generated_at")
                    or evidence.get("ended_at")
                    or evidence.get("started_at")
                ),
                "payload": evidence,
            }
        )
        if len(items) >= limit:
            break
    return items


def slo_definitions() -> dict[str, Any]:
    settings = get_settings()
    path = Path(settings.slo_definitions_file)
    if not path.is_file():
        return {"version": 1, "service": "unknown", "objectives": []}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def latest_release_gate() -> dict[str, Any] | None:
    for item in list_evidence(limit=100):
        if item["evidence_type"] == "release_gate":
            return item
    return None


def evidence_summary() -> dict[str, Any]:
    items = list_evidence(limit=100)
    latest_gate = next(
        (
            item
            for item in items
            if item["evidence_type"] == "release_gate"
        ),
        None,
    )
    latest_failover = next(
        (
            item
            for item in items
            if item["evidence_type"]
            == "regional_failover_exercise"
        ),
        None,
    )
    latest_chaos = next(
        (
            item
            for item in items
            if item["evidence_type"] == "chaos_exercise"
        ),
        None,
    )
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
        "latest_release_gate": latest_gate,
        "latest_failover_exercise": latest_failover,
        "latest_chaos_exercise": latest_chaos,
        "evidence_count": len(items),
    }


def list_supply_chain_evidence(limit: int = 50) -> list[dict[str, Any]]:
    settings = get_settings()
    directory = Path(settings.supply_chain_evidence_directory)
    if not directory.is_dir():
        return []

    items: list[dict[str, Any]] = []
    for path in sorted(
        directory.glob("*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    ):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        items.append(
            {
                "filename": path.name,
                "evidence_type": payload.get(
                    "evidence_type",
                    "supply_chain_unknown",
                ),
                "result": payload.get("result"),
                "generated_at": payload.get("generated_at"),
                "commit_sha": payload.get("commit_sha"),
                "components": payload.get("components", []),
                "payload": payload,
            }
        )
        if len(items) >= limit:
            break
    return items


def supply_chain_summary() -> dict[str, Any]:
    items = list_supply_chain_evidence(limit=100)
    latest = next(
        (
            item
            for item in items
            if item["evidence_type"] == "supply_chain_assurance"
        ),
        None,
    )
    components = latest.get("components", []) if latest else []
    return {
        "status": (
            "ok"
            if latest and latest.get("result") == "passed"
            else "unknown"
        ),
        "timestamp": datetime.now(UTC).isoformat(),
        "latest_assurance": latest,
        "component_count": len(components),
        "evidence_count": len(items),
    }



def list_gitops_evidence(limit: int = 50) -> list[dict[str, Any]]:
    settings = get_settings()
    directory = Path(settings.gitops_evidence_directory)
    if not directory.is_dir():
        return []

    items: list[dict[str, Any]] = []
    for path in sorted(
        directory.glob("*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    ):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        items.append(
            {
                "filename": path.name,
                "evidence_type": payload.get(
                    "evidence_type",
                    "gitops_unknown",
                ),
                "result": payload.get("result"),
                "generated_at": payload.get("generated_at"),
                "application": payload.get("application"),
                "health": payload.get("health"),
                "sync": payload.get("sync"),
                "rollout": payload.get("rollout"),
                "release_version": payload.get("release_version"),
                "commit_sha": payload.get("commit_sha"),
                "payload": payload,
            }
        )
        if len(items) >= limit:
            break
    return items


def gitops_summary() -> dict[str, Any]:
    items = list_gitops_evidence(limit=100)
    latest_reconciliation = next(
        (
            item
            for item in items
            if item["evidence_type"] == "gitops_reconciliation"
        ),
        None,
    )
    latest_promotion = next(
        (
            item
            for item in items
            if item["evidence_type"] in {
                "gitops_promotion",
                "standby_gitops_promotion",
            }
        ),
        None,
    )

    status = "unknown"
    if latest_reconciliation:
        status = (
            "ok"
            if latest_reconciliation.get("result") == "passed"
            else "degraded"
        )

    return {
        "status": status,
        "timestamp": datetime.now(UTC).isoformat(),
        "latest_reconciliation": latest_reconciliation,
        "latest_promotion": latest_promotion,
        "evidence_count": len(items),
    }
