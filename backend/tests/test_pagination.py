from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.api.pagination import (
    CursorPosition,
    InvalidCursorError,
    decode_cursor,
    encode_cursor,
)

TENANT_A = UUID("11111111-1111-1111-1111-111111111111")
TENANT_B = UUID("22222222-2222-2222-2222-222222222222")
ITEM_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
MATERIAL = "unit-test-cursor-material-unit-test"


def test_cursor_round_trip_preserves_deterministic_position() -> None:
    position = CursorPosition(
        created_at=datetime(2026, 8, 11, 10, 30, 15, 123456, tzinfo=UTC),
        id=ITEM_ID,
    )

    cursor = encode_cursor(
        position,
        tenant_id=TENANT_A,
        secret_key=MATERIAL,
    )

    assert decode_cursor(
        cursor,
        tenant_id=TENANT_A,
        secret_key=MATERIAL,
    ) == position
    assert str(TENANT_A) not in cursor


def test_cursor_is_rejected_for_another_tenant() -> None:
    cursor = encode_cursor(
        CursorPosition(
            created_at=datetime(2026, 8, 11, tzinfo=UTC),
            id=ITEM_ID,
        ),
        tenant_id=TENANT_A,
        secret_key=MATERIAL,
    )

    with pytest.raises(InvalidCursorError):
        decode_cursor(
            cursor,
            tenant_id=TENANT_B,
            secret_key=MATERIAL,
        )


@pytest.mark.parametrize(
    "cursor",
    [
        "",
        "not-a-cursor",
        "invalid.invalid",
        "a" * 2049,
    ],
)
def test_malformed_or_oversized_cursor_is_rejected(cursor: str) -> None:
    with pytest.raises(InvalidCursorError):
        decode_cursor(
            cursor,
            tenant_id=TENANT_A,
            secret_key=MATERIAL,
        )


def test_tampered_cursor_is_rejected() -> None:
    cursor = encode_cursor(
        CursorPosition(
            created_at=datetime(2026, 8, 11, tzinfo=UTC),
            id=ITEM_ID,
        ),
        tenant_id=TENANT_A,
        secret_key=MATERIAL,
    )
    payload, signature = cursor.split(".")

    replacement = "A" if payload[-1] != "A" else "B"
    with pytest.raises(InvalidCursorError):
        decode_cursor(
            f"{payload[:-1]}{replacement}.{signature}",
            tenant_id=TENANT_A,
            secret_key=MATERIAL,
        )
