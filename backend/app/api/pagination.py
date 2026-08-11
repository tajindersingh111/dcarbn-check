from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID


class InvalidCursorError(ValueError):
    """Raised when a cursor is malformed, expired by contract, or tenant-invalid."""


@dataclass(frozen=True)
class CursorPosition:
    created_at: datetime
    id: UUID


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.b64decode(
            value + padding,
            altchars=b"-_",
            validate=True,
        )
    except (binascii.Error, ValueError, TypeError) as exc:
        raise InvalidCursorError("The pagination cursor is invalid.") from exc


def encode_cursor(
    position: CursorPosition,
    *,
    tenant_id: UUID,
    secret_key: str,
) -> str:
    """Create an opaque cursor bound to the authenticated tenant."""
    if position.created_at.tzinfo is None:
        raise ValueError("Cursor timestamps must be timezone-aware.")
    timestamp = (
        position.created_at.astimezone(UTC)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )
    payload = json.dumps(
        {"v": 1, "created_at": timestamp, "id": str(position.id)},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    encoded_payload = _base64url_encode(payload)
    signature = hmac.new(
        secret_key.encode("utf-8"),
        f"{tenant_id}.{encoded_payload}".encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{encoded_payload}.{_base64url_encode(signature)}"


def decode_cursor(
    cursor: str,
    *,
    tenant_id: UUID,
    secret_key: str,
) -> CursorPosition:
    """Validate and decode a cursor without trusting tenant data from the token."""
    if len(cursor) > 2048:
        raise InvalidCursorError("The pagination cursor is invalid.")
    try:
        encoded_payload, encoded_signature = cursor.split(".", maxsplit=1)
    except ValueError as exc:
        raise InvalidCursorError("The pagination cursor is invalid.") from exc

    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        f"{tenant_id}.{encoded_payload}".encode("ascii"),
        hashlib.sha256,
    ).digest()
    supplied_signature = _base64url_decode(encoded_signature)
    if not hmac.compare_digest(expected_signature, supplied_signature):
        raise InvalidCursorError("The pagination cursor is invalid.")

    try:
        payload = json.loads(_base64url_decode(encoded_payload))
        if not isinstance(payload, dict) or payload.get("v") != 1:
            raise ValueError
        created_at_raw = payload["created_at"]
        item_id_raw = payload["id"]
        if not isinstance(created_at_raw, str) or not isinstance(item_id_raw, str):
            raise ValueError
        created_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
        if created_at.tzinfo is None:
            raise ValueError
        item_id = UUID(item_id_raw)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise InvalidCursorError("The pagination cursor is invalid.") from exc

    return CursorPosition(created_at=created_at.astimezone(UTC), id=item_id)
