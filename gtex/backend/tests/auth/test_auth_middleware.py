from __future__ import annotations

import pytest

from app.auth.middleware import (
    _PROTECTED_PATH_PREFIX_SOURCES,
    AuthEnforcementMiddleware,
)
from app.core.api_contract import build_versioned_path


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
        "/api/admin",
        "/api/v2/admin",
        "/api/admin/access/permissions",
        "/api/v2/admin/access/permissions",
        "/api/v2/admin/talent/some-player/visibility",
        "/api/v2/admin/players/some-player",
        "/api/v2/admin/finance/control-tower",
    ),
)
def test_admin_paths_require_auth_under_both_legacy_and_versioned_prefixes(path: str) -> None:
    """The versioned admin surface must be protected, not just the legacy one.

    `register_versioned_route_aliases` serves every route at `/api/v2/...` too.
    The prefix list previously carried v2 entries for profile, session, and
    wallet but not for admin, so all 321 canonical `/api/v2/admin/...` paths
    bypassed this middleware. `GET /api/v2/admin/access/permissions` has no
    handler-level guard and returned 200 to unauthenticated callers while
    `/api/admin/access/permissions` returned 401.
    """
    assert AuthEnforcementMiddleware._requires_auth(path) is True


def test_every_protected_prefix_also_protects_its_versioned_alias() -> None:
    """Guards the class of bug, not just the admin instance.

    Adding a prefix to `_PROTECTED_PATH_PREFIX_SOURCES` without its `/api/v2`
    alias is exactly how the admin gap appeared. The aliases are derived rather
    than hand-listed, so this asserts the derivation actually covers every
    source entry.
    """
    missing = [
        versioned
        for prefix in _PROTECTED_PATH_PREFIX_SOURCES
        if (versioned := build_versioned_path(prefix)) is not None
        and not AuthEnforcementMiddleware._requires_auth(versioned)
    ]
    assert not missing, f"protected prefixes whose /api/v2 alias is unguarded: {missing}"


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
