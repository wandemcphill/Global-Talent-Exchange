from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools.provision_gtex_live_match import (
    AUTH_LOGIN_PATHS,
    AUTH_REGISTER_PATHS,
    ensure_user_access_token,
    write_bootstrap_file,
    write_unity_config,
)


def test_auth_register_paths_uses_current_signup_endpoints() -> None:
    assert "/api/auth/register" not in AUTH_REGISTER_PATHS
    assert "/api/v2/auth/signup/user" in AUTH_REGISTER_PATHS
    assert "/api/auth/signup/user" in AUTH_REGISTER_PATHS
    assert "/auth/signup/user" in AUTH_REGISTER_PATHS


def test_ensure_user_access_token_registers_via_user_signup_contract(client) -> None:

    token = ensure_user_access_token(
        client,
        existing_access_token="",
        email="unity-live-provision-test@gtex.local",
        password="UnityLivePass123!",  # pragma: allowlist secret
        full_name="GTEX Unity Live Test",
        phone_number="08000000000",
        region_code="NG",
        username="unitylivetest",
        allow_register=True,
    )

    assert isinstance(token, str) and len(token) > 20


def test_ensure_user_access_token_login_and_fallback(client) -> None:

    email = "unity-live-repeat@gtex.local"
    password = "UnityLivePass123!"  # pragma: allowlist secret

    token1 = ensure_user_access_token(
        client,
        existing_access_token="",
        email=email,
        password=password,
        full_name="GTEX Unity Live Repeat",
        phone_number="08000000000",
        region_code="NG",
        username="unityliverepeat",
        allow_register=True,
    )
    assert token1

    token2 = ensure_user_access_token(
        client,
        existing_access_token="",
        email=email,
        password=password,
        full_name="GTEX Unity Live Repeat",
        phone_number="08000000000",
        region_code="NG",
        username="unityliverepeat",
        allow_register=False,
    )
    assert token2


def test_ensure_user_access_token_fails_closed_when_register_disallowed(client) -> None:

    with pytest.raises(RuntimeError, match="automatic registration is disabled"):
        ensure_user_access_token(
            client,
            existing_access_token="",
            email="nonexistent-user@gtex.local",
            password="SomePassword123!",  # pragma: allowlist secret
            full_name="Nonexistent",
            phone_number="08000000000",
            region_code="NG",
            username="nonexistent",
            allow_register=False,
        )


def test_unity_artifact_writing(tmp_path: Path) -> None:
    config_file = tmp_path / "match-config.json"
    bootstrap_file = tmp_path / "gtex-live-bootstrap.json"

    config_file.write_text(
        json.dumps(
            {
                "enabled": False,
                "autoStartOnBoot": False,
                "runtimeMode": "offline",
                "environment": "offline",
                "matchId": "old",
                "liveAccessToken": "old_acc",
                "liveRefreshToken": "old_ref",
            }
        ),
        encoding="utf-8",
    )

    written_config = write_unity_config(config_file, dry_run=False)
    assert written_config["enabled"] is True
    assert written_config["autoStartOnBoot"] is True
    assert written_config["runtimeMode"] == "live"
    assert written_config["matchId"] == ""

    written_bootstrap = write_bootstrap_file(
        [bootstrap_file],
        profile="local",
        base_url="http://127.0.0.1:8000",
        match_id="test-match-123",
        unity_access_token="access-123",
        unity_refresh_token="refresh-123",
        persist_access_token=True,
        bootstrap_ttl_seconds=900,
        consume_on_load=False,
        dry_run=False,
    )

    assert written_bootstrap["matchId"] == "test-match-123"
    assert written_bootstrap["liveAccessToken"] == "access-123"
    assert written_bootstrap["liveRefreshToken"] == "refresh-123"
    assert bootstrap_file.exists()
