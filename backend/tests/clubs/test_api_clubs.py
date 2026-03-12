from __future__ import annotations

def test_club_profile_and_identity_endpoints_work(client, create_club) -> None:
    profile = create_club()
    club_id = profile["id"]

    profile_response = client.get(f"/api/clubs/{club_id}")
    reputation_response = client.get(f"/api/clubs/{club_id}/reputation")
    branding_response = client.post(
        f"/api/clubs/{club_id}/branding",
        json={
            "theme_name": "Spotlight",
            "assets": [
                {
                    "asset_type": "profile_header",
                    "asset_name": "Spotlight Header",
                    "asset_ref": "header-spotlight",
                }
            ],
        },
    )
    jersey_response = client.post(
        f"/api/clubs/{club_id}/jerseys",
        json={
            "name": "Home Kit",
            "slot_type": "home",
            "base_template_id": "classic",
            "primary_color": "#112233",
            "secondary_color": "#ffffff",
            "trim_color": "#778899",
        },
    )
    jerseys_response = client.get(f"/api/clubs/{club_id}/jerseys")
    dynasty_response = client.get(f"/api/clubs/{club_id}/dynasty")
    trophies_response = client.get(f"/api/clubs/{club_id}/trophies")
    showcase_response = client.get(f"/api/clubs/{club_id}/showcase")

    assert profile_response.status_code == 200
    assert reputation_response.status_code == 200
    assert branding_response.status_code == 201
    assert jersey_response.status_code == 201
    assert jerseys_response.status_code == 200
    assert dynasty_response.status_code == 200
    assert trophies_response.status_code == 200
    assert showcase_response.status_code == 200
    assert profile_response.json()["profile"]["slug"] == "legacy-fc"
    assert reputation_response.json()["reputation"]["tier"] == "grassroots"
    assert branding_response.json()["theme"]["name"] == "Spotlight"
    assert len(jerseys_response.json()["jerseys"]) == 1
    assert trophies_response.json()["cabinet"]["total_trophies"] == 0
