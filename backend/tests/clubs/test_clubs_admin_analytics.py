from __future__ import annotations

from app.common.enums.trophy_type import TrophyType
from app.services.club_trophy_service import ClubTrophyService


def test_admin_summary_analytics_and_moderation_endpoints_work(client, session, create_club) -> None:
    profile = create_club(slug="admin-fc")
    club_id = profile["id"]

    client.post(
        f"/api/clubs/{club_id}/branding",
        json={
            "theme_name": "Review Queue",
            "assets": [
                {
                    "asset_type": "banner",
                    "asset_name": "Review Banner",
                    "asset_ref": "review-banner",
                    "custom_text": "Pending Review",
                }
            ],
        },
    )
    client.post(
        f"/api/clubs/{club_id}/jerseys",
        json={
            "name": "Home Kit",
            "slot_type": "home",
            "base_template_id": "classic",
            "primary_color": "#112233",
            "secondary_color": "#ffffff",
            "trim_color": "#778899",
            "motto_text": "Pending Review",
        },
    )
    catalog_items = client.get("/api/clubs/catalog").json()["items"]
    client.post(
        "/api/clubs/catalog/purchase",
        json={"club_id": club_id, "catalog_item_id": catalog_items[0]["id"]},
    )
    ClubTrophyService(session).award_trophy(
        club_id=club_id,
        trophy_type=TrophyType.LEAGUE_TITLE,
        trophy_name="League Crown",
        competition_source="senior_league",
        season_label="Season 1",
        featured=True,
    )

    summary_response = client.get("/api/admin/clubs/summary")
    analytics_response = client.get("/api/admin/clubs/analytics")
    detail_response = client.get(f"/api/admin/clubs/{club_id}")

    assert summary_response.status_code == 200
    assert analytics_response.status_code == 200
    assert detail_response.status_code == 200
    assert summary_response.json()["pending_branding_reviews"] >= 2
    assert analytics_response.json()["cosmetic_revenue"]["purchase_count"] >= 1
    detail = detail_response.json()
    assert detail["profile"]["id"] == club_id
    assert detail["trophies"][0]["trophy_name"] == "League Crown"

    asset_id = next(asset["id"] for asset in detail["branding_assets"] if asset["moderation_status"] == "pending_review")
    jersey_id = detail["jerseys"][0]["id"]
    moderate_response = client.post(
        f"/api/admin/clubs/{club_id}/moderate-branding",
        json={
            "asset_ids": [asset_id],
            "jersey_ids": [jersey_id],
            "moderation_status": "approved",
            "reason": "cleaned",
        },
    )
    post_summary_response = client.get("/api/admin/clubs/summary")

    assert moderate_response.status_code == 200
    assert moderate_response.json()["updated_assets"][0]["moderation_status"] == "approved"
    assert moderate_response.json()["updated_jerseys"][0]["moderation_status"] == "approved"
    assert post_summary_response.json()["pending_branding_reviews"] == 0
