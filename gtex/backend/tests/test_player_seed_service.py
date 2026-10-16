from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.clubs.service import ClubQueryService
from app.core.config import load_settings
from app.core.database import load_model_modules
from app.ingestion.models import MarketSignal, Player, PlayerSeasonStat
from app.models.base import Base
from app.models.player_cards import PlayerMarketValueSnapshot, PlayerStatsSnapshot
from app.player_cards.service import PlayerCardMarketService
from app.players.read_models import PlayerSummaryReadModel
from app.schemas.player_seed import PlayerSeedRequest
from app.services.player_seed_service import PlayerSeedService
from app.simulation.service import DemoMarketSimulationService
from app.value_engine.read_models import PlayerValueSnapshotRecord


@pytest.fixture()
def session_factory():
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()


@pytest.fixture()
def settings():
    return load_settings(environ={**os.environ, "GTE_DATABASE_URL": "sqlite+pysqlite:///:memory:"})


def test_player_seed_service_populates_market_squad_and_simulation_surfaces(session_factory, settings, tmp_path: Path) -> None:
    as_of = "2026-03-21T12:00:00+00:00"
    request = PlayerSeedRequest.model_validate(
        {
            "mode": "test_seed_small",
            "target_player_count": 30,
            "provider_name": "test-seed-e2e",
            "random_seed": 77,
            "batch_size": 10,
            "checkpoint_path": str(tmp_path / "player-seed-e2e.json"),
            "as_of": as_of,
        }
    )

    result = PlayerSeedService(session_factory=session_factory, settings=settings).seed(request)

    assert result.players_seeded == 30
    assert result.value_snapshots_seeded == 30
    assert result.free_agents_seeded > 0

    with session_factory() as session:
        player_count = session.scalar(
            select(func.count()).select_from(Player).where(Player.source_provider == "test-seed-e2e")
        )
        season_stat_count = session.scalar(
            select(func.count())
            .select_from(PlayerSeasonStat)
            .join(Player, Player.id == PlayerSeasonStat.player_id)
            .where(Player.source_provider == "test-seed-e2e")
        )
        signal_count = session.scalar(
            select(func.count())
            .select_from(MarketSignal)
            .join(Player, Player.id == MarketSignal.player_id)
            .where(Player.source_provider == "test-seed-e2e")
        )
        value_snapshot_count = session.scalar(
            select(func.count())
            .select_from(PlayerValueSnapshotRecord)
            .join(Player, Player.id == PlayerValueSnapshotRecord.player_id)
            .where(Player.source_provider == "test-seed-e2e")
        )
        summary_count = session.scalar(
            select(func.count())
            .select_from(PlayerSummaryReadModel)
            .join(Player, Player.id == PlayerSummaryReadModel.player_id)
            .where(Player.source_provider == "test-seed-e2e")
        )
        market_snapshot_count = session.scalar(
            select(func.count())
            .select_from(PlayerMarketValueSnapshot)
            .join(Player, Player.id == PlayerMarketValueSnapshot.player_id)
            .where(Player.source_provider == "test-seed-e2e")
        )
        stats_snapshot_count = session.scalar(
            select(func.count())
            .select_from(PlayerStatsSnapshot)
            .join(Player, Player.id == PlayerStatsSnapshot.player_id)
            .where(Player.source_provider == "test-seed-e2e")
        )

        assert player_count == 30
        assert season_stat_count == 30
        assert signal_count == 30 * 7
        assert value_snapshot_count == 30
        assert summary_count == 30
        assert market_snapshot_count == 30
        assert stats_snapshot_count == 30

        summary = session.scalar(
            select(PlayerSummaryReadModel)
            .join(Player, Player.id == PlayerSummaryReadModel.player_id)
            .where(Player.source_provider == "test-seed-e2e")
            .order_by(Player.provider_external_id.asc())
        )
        assert summary is not None
        assert summary.summary_json["formation_ready"] is True
        assert summary.summary_json["avatar_seed_token"]
        assert summary.summary_json["market_visibility"]["eligible"] is True
        assert summary.summary_json["secondary_positions"] is not None

        player_cards_surface = PlayerCardMarketService(session).list_players(limit=5)
        assert any(item["latest_value_credits"] is not None for item in player_cards_surface)

        club_id = session.scalar(
            select(Player.current_club_id)
            .where(Player.source_provider == "test-seed-e2e", Player.current_club_id.is_not(None))
            .limit(1)
        )
        assert club_id is not None
        assert ClubQueryService(session).get_club(club_id).player_count > 0

    simulation_summary = DemoMarketSimulationService(session_factory=session_factory).seed_demo_liquidity(
        liquid_player_count=2,
        illiquid_player_count=1,
        demo_password="SeedPass123!",
    )
    assert simulation_summary.player_count == 3
    assert len(simulation_summary.players) == 3


def test_player_seed_service_resumes_from_seed_checkpoint(session_factory, settings, tmp_path: Path) -> None:
    checkpoint_path = tmp_path / "resume-seed.json"
    request = PlayerSeedRequest.model_validate(
        {
            "mode": "test_seed_small",
            "target_player_count": 18,
            "provider_name": "test-seed-resume",
            "random_seed": 91,
            "batch_size": 6,
            "checkpoint_path": str(checkpoint_path),
            "as_of": "2026-03-22T12:00:00+00:00",
        }
    )

    class _FailingBridge:
        def run(self, **_kwargs):
            raise RuntimeError("value bridge exploded")

    with pytest.raises(RuntimeError, match="value bridge exploded"):
        PlayerSeedService(
            session_factory=session_factory,
            value_engine_bridge=_FailingBridge(),
            settings=settings,
        ).seed(request)

    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert checkpoint["phase"] == "seeded"

    with session_factory() as session:
        player_count = session.scalar(
            select(func.count()).select_from(Player).where(Player.source_provider == "test-seed-resume")
        )
        snapshot_count = session.scalar(
            select(func.count())
            .select_from(PlayerValueSnapshotRecord)
            .join(Player, Player.id == PlayerValueSnapshotRecord.player_id)
            .where(Player.source_provider == "test-seed-resume")
        )
        assert player_count == 18
        assert snapshot_count == 0

    resumed = PlayerSeedService(session_factory=session_factory, settings=settings).seed(
        request.model_copy(update={"resume_from_checkpoint": True})
    )

    assert resumed.players_seeded == 18
    assert resumed.value_snapshots_seeded == 18

    with session_factory() as session:
        player_count = session.scalar(
            select(func.count()).select_from(Player).where(Player.source_provider == "test-seed-resume")
        )
        snapshot_count = session.scalar(
            select(func.count())
            .select_from(PlayerValueSnapshotRecord)
            .join(Player, Player.id == PlayerValueSnapshotRecord.player_id)
            .where(Player.source_provider == "test-seed-resume")
        )
        assert player_count == 18
        assert snapshot_count == 18
