from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.ingestion.models import Player, PlayerSeasonStat
from app.regen_universe.models import RegenSeason
from app.regen_universe.service import RegenUniverseService
from tests.regen_universe_support import build_regen_universe_session, seed_two_season_universe


def test_regen_awards_compute_for_sample_season_with_regen_only_players() -> None:
    session = build_regen_universe_session()
    try:
        bundle = seed_two_season_universe(session)
        service: RegenUniverseService = bundle["service"]
        players = bundle["players"]

        first_season = session.scalar(select(RegenSeason).where(RegenSeason.is_active.is_(True)))
        assert first_season is not None
        first_close = service.close_season(first_season.id, start_next_season=True)
        assert first_close["performance_records_created"] == len(players)

        second_season = session.scalar(select(RegenSeason).where(RegenSeason.is_active.is_(True)))
        assert second_season is not None
        second_season.start_date = bundle["ingestion_season_two"].start_date
        second_season.end_date = bundle["ingestion_season_two"].end_date
        second_season.metadata_json = {"source_ingestion_season_ids": [bundle["ingestion_season_two"].id]}
        session.flush()

        second_close = service.close_season(second_season.id, start_next_season=False)
        awards = service.list_awards(season_id=second_season.id)
        awards_by_code = {item["award"]["code"]: item["winners"] for item in awards}

        assert second_close["performance_records_created"] == len(players)
        assert second_close["award_winners_created"] >= 8
        assert awards_by_code["WORLD_PLAYER"][0]["player_id"] == players["veteran"].id
        assert awards_by_code["GOLDEN_BOY"][0]["player_id"] == players["wonderkid"].id
        assert awards_by_code["TOP_SCORER"][0]["player_id"] == players["veteran"].id
        assert awards_by_code["PLAYMAKER"][0]["player_id"] == players["playmaker"].id
        assert awards_by_code["DEFENDER"][0]["player_id"] == players["defender"].id
        assert awards_by_code["GOALKEEPER"][0]["player_id"] == players["keeper"].id
        assert awards_by_code["BREAKOUT_STAR"][0]["player_id"] == players["breakout"].id
        assert len(awards_by_code["TEAM_OF_THE_YEAR"]) >= 6
    finally:
        session.close()


def test_awards_ignore_real_players_even_when_mixed_with_regen_stats() -> None:
    session = build_regen_universe_session()
    try:
        bundle = seed_two_season_universe(session)
        service: RegenUniverseService = bundle["service"]
        players = bundle["players"]
        competition = bundle["competition"]

        first_season = session.scalar(select(RegenSeason).where(RegenSeason.is_active.is_(True)))
        assert first_season is not None
        service.close_season(first_season.id, start_next_season=True)

        second_season = session.scalar(select(RegenSeason).where(RegenSeason.is_active.is_(True)))
        assert second_season is not None
        second_season.start_date = bundle["ingestion_season_two"].start_date
        second_season.end_date = bundle["ingestion_season_two"].end_date
        second_season.metadata_json = {"source_ingestion_season_ids": [bundle["ingestion_season_two"].id]}
        session.flush()

        session.add(
            Player(
                id="player-real-award",
                source_provider="test",
                provider_external_id="player-real-award",
                full_name="Victor Awards",
                position="ST",
                normalized_position="forward",
                date_of_birth=date(1998, 12, 29),
                is_real_player=True,
            )
        )
        session.add(
            PlayerSeasonStat(
                id="stat-player-real-award",
                source_provider="test",
                provider_external_id="stat-player-real-award",
                player_id="player-real-award",
                competition_id=competition.id,
                season_id=bundle["ingestion_season_two"].id,
                appearances=38,
                starts=38,
                minutes=3340,
                goals=41,
                assists=14,
                average_rating=9.1,
            )
        )
        session.flush()

        close_result = service.close_season(second_season.id, start_next_season=False)
        awards = service.list_awards(season_id=second_season.id)
        winner_ids = {
            winner["player_id"]
            for award in awards
            for winner in award["winners"]
        }

        assert close_result["performance_records_created"] == len(players)
        assert "player-real-award" not in winner_ids
        assert players["veteran"].id in winner_ids
        assert players["wonderkid"].id in winner_ids
    finally:
        session.close()
