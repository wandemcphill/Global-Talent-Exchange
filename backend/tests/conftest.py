from __future__ import annotations

import os

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine

from backend.app.core.config import load_settings
from backend.app.ingestion.demo_bootstrap import DemoBootstrapService
from backend.app.main import create_app

SMOKE_DEMO_PLAYER_COUNT = 12


@pytest.fixture(scope="module")
def test_settings(tmp_path_factory: pytest.TempPathFactory):
    database_path = tmp_path_factory.mktemp("gte-app") / "gte_app.db"
    media_root = tmp_path_factory.mktemp("gte-media")
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    return load_settings(
        environ={
            **os.environ,
            "GTE_DATABASE_URL": database_url,
            "GTE_MEDIA_STORAGE_ROOT": str(media_root),
        }
    )


@pytest.fixture(scope="module")
def app(test_settings):
    engine = create_engine(test_settings.database_url, connect_args={"check_same_thread": False})
    application = create_app(settings=test_settings, engine=engine, run_migration_check=True)
    yield application
    engine.dispose()


@pytest.fixture(scope="module")
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def app_session_factory(app, client):
    return app.state.session_factory


@pytest.fixture(scope="module")
def demo_seed(app, client):
    service = DemoBootstrapService(
        session_factory=app.state.session_factory,
        settings=app.state.settings,
        event_publisher=app.state.event_publisher,
    )
    return service.seed(player_target_count=SMOKE_DEMO_PLAYER_COUNT, batch_size=6)


@pytest.fixture(scope="module")
def demo_user_credentials(demo_seed):
    primary_user = demo_seed.demo_users[0]
    return {
        "email": primary_user.email,
        "password": primary_user.password,
    }


@pytest.fixture(scope="module")
def demo_auth_headers(client, demo_seed, demo_user_credentials):
    response = client.post(
        "/auth/login",
        json={
            "email": demo_user_credentials["email"],
            "password": demo_user_credentials["password"],
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
