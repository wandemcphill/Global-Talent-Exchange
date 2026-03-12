from __future__ import annotations

from fastapi.testclient import TestClient


def test_identity_payload_retrieval_exposes_match_metadata(client: TestClient) -> None:
    response = client.get("/api/clubs/rio-royals/identity")

    assert response.status_code == 200
    payload = response.json()

    assert payload["club_id"] == "rio-royals"
    assert payload["match_identity"]["club_name"] == "Rio Royals"
    assert payload["match_identity"]["short_club_code"] == "RR"
    assert len(payload["match_identity"]["home_kit_colors"]) == 3
    assert len(payload["match_identity"]["away_kit_colors"]) == 3


def test_patch_identity_and_jerseys_round_trip_through_api(client: TestClient) -> None:
    identity_response = client.patch(
        "/api/clubs/oslo-orbit/identity",
        json={
            "club_name": "Oslo Orbit",
            "short_club_code": "ORB",
            "badge_profile": {
                "shape": "shield",
                "icon_family": "bolt",
                "trophy_star_count": 2,
            },
        },
    )
    jerseys_response = client.patch(
        "/api/clubs/oslo-orbit/jerseys",
        json={
            "home": {
                "primary_color": "#101820",
                "secondary_color": "#FEE715",
                "accent_color": "#F8F8F2",
                "pattern_type": "stripes",
            },
            "away": {
                "primary_color": "#F8F8F2",
                "secondary_color": "#101820",
                "accent_color": "#FEE715",
                "pattern_type": "sash",
            },
        },
    )
    badge_response = client.get("/api/clubs/oslo-orbit/badge")
    identity_get_response = client.get("/api/clubs/oslo-orbit/identity")

    assert identity_response.status_code == 200
    assert jerseys_response.status_code == 200
    assert badge_response.status_code == 200
    assert identity_get_response.status_code == 200

    assert identity_response.json()["short_club_code"] == "ORB"
    assert jerseys_response.json()["home"]["pattern_type"] == "stripes"
    assert badge_response.json()["trophy_star_count"] == 2
    assert identity_get_response.json()["badge_profile"]["icon_family"] == "bolt"


def test_api_rejects_home_away_color_clash(client: TestClient) -> None:
    response = client.patch(
        "/api/clubs/tokyo-tide/jerseys",
        json={
            "home": {
                "primary_color": "#FFFFFF",
                "secondary_color": "#0A2540",
                "accent_color": "#00A6FB",
                "pattern_type": "solid",
            },
            "away": {
                "primary_color": "#FFFFFF",
                "secondary_color": "#0A2540",
                "accent_color": "#00A6FB",
                "pattern_type": "solid",
            },
        },
    )

    assert response.status_code == 400
    assert "Home and away jerseys" in response.json()["detail"]
