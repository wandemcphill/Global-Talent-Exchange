from __future__ import annotations

import os

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.ingestion.models  # noqa: F401
import backend.app.models  # noqa: F401
import backend.app.players.read_models  # noqa: F401
import backend.app.value_engine.read_models  # noqa: F401
from backend.app.core.config import load_settings
from backend.app.ingestion.demo_bootstrap import DemoBootstrapService
from backend.app.main import create_app
from backend.app.models.base import Base


@pytest.fixture()
def engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def session(session_factory):
    with session_factory() as db_session:
        yield db_session


@pytest.fixture(scope="module")
def app_settings(tmp_path_factory: pytest.TempPathFactory):
    database_path = tmp_path_factory.mktemp("gte-ingestion-app") / "gte_ingestion_app.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    return load_settings(
        environ={
            **os.environ,
            "GTE_DATABASE_URL": database_url,
        }
    )


@pytest.fixture(scope="module")
def app_engine(app_settings):
    engine = create_engine(app_settings.database_url, connect_args={"check_same_thread": False})
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def test_app(app_settings, app_engine):
    app = create_app(settings=app_settings, engine=app_engine, run_migration_check=True)
    yield app


@pytest.fixture(scope="module")
def test_client(test_app):
    with TestClient(test_app) as client:
        yield client


@pytest.fixture(scope="module")
def seeded_demo_environment(test_app, test_client):
    service = DemoBootstrapService(
        session_factory=test_app.state.session_factory,
        settings=test_app.state.settings,
        event_publisher=test_app.state.event_publisher,
    )
    return service.seed(player_target_count=12, batch_size=6)


@pytest.fixture(scope="module")
def seeded_demo_users_by_username(seeded_demo_environment):
    return {user.username: user for user in seeded_demo_environment.demo_users}


@pytest.fixture(scope="module")
def seeded_demo_primary_user(seeded_demo_environment):
    return seeded_demo_environment.demo_users[0]


def _login_demo_user(test_client: TestClient, *, email: str, password: str) -> dict[str, str]:
    response = test_client.post(
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
def seeded_demo_auth_headers(test_client, seeded_demo_primary_user):
    return _login_demo_user(
        test_client,
        email=seeded_demo_primary_user.email,
        password=seeded_demo_primary_user.password,
    )
