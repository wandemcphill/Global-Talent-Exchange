from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine

from app.auth.service import AuthService
from app.main import create_app
from app.replay_archive.service import ensure_replay_archive


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    user_id: str
    headers: dict[str, str]


def _create_authenticated_user(
    app,
    *,
    email: str,
    username: str,
    display_name: str,
) -> AuthenticatedUser:
    with app.state.session_factory() as session:
        service = AuthService()
        user = service.register_user(
            session,
            email=email,
            username=username,
            password="SuperSecret1",
            display_name=display_name,
        )
        token, _ = service.issue_access_token(user)
        session.commit()
        session.refresh(user)
        return AuthenticatedUser(
            user_id=user.id,
            headers={"Authorization": f"Bearer {token}"},
        )


@pytest.fixture()
def app_client(tmp_path):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'notifications.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    app = create_app(engine=engine, run_migration_check=True)
    with TestClient(app) as client:
        ensure_replay_archive(app)
        yield app, client
    engine.dispose()


@pytest.fixture()
def participant_user(app_client) -> AuthenticatedUser:
    app, _client = app_client
    return _create_authenticated_user(
        app,
        email="participant@example.com",
        username="participant",
        display_name="Participant User",
    )


@pytest.fixture()
def spectator_user(app_client) -> AuthenticatedUser:
    app, _client = app_client
    return _create_authenticated_user(
        app,
        email="spectator@example.com",
        username="spectator",
        display_name="Spectator User",
    )
