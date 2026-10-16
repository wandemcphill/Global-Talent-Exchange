from __future__ import annotations


def test_creator_copilot_endpoint_returns_analysis_and_alias(referral_api) -> None:
    app, client, users, _session = referral_api
    app.state.current_user = users["creator"]

    create_response = client.post(
        "/api/creators/profile",
        json={
            "handle": "creator.copilot",
            "display_name": "Creator Copilot",
            "tier": "featured",
            "status": "active",
            "default_competition_id": "comp-copilot-1",
            "revenue_share_percent": "12.5",
        },
    )
    assert create_response.status_code == 201
    creator_id = create_response.json()["creator_id"]

    payload = {
        "title": "Matchday flash upload",
        "duration_seconds": 16,
        "event_type": "goal",
        "tags": ["goal", "reaction"],
        "preferred_format": "instant",
        "intro_seconds": 1.1,
        "visual_intensity": 0.72,
        "event_density": 0.66,
        "audience_cluster": "general",
        "has_reaction_overlay": True,
    }
    response = client.post("/api/creators/me/copilot/analyze", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["creator_id"] == creator_id
    assert body["prediction"]["best_format"]
    assert body["strategy_profile"]["profile_key"] == f"creator:{creator_id}:strategy_profile"
    assert body["live_coaching"]["event_name"] == "copilot.alert.triggered"

    alias_response = client.post("/creators/me/copilot/analyze", json=payload)
    assert alias_response.status_code == 200, alias_response.text
    assert alias_response.json()["creator_id"] == creator_id
