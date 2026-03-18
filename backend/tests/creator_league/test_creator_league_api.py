from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from backend.app.models.competition_match import CompetitionMatch
from backend.app.models.creator_monetization import CreatorRevenueSettlement


def test_creator_league_admin_config_and_reset_routes(api_client) -> None:
    overview_response = api_client.get("/api/competitions/creator-league")
    assert overview_response.status_code == 200, overview_response.text
    overview_payload = overview_response.json()
    assert overview_payload["division_count"] == 3

    update_response = api_client.patch(
        "/api/competitions/creator-league/config",
        json={
            "match_frequency_days": 5,
            "season_duration_days": 220,
            "division_count": 4,
        },
    )
    assert update_response.status_code == 200, update_response.text
    updated_payload = update_response.json()
    assert updated_payload["division_count"] == 4
    assert updated_payload["match_frequency_days"] == 5
    assert updated_payload["season_duration_days"] == 220
    assert updated_payload["tiers"][-1]["name"] == "Division 4"

    tier_id = updated_payload["tiers"][-1]["id"]
    tier_response = api_client.patch(
        f"/api/competitions/creator-league/tiers/{tier_id}",
        json={
            "club_count": 18,
            "promotion_spots": 2,
        },
    )
    assert tier_response.status_code == 200, tier_response.text
    tier_payload = tier_response.json()
    assert tier_payload["tiers"][-1]["club_count"] == 18
    assert tier_payload["tiers"][-1]["promotion_spots"] == 2

    reset_response = api_client.post("/api/competitions/creator-league/reset")
    assert reset_response.status_code == 200, reset_response.text
    reset_payload = reset_response.json()
    assert reset_payload["division_count"] == 3
    assert [tier["name"] for tier in reset_payload["tiers"]] == ["Division 1", "Division 2", "Division 3"]


def test_creator_league_admin_can_create_and_pause_season(api_client, seeded_clubs) -> None:
    overview_response = api_client.get("/api/competitions/creator-league")
    assert overview_response.status_code == 200, overview_response.text
    tiers = overview_response.json()["tiers"]

    season_response = api_client.post(
        "/api/competitions/creator-league/seasons",
        json={
            "start_date": "2026-04-05",
            "activate": True,
            "created_by_user_id": "admin-user",
            "assignments": [
                {"tier_id": tiers[0]["id"], "club_ids": [club.id for club in seeded_clubs[0:20]]},
                {"tier_id": tiers[1]["id"], "club_ids": [club.id for club in seeded_clubs[20:40]]},
                {"tier_id": tiers[2]["id"], "club_ids": [club.id for club in seeded_clubs[40:60]]},
            ],
        },
    )
    assert season_response.status_code == 201, season_response.text
    season_payload = season_response.json()
    assert season_payload["status"] == "live"
    assert len(season_payload["tiers"]) == 3
    assert season_payload["tiers"][0]["round_count"] == 38
    assert season_payload["tiers"][0]["fixture_count"] == 380

    pause_response = api_client.post(f"/api/competitions/creator-league/seasons/{season_payload['id']}/pause")
    assert pause_response.status_code == 200, pause_response.text
    paused_payload = pause_response.json()
    assert paused_payload["status"] == "paused"

    overview_after_pause = api_client.get("/api/competitions/creator-league")
    assert overview_after_pause.status_code == 200, overview_after_pause.text
    assert overview_after_pause.json()["seasons_paused"] is True


def test_creator_league_financial_report_and_review_routes(api_client, session, seeded_clubs) -> None:
    overview_response = api_client.get("/api/competitions/creator-league")
    assert overview_response.status_code == 200, overview_response.text
    tiers = overview_response.json()["tiers"]

    update_response = api_client.patch(
        "/api/competitions/creator-league/config",
        json={
            "broadcast_purchases_enabled": False,
            "match_gifting_enabled": False,
            "settlement_review_total_revenue_coin": "50.0000",
            "settlement_review_shareholder_distribution_coin": "10.0000",
        },
    )
    assert update_response.status_code == 200, update_response.text
    updated_payload = update_response.json()
    assert updated_payload["broadcast_purchases_enabled"] is False
    assert updated_payload["match_gifting_enabled"] is False
    assert updated_payload["settlement_review_total_revenue_coin"] == "50.0000"

    season_response = api_client.post(
        "/api/competitions/creator-league/seasons",
        json={
            "start_date": "2026-05-03",
            "activate": True,
            "created_by_user_id": "admin-user",
            "assignments": [
                {"tier_id": tiers[0]["id"], "club_ids": [club.id for club in seeded_clubs[0:20]]},
                {"tier_id": tiers[1]["id"], "club_ids": [club.id for club in seeded_clubs[20:40]]},
                {"tier_id": tiers[2]["id"], "club_ids": [club.id for club in seeded_clubs[40:60]]},
            ],
        },
    )
    assert season_response.status_code == 201, season_response.text
    season_payload = season_response.json()
    review_match = session.scalars(
        select(CompetitionMatch).where(CompetitionMatch.competition_id == season_payload["tiers"][0]["competition_id"])
    ).first()
    assert review_match is not None

    settlement = CreatorRevenueSettlement(
        id="settlement-review-1",
        season_id=season_payload["id"],
        competition_id=season_payload["tiers"][0]["competition_id"],
        match_id=review_match.id,
        home_club_id=seeded_clubs[0].id,
        away_club_id=seeded_clubs[1].id,
        total_revenue_coin=Decimal("80.0000"),
        total_creator_share_coin=Decimal("45.0000"),
        total_platform_share_coin=Decimal("35.0000"),
        shareholder_total_distribution_coin=Decimal("12.0000"),
        review_status="review_required",
        review_reason_codes_json=["total_revenue_threshold_exceeded"],
        policy_snapshot_json={"settlement_review_total_revenue_coin": "50.0000"},
        metadata_json={"source": "api-test"},
    )
    session.add(settlement)
    session.commit()

    report_response = api_client.get("/api/competitions/creator-league/financial-report")
    assert report_response.status_code == 200, report_response.text
    report_payload = report_response.json()
    assert report_payload["config"]["broadcast_purchases_enabled"] is False
    assert report_payload["config"]["match_gifting_enabled"] is False
    assert report_payload["current_season_summary"]["review_required_settlement_count"] == 1
    assert report_payload["settlements_requiring_review"][0]["id"] == settlement.id

    settlements_response = api_client.get(
        "/api/competitions/creator-league/financial-settlements",
        params={"review_status": "review_required"},
    )
    assert settlements_response.status_code == 200, settlements_response.text
    settlements_payload = settlements_response.json()
    assert settlements_payload[0]["id"] == settlement.id

    approve_response = api_client.post(
        f"/api/competitions/creator-league/financial-settlements/{settlement.id}/approve",
        json={"review_note": "Reviewed and accepted."},
    )
    assert approve_response.status_code == 200, approve_response.text
    approved_payload = approve_response.json()
    assert approved_payload["review_status"] == "approved"
    assert approved_payload["reviewed_by_user_id"] == "admin-user"
    assert approved_payload["review_note"] == "Reviewed and accepted."
