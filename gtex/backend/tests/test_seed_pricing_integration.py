from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import load_settings
from app.core.database import load_model_modules
from app.ingestion.models import Player
from app.models.base import Base
from app.players.read_models import PlayerSummaryReadModel
from app.players.service import PlayerSummaryProjector
from app.schemas.player_seed import PlayerSeedRequest
from app.services.player_seed_service import PlayerSeedError, PlayerSeedService
from app.value_engine.read_models import PlayerValueSnapshotRecord
from app.value_engine.service import IngestionValueEngineBridge


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


def test_seed_service_invokes_authoritative_value_engine_bridge(session_factory, settings) -> None:
    bridge = IngestionValueEngineBridge(
        session_factory=session_factory,
        settings=settings,
        summary_projector=PlayerSummaryProjector(),
        default_lookback_days=settings.value_snapshot_lookback_days,
    )

    class _SpyBridge:
        def __init__(self, wrapped: IngestionValueEngineBridge) -> None:
            self.wrapped = wrapped
            self.calls: list[dict] = []

        def run(self, **kwargs):
            self.calls.append(kwargs)
            return self.wrapped.run(**kwargs)

    spy_bridge = _SpyBridge(bridge)
    service = PlayerSeedService(session_factory=session_factory, value_engine_bridge=spy_bridge, settings=settings)

    result = service.seed(
        PlayerSeedRequest.model_validate(
            {
                "mode": "test_seed_small",
                "target_player_count": 12,
                "provider_name": "test-seed-pricing",
                "random_seed": 123,
                "batch_size": 6,
                "as_of": "2026-03-23T12:00:00+00:00",
            }
        )
    )

    assert result.value_snapshots_seeded == 12
    assert len(spy_bridge.calls) == 1
    kwargs = spy_bridge.calls[0]
    assert len(kwargs["player_ids"]) == 12
    assert kwargs["triggered_by"] == "player_seed_service"

    with session_factory() as session:
        snapshot = session.scalar(
            select(PlayerValueSnapshotRecord)
            .join(Player, Player.id == PlayerValueSnapshotRecord.player_id)
            .where(Player.source_provider == "test-seed-pricing")
            .order_by(Player.provider_external_id.asc())
        )
        summary = session.scalar(
            select(PlayerSummaryReadModel)
            .join(Player, Player.id == PlayerSummaryReadModel.player_id)
            .where(Player.source_provider == "test-seed-pricing")
            .order_by(Player.provider_external_id.asc())
        )
        assert snapshot is not None
        assert summary is not None
        assert summary.current_value_credits == snapshot.target_credits
        assert summary.last_snapshot_id == snapshot.id


def test_seed_service_refuses_to_create_fallback_prices_when_bridge_returns_no_snapshots(session_factory, settings) -> None:
    class _EmptyBridge:
        def run(self, **_kwargs):
            return []

    service = PlayerSeedService(
        session_factory=session_factory,
        value_engine_bridge=_EmptyBridge(),
        settings=settings,
    )

    with pytest.raises(PlayerSeedError, match="No fallback pricing path was used"):
        service.seed(
            PlayerSeedRequest.model_validate(
                {
                    "mode": "test_seed_small",
                    "target_player_count": 8,
                    "provider_name": "test-seed-no-fallback",
                    "random_seed": 55,
                    "batch_size": 4,
                    "as_of": "2026-03-24T12:00:00+00:00",
                }
            )
        )
