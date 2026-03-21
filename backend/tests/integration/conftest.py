from __future__ import annotations

import os

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy import create_engine

from app.core.config import load_settings
from app.ingestion.demo_bootstrap import DemoBootstrapService
from app.main import create_app
from app.players.read_models import PlayerSummaryReadModel
from app.simulation.runtime import replace_market_engine
from app.simulation.service import DemoMarketSimulationService


@pytest.fixture(scope="module")
def integration_app_settings(tmp_path_factory: pytest.TempPathFactory):
    database_path = tmp_path_factory.mktemp("gte-integration-app") / "gte_integration_app.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    return load_settings(
        environ={
            **os.environ,
            "GTE_DATABASE_URL": database_url,
        }
    )


@pytest.fixture(scope="module")
def integration_engine(integration_app_settings):
    engine = create_engine(integration_app_settings.database_url, connect_args={"check_same_thread": False})
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def integration_app(integration_app_settings, integration_engine):
    app = create_app(settings=integration_app_settings, engine=integration_engine, run_migration_check=True)
    yield app


@pytest.fixture(scope="module")
def integration_client(integration_app):
    with TestClient(integration_app) as client:
        yield client


@pytest.fixture(scope="module")
def seeded_demo_market(integration_app, integration_client):
    bootstrap = DemoBootstrapService(
        session_factory=integration_app.state.session_factory,
        settings=integration_app.state.settings,
        event_publisher=integration_app.state.event_publisher,
    ).seed(player_target_count=12, batch_size=6)

    simulation_service = DemoMarketSimulationService(
        session_factory=integration_app.state.session_factory,
        event_publisher=integration_app.state.event_publisher,
    )
    liquidity = simulation_service.seed_demo_liquidity()
    replace_market_engine(integration_app)
    replay = simulation_service.replay_market_state(integration_app.state.market_engine)
    return {
        "bootstrap": bootstrap,
        "liquidity": liquidity,
        "replay": replay,
    }


@pytest.fixture(scope="module")
def demo_users_by_username(seeded_demo_market):
    bootstrap = seeded_demo_market["bootstrap"]
    return {user.username: user for user in bootstrap.demo_users}


@pytest.fixture(scope="module")
def demo_primary_user(demo_users_by_username):
    return demo_users_by_username["seed_fan"]


@pytest.fixture(scope="module")
def demo_secondary_user(demo_users_by_username):
    return demo_users_by_username["seed_scout"]


def _login_demo_user(client: TestClient, *, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def demo_auth_headers(integration_client, demo_primary_user):
    return _login_demo_user(
        integration_client,
        email=demo_primary_user.email,
        password=demo_primary_user.password,
    )


@pytest.fixture(scope="module")
def demo_secondary_auth_headers(integration_client, demo_secondary_user):
    return _login_demo_user(
        integration_client,
        email=demo_secondary_user.email,
        password=demo_secondary_user.password,
    )


@pytest.fixture(scope="module")
def live_player_subset(seeded_demo_market):
    return seeded_demo_market["liquidity"].players


@pytest.fixture(scope="module")
def market_state_players(integration_app, seeded_demo_market):
    with integration_app.state.session_factory() as session:
        rows = session.scalars(
            select(PlayerSummaryReadModel).order_by(
                PlayerSummaryReadModel.player_name.asc(),
                PlayerSummaryReadModel.player_id.asc(),
            )
        ).all()
    return tuple(
        {
            "player_id": row.player_id,
            "player_name": row.player_name,
            "movement_pct": row.movement_pct,
            "current_value_credits": row.current_value_credits,
        }
        for row in rows
    )


@pytest.fixture(scope="module")
def rising_player(market_state_players):
    return next(player for player in market_state_players if player["movement_pct"] > 0)


@pytest.fixture(scope="module")
def falling_player(market_state_players):
    return next(player for player in market_state_players if player["movement_pct"] < 0)


@pytest.fixture(scope="module")
def liquid_player(seeded_demo_market):
    return next(player for player in seeded_demo_market["liquidity"].players if player.liquidity_label == "liquid")


@pytest.fixture(scope="module")
def illiquid_player(seeded_demo_market):
    return next(player for player in seeded_demo_market["liquidity"].players if player.liquidity_label == "illiquid")
