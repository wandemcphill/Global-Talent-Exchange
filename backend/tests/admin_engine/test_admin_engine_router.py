from __future__ import annotations

import pytest
from sqlalchemy import select

from backend.tests.support.secrets import TEST_PASSWORD
from app.admin_engine.service import AdminEngineService
from app.auth.service import AuthService
from app.models.notification_record import NotificationRecord
from app.models.user import UserRole


def _login(client, *, email: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_headers(client, app_session_factory) -> dict[str, str]:
    with app_session_factory() as session:
        AuthService().ensure_admin_user(
            session,
            email="admin-engine@example.com",
            password=TEST_PASSWORD,
            username="admin_engine",
            display_name="Admin Engine",
            role=UserRole.SUPER_ADMIN,
        )
        session.commit()
    return _login(client, email="admin-engine@example.com", password=TEST_PASSWORD)


@pytest.fixture()
def admin_engine_defaults(app_session_factory) -> None:
    with app_session_factory() as session:
        service = AdminEngineService(session)
        service.seed_defaults()
        session.commit()


@pytest.fixture()
def user_account(client, app_session_factory) -> tuple[str, dict[str, str]]:
    with app_session_factory() as session:
        user = AuthService().ensure_admin_user(
            session,
            email="launch-user@example.com",
            password=TEST_PASSWORD,
            username="launch_user",
            display_name="Launch User",
            role=UserRole.USER,
        )
        user_id = user.id
        session.commit()
    return user_id, _login(client, email="launch-user@example.com", password=TEST_PASSWORD)


def test_bootstrap_contains_seeded_defaults(client, admin_headers, admin_engine_defaults) -> None:
    response = client.get("/admin-engine/bootstrap", headers=admin_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert any(item["feature_key"] == "story-feed" for item in payload["active_feature_flags"])
    assert any(item["rule_key"] == "world-cup-exclusive-senior-windows" for item in payload["active_calendar_rules"])
    assert any(item["rule_key"] == "platform-economy-defaults" for item in payload["active_reward_rules"])


def test_admin_can_upsert_feature_flag_and_reward_rule(
    client,
    admin_headers,
    admin_engine_defaults,
) -> None:
    feature_response = client.post(
        "/admin/admin-engine/feature-flags",
        headers=admin_headers,
        json={
            "feature_key": "gift-engine",
            "title": "Gift Engine",
            "description": "Enable catalog gifts and combo animations.",
            "enabled": True,
            "audience": "global",
        },
    )
    assert feature_response.status_code == 200, feature_response.text
    assert feature_response.json()["feature_key"] == "gift-engine"

    reward_response = client.post(
        "/admin/admin-engine/reward-rules",
        headers=admin_headers,
        json={
            "rule_key": "creator-campaign-rules",
            "title": "Creator Campaign Rules",
            "description": "Use tighter economics for sponsored campaign competitions.",
            "trading_fee_bps": 2000,
            "gift_platform_rake_bps": 3000,
            "withdrawal_fee_bps": 1000,
            "minimum_withdrawal_fee_credits": "5.0000",
            "competition_platform_fee_bps": 1200,
            "stability_controls": {
                "creator_match_gift": {
                    "max_amount": "80.0000",
                    "daily_sender_limit": "400.0000",
                    "daily_recipient_limit": "900.0000",
                    "daily_pair_limit": "160.0000",
                    "cooldown_seconds": 5,
                    "burst_window_seconds": 60,
                    "burst_max_count": 4,
                    "review_threshold_bps": 8000,
                }
            },
            "active": True,
        },
    )
    assert reward_response.status_code == 200, reward_response.text
    assert reward_response.json()["competition_platform_fee_bps"] == 1200
    assert reward_response.json()["stability_controls"]["creator_match_gift"]["max_amount"] == "80.0000"


def test_admin_schedule_preview_pauses_league_on_world_cup_date(
    client,
    admin_headers,
    admin_engine_defaults,
) -> None:
    response = client.post(
        "/admin/admin-engine/schedule-preview",
        headers=admin_headers,
        json={
            "requests": [
                {
                    "competition_id": "gtex-world-cup-1",
                    "competition_type": "world_super_cup",
                    "requested_dates": ["2026-07-14"],
                    "required_windows": 1,
                    "preferred_windows": [],
                    "priority": 1,
                    "requires_exclusive_windows": True,
                },
                {
                    "competition_id": "gtex-league-1",
                    "competition_type": "league",
                    "requested_dates": ["2026-07-14", "2026-07-21"],
                    "required_windows": 1,
                    "preferred_windows": [],
                    "priority": 5,
                    "requires_exclusive_windows": False,
                },
            ]
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    paused = payload["plan"]["paused_competitions"]
    assert payload["world_cup_exclusive_rule_active"] is True
    assert any(item["competition_id"] == "gtex-league-1" for item in paused)
    assignments = payload["plan"]["assignments"]
    league_dates = [item["match_date"] for item in assignments if item["competition_id"] == "gtex-league-1"]
    assert "2026-07-14" not in league_dates
    assert "2026-07-21" in league_dates


def test_launch_control_is_admin_only(client, user_account, admin_engine_defaults) -> None:
    _, user_headers = user_account

    guest_response = client.get("/api/admin/launch-control")
    assert guest_response.status_code == 401

    user_response = client.get("/api/admin/launch-control", headers=user_headers)
    assert user_response.status_code == 403


def test_admin_can_update_batch34_flag_and_audit_is_recorded(
    client,
    admin_headers,
    admin_engine_defaults,
) -> None:
    response = client.patch(
        "/api/admin/feature-flags/transfer_hub",
        headers=admin_headers,
        json={
            "enabled": True,
            "launch_state": "beta",
            "allowed_roles": ["admin", "super_admin"],
            "reason": "Batch 34 rollout smoke test.",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["feature_key"] == "transfer_hub"
    assert payload["enabled"] is True
    assert payload["launch_state"] == "beta"
    assert payload["allowed_roles"] == ["admin", "super_admin"]

    dashboard_response = client.get("/api/admin/launch-control", headers=admin_headers)
    assert dashboard_response.status_code == 200, dashboard_response.text
    dashboard = dashboard_response.json()
    assert any(item["feature_key"] == "transfer_hub" for item in dashboard["flags"])
    assert any(
        event["feature_key"] == "transfer_hub" and event["action"] == "flag_updated"
        for event in dashboard["recent_audit_events"]
    )
    assert any(route["module_key"] == "launch_control" for route in dashboard["command_routes"])


def test_client_feature_flags_filter_beta_access_and_kill_switch(
    client,
    admin_headers,
    user_account,
    admin_engine_defaults,
    app_session_factory,
) -> None:
    user_id, user_headers = user_account

    response = client.patch(
        "/api/admin/feature-flags/fan_coin",
        headers=admin_headers,
        json={
            "enabled": True,
            "launch_state": "beta",
            "beta_only": True,
            "reason": "Prepare fan coin beta.",
        },
    )
    assert response.status_code == 200, response.text

    public_response = client.get("/api/feature-flags/client")
    assert public_response.status_code == 200, public_response.text
    assert all(item["feature_key"] != "fan_coin" for item in public_response.json())

    normal_response = client.get("/api/feature-flags/client", headers=user_headers)
    assert normal_response.status_code == 200, normal_response.text
    assert all(item["feature_key"] != "fan_coin" for item in normal_response.json())

    grant_response = client.post(
        "/api/admin/beta-access",
        headers=admin_headers,
        json={"feature_key": "fan_coin", "user_id": user_id, "notes": "fixture beta grant"},
    )
    assert grant_response.status_code == 200, grant_response.text

    granted_response = client.get("/api/feature-flags/client", headers=user_headers)
    assert granted_response.status_code == 200, granted_response.text
    granted_flags = {item["feature_key"]: item for item in granted_response.json()}
    assert granted_flags["fan_coin"]["enabled"] is True

    kill_response = client.post(
        "/api/admin/feature-flags/fan_coin/kill-switch",
        headers=admin_headers,
        json={"enabled": True, "reason": "Emergency pause"},
    )
    assert kill_response.status_code == 200, kill_response.text
    assert kill_response.json()["kill_switch_enabled"] is True

    killed_response = client.get("/api/feature-flags/client", headers=user_headers)
    assert killed_response.status_code == 200, killed_response.text
    killed_flags = {item["feature_key"]: item for item in killed_response.json()}
    assert killed_flags["fan_coin"]["enabled"] is False

    revoke_response = client.delete(
        f"/api/admin/beta-access/fan_coin/{user_id}",
        headers=admin_headers,
    )
    assert revoke_response.status_code == 204, revoke_response.text

    with app_session_factory() as session:
        records = list(
            session.scalars(select(NotificationRecord).where(NotificationRecord.resource_id == "fan_coin")).all()
        )
    event_keys = {record.resource_type for record in records}
    assert {
        "feature_flag_changed",
        "beta_access_granted",
        "kill_switch_enabled",
        "beta_access_revoked",
    }.issubset(event_keys)
    assert any(record.user_id == user_id and record.resource_type == "beta_access_granted" for record in records)


def test_launch_control_module_health_tracks_paused_state(
    client,
    admin_headers,
    admin_engine_defaults,
) -> None:
    response = client.patch(
        "/api/admin/feature-flags/broadcast",
        headers=admin_headers,
        json={
            "enabled": True,
            "launch_state": "maintenance",
            "maintenance_message": "Broadcast worker is paused.",
            "reason": "Fixture maintenance window.",
        },
    )
    assert response.status_code == 200, response.text

    health_response = client.get("/api/admin/modules/health", headers=admin_headers)
    assert health_response.status_code == 200, health_response.text
    broadcast = next(item for item in health_response.json() if item["feature_key"] == "broadcast")
    assert broadcast["status"] == "maintenance"
    assert broadcast["launch_state"] == "maintenance"


def test_admin_command_router_covers_combined_batch_modules(
    client,
    admin_headers,
    admin_engine_defaults,
) -> None:
    response = client.get("/api/admin/command-router", headers=admin_headers)

    assert response.status_code == 200, response.text
    module_keys = {item["module_key"] for item in response.json()}
    assert {
        "club_lifecycle",
        "squad_registration",
        "academy_regens",
        "staff_marketplace",
        "sponsorships",
        "federations",
        "fan_predictions",
        "fan_wars",
        "viral_clips",
        "ticketing",
        "player_card_marketplace",
        "global_search",
        "operations_readiness",
    }.issubset(module_keys)
