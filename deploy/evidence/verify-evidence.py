from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def canonical_json(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--public-key", type=Path, required=True)
    args = parser.parse_args()

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    evidence = canonical_json(bundle["evidence"])
    digest = hashlib.sha256(evidence).hexdigest()
    if digest != bundle["sha256"]:
        raise SystemExit("Evidence digest does not match.")

    key = serialization.load_pem_public_key(args.public_key.read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise SystemExit("Evidence key must be an Ed25519 public key.")

    try:
        key.verify(base64.b64decode(bundle["signature"]), evidence)
    except InvalidSignature as exc:
        raise SystemExit("Evidence signature is invalid.") from exc

    print("Evidence signature and digest are valid.")


if __name__ == "__main__":
    main()
