from __future__ import annotations

import os

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine

from app.core.config import load_settings
from app.ingestion.demo_bootstrap import DemoBootstrapService
from app.main import create_app
from app.simulation.runtime import replace_market_engine
from app.simulation.service import DemoMarketSimulationService


@pytest.fixture(scope="module")
def simulation_app_settings(tmp_path_factory: pytest.TempPathFactory):
    database_path = tmp_path_factory.mktemp("gte-simulation-app") / "gte_simulation_app.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    return load_settings(
        environ={
            **os.environ,
            "GTE_DATABASE_URL": database_url,
        }
    )


@pytest.fixture(scope="module")
def simulation_engine(simulation_app_settings):
    engine = create_engine(simulation_app_settings.database_url, connect_args={"check_same_thread": False})
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def simulation_app(simulation_app_settings, simulation_engine):
    app = create_app(settings=simulation_app_settings, engine=simulation_engine, run_migration_check=True)
    yield app


@pytest.fixture(scope="module")
def simulation_client(simulation_app):
    with TestClient(simulation_app) as client:
        yield client


@pytest.fixture(scope="module")
def seeded_simulation_market(simulation_app, simulation_client):
    DemoBootstrapService(
        session_factory=simulation_app.state.session_factory,
        settings=simulation_app.state.settings,
        event_publisher=simulation_app.state.event_publisher,
    ).seed(player_target_count=12, batch_size=6)

    service = DemoMarketSimulationService(
        session_factory=simulation_app.state.session_factory,
        event_publisher=simulation_app.state.event_publisher,
    )
    liquidity = service.seed_demo_liquidity()
    replace_market_engine(simulation_app)
    replay = service.replay_market_state(simulation_app.state.market_engine)
    return {
        "service": service,
        "liquidity": liquidity,
        "replay": replay,
    }


@pytest.fixture(scope="module")
def liquid_player(seeded_simulation_market):
    return next(player for player in seeded_simulation_market["liquidity"].players if player.liquidity_label == "liquid")


@pytest.fixture(scope="module")
def illiquid_player(seeded_simulation_market):
    return next(player for player in seeded_simulation_market["liquidity"].players if player.liquidity_label == "illiquid")
