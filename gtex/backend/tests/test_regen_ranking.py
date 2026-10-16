from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.ingestion.models import Player, PlayerSeasonStat
from app.regen_universe.models import RegenSeason
from app.regen_universe.service import RegenUniverseService
from tests.regen_universe_support import build_regen_universe_session, seed_tied_ranking_universe


def test_rankings_are_stable_and_hall_of_fame_accumulates_without_pricing_tables() -> None:
    session = build_regen_universe_session()
    try:
        bundle = seed_tied_ranking_universe(session)
        service: RegenUniverseService = bundle["service"]
        players = bundle["players"]
        active_season = session.scalar(select(RegenSeason).where(RegenSeason.is_active.is_(True)))
        assert active_season is not None

        close_result = service.close_season(active_season.id, start_next_season=False)
        midfielder_ranking = service.list_rankings(season_id=active_season.id, category="midfielder", limit=5)
        hall_of_fame = service.list_hall_of_fame(limit=10)
        veteran_summary = service.get_player_prestige_summary(players["veteran"].id)

        ordered_player_ids = [entry["player_id"] for entry in midfielder_ranking["entries"]]
        alpha_index = ordered_player_ids.index(players["alpha"].id)
        beta_index = ordered_player_ids.index(players["beta"].id)
        veteran_hof = next(item for item in hall_of_fame["entries"] if item["player_id"] == players["veteran"].id)

        assert close_result["performance_records_created"] >= len(players)
        assert alpha_index < beta_index
        assert veteran_hof["total_awards"] >= 2
        assert veteran_hof["seasons_active"] == 2
        assert veteran_hof["peak_rank"] == 1
        assert veteran_hof["legacy_score"] > 0
        assert veteran_summary is not None
        assert veteran_summary["total_awards"] == veteran_hof["total_awards"]
        assert veteran_summary["peak_rank"] == 1
    finally:
        session.close()


def test_rankings_ignore_real_players_and_preserve_regen_ordering() -> None:
    session = build_regen_universe_session()
    try:
        bundle = seed_tied_ranking_universe(session)
        service: RegenUniverseService = bundle["service"]
        competition = bundle["competition"]
        ingestion_season = bundle["ingestion_season_two"]
        players = bundle["players"]
        active_season = bundle["active_regen_season"]

        session.add(
            Player(
                id="player-real-ranking",
                source_provider="test",
                provider_external_id="player-real-ranking",
                full_name="Victor Realstar",
                position="CM",
                normalized_position="midfielder",
                date_of_birth=date(1999, 7, 2),
                is_real_player=True,
            )
        )
        session.add(
            PlayerSeasonStat(
                id="stat-player-real-ranking",
                source_provider="test",
                provider_external_id="stat-player-real-ranking",
                player_id="player-real-ranking",
                competition_id=competition.id,
                season_id=ingestion_season.id,
                appearances=34,
                starts=34,
                minutes=3060,
                goals=34,
                assists=20,
                average_rating=8.9,
            )
        )
        session.flush()

        close_result = service.close_season(active_season.id, start_next_season=False)
        ranking = service.list_rankings(season_id=active_season.id, category="overall", limit=20)
        ranked_ids = [entry["player_id"] for entry in ranking["entries"]]

        assert close_result["performance_records_created"] == len(players)
        assert "player-real-ranking" not in ranked_ids
        assert ranked_ids[0] == players["veteran"].id
        assert players["alpha"].id in ranked_ids
        assert players["beta"].id in ranked_ids
    finally:
        session.close()
