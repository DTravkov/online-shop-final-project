import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_ALGORITHM, JWT_SECRET

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


def _encode(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _decode(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"), validate=True)


def hash_password(password: str) -> str:
    """Return a salted scrypt hash: scrypt$n$r$p$salt$digest."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return "$".join(["scrypt", str(_SCRYPT_N), str(_SCRYPT_R), str(_SCRYPT_P), _encode(salt), _encode(digest)])


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = password_hash.split("$")
        if algorithm != "scrypt":
            return False
        expected_digest = _decode(expected)
        digest = hashlib.scrypt(
            password.encode(),
            salt=_decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected_digest),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected_digest)


# Verified against when the email is unknown, so login takes the same time either way.
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(16))


def create_access_token(claims: dict[str, Any]) -> str:
    now = datetime.now(UTC)
    payload = {**claims, "iat": now, "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Raise jwt.PyJWTError when the token is malformed, tampered with, or expired."""
    return jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["exp", "sub"]},
    )
