from __future__ import annotations

from app.club_identity.reputation.schemas import ContinentalStage, SeasonReputationOutcome, WorldSuperCupStage
from app.club_identity.reputation.season_reputation_rollup import SeasonReputationRollupService


def test_reputation_endpoints_return_profile_history_and_leaderboard(client, session) -> None:
    rollup = SeasonReputationRollupService()
    rollup.apply_season_outcome(
        session,
        SeasonReputationOutcome(
            club_id="alpha",
            season=1,
            league_finish=1,
            qualified_for_continental=True,
            continental_stage=ContinentalStage.WINNER,
            qualified_for_world_super_cup=True,
            world_super_cup_stage=WorldSuperCupStage.SEMI_FINAL,
            top_scorer_awards=1,
            top_assist_awards=1,
            undefeated_league_season=True,
            league_title_streak=2,
            continental_title_streak=2,
            club_age_years=80,
        ),
    )
    rollup.apply_season_outcome(
        session,
        SeasonReputationOutcome(
            club_id="beta",
            season=1,
            league_finish=4,
            qualified_for_continental=True,
            continental_stage=ContinentalStage.ROUND_OF_16,
            club_age_years=25,
        ),
    )
    session.commit()

    reputation_response = client.get("/api/clubs/alpha/reputation")
    history_response = client.get("/api/clubs/alpha/reputation/history")
    prestige_response = client.get("/api/clubs/alpha/prestige")
    leaderboard_response = client.get("/api/leaderboards/prestige", params={"limit": 2})

    assert reputation_response.status_code == 200
    assert history_response.status_code == 200
    assert prestige_response.status_code == 200
    assert leaderboard_response.status_code == 200

    reputation_payload = reputation_response.json()
    history_payload = history_response.json()
    prestige_payload = prestige_response.json()
    leaderboard_payload = leaderboard_response.json()

    assert reputation_payload["club_id"] == "alpha"
    assert reputation_payload["current_score"] > 0
    assert "continental_champion" in reputation_payload["badges_earned"]
    assert history_payload["history"][0]["season"] == 1
    assert prestige_payload["current_prestige_tier"] in {"Established", "Elite", "Legendary", "Dynasty"}
    assert leaderboard_payload["leaderboard"][0]["club_id"] == "alpha"
    assert leaderboard_payload["leaderboard"][1]["club_id"] == "beta"
