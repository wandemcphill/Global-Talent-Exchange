from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import load_settings
from app.core.database import load_model_modules
from app.ingestion.models import Club, Competition, Country, Player
from app.ingestion.real_player_ingestion_service import RealPlayerIngestionService, RealPlayerPricingError
from app.models.base import Base
from app.players.read_models import PlayerSummaryReadModel
from app.players.service import PlayerSummaryProjector
from app.schemas.real_player_ingestion import RealPlayerIngestionRequest
from app.value_engine.read_models import PlayerValueSnapshotRecord, RealPlayerValueLineageRecord
from app.value_engine.service import IngestionValueEngineBridge


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
    return load_settings(
        environ={
            **os.environ,
            "GTE_DATABASE_URL": "sqlite+pysqlite:///:memory:",
            "GTE_REAL_PLAYER_MAPPING_AUTO_CREATE_MISSING_ENTITIES": "1",
        }
    )


def _seed_pricing_canonical_entities(session) -> None:
    nigeria = Country(
        source_provider="curated-feed",
        provider_external_id="NG",
        name="Nigeria",
        alpha2_code="NG",
        alpha3_code="NGA",
        fifa_code="NGA",
        confederation_code="CAF",
        market_region="africa",
    )
    elite = Competition(
        source_provider="curated-feed",
        provider_external_id="launch-league-elite",
        country=nigeria,
        name="Launch League Elite",
        slug="launch-league-elite",
        competition_type="league",
        format_type="real_world",
        is_tradable=True,
    )
    premier = Competition(
        source_provider="curated-feed",
        provider_external_id="launch-league-premier",
        country=nigeria,
        name="Launch League Premier",
        slug="launch-league-premier",
        competition_type="league",
        format_type="real_world",
        is_tradable=True,
    )
    session.add_all([nigeria, elite, premier])
    session.flush()
    session.add_all(
        [
            Club(
                source_provider="curated-feed",
                provider_external_id="launch-club-a",
                country=nigeria,
                current_competition=elite,
                name="Launch Club A",
                slug="launch-club-a",
                short_name="Launch A",
                is_tradable=True,
            ),
            Club(
                source_provider="curated-feed",
                provider_external_id="launch-club-b",
                country=nigeria,
                current_competition=premier,
                name="Launch Club B",
                slug="launch-club-b",
                short_name="Launch B",
                is_tradable=True,
            ),
        ]
    )
    session.commit()


def _request() -> RealPlayerIngestionRequest:
    return RealPlayerIngestionRequest.model_validate(
        {
            "mode": "test_small_real_seed",
            "as_of": "2026-03-22T15:00:00+00:00",
            "players": [
                {
                    "source_name": "curated-feed",
                    "source_player_key": "osimhen-001",
                    "canonical_name": "Victor Osimhen",
                    "nationality": "Nigeria",
                    "nationality_code": "NG",
                    "date_of_birth": "1998-12-29",
                    "primary_position": "Striker",
                    "current_real_world_club": "Launch Club A",
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
                    "primary_position": "Winger",
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
            ],
        }
    )


def test_real_player_ingestion_invokes_authoritative_value_engine_bridge() -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            _seed_pricing_canonical_entities(session)

        settings = _settings()
        wrapped_bridge = IngestionValueEngineBridge(
            session_factory=session_factory,
            settings=settings,
            summary_projector=PlayerSummaryProjector(),
            default_lookback_days=settings.value_snapshot_lookback_days,
        )

        class _SpyBridge:
            def __init__(self, wrapped: IngestionValueEngineBridge) -> None:
                self.wrapped = wrapped
                self.calls: list[dict] = []

            def preview_player(self, session, **kwargs):
                self.calls.append(kwargs)
                return self.wrapped.preview_player(session, **kwargs)

        spy_bridge = _SpyBridge(wrapped_bridge)
        service = RealPlayerIngestionService(
            session_factory=session_factory,
            value_engine_bridge=spy_bridge,
            settings=settings,
        )

        result = service.ingest(_request())

        assert result.authoritative_snapshots_seeded == 2
        assert len(spy_bridge.calls) == 2
        assert {call["player_id"] for call in spy_bridge.calls} == set(result.player_ids)
        assert {call["snapshot_type"] for call in spy_bridge.calls} == {"intraday"}

        with session_factory() as session:
            snapshot = session.scalar(
                select(PlayerValueSnapshotRecord)
                .join(Player, Player.id == PlayerValueSnapshotRecord.player_id)
                .where(Player.full_name == "Victor Osimhen")
            )
            summary = session.scalar(
                select(PlayerSummaryReadModel)
                .join(Player, Player.id == PlayerSummaryReadModel.player_id)
                .where(Player.full_name == "Victor Osimhen")
            )
            assert snapshot is not None
            assert summary is not None
            assert float(summary.current_value_credits) == pytest.approx(float(snapshot.target_credits), abs=0.25)
            assert summary.summary_json["real_player_profile"]["pricing_snapshot_id"] == snapshot.id
            lineage = session.scalar(
                select(RealPlayerValueLineageRecord).where(RealPlayerValueLineageRecord.snapshot_id == snapshot.id)
            )
            assert lineage is not None
            assert snapshot.breakdown_json["real_player_valuation"]["lineage_id"] == lineage.id
            assert summary.summary_json["real_player_profile"]["valuation_lineage_id"] == lineage.id
            assert summary.summary_json["real_player_valuation"]["lineage_id"] == lineage.id
            assert float(lineage.base_value_credits) == pytest.approx(
                float(snapshot.breakdown_json["real_player_valuation"]["base_value_credits"]),
                abs=0.01,
            )
    finally:
        engine.dispose()


def test_real_player_ingestion_fails_when_bridge_returns_no_snapshots() -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            _seed_pricing_canonical_entities(session)

        class _EmptyBridge:
            def preview_player(self, _session, **_kwargs):
                return None

        service = RealPlayerIngestionService(
            session_factory=session_factory,
            value_engine_bridge=_EmptyBridge(),
            settings=_settings(),
        )

        with pytest.raises(RealPlayerPricingError, match="No fallback pricing path was used"):
            service.ingest(_request())
    finally:
        engine.dispose()
