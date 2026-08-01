from __future__ import annotations

import argparse
import base64
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def canonical_json(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def load_private_key(path: Path) -> Ed25519PrivateKey:
    value = path.read_bytes()
    key = serialization.load_pem_private_key(value, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("Evidence key must be an Ed25519 private key.")
    return key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.evidence.read_text(encoding="utf-8"))
    unsigned = canonical_json(payload)
    digest = hashlib.sha256(unsigned).hexdigest()
    signature = load_private_key(args.private_key).sign(unsigned)

    bundle = {
        "schema_version": 1,
        "signed_at": datetime.now(UTC).isoformat(),
        "algorithm": "Ed25519",
        "sha256": digest,
        "evidence": payload,
        "signature": base64.b64encode(signature).decode("ascii"),
    }
    output = args.output or args.evidence.with_suffix(".signed.json")
    output.write_text(
        json.dumps(bundle, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
