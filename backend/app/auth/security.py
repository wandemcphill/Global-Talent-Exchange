from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from datetime import timedelta
from typing import Any

from app.core.config import get_settings

PBKDF2_DIGEST = "sha256"
PBKDF2_ITERATIONS = 390000
ACCESS_TOKEN_TTL_SECONDS = 3600
AUTH_SECRET_ENV = "GTE_AUTH_SECRET"
DEFAULT_AUTH_SECRET = "gte-dev-secret-change-me"


class TokenError(ValueError):
    pass


def _urlsafe_b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _urlsafe_b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def _auth_secret(secret: str | None = None) -> bytes:
    return (secret or get_settings().auth_secret or DEFAULT_AUTH_SECRET).encode("utf-8")


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Passwords must be at least 8 characters long.")

    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(PBKDF2_DIGEST, password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        scheme, iterations_text, salt_hex, digest_hex = stored_hash.split("$", maxsplit=3)
    except ValueError:
        return False

    if scheme != "pbkdf2_sha256":
        return False

    iterations = int(iterations_text)
    salt = bytes.fromhex(salt_hex)
    expected_digest = bytes.fromhex(digest_hex)
    candidate_digest = hashlib.pbkdf2_hmac(PBKDF2_DIGEST, password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate_digest, expected_digest)


def create_access_token(
    subject: str,
    *,
    expires_delta: timedelta | None = None,
    claims: dict[str, Any] | None = None,
    secret: str | None = None,
) -> str:
    ttl = expires_delta or timedelta(seconds=ACCESS_TOKEN_TTL_SECONDS)
    issued_at = int(time.time())
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": issued_at,
        "exp": issued_at + int(ttl.total_seconds()),
    }
    if claims:
        payload.update(claims)

    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _urlsafe_b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(_auth_secret(secret), signing_input, hashlib.sha256).digest()
    encoded_signature = _urlsafe_b64encode(signature)
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def decode_access_token(token: str, *, secret: str | None = None) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".", maxsplit=2)
    except ValueError as exc:
        raise TokenError("Malformed access token.") from exc

    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected_signature = hmac.new(_auth_secret(secret), signing_input, hashlib.sha256).digest()
    signature = _urlsafe_b64decode(encoded_signature)
    if not hmac.compare_digest(signature, expected_signature):
        raise TokenError("Invalid access token signature.")

    payload = json.loads(_urlsafe_b64decode(encoded_payload))
    expires_at = int(payload.get("exp", 0))
    if expires_at <= int(time.time()):
        raise TokenError("Access token has expired.")

    return payload
