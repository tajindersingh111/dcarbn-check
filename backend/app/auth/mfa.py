from __future__ import annotations

import base64
import hashlib
import json
import secrets

import pyotp
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(get_settings().mfa_encryption_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except InvalidToken:
        return None


def provisioning_uri(secret: str, email: str) -> str:
    settings = get_settings()
    return pyotp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name=settings.mfa_issuer,
    )


def verify_totp(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def generate_recovery_codes(count: int = 10) -> list[str]:
    return [f"{secrets.token_hex(4)}-{secrets.token_hex(4)}" for _ in range(count)]


def hash_recovery_code(code: str) -> str:
    return hashlib.sha256(code.strip().casefold().encode("utf-8")).hexdigest()


def encode_recovery_hashes(codes: list[str]) -> str:
    return json.dumps([hash_recovery_code(code) for code in codes])


def consume_recovery_code(encoded: str | None, code: str) -> tuple[bool, str]:
    hashes = json.loads(encoded or "[]")
    candidate = hash_recovery_code(code)
    if candidate not in hashes:
        return False, encoded or "[]"
    hashes.remove(candidate)
    return True, json.dumps(hashes)
