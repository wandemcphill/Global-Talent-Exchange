"""Cloudflare Turnstile verification for signup (and optional login)."""

from __future__ import annotations

import os
from typing import Any

import httpx

from app.auth.service import AuthError

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
DEV_BYPASS_TOKENS = frozenset({"dev-bypass", "test-bypass"})


def turnstile_secret() -> str | None:
    raw = (os.environ.get("GTE_TURNSTILE_SECRET_KEY") or os.environ.get("TURNSTILE_SECRET_KEY") or "").strip()
    return raw or None


def turnstile_site_key() -> str | None:
    raw = (os.environ.get("GTE_TURNSTILE_SITE_KEY") or os.environ.get("TURNSTILE_SITE_KEY") or "").strip()
    return raw or None


def turnstile_required() -> bool:
    """Require Turnstile when a secret is configured (production)."""
    return turnstile_secret() is not None


def verify_turnstile_token(
    token: str | None,
    *,
    remote_ip: str | None = None,
) -> None:
    """Raise AuthError when verification fails.

    When no secret is configured (local/dev), accept empty / bypass tokens so
    tests and local signup keep working. When a secret is set, token is required.
    """
    candidate = (token or "").strip()
    secret = turnstile_secret()
    if secret is None:
        return
    if not candidate:
        raise AuthError("Complete the security check to continue.")
    if candidate in DEV_BYPASS_TOKENS and (os.environ.get("GTE_APP_ENV") or "development").lower() in {
        "development",
        "test",
        "local",
    }:
        return

    payload: dict[str, Any] = {"secret": secret, "response": candidate}
    if remote_ip:
        payload["remoteip"] = remote_ip
    try:
        response = httpx.post(TURNSTILE_VERIFY_URL, data=payload, timeout=8.0)
        response.raise_for_status()
        body = response.json()
    except Exception as exc:  # noqa: BLE001 — surface as auth failure
        raise AuthError("Security check failed. Try again.") from exc
    if not bool(body.get("success")):
        raise AuthError("Security check failed. Try again.")


__all__ = [
    "turnstile_required",
    "turnstile_secret",
    "turnstile_site_key",
    "verify_turnstile_token",
]
