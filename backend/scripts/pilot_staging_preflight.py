from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

from app.core.config import Settings
from app.services.pilot_preflight import (
    PilotApprovalEvidence,
    evaluate_pilot_preflight,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the controlled pilot staging gate and emit redacted evidence."
        )
    )
    parser.add_argument(
        "--evidence-file",
        required=True,
        type=Path,
        help="Protected approval evidence JSON; never include tenant IDs or secrets.",
    )
    parser.add_argument(
        "--release-sha",
        required=True,
        help="Exact immutable 40-character lowercase release commit SHA.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional redacted JSON report destination. Defaults to stdout.",
    )
    return parser.parse_args()


def _write_report(payload: dict[str, object], output: Path | None) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if output is None:
        print(rendered, end="")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")


def main() -> int:
    args = _arguments()
    release_sha = cast(str, args.release_sha)
    output = cast(Path | None, args.output)

    try:
        raw = json.loads(cast(Path, args.evidence_file).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("approval evidence must be a JSON object")
        evidence = PilotApprovalEvidence.from_mapping(raw)
    except (OSError, ValueError, json.JSONDecodeError):
        _write_report(
            {
                "decision": "NO_GO",
                "release_sha": release_sha,
                "error": (
                    "Approval evidence is unavailable or invalid. "
                    "Review the protected record without exposing it in logs."
                ),
            },
            output,
        )
        return 2

    try:
        settings = Settings()
    except Exception:
        _write_report(
            {
                "decision": "NO_GO",
                "release_sha": release_sha,
                "error": (
                    "Environment settings failed validation. "
                    "Review protected staging configuration."
                ),
            },
            output,
        )
        return 2

    report = evaluate_pilot_preflight(
        settings,
        evidence,
        release_sha=release_sha,
    )
    _write_report(report.as_dict(), output)
    return 0 if report.decision == "READY_FOR_GO_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
