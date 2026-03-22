from __future__ import annotations

import os

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import load_settings
from app.core.database import load_model_modules
from app.ingestion.models import Player, PlayerImageMetadata
from app.ingestion.real_player_ingestion_service import RealPlayerIngestionService
from app.models.base import Base
from app.models.player_cards import PlayerMarketValueSnapshot, PlayerStatsSnapshot
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_source_link import RealPlayerSourceLink
from app.player_cards.service import PlayerCardMarketService
from app.players.read_models import PlayerSummaryReadModel
from app.schemas.real_player_ingestion import RealPlayerIngestionRequest


def _session_factory():
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _settings():
    return load_settings(environ={**os.environ, "GTE_DATABASE_URL": "sqlite+pysqlite:///:memory:"})


def _curated_request(*, mode: str, as_of: str, osimhen_club: str = "Launch Club A") -> RealPlayerIngestionRequest:
    return RealPlayerIngestionRequest.model_validate(
        {
            "mode": mode,
            "as_of": as_of,
            "ingestion_source_version": "launch-pack-v1",
            "players": [
                {
                    "source_name": "curated-feed",
                    "source_player_key": "osimhen-001",
                    "canonical_name": "Victor Osimhen",
                    "known_aliases": ["V. Osimhen"],
                    "nationality": "Nigeria",
                    "nationality_code": "NG",
                    "date_of_birth": "1998-12-29",
                    "dominant_foot": "right",
                    "primary_position": "Striker",
                    "secondary_positions": ["Winger"],
                    "current_real_world_club": osimhen_club,
                    "current_real_world_league": "Launch League Elite",
                    "competition_level": "elite",
                    "appearances": 31,
                    "minutes_played": 2410,
                    "goals": 19,
                    "assists": 4,
                    "current_market_reference_value": 60000000,
                    "market_reference_currency": "EUR",
                },
                {
                    "source_name": "curated-feed",
                    "source_player_key": "iwobi-001",
                    "canonical_name": "Alex Iwobi",
                    "nationality": "Nigeria",
                    "nationality_code": "NG",
                    "date_of_birth": "1996-05-03",
                    "dominant_foot": "right",
                    "primary_position": "Winger",
                    "secondary_positions": ["Attacking Midfielder"],
                    "current_real_world_club": "Launch Club B",
                    "current_real_world_league": "Launch League Premier",
                    "competition_level": "top_flight",
                    "appearances": 29,
                    "minutes_played": 2280,
                    "goals": 6,
                    "assists": 7,
                    "current_market_reference_value": 18000000,
                    "market_reference_currency": "EUR",
                },
                {
                    "source_name": "curated-feed",
                    "source_player_key": "bassey-001",
                    "canonical_name": "Calvin Bassey",
                    "nationality": "Nigeria",
                    "nationality_code": "NG",
                    "birth_year": 1999,
                    "dominant_foot": "left",
                    "primary_position": "Centre-Back",
                    "secondary_positions": ["Full-Back"],
                    "current_real_world_club": "Launch Club C",
                    "current_real_world_league": "Launch League Premier",
                    "competition_level": "top_flight",
                    "appearances": 30,
                    "minutes_played": 2550,
                    "goals": 1,
                    "assists": 2,
                    "clean_sheets": 11,
                    "current_market_reference_value": 22000000,
                    "market_reference_currency": "EUR",
                },
            ],
        }
    )


def test_real_player_ingestion_seeds_curated_batch_without_duplicate_identities() -> None:
    engine, session_factory = _session_factory()
    try:
        service = RealPlayerIngestionService(session_factory=session_factory, settings=_settings())
        result = service.ingest(_curated_request(mode="curated_seed", as_of="2026-03-22T12:00:00+00:00"))

        assert result.players_processed == 3
        assert result.players_created == 3
        assert result.players_updated == 0
        assert result.authoritative_snapshots_seeded == 3

        with session_factory() as session:
            assert session.scalar(select(func.count()).select_from(Player).where(Player.is_real_player.is_(True))) == 3
            assert session.scalar(select(func.count()).select_from(RealPlayerSourceLink)) == 3
            assert session.scalar(select(func.count()).select_from(RealPlayerProfile)) == 3
            assert session.scalar(select(func.count()).select_from(PlayerSummaryReadModel)) == 3
            assert session.scalar(select(func.count()).select_from(PlayerMarketValueSnapshot)) == 3
            assert session.scalar(select(func.count()).select_from(PlayerStatsSnapshot)) == 3
            assert session.scalar(select(func.count()).select_from(PlayerImageMetadata)) == 0

            summary = session.scalar(
                select(PlayerSummaryReadModel)
                .join(Player, Player.id == PlayerSummaryReadModel.player_id)
                .where(Player.full_name == "Victor Osimhen")
            )
            assert summary is not None
            assert summary.summary_json["formation_ready"] is True
            assert summary.summary_json["real_player_profile"]["is_real_player"] is True
            assert summary.summary_json["real_player_profile"]["pricing_snapshot_id"]
            assert summary.summary_json["market_visibility"]["eligible"] is True

            listed = PlayerCardMarketService(session).list_players(search="Osimhen", limit=5)
            assert listed
            assert listed[0]["latest_value_credits"] is not None
            assert listed[0]["avatar"]["seed_token"]
    finally:
        engine.dispose()


def test_real_player_ingestion_refresh_updates_existing_players_without_creating_duplicates() -> None:
    engine, session_factory = _session_factory()
    try:
        service = RealPlayerIngestionService(session_factory=session_factory, settings=_settings())
        first = service.ingest(_curated_request(mode="curated_seed", as_of="2026-03-22T12:00:00+00:00"))
        second = service.ingest(
            _curated_request(
                mode="refresh_existing",
                as_of="2026-03-23T12:00:00+00:00",
                osimhen_club="Launch Club Z",
            )
        )

        assert set(first.player_ids) == set(second.player_ids)
        assert second.players_created == 0
        assert second.players_updated == 3

        with session_factory() as session:
            assert session.scalar(select(func.count()).select_from(Player).where(Player.is_real_player.is_(True))) == 3
            assert session.scalar(select(func.count()).select_from(RealPlayerSourceLink)) == 3
            assert session.scalar(select(func.count()).select_from(RealPlayerProfile)) == 3

            refreshed_player = session.scalar(select(Player).where(Player.full_name == "Victor Osimhen"))
            assert refreshed_player is not None
            assert refreshed_player.real_world_club_name == "Launch Club Z"

            refreshed_profile = session.scalar(
                select(RealPlayerProfile).where(RealPlayerProfile.canonical_name == "Victor Osimhen")
            )
            assert refreshed_profile is not None
            assert refreshed_profile.current_club_name == "Launch Club Z"
            assert refreshed_profile.pricing_snapshot_id is not None
    finally:
        engine.dispose()
