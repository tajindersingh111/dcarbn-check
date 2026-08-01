from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


def replace_digest(text: str, placeholder: str, digest: str) -> str:
    if not DIGEST_PATTERN.fullmatch(digest):
        raise ValueError(f"Invalid digest: {digest}")
    updated = re.sub(
        rf"(name:\s*{re.escape(placeholder)}\s*\n"
        rf"\s*newName:\s*[^\n]+\s*\n"
        rf"\s*digest:\s*)[^\n]+",
        rf"\g<1>{digest}",
        text,
    )
    if updated == text:
        raise ValueError(f"Image entry was not found: {placeholder}")
    return updated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--backend-digest", required=True)
    parser.add_argument("--frontend-digest", required=True)
    parser.add_argument("--release-version", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()

    kustomization = args.overlay / "kustomization.yml"
    text = kustomization.read_text(encoding="utf-8")
    text = replace_digest(
        text,
        "ghcr.io/example/dcarbn-backend",
        args.backend_digest,
    )
    text = replace_digest(
        text,
        "ghcr.io/example/dcarbn-frontend",
        args.frontend_digest,
    )
    kustomization.write_text(text, encoding="utf-8")

    payload = {
        "schema_version": 1,
        "evidence_type": "gitops_promotion",
        "generated_at": datetime.now(UTC).isoformat(),
        "release_version": args.release_version,
        "commit_sha": args.commit_sha,
        "overlay": str(args.overlay),
        "images": {
            "backend": args.backend_digest,
            "frontend": args.frontend_digest,
        },
        "result": "passed",
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    payload["sha256"] = hashlib.sha256(canonical).hexdigest()
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
