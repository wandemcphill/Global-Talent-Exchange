from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select

from app.core.config import load_settings
from app.ingestion.demo_bootstrap import DemoBootstrapService
from app.main import create_app
from app.matching.models import TradeExecution
from app.orders.models import Order, OrderSide, OrderStatus
from app.simulation.runtime import replace_market_engine
from app.simulation.service import DemoMarketSimulationService


def test_seed_demo_liquidity_creates_open_order_book_and_trade_history(
    simulation_app,
    seeded_simulation_market,
    liquid_player,
) -> None:
    session_factory = simulation_app.state.session_factory
    liquidity = seeded_simulation_market["liquidity"]

    assert liquidity.buy_orders_seeded > 0
    assert liquidity.sell_orders_seeded > 0
    assert liquidity.trade_executions_seeded > 0

    with session_factory() as session:
        open_buys = session.scalar(
            select(func.count())
            .select_from(Order)
            .where(
                Order.player_id == liquid_player.player_id,
                Order.side == OrderSide.BUY,
                Order.status.in_((OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED)),
            )
        )
        open_sells = session.scalar(
            select(func.count())
            .select_from(Order)
            .where(
                Order.player_id == liquid_player.player_id,
                Order.side == OrderSide.SELL,
                Order.status.in_((OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED)),
            )
        )
        executions = session.scalar(
            select(func.count())
            .select_from(TradeExecution)
            .where(TradeExecution.player_id == liquid_player.player_id)
        )

    assert open_buys >= 1
    assert open_sells >= 1
    assert executions >= 1


def test_simulation_tick_writes_additional_orders_and_trades(
    simulation_app,
    seeded_simulation_market,
) -> None:
    service: DemoMarketSimulationService = seeded_simulation_market["service"]
    session_factory = simulation_app.state.session_factory

    with session_factory() as session:
        baseline_orders = session.scalar(select(func.count()).select_from(Order))
        baseline_executions = session.scalar(select(func.count()).select_from(TradeExecution))

    summary = service.run_simulation_tick(tick_number=1)

    with session_factory() as session:
        next_orders = session.scalar(select(func.count()).select_from(Order))
        next_executions = session.scalar(select(func.count()).select_from(TradeExecution))

    assert summary.orders_created > 0
    assert summary.trade_executions_created > 0
    assert next_orders > baseline_orders
    assert next_executions >= baseline_executions + summary.trade_executions_created


def test_simulation_tick_is_deterministic_for_summary_shape(tmp_path: Path) -> None:
    first = _run_isolated_tick(tmp_path / "first.db")
    second = _run_isolated_tick(tmp_path / "second.db")

    assert first["tick_number"] == second["tick_number"]
    assert first["orders_created"] == second["orders_created"]
    assert first["trade_executions_created"] == second["trade_executions_created"]
    assert len(first["players_touched"]) == len(second["players_touched"])


def _run_isolated_tick(database_path: Path) -> dict:
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    settings = load_settings(
        environ={
            **os.environ,
            "GTE_DATABASE_URL": database_url,
        }
    )
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    app = create_app(settings=settings, engine=engine, run_migration_check=True)
    try:
        with TestClient(app):
            DemoBootstrapService(
                session_factory=app.state.session_factory,
                settings=app.state.settings,
                event_publisher=app.state.event_publisher,
            ).seed(player_target_count=12, batch_size=6)
            service = DemoMarketSimulationService(
                session_factory=app.state.session_factory,
                event_publisher=app.state.event_publisher,
            )
            service.seed_demo_liquidity()
            replace_market_engine(app)
            service.replay_market_state(app.state.market_engine)
            return service.run_simulation_tick(tick_number=2).to_dict()
    finally:
        engine.dispose()
