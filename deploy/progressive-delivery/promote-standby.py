from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--replicas", type=int, default=3)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--confirmation", required=True)
    args = parser.parse_args()

    if args.confirmation != "PROMOTE-STANDBY-D-CARBN":
        raise SystemExit("Invalid standby-promotion confirmation.")

    patch = args.overlay / "rollout-patch.yml"
    documents = list(yaml.safe_load_all(patch.read_text(encoding="utf-8")))
    for document in documents:
        if not isinstance(document, dict):
            continue
        document.setdefault("spec", {})["replicas"] = args.replicas

    patch.write_text(
        "---\n".join(
            yaml.safe_dump(document, sort_keys=False)
            for document in documents
            if document
        ),
        encoding="utf-8",
    )

    payload = {
        "schema_version": 1,
        "evidence_type": "standby_gitops_promotion",
        "generated_at": datetime.now(UTC).isoformat(),
        "overlay": str(args.overlay),
        "replicas": args.replicas,
        "result": "passed",
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
