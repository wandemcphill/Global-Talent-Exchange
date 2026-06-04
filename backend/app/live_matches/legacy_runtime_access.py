from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.auth.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)

LEGACY_MATCH_RUNTIME_ACCESS_SCOPE = "legacy_match_runtime"
LEGACY_MATCH_RUNTIME_REFRESH_SCOPE = "legacy_match_runtime_refresh"
LEGACY_MATCH_RUNTIME_ACCESS_TTL_SECONDS = 30 * 60
LEGACY_MATCH_RUNTIME_REFRESH_TTL_SECONDS = 12 * 60 * 60
_LEGACY_MATCH_RUNTIME_SUBJECT_PREFIX = "legacy-match-runtime:"


def _issue_legacy_match_runtime_token(
    *,
    token_kind: str,
    match_id: str,
    spectator_session_id: str,
    viewer_user_id: str,
    expires_in_seconds: int,
) -> tuple[str, int]:
    ttl_seconds = max(60, int(expires_in_seconds))
    claims = {
        "scope": (
            LEGACY_MATCH_RUNTIME_ACCESS_SCOPE
            if token_kind == "access"
            else LEGACY_MATCH_RUNTIME_REFRESH_SCOPE
        ),
        "match_id": match_id,
        "spectator_session_id": spectator_session_id,
        "viewer_user_id": viewer_user_id,
    }
    issue = create_access_token if token_kind == "access" else create_refresh_token
    token = issue(
        subject=f"{_LEGACY_MATCH_RUNTIME_SUBJECT_PREFIX}{spectator_session_id}",
        expires_delta=timedelta(seconds=ttl_seconds),
        claims=claims,
    )
    return token, ttl_seconds


def issue_legacy_match_runtime_access_token(
    *,
    match_id: str,
    spectator_session_id: str,
    viewer_user_id: str,
    expires_in_seconds: int = LEGACY_MATCH_RUNTIME_ACCESS_TTL_SECONDS,
) -> tuple[str, int]:
    return _issue_legacy_match_runtime_token(
        token_kind="access",
        match_id=match_id,
        spectator_session_id=spectator_session_id,
        viewer_user_id=viewer_user_id,
        expires_in_seconds=expires_in_seconds,
    )


def issue_legacy_match_runtime_refresh_token(
    *,
    match_id: str,
    spectator_session_id: str,
    viewer_user_id: str,
    expires_in_seconds: int = LEGACY_MATCH_RUNTIME_REFRESH_TTL_SECONDS,
) -> tuple[str, int]:
    return _issue_legacy_match_runtime_token(
        token_kind="refresh",
        match_id=match_id,
        spectator_session_id=spectator_session_id,
        viewer_user_id=viewer_user_id,
        expires_in_seconds=expires_in_seconds,
    )


def issue_legacy_match_runtime_token_bundle(
    *,
    match_id: str,
    spectator_session_id: str,
    viewer_user_id: str,
    access_expires_in_seconds: int = LEGACY_MATCH_RUNTIME_ACCESS_TTL_SECONDS,
    refresh_expires_in_seconds: int = LEGACY_MATCH_RUNTIME_REFRESH_TTL_SECONDS,
) -> dict[str, int | str]:
    access_token, access_expires_in = issue_legacy_match_runtime_access_token(
        match_id=match_id,
        spectator_session_id=spectator_session_id,
        viewer_user_id=viewer_user_id,
        expires_in_seconds=access_expires_in_seconds,
    )
    refresh_token, refresh_expires_in = issue_legacy_match_runtime_refresh_token(
        match_id=match_id,
        spectator_session_id=spectator_session_id,
        viewer_user_id=viewer_user_id,
        expires_in_seconds=refresh_expires_in_seconds,
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "access_expires_in": access_expires_in,
        "refresh_expires_in": refresh_expires_in,
    }


def _validate_legacy_match_runtime_token_payload(
    payload: dict[str, Any],
    *,
    match_id: str,
    expected_scope: str,
    scope_error_message: str,
) -> dict[str, Any]:
    if str(payload.get("scope") or "").strip().lower() != expected_scope:
        raise TokenError(scope_error_message)

    resolved_match_id = str(payload.get("match_id") or "").strip()
    if not resolved_match_id or resolved_match_id != match_id:
        raise TokenError("Legacy match runtime access token does not match the requested match.")

    spectator_session_id = str(payload.get("spectator_session_id") or "").strip()
    if not spectator_session_id:
        raise TokenError("Legacy match runtime access token is missing a spectator session.")

    viewer_user_id = str(payload.get("viewer_user_id") or "").strip()
    if not viewer_user_id:
        raise TokenError("Legacy match runtime access token is missing a viewer identity.")

    expected_subject = f"{_LEGACY_MATCH_RUNTIME_SUBJECT_PREFIX}{spectator_session_id}"
    if str(payload.get("sub") or "").strip() != expected_subject:
        raise TokenError("Legacy match runtime access token subject is invalid.")

    return {
        "match_id": resolved_match_id,
        "spectator_session_id": spectator_session_id,
        "viewer_user_id": viewer_user_id,
        "payload": payload,
    }


def validate_legacy_match_runtime_access_token(token: str, *, match_id: str) -> dict[str, Any]:
    payload = decode_access_token(token)
    return _validate_legacy_match_runtime_token_payload(
        payload,
        match_id=match_id,
        expected_scope=LEGACY_MATCH_RUNTIME_ACCESS_SCOPE,
        scope_error_message="Legacy match runtime access token scope is invalid.",
    )


def validate_legacy_match_runtime_refresh_token(token: str, *, match_id: str) -> dict[str, Any]:
    payload = decode_refresh_token(token)
    return _validate_legacy_match_runtime_token_payload(
        payload,
        match_id=match_id,
        expected_scope=LEGACY_MATCH_RUNTIME_REFRESH_SCOPE,
        scope_error_message="Legacy match runtime refresh token scope is invalid.",
    )


__all__ = [
    "LEGACY_MATCH_RUNTIME_ACCESS_SCOPE",
    "LEGACY_MATCH_RUNTIME_ACCESS_TTL_SECONDS",
    "LEGACY_MATCH_RUNTIME_REFRESH_SCOPE",
    "LEGACY_MATCH_RUNTIME_REFRESH_TTL_SECONDS",
    "issue_legacy_match_runtime_access_token",
    "issue_legacy_match_runtime_refresh_token",
    "issue_legacy_match_runtime_token_bundle",
    "validate_legacy_match_runtime_access_token",
    "validate_legacy_match_runtime_refresh_token",
]
