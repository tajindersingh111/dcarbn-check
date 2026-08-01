from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def request_json(url: str, timeout: int = 20) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object from {url}.")
    return payload


def prometheus_value(base_url: str, expression: str) -> float:
    query = urllib.parse.urlencode({"query": expression})
    payload = request_json(f"{base_url.rstrip('/')}/api/v1/query?{query}")
    if payload.get("status") != "success":
        raise ValueError("Prometheus query failed.")
    result = payload.get("data", {}).get("result", [])
    if len(result) != 1:
        raise ValueError(
            f"Prometheus query returned {len(result)} series; expected one."
        )
    return float(result[0]["value"][1])


def canonical_json(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def verify_signed_evidence(
    path: Path,
    public_key_path: Path,
) -> dict[str, Any]:
    bundle = json.loads(path.read_text(encoding="utf-8"))
    evidence = bundle["evidence"]
    canonical = canonical_json(evidence)
    digest = hashlib.sha256(canonical).hexdigest()
    if digest != bundle.get("sha256"):
        raise ValueError("Evidence digest does not match.")

    key = serialization.load_pem_public_key(public_key_path.read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("Evidence public key must be Ed25519.")

    try:
        key.verify(base64.b64decode(bundle["signature"]), canonical)
    except InvalidSignature as exc:
        raise ValueError("Evidence signature is invalid.") from exc

    return evidence


def nested_value(payload: dict[str, Any], dotted_path: str) -> Any:
    value: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(dotted_path)
        value = value[part]
    return value


def check_objective(
    objective: dict[str, Any],
    prometheus_url: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    if "query" in objective:
        observed = prometheus_value(prometheus_url, str(objective["query"]))
        source = "prometheus"
    else:
        observed = float(
            nested_value(evidence, str(objective["evidence_field"]))
        )
        source = "exercise_evidence"

    if "target" in objective:
        target = float(objective["target"])
        passed = observed >= target
        comparator = ">="
    else:
        target = float(objective["target_max"])
        passed = observed <= target
        comparator = "<="

    return {
        "id": objective["id"],
        "name": objective["name"],
        "source": source,
        "observed": observed,
        "target": target,
        "comparator": comparator,
        "passed": passed,
    }



def validate_supply_chain_evidence(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [
            {
                "name": "supply_chain_evidence",
                "passed": False,
                "detail": str(exc),
            }
        ]

    components = payload.get("components", [])
    checks: list[dict[str, Any]] = [
        {
            "name": "supply_chain_evidence",
            "passed": payload.get("result") == "passed" and bool(components),
            "generated_at": payload.get("generated_at"),
            "commit_sha": payload.get("commit_sha"),
        }
    ]

    required_commit = os.getenv("RELEASE_COMMIT_SHA", "")
    if required_commit:
        checks.append(
            {
                "name": "supply_chain_commit_match",
                "passed": payload.get("commit_sha") == required_commit,
                "observed": payload.get("commit_sha"),
                "expected": required_commit,
            }
        )

    source_security = payload.get("source_security", {})
    checks.extend(
        [
            {
                "name": "secret_scan",
                "passed": source_security.get("secret_scan") == "passed",
            },
            {
                "name": "python_dependency_audit",
                "passed": (
                    source_security.get("python_dependency_audit")
                    == "passed"
                ),
            },
            {
                "name": "node_dependency_audit",
                "passed": (
                    source_security.get("node_dependency_audit")
                    == "passed"
                ),
            },
        ]
    )

    for component in components:
        component_name = str(component.get("component", "unknown"))
        digest = str(component.get("digest") or "")
        checks.extend(
            [
                {
                    "name": f"{component_name}_digest",
                    "passed": digest.startswith("sha256:"),
                    "observed": digest or None,
                },
                {
                    "name": f"{component_name}_sbom",
                    "passed": bool(
                        component.get("sbom", {}).get("spdx")
                        and component.get("sbom", {}).get("cyclonedx")
                    ),
                },
                {
                    "name": f"{component_name}_signature",
                    "passed": component.get("signature") is True,
                },
                {
                    "name": f"{component_name}_provenance",
                    "passed": component.get("provenance") is True,
                },
                {
                    "name": f"{component_name}_vulnerability_policy",
                    "passed": (
                        component.get("vulnerability_policy") == "passed"
                    ),
                },
                {
                    "name": f"{component_name}_license_policy",
                    "passed": component.get("license_policy") == "passed",
                },
            ]
        )
    return checks

def validate_image_references() -> list[dict[str, Any]]:
    names = [
        item.strip()
        for item in os.getenv("RELEASE_IMAGE_REFERENCES", "").split(",")
        if item.strip()
    ]
    results: list[dict[str, Any]] = []
    for reference in names:
        immutable = "@sha256:" in reference
        results.append(
            {
                "name": "immutable_image_reference",
                "reference": reference,
                "passed": immutable,
            }
        )
    if not names:
        results.append(
            {
                "name": "immutable_image_reference",
                "reference": None,
                "passed": False,
                "detail": "RELEASE_IMAGE_REFERENCES is empty.",
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--slo-definitions",
        type=Path,
        default=Path("/config/slo-definitions.yml"),
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=Path("/evidence/latest.signed.json"),
    )
    parser.add_argument(
        "--public-key",
        type=Path,
        default=Path("/run/secrets/evidence_public_key"),
    )
    parser.add_argument(
        "--supply-chain-evidence",
        type=Path,
        default=Path("/supply-chain/supply-chain-release.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/output/release-gate-evidence.json"),
    )
    args = parser.parse_args()

    prometheus_url = os.environ["PROMETHEUS_URL"]
    readiness_url = os.environ["READINESS_URL"]
    recovery_url = os.environ["RECOVERY_READINESS_URL"]
    max_evidence_age_days = int(
        os.getenv("MAX_FAILOVER_EVIDENCE_AGE_DAYS", "90")
    )

    checks: list[dict[str, Any]] = []

    for name, url in (
        ("application_readiness", readiness_url),
        ("recovery_readiness", recovery_url),
    ):
        try:
            payload = request_json(url)
            passed = payload.get("status") == "ok"
            checks.append(
                {
                    "name": name,
                    "passed": passed,
                    "observed": payload.get("status"),
                }
            )
        except (OSError, ValueError, urllib.error.URLError) as exc:
            checks.append(
                {
                    "name": name,
                    "passed": False,
                    "detail": type(exc).__name__,
                }
            )

    try:
        evidence = verify_signed_evidence(args.evidence, args.public_key)
        ended_at = datetime.fromisoformat(
            str(evidence["ended_at"]).replace("Z", "+00:00")
        ).astimezone(UTC)
        evidence_fresh = ended_at >= (
            datetime.now(UTC) - timedelta(days=max_evidence_age_days)
        )
        checks.append(
            {
                "name": "signed_failover_evidence",
                "passed": evidence_fresh
                and evidence.get("result") == "passed",
                "exercise_id": evidence.get("exercise_id"),
                "ended_at": ended_at.isoformat(),
                "max_age_days": max_evidence_age_days,
            }
        )
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        evidence = {}
        checks.append(
            {
                "name": "signed_failover_evidence",
                "passed": False,
                "detail": str(exc),
            }
        )

    definitions = yaml.safe_load(
        args.slo_definitions.read_text(encoding="utf-8")
    )
    objective_results: list[dict[str, Any]] = []
    for objective in definitions["objectives"]:
        if not objective.get("release_gate"):
            continue
        try:
            objective_results.append(
                check_objective(objective, prometheus_url, evidence)
            )
        except (
            KeyError,
            OSError,
            ValueError,
            urllib.error.URLError,
        ) as exc:
            objective_results.append(
                {
                    "id": objective["id"],
                    "name": objective["name"],
                    "passed": False,
                    "detail": str(exc),
                }
            )

    checks.extend(validate_image_references())
    checks.extend(
        validate_supply_chain_evidence(args.supply_chain_evidence)
    )

    passed = all(item["passed"] for item in checks) and all(
        item["passed"] for item in objective_results
    )
    decision = "approved" if passed else "blocked"

    output = {
        "schema_version": 1,
        "evidence_type": "release_gate",
        "generated_at": datetime.now(UTC).isoformat(),
        "release_version": os.getenv("RELEASE_VERSION", "unknown"),
        "commit_sha": os.getenv("RELEASE_COMMIT_SHA", "unknown"),
        "decision": decision,
        "checks": checks,
        "slo_objectives": objective_results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
