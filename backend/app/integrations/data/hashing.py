from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_sha256(payload: Any) -> str:
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()
