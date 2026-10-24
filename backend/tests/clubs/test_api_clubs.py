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
    assert reputation_response.json()["current_prestige_tier"] == "Local"
    assert branding_response.json()["theme"]["name"] == "Spotlight"
    assert len(jerseys_response.json()["jerseys"]) == 1
    assert trophies_response.json()["cabinet"]["total_trophies"] == 0


def test_club_sale_market_route_parity(client, create_club, app_session_factory) -> None:
    from app.models.base import Base
    import app.models  # noqa: F401

    with app_session_factory() as session:
        Base.metadata.create_all(session.bind)
    profile = create_club()
    club_id = profile["id"]

    # Market listing endpoints parity
    resp1 = client.get("/api/clubs/sale-market/listings")
    resp2 = client.get("/api/v2/clubs/sale-market/listings")
    resp3 = client.get("/clubs/marketplace")
    resp4 = client.get("/api/clubs/marketplace")
    resp5 = client.get("/api/v2/clubs/marketplace")

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp3.status_code == 200
    assert resp4.status_code == 200
    assert resp5.status_code == 200

    # Club valuation endpoints parity
    val1 = client.get(f"/api/clubs/{club_id}/valuation")
    val2 = client.get(f"/api/v2/clubs/{club_id}/valuation")
    val3 = client.get(f"/clubs/{club_id}/valuation")

    assert val1.status_code == 200
    assert val2.status_code == 200
    assert val3.status_code == 200

    # Reputation parity
    rep1 = client.get(f"/api/clubs/{club_id}/reputation")
    rep2 = client.get(f"/api/v2/clubs/{club_id}/reputation")
    rep3 = client.get(f"/clubs/{club_id}/reputation")

    assert rep1.status_code == 200
    assert rep2.status_code == 200
    assert rep3.status_code == 200
