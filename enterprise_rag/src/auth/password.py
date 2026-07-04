"""Password hashing (PBKDF2, stdlib only)."""

from __future__ import annotations

import hashlib
import hmac
import secrets

_PBKDF2_ITERATIONS = 260_000


def hash_password(plain: str, *, salt: bytes | None = None) -> tuple[str, str]:
    raw = (plain or "").encode("utf-8")
    if not raw:
        raise ValueError("password required")
    salt_bytes = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", raw, salt_bytes, _PBKDF2_ITERATIONS)
    return digest.hex(), salt_bytes.hex()


def verify_password(plain: str, password_hash: str, password_salt: str) -> bool:
    if not plain or not password_hash or not password_salt:
        return False
    try:
        salt_bytes = bytes.fromhex(password_salt)
        expected = bytes.fromhex(password_hash)
    except ValueError:
        return False
    got = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt_bytes, _PBKDF2_ITERATIONS)
    return hmac.compare_digest(got, expected)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
