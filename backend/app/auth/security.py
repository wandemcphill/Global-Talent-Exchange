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

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
except ImportError:  # pragma: no cover - exercised only in environments without optional crypto deps.
    PasswordHasher = None  # type: ignore[assignment]
    InvalidHashError = VerificationError = VerifyMismatchError = ValueError  # type: ignore[misc,assignment]

PBKDF2_DIGEST = "sha256"
PBKDF2_ITERATIONS = 390000
ARGON2_HASHER = (
    PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
    if PasswordHasher is not None
    else None
)
ACCESS_TOKEN_TTL_SECONDS = 15 * 60
REFRESH_TOKEN_TTL_SECONDS = 30 * 24 * 60 * 60
AUTH_SECRET_ENV = "GTE_AUTH_SECRET"
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


class TokenError(ValueError):
    pass


def _urlsafe_b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _urlsafe_b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def _auth_secret(secret: str | None = None) -> bytes:
    resolved_secret = secret or get_settings().auth_secret
    if not resolved_secret:
        raise RuntimeError(f"{AUTH_SECRET_ENV} must be configured before issuing tokens.")
    return resolved_secret.encode("utf-8")


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Passwords must be at least 8 characters long.")

    return hash_sensitive_secret(password)


def hash_sensitive_secret(value: str) -> str:
    if not value:
        raise ValueError("Secret value is required.")
    if ARGON2_HASHER is not None:
        return ARGON2_HASHER.hash(value)
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(PBKDF2_DIGEST, value.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    return verify_sensitive_secret(password, stored_hash)


def verify_sensitive_secret(value: str, stored_hash: str) -> bool:
    if stored_hash.startswith("$argon2"):
        if ARGON2_HASHER is None:
            return False
        try:
            return bool(ARGON2_HASHER.verify(stored_hash, value))
        except (InvalidHashError, VerificationError, VerifyMismatchError, ValueError):
            return False

    try:
        scheme, iterations_text, salt_hex, digest_hex = stored_hash.split("$", maxsplit=3)
    except ValueError:
        return False

    if scheme != "pbkdf2_sha256":
        return False

    try:
        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_hex)
        expected_digest = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    candidate_digest = hashlib.pbkdf2_hmac(PBKDF2_DIGEST, value.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate_digest, expected_digest)


def _create_token(
    subject: str,
    *,
    token_type: str,
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
        "token_type": token_type,
        "jti": _urlsafe_b64encode(os.urandom(12)),
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


def create_access_token(
    subject: str,
    *,
    expires_delta: timedelta | None = None,
    claims: dict[str, Any] | None = None,
    secret: str | None = None,
) -> str:
    return _create_token(
        subject,
        token_type=ACCESS_TOKEN_TYPE,
        expires_delta=expires_delta or timedelta(seconds=ACCESS_TOKEN_TTL_SECONDS),
        claims=claims,
        secret=secret,
    )


def create_refresh_token(
    subject: str,
    *,
    expires_delta: timedelta | None = None,
    claims: dict[str, Any] | None = None,
    secret: str | None = None,
) -> str:
    return _create_token(
        subject,
        token_type=REFRESH_TOKEN_TYPE,
        expires_delta=expires_delta or timedelta(seconds=REFRESH_TOKEN_TTL_SECONDS),
        claims=claims,
        secret=secret,
    )


def _decode_token(
    token: str,
    *,
    expected_token_type: str,
    expired_message: str,
    malformed_message: str,
    invalid_signature_message: str,
    secret: str | None = None,
) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".", maxsplit=2)
    except ValueError as exc:
        raise TokenError(malformed_message) from exc

    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected_signature = hmac.new(_auth_secret(secret), signing_input, hashlib.sha256).digest()
    signature = _urlsafe_b64decode(encoded_signature)
    if not hmac.compare_digest(signature, expected_signature):
        raise TokenError(invalid_signature_message)

    payload = json.loads(_urlsafe_b64decode(encoded_payload))
    expires_at = int(payload.get("exp", 0))
    if expires_at <= int(time.time()):
        raise TokenError(expired_message)

    token_type = payload.get("token_type") or ACCESS_TOKEN_TYPE
    if token_type != expected_token_type:
        raise TokenError("Unexpected token type.")

    return payload


def decode_access_token(token: str, *, secret: str | None = None) -> dict[str, Any]:
    return _decode_token(
        token,
        expected_token_type=ACCESS_TOKEN_TYPE,
        expired_message="Access token has expired.",
        malformed_message="Malformed access token.",
        invalid_signature_message="Invalid access token signature.",
        secret=secret,
    )


def decode_refresh_token(token: str, *, secret: str | None = None) -> dict[str, Any]:
    return _decode_token(
        token,
        expected_token_type=REFRESH_TOKEN_TYPE,
        expired_message="Refresh token has expired.",
        malformed_message="Malformed refresh token.",
        invalid_signature_message="Invalid refresh token signature.",
        secret=secret,
    )
