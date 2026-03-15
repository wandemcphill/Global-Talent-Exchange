from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import base64
import hmac
import json
from hashlib import sha256
from typing import Any


class SignatureError(ValueError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


@dataclass(frozen=True, slots=True)
class SignedToken:
    token: str
    expires_at: datetime


@dataclass(slots=True)
class SignedTokenService:
    secret: str
    purpose: str = "default"
    version: int = 1

    def sign(self, payload: dict[str, Any], *, expires_in_seconds: int) -> SignedToken:
        issued_at = _utcnow()
        expires_at = issued_at + timedelta(seconds=max(1, int(expires_in_seconds)))
        body = {
            "v": self.version,
            "purpose": self.purpose,
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
            "payload": payload,
        }
        encoded = _b64url_encode(json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        signature = self._sign(encoded)
        return SignedToken(token=f"{encoded}.{signature}", expires_at=expires_at)

    def verify(self, token: str) -> dict[str, Any]:
        try:
            encoded, signature = token.split(".", 1)
        except ValueError as exc:
            raise SignatureError("Malformed token.") from exc
        expected = self._sign(encoded)
        if not hmac.compare_digest(expected, signature):
            raise SignatureError("Invalid token signature.")
        try:
            data = json.loads(_b64url_decode(encoded))
        except Exception as exc:
            raise SignatureError("Invalid token payload.") from exc
        if data.get("purpose") != self.purpose:
            raise SignatureError("Token purpose mismatch.")
        exp = int(data.get("exp") or 0)
        if exp < int(_utcnow().timestamp()):
            raise SignatureError("Token has expired.")
        payload = data.get("payload")
        if not isinstance(payload, dict):
            raise SignatureError("Token payload is invalid.")
        return payload

    def _sign(self, encoded: str) -> str:
        digest = hmac.new(self.secret.encode("utf-8"), encoded.encode("ascii"), sha256).digest()
        return _b64url_encode(digest)


__all__ = ["SignatureError", "SignedToken", "SignedTokenService"]
