from __future__ import annotations

import pytest

from app.auth.middleware import AuthEnforcementMiddleware


@pytest.mark.parametrize(
    "path",
    (
        "/api/session/bootstrap",
        "/api/v2/session/bootstrap",
        "/api/profile",
        "/api/profile/security",
        "/api/profile/sessions",
        "/api/v2/profile",
        "/api/v2/profile/security",
        "/api/v2/profile/sessions",
        "/api/wallet/summary",
        "/api/v2/wallet/summary",
        "/wallet/summary",
        "/api/auth/me",
        "/api/v2/auth/me",
    ),
)
def test_strict_live_session_profile_wallet_paths_require_auth(path: str) -> None:
    assert AuthEnforcementMiddleware._requires_auth(path) is True


@pytest.mark.parametrize(
    "path",
    (
        "/api/profiled",
        "/api/sessionless/bootstrap",
        "/api/v2/sessionless/bootstrap",
        "/api/wallet-summary",
        "/api/v2/wallet-summary",
        "/wallet-summary",
    ),
)
def test_auth_prefix_matching_respects_path_boundaries(path: str) -> None:
    assert AuthEnforcementMiddleware._requires_auth(path) is False
