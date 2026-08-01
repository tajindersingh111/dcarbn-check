from app.auth.mfa import (
    consume_recovery_code,
    decrypt_secret,
    encode_recovery_hashes,
    encrypt_secret,
    generate_recovery_codes,
    generate_totp_secret,
)


def test_mfa_secret_encryption_round_trip() -> None:
    secret = generate_totp_secret()
    encrypted = encrypt_secret(secret)

    assert encrypted != secret
    assert decrypt_secret(encrypted) == secret


def test_recovery_code_is_single_use() -> None:
    codes = generate_recovery_codes(2)
    encoded = encode_recovery_hashes(codes)

    accepted, updated = consume_recovery_code(encoded, codes[0])
    accepted_again, _ = consume_recovery_code(updated, codes[0])

    assert accepted is True
    assert accepted_again is False
