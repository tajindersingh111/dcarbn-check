from app.auth.security import (
    hash_opaque_token,
    hash_password,
    normalize_email,
    verify_password,
)


def test_password_hash_and_verify() -> None:
    password_hash = hash_password("Correct-Horse-Battery-Staple-2026")
    assert verify_password(password_hash, "Correct-Horse-Battery-Staple-2026")
    assert not verify_password(password_hash, "wrong-password")


def test_email_normalization() -> None:
    assert normalize_email("  User@Example.COM ") == "user@example.com"


def test_opaque_token_hash_is_deterministic() -> None:
    assert hash_opaque_token("token") == hash_opaque_token("token")
    assert hash_opaque_token("token") != hash_opaque_token("different")
