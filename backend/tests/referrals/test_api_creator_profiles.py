from __future__ import annotations


def test_creator_profile_endpoints_create_patch_and_read_by_handle(referral_api) -> None:
    app, client, users = referral_api
    app.state.current_user = users["creator"]

    create_response = client.post(
        "/api/creators/profile",
        json={
            "handle": "creator.one",
            "display_name": "Creator One",
            "tier": "featured",
            "status": "active",
            "default_competition_id": "comp-creator-1",
            "revenue_share_percent": "12.5",
        },
    )
    assert create_response.status_code == 201
    create_payload = create_response.json()
    assert create_payload["handle"] == "creator.one"
    assert create_payload["default_share_code"] == "creatorone"

    me_response = client.get("/api/creators/profile/me")
    assert me_response.status_code == 200
    assert me_response.json()["default_competition_id"] == "comp-creator-1"

    patch_response = client.patch(
        "/api/creators/profile",
        json={
            "display_name": "Creator One Updated",
            "default_competition_id": "comp-creator-2",
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["display_name"] == "Creator One Updated"

    public_response = client.get("/api/creators/creator.one")
    assert public_response.status_code == 200
    assert public_response.json()["user_id"] == users["creator"].id

    competitions_response = client.get("/api/creators/me/competitions")
    assert competitions_response.status_code == 200
    competitions_payload = competitions_response.json()
    assert competitions_payload[0]["competition_id"] == "comp-creator-2"

    summary_response = client.get("/api/creators/me/summary")
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload["profile"]["default_share_code"] == "creatorone"
    assert summary_payload["featured_competitions"][0]["competition_id"] == "comp-creator-2"
