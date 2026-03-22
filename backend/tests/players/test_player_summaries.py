from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_session
from app.ingestion.models import Player
from app.players.read_models import PlayerSummaryReadModel
from app.players.router import router as players_router
from tests.regen_universe_support import build_regen_universe_session, seed_two_season_universe


def _seed_summary(
    *,
    player_id: str,
    player_name: str,
    current_value_credits: float,
    movement_pct: float,
    summary_json: dict | None = None,
) -> PlayerSummaryReadModel:
    return PlayerSummaryReadModel(
        player_id=player_id,
        player_name=player_name,
        current_club_name="Prestige FC",
        current_competition_name="Prestige Premier League",
        last_snapshot_at=datetime(2026, 3, 22, 12, 0, tzinfo=timezone.utc),
        current_value_credits=current_value_credits,
        previous_value_credits=max(current_value_credits - 10.0, 0.0),
        movement_pct=movement_pct,
        average_rating=7.8,
        market_interest_score=85,
        summary_json=summary_json or {"position": "forward"},
    )


def test_player_summaries_expose_regen_universe_only_for_regen_players() -> None:
    session = build_regen_universe_session()
    try:
        bundle = seed_two_season_universe(session)
        service = bundle["service"]
        first_season = service.list_seasons(active_only=True)[0]
        service.close_season(first_season.id, start_next_season=False)

        regen_player = bundle["players"]["veteran"]
        session.add(
            Player(
                id="player-real-summary",
                source_provider="test",
                provider_external_id="player-real-summary",
                full_name="Victor Real Summary",
                position="ST",
                normalized_position="forward",
                date_of_birth=date(1998, 12, 29),
                is_real_player=True,
            )
        )
        session.add_all(
            [
                _seed_summary(
                    player_id=regen_player.id,
                    player_name=regen_player.full_name,
                    current_value_credits=340.0,
                    movement_pct=12.0,
                ),
                _seed_summary(
                    player_id="player-real-summary",
                    player_name="Victor Real Summary",
                    current_value_credits=410.0,
                    movement_pct=5.0,
                    summary_json={
                        "position": "forward",
                        "real_player_profile": {
                            "is_real_player": True,
                            "is_verified_real_player": True,
                            "canonical_display_name": "Victor Real Summary",
                            "real_player_tier": "featured",
                            "source_name": "curated-feed",
                            "source_player_key": "victor-real-summary",
                            "real_world_club_name": "Launch Club A",
                            "real_world_league_name": "Launch League Elite",
                            "current_market_reference_value": 60000000,
                            "market_reference_currency": "EUR",
                        },
                    },
                ),
            ]
        )
        session.commit()

        app = FastAPI()
        app.include_router(players_router)

        def _session_override():
            yield session

        app.dependency_overrides[get_session] = _session_override

        with TestClient(app) as client:
            recent_response = client.get("/players/summaries/recent", params={"limit": 5})
            regen_response = client.get(f"/players/{regen_player.id}/summary")
            real_response = client.get("/players/player-real-summary/summary")

        assert recent_response.status_code == 200
        assert regen_response.status_code == 200
        assert real_response.status_code == 200

        recent_payload = recent_response.json()
        regen_payload = regen_response.json()
        real_payload = real_response.json()

        by_player_id = {entry["player_id"]: entry for entry in recent_payload}

        assert regen_player.id in by_player_id
        assert "player-real-summary" in by_player_id
        assert regen_payload["identity_rail"] == "regen_universe"
        assert regen_payload["is_real_player"] is False
        assert regen_payload["regen_universe"] is not None
        assert regen_payload["regen_universe"]["total_awards"] >= 1
        assert regen_payload["regen_universe"]["latest_overall_ranking"] is not None
        assert regen_payload["real_player_universe"] is None
        assert real_payload["identity_rail"] == "real_player_universe"
        assert real_payload["is_real_player"] is True
        assert real_payload["real_player_universe"] is not None
        assert real_payload["real_player_universe"]["source_name"] == "curated-feed"
        assert real_payload["regen_universe"] is None
        assert by_player_id[regen_player.id]["identity_rail"] == "regen_universe"
        assert by_player_id["player-real-summary"]["identity_rail"] == "real_player_universe"
        assert by_player_id[regen_player.id]["regen_universe"] is not None
        assert by_player_id["player-real-summary"]["real_player_universe"] is not None
        assert by_player_id["player-real-summary"]["regen_universe"] is None
    finally:
        session.close()
