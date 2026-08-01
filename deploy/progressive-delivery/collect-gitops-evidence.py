from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def command_json(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    if not isinstance(payload, dict):
        raise ValueError("Expected JSON object.")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--application", required=True)
    parser.add_argument("--rollout", required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    application = command_json(
        ["argocd", "app", "get", args.application, "-o", "json"]
    )
    rollout = command_json(
        [
            "kubectl",
            "argo",
            "rollouts",
            "get",
            "rollout",
            args.rollout,
            "-n",
            args.namespace,
            "-o",
            "json",
        ]
    )

    health = application.get("status", {}).get("health", {}).get("status")
    sync = application.get("status", {}).get("sync", {}).get("status")
    rollout_phase = rollout.get("status", {}).get("phase")
    passed = (
        health == "Healthy"
        and sync == "Synced"
        and rollout_phase == "Healthy"
    )

    payload = {
        "schema_version": 1,
        "evidence_type": "gitops_reconciliation",
        "generated_at": datetime.now(UTC).isoformat(),
        "application": args.application,
        "namespace": args.namespace,
        "health": health,
        "sync": sync,
        "rollout": {
            "name": args.rollout,
            "phase": rollout_phase,
            "stable_revision": rollout.get("status", {}).get(
                "stableRS"
            ),
            "current_revision": rollout.get("status", {}).get(
                "currentPodHash"
            ),
        },
        "result": "passed" if passed else "failed",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
