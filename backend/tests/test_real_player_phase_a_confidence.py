from __future__ import annotations

from datetime import UTC, date, datetime
import os

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import load_settings
from app.core.database import load_model_modules
from app.ingestion.real_player_ingestion_service import RealPlayerIngestionService
from app.market.service import MarketPlayerQueryService
from app.models.base import Base
from app.player_cards.service import PlayerCardMarketService
from app.players.read_models import PlayerSummaryReadModel
from app.schemas.real_player_ingestion import RealPlayerIngestionRequest
from app.value_engine.read_models import PlayerValueSnapshotRecord


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


def _request() -> RealPlayerIngestionRequest:
    return RealPlayerIngestionRequest.model_validate(
        {
            "mode": "curated_seed",
            "as_of": "2026-03-22T12:00:00+00:00",
            "ingestion_source_version": "phase-a-confidence-v1",
            "players": [
                {
                    "source_name": "curated-feed",
                    "source_player_key": "osimhen-001",
                    "canonical_name": "Victor Osimhen",
                    "nationality": "Nigeria",
                    "nationality_code": "NG",
                    "date_of_birth": "1998-12-29",
                    "primary_position": "Striker",
                    "secondary_positions": ["Winger"],
                    "current_real_world_club": "Galatasaray",
                    "current_real_world_league": "Super Lig",
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
                    "primary_position": "Winger",
                    "secondary_positions": ["Attacking Midfielder"],
                    "current_real_world_club": "Fulham",
                    "current_real_world_league": "Premier League",
                    "competition_level": "top_flight",
                    "appearances": 29,
                    "minutes_played": 2280,
                    "goals": 6,
                    "assists": 7,
                    "current_market_reference_value": 18000000,
                    "market_reference_currency": "EUR",
                },
            ],
        }
    )


def _valuation_projection(session_factory) -> dict[str, tuple[float, float]]:
    with session_factory() as session:
        snapshots = {
            snapshot.player_name: round(float(snapshot.target_credits), 6)
            for snapshot in session.scalars(select(PlayerValueSnapshotRecord))
        }
        summaries = {
            summary.player_name: round(float(summary.current_value_credits), 6)
            for summary in session.scalars(select(PlayerSummaryReadModel))
        }
    return {
        player_name: (snapshots[player_name], summaries[player_name])
        for player_name in sorted(snapshots)
    }


def test_real_player_authoritative_valuation_is_deterministic_across_isolated_databases() -> None:
    engine_a, factory_a = _session_factory()
    engine_b, factory_b = _session_factory()
    try:
        RealPlayerIngestionService(session_factory=factory_a, settings=_settings()).ingest(_request())
        RealPlayerIngestionService(session_factory=factory_b, settings=_settings()).ingest(_request())

        assert _valuation_projection(factory_a) == _valuation_projection(factory_b)
    finally:
        engine_a.dispose()
        engine_b.dispose()


def test_market_and_player_card_surfaces_expose_imported_real_players() -> None:
    engine, factory = _session_factory()
    try:
        RealPlayerIngestionService(session_factory=factory, settings=_settings()).ingest(_request())

        with factory() as session:
            market_service = MarketPlayerQueryService(session=session, today=date(2026, 3, 22))
            market_payload = market_service.list_players(search="Osimhen", limit=5)
            assert market_payload.total >= 1
            assert market_payload.items[0].player_name == "Victor Osimhen"
            assert market_payload.items[0].current_value_credits is not None

            detail = market_service.get_player_detail(market_payload.items[0].player_id)
            assert detail.identity.player_name == "Victor Osimhen"
            assert detail.value.last_snapshot_id is not None
            assert detail.value.current_value_credits is not None

            player_card_payload = PlayerCardMarketService(session=session).list_players(search="Osimhen", limit=5)
            assert player_card_payload
            assert player_card_payload[0]["player_name"] == "Victor Osimhen"
            assert player_card_payload[0]["latest_value_credits"] is not None
    finally:
        engine.dispose()
