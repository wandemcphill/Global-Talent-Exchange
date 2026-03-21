from __future__ import annotations

from decimal import Decimal
import os

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.ingestion.models  # noqa: F401
import backend.app.ledger.models  # noqa: F401
import backend.app.matching.models  # noqa: F401
import backend.app.models  # noqa: F401
import backend.app.orders.models  # noqa: F401
import backend.app.players.read_models  # noqa: F401
import backend.app.value_engine.read_models  # noqa: F401
from backend.app.core.config import load_settings
from backend.app.core.events import InMemoryEventPublisher
from backend.app.ingestion.demo_bootstrap import (
    DEFAULT_DEMO_PASSWORD,
    DEMO_USER_SPECS,
    canonical_band_counts_for_player_count,
    DemoBootstrapService,
)
from backend.app.ingestion.models import MarketSignal, Player
from backend.app.matching.models import TradeExecution
from backend.app.models.base import Base
from backend.app.models.user import User
from backend.app.models.wallet import LedgerEntry, PaymentEvent
from backend.app.orders.models import Order
from backend.app.portfolio.service import PortfolioService
from backend.app.players.read_models import PlayerSummaryReadModel
from backend.app.value_engine.read_models import PlayerValueSnapshotRecord


@pytest.fixture()
def demo_service():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    settings = load_settings(
        environ={
            **os.environ,
            "GTE_DATABASE_URL": "sqlite+pysqlite:///:memory:",
        }
    )
    yield DemoBootstrapService(
        session_factory=SessionLocal,
        settings=settings,
        event_publisher=InMemoryEventPublisher(),
    ), SessionLocal
    engine.dispose()


def test_demo_bootstrap_service_seeds_demo_users_wallets_and_player_summaries(demo_service) -> None:
    service, session_factory = demo_service

    summary = service.seed(player_target_count=12, batch_size=6)

    assert summary.players_seeded == 12
    assert summary.market_signals_seeded == 48
    assert summary.value_snapshots_seeded == 24
    assert summary.player_summaries_seeded == 12
    assert summary.holdings_seeded == 5
    assert len(summary.demo_users) == len(DEMO_USER_SPECS)
    assert len(summary.featured_players) == 5
    assert len(summary.sample_holdings) == 5

    fan_user = next(user for user in summary.demo_users if user.username == "demo_fan")
    assert fan_user.password == DEFAULT_DEMO_PASSWORD
    assert fan_user.coin_balance == Decimal("150.0000")
    assert fan_user.credit_balance == Decimal("1200.0000")

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(User)) == len(DEMO_USER_SPECS)
        assert session.scalar(
            select(func.count()).select_from(Player).where(Player.source_provider == summary.provider_name)
        ) == 12
        assert session.scalar(
            select(func.count()).select_from(MarketSignal).where(MarketSignal.source_provider == summary.signal_provider)
        ) == 48
        assert session.scalar(select(func.count()).select_from(PaymentEvent)) == len(DEMO_USER_SPECS)
        assert session.scalar(select(func.count()).select_from(LedgerEntry)) >= len(DEMO_USER_SPECS) * 4
        assert session.scalar(select(func.count()).select_from(PlayerValueSnapshotRecord)) == 24
        assert session.scalar(select(func.count()).select_from(PlayerSummaryReadModel)) == 12

        fan_user = session.scalar(select(User).where(User.username == "demo_fan"))
        assert fan_user is not None

        portfolio = PortfolioService().build_for_user(session, fan_user)
        expected_player_ids = {
            holding.player_id
            for holding in summary.sample_holdings
            if holding.owner_username == "demo_fan"
        }
        assert expected_player_ids
        assert {holding.player_id for holding in portfolio.holdings} == expected_player_ids
        assert all(holding.quantity == Decimal("1.0000") for holding in portfolio.holdings)


def test_demo_bootstrap_service_is_repeatable_for_demo_users_and_balances(demo_service) -> None:
    service, session_factory = demo_service

    first = service.seed(player_target_count=8, batch_size=4)
    second = service.seed(player_target_count=8, batch_size=4)

    assert first.players_seeded == 8
    assert second.players_seeded == 8
    assert second.value_snapshots_seeded == 16
    assert second.holdings_seeded == 5

    balances = {
        user.username: (user.coin_balance, user.credit_balance)
        for user in second.demo_users
    }
    assert balances["demo_fan"] == (Decimal("150.0000"), Decimal("1200.0000"))
    assert balances["demo_scout"] == (Decimal("90.0000"), Decimal("850.0000"))
    assert balances["demo_admin"] == (Decimal("500.0000"), Decimal("5000.0000"))

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(User)) == len(DEMO_USER_SPECS)
        assert session.scalar(select(func.count()).select_from(PaymentEvent)) == len(DEMO_USER_SPECS)
        assert session.scalar(
            select(func.count()).select_from(Player).where(Player.source_provider == second.provider_name)
        ) == 8
        assert session.scalar(select(func.count()).select_from(PlayerValueSnapshotRecord)) == 16


def test_canonical_band_counts_match_locked_demo_distribution() -> None:
    assert canonical_band_counts_for_player_count(120) == {
        "band_a": 45,
        "band_b": 40,
        "band_c": 20,
        "band_d": 10,
        "band_e": 5,
    }


def test_demo_bootstrap_guarantees_rising_and_falling_players(demo_service) -> None:
    service, session_factory = demo_service

    summary = service.seed(player_target_count=12, batch_size=6)

    assert summary.players_seeded == 12

    with session_factory() as session:
        rising_count = session.scalar(
            select(func.count()).select_from(PlayerSummaryReadModel).where(PlayerSummaryReadModel.movement_pct > 0)
        )
        falling_count = session.scalar(
            select(func.count()).select_from(PlayerSummaryReadModel).where(PlayerSummaryReadModel.movement_pct < 0)
        )

    assert rising_count > 0
    assert falling_count > 0


def test_demo_bootstrap_can_include_demo_liquidity(demo_service) -> None:
    service, session_factory = demo_service

    summary = service.seed(
        player_target_count=10,
        batch_size=5,
        with_liquidity=True,
        liquid_player_count=3,
        illiquid_player_count=1,
    )

    assert summary.liquidity_seed is not None
    assert summary.liquidity_seed["player_count"] == 4
    assert summary.liquidity_seed["buy_orders_seeded"] > 0
    assert summary.liquidity_seed["sell_orders_seeded"] > 0
    assert summary.liquidity_seed["trade_executions_seeded"] > 0

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Order)) > 0
        assert session.scalar(select(func.count()).select_from(TradeExecution)) > 0
