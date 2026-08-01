from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import yaml


def normalize_license(value: str) -> str:
    return value.strip().upper().replace(" ", "-")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sbom", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = yaml.safe_load(args.policy.read_text(encoding="utf-8"))
    denied = {
        normalize_license(item)
        for item in policy["licenses"]["denied"]
    }

    sbom = json.loads(args.sbom.read_text(encoding="utf-8"))
    violations: list[dict[str, str]] = []

    for package in sbom.get("packages", []):
        declared = str(package.get("licenseDeclared") or "")
        concluded = str(package.get("licenseConcluded") or "")
        values = {
            normalize_license(value)
            for value in (declared, concluded)
            if value and value not in {"NOASSERTION", "NONE"}
        }
        matches = sorted(values & denied)
        if matches:
            violations.append(
                {
                    "package": str(package.get("name", "unknown")),
                    "version": str(package.get("versionInfo", "unknown")),
                    "licenses": ", ".join(matches),
                }
            )

    result = {
        "schema_version": 1,
        "evidence_type": "license_policy",
        "generated_at": datetime.now(UTC).isoformat(),
        "result": "passed" if not violations else "failed",
        "violations": violations,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    raise SystemExit(0 if not violations else 1)


if __name__ == "__main__":
    main()
