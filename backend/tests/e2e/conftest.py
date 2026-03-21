from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine

from app.auth.service import AuthService
from app.leagues.repository import InMemoryLeagueEventRepository, get_league_event_repository
from app.main import create_app
from app.match_engine.services import ensure_local_match_execution_runtime
from app.replay_archive.service import ensure_replay_archive


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    club_id: str | None
    user_id: str
    headers: dict[str, str]


def _create_authenticated_user(
    app,
    *,
    club_id: str | None,
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
            club_id=club_id,
            user_id=user.id,
            headers={"Authorization": f"Bearer {token}"},
        )


@pytest.fixture(autouse=True)
def isolated_league_repository():
    repository = get_league_event_repository()
    if isinstance(repository, InMemoryLeagueEventRepository):
        repository.clear()
    try:
        yield repository
    finally:
        if isinstance(repository, InMemoryLeagueEventRepository):
            repository.clear()


@pytest.fixture()
def app_client(tmp_path):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'match_lifecycle_e2e.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    app = create_app(engine=engine, run_migration_check=True)
    try:
        with TestClient(app) as client:
            ensure_replay_archive(app)
            ensure_local_match_execution_runtime(app)
            yield app, client
    finally:
        engine.dispose()


@pytest.fixture()
def user_factory(app_client):
    app, _client = app_client

    def factory(
        *,
        club_id: str | None,
        email: str,
        username: str,
        display_name: str,
    ) -> AuthenticatedUser:
        return _create_authenticated_user(
            app,
            club_id=club_id,
            email=email,
            username=username,
            display_name=display_name,
        )

    return factory
