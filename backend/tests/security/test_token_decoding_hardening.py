"""Regression tests: a malformed bearer token is a 401, never a 500.

_decode_token used to let binascii/JSON errors escape as-is. Because the auth
dependency only catches TokenError, any unauthenticated caller could turn a junk
Authorization header into a server error.
"""

from __future__ import annotations

import pytest

from app.auth.security import TokenError, create_access_token, decode_access_token

_SECRET = "phase-b-hardening-test-secret-value-0123456789"


@pytest.mark.parametrize(
    "token",
    [
        "a.b.x",
        "a.b.!!!",
        "....",
        "a.b.",
        "$.$.$",
        "eyJ.eyJ.@@@@",
    ],
)
def test_malformed_tokens_raise_token_error(token: str) -> None:
    with pytest.raises(TokenError):
        decode_access_token(token, secret=_SECRET)


def test_token_without_three_segments_raises_token_error() -> None:
    with pytest.raises(TokenError):
        decode_access_token("not-a-token", secret=_SECRET)


def test_valid_token_still_decodes() -> None:
    token = create_access_token("user-1", claims={"sid": "session-1"}, secret=_SECRET)
    payload = decode_access_token(token, secret=_SECRET)
    assert payload["sub"] == "user-1"
    assert payload["sid"] == "session-1"


def test_token_signed_with_another_secret_is_rejected() -> None:
    token = create_access_token("user-1", claims={"sid": "session-1"}, secret="a-different-secret-value-0123456789")
    with pytest.raises(TokenError):
        decode_access_token(token, secret=_SECRET)
