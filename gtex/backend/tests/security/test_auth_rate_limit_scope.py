"""Regression tests: every auth alias must land in the throttled auth bucket.

The auth scope previously matched only the literal paths /auth/login and
/api/auth/login. The production Flutter client calls /api/v2/auth/login, and
registration plus password recovery were never covered at all, so those
credential endpoints fell through to the permissive default bucket.
"""

from __future__ import annotations

import pytest

from app.core.rate_limit import ApiRateLimiter


@pytest.mark.parametrize(
    "path",
    [
        "/auth/login",
        "/api/auth/login",
        "/api/v2/auth/login",
        "/auth/register",
        "/api/auth/register",
        "/api/v2/auth/register",
        "/api/auth/signup/user",
        "/api/v2/auth/signup/trader",
        "/api/v2/auth/signup/creator",
        "/auth/recovery/request",
        "/api/v2/auth/recovery/reset",
        "/api/v2/auth/refresh",
        "/api/v2/auth/change-password",
        "/api/v2/auth/confirm-email",
    ],
)
def test_credential_endpoints_use_the_auth_bucket(path: str) -> None:
    assert ApiRateLimiter._is_auth_path(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "/api/auth/me",
        "/api/v2/auth/me",
        "/api/v2/auth/logout",
        "/api/competitions",
        "/api/v2/authors/login",
        "/authenticate/login",
        "/api/v2/auth/login/extra",
    ],
)
def test_non_credential_paths_stay_out_of_the_auth_bucket(path: str) -> None:
    assert ApiRateLimiter._is_auth_path(path) is False


def test_auth_bucket_is_stricter_than_the_default_bucket() -> None:
    from app.core.config import SettingsSource

    source = SettingsSource.model_validate({})
    assert source.auth_rate_limit_per_minute < source.api_rate_limit_per_minute
