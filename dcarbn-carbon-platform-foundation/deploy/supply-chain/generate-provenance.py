from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    subjects = [
        {
            "name": path.name,
            "digest": {"sha256": sha256(path)},
        }
        for path in args.subject
    ]
    payload = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": subjects,
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": "https://github.com/Attestations/GitHubActionsWorkflow@v1",
                "externalParameters": {
                    "repository": os.getenv("GITHUB_REPOSITORY", "local"),
                    "ref": os.getenv("GITHUB_REF", "local"),
                    "workflow": os.getenv("GITHUB_WORKFLOW", "local"),
                },
                "internalParameters": {
                    "commit_sha": os.getenv("GITHUB_SHA", "unknown"),
                },
                "resolvedDependencies": [],
            },
            "runDetails": {
                "builder": {
                    "id": (
                        "https://github.com/actions/runner"
                        if os.getenv("GITHUB_ACTIONS") == "true"
                        else "local-builder"
                    )
                },
                "metadata": {
                    "invocationId": os.getenv(
                        "GITHUB_RUN_ID",
                        f"local-{datetime.now(UTC).timestamp()}",
                    ),
                    "startedOn": os.getenv("BUILD_STARTED_AT"),
                    "finishedOn": datetime.now(UTC).isoformat(),
                },
            },
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
