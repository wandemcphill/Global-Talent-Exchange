from __future__ import annotations


def _login(client, *, email: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_bootstrap_contains_seeded_defaults(client) -> None:
    response = client.get("/admin-engine/bootstrap")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert any(item["feature_key"] == "story-feed" for item in payload["active_feature_flags"])
    assert any(item["rule_key"] == "world-cup-exclusive-senior-windows" for item in payload["active_calendar_rules"])
    assert any(item["rule_key"] == "platform-economy-defaults" for item in payload["active_reward_rules"])


def test_admin_can_upsert_feature_flag_and_reward_rule(client) -> None:
    headers = _login(client, email="vidvimedialtd@gmail.com", password="NewPass1234!")

    feature_response = client.post(
        "/admin/admin-engine/feature-flags",
        headers=headers,
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
        headers=headers,
        json={
            "rule_key": "creator-campaign-rules",
            "title": "Creator Campaign Rules",
            "description": "Use tighter economics for sponsored campaign competitions.",
            "trading_fee_bps": 2000,
            "gift_platform_rake_bps": 3000,
            "withdrawal_fee_bps": 1000,
            "minimum_withdrawal_fee_credits": "5.0000",
            "competition_platform_fee_bps": 1200,
            "active": True,
        },
    )
    assert reward_response.status_code == 200, reward_response.text
    assert reward_response.json()["competition_platform_fee_bps"] == 1200


def test_admin_schedule_preview_pauses_league_on_world_cup_date(client) -> None:
    headers = _login(client, email="vidvimedialtd@gmail.com", password="NewPass1234!")
    response = client.post(
        "/admin/admin-engine/schedule-preview",
        headers=headers,
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
