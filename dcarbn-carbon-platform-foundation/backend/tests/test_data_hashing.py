from app.integrations.data.hashing import canonical_json_sha256


def test_hash_is_stable_across_key_order() -> None:
    first = canonical_json_sha256({"b": 2, "a": 1})
    second = canonical_json_sha256({"a": 1, "b": 2})

    assert first == second


def test_hash_changes_when_payload_changes() -> None:
    assert canonical_json_sha256({"a": 1}) != canonical_json_sha256({"a": 2})
