from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI

from backend.app.ingestion.demo_bootstrap import CANONICAL_DEMO_PLAYER_COUNT, DemoBootstrapService
from backend.app.market.projections import MarketSummaryProjector
from backend.app.market.repositories import InMemoryMarketRepository
from backend.app.market.service import MarketEngine
from backend.app.simulation.service import (
    DEFAULT_ILLIQUID_PLAYER_COUNT,
    DEFAULT_LIQUID_PLAYER_COUNT,
    DEFAULT_SIMULATION_SEED,
    DemoLiquiditySeedSummary,
    DemoMarketSimulationService,
)


@dataclass(frozen=True, slots=True)
class DemoSimulationRuntimeSummary:
    bootstrap: dict[str, Any] | None
    liquidity: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "bootstrap": self.bootstrap,
            "liquidity": self.liquidity,
        }


def replace_market_engine(app: FastAPI) -> MarketEngine:
    market_engine = MarketEngine(
        repository=InMemoryMarketRepository(),
        summary_projector=MarketSummaryProjector(app.state.session_factory),
        event_publisher=app.state.event_publisher,
    )
    app.state.market_engine = market_engine
    return market_engine


def seed_demo_simulation_for_app(
    app: FastAPI,
    *,
    bootstrap_demo: bool = False,
    with_liquidity_seed: bool = True,
    demo_player_count: int = CANONICAL_DEMO_PLAYER_COUNT,
    simulation_seed: int = DEFAULT_SIMULATION_SEED,
    liquid_player_count: int = DEFAULT_LIQUID_PLAYER_COUNT,
    illiquid_player_count: int = DEFAULT_ILLIQUID_PLAYER_COUNT,
) -> DemoSimulationRuntimeSummary:
    bootstrap_summary: dict[str, Any] | None = None
    if bootstrap_demo:
        bootstrap_summary = DemoBootstrapService(
            session_factory=app.state.session_factory,
            settings=app.state.settings,
            event_publisher=app.state.event_publisher,
        ).seed(
            player_target_count=demo_player_count,
            batch_size=min(500, demo_player_count),
        ).to_dict()

    simulation_service = DemoMarketSimulationService(
        session_factory=app.state.session_factory,
        event_publisher=app.state.event_publisher,
    )

    liquidity_summary: DemoLiquiditySeedSummary
    if with_liquidity_seed:
        liquidity_summary = simulation_service.seed_demo_liquidity(
            random_seed=simulation_seed,
            liquid_player_count=liquid_player_count,
            illiquid_player_count=illiquid_player_count,
        )
    else:
        liquidity_summary = simulation_service.replay_market_state(
            replace_market_engine(app),
            liquid_player_count=liquid_player_count,
            illiquid_player_count=illiquid_player_count,
        )
        runtime_summary = DemoSimulationRuntimeSummary(
            bootstrap=bootstrap_summary,
            liquidity=liquidity_summary.to_dict(),
        )
        app.state.demo_simulation = runtime_summary.to_dict()
        return runtime_summary

    market_engine = replace_market_engine(app)
    replay_summary = simulation_service.replay_market_state(
        market_engine,
        liquid_player_count=liquid_player_count,
        illiquid_player_count=illiquid_player_count,
    )
    runtime_summary = DemoSimulationRuntimeSummary(
        bootstrap=bootstrap_summary,
        liquidity=replay_summary.to_dict(),
    )
    app.state.demo_simulation = runtime_summary.to_dict()
    return runtime_summary


__all__ = [
    "DemoSimulationRuntimeSummary",
    "replace_market_engine",
    "seed_demo_simulation_for_app",
]
