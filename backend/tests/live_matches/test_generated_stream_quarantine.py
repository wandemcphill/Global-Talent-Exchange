from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_match_user
from app.core.config import reset_settings_cache
from app.live_matches.legacy_runtime_access import issue_legacy_match_runtime_access_token
from app.live_matches.router import router as live_matches_router
from app.live_matches.service import LiveMatchHub
from app.live_matches.schemas import LiveMatchStreamEventView
from app.models.base import Base
from app.models.competition_match import CompetitionMatch
from app.models.manager_duel import ManagerDuel
from app.models.spectator_session import SpectatorSession
from app.models.user import User
from app.replay_archive.persistence import ReplayArchiveRecordRow
from backend.tests.support.secrets import MEDIA_SIGNING_TEST_SECRET, TEST_AUTH_SECRET


@dataclass
class _GeneratedStream:
    match_id: str
    home_team_id: str = "infinite-home"
    away_team_id: str = "infinite-away"
    home_team_name: str = "Infinite Home"
    away_team_name: str = "Infinite Away"
    base_home_possession: int = 52
    base_away_possession: int = 48
    atmosphere_profile: str = "standard"
    sync_strategy: str = "deterministic_playback"
    checkpoint_interval_seconds: int = 15
    max_latency_ms: int = 320

    @property
    def events(self) -> list[LiveMatchStreamEventView]:
        return [
            LiveMatchStreamEventView(
                match_id=self.match_id,
                event_id=f"{self.match_id}:kickoff",
                sequence=1,
                sequence_id=1,
                tick=0,
                minute=1,
                event_type="kickoff",
                team_id=self.home_team_id,
                team=self.home_team_name,
                team_side="home",
                commentary="The generated stream has kicked off.",
                home_score=0,
                away_score=0,
                meta={"source": "infinite_league"},
            )
        ]


class _FakeInfiniteLeagueRuntime:
    def __init__(self) -> None:
        self.live_stream_calls: list[str] = []

    def live_stream(self, match_id: str) -> _GeneratedStream:
        self.live_stream_calls.append(match_id)
        return _GeneratedStream(match_id=match_id)


def _viewer() -> User:
    return User(
        id="viewer-user-001",
        email="viewer@example.com",
        username="viewer",
        password_hash="hashed-password",  # pragma: allowlist secret
        is_active=True,
    )


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(live_matches_router)
    app.state.live_match_hub = LiveMatchHub(step_interval_seconds=0.01)
    app.dependency_overrides[get_current_match_user] = _viewer
    return app


def _build_app_with_session() -> tuple[FastAPI, sessionmaker[Session], str, str]:
    app = _build_app()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            CompetitionMatch.__table__,
            ManagerDuel.__table__,
            ReplayArchiveRecordRow.__table__,
            SpectatorSession.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app.state.session_factory = session_factory
    app.state.live_match_hub = LiveMatchHub(session_factory=session_factory, step_interval_seconds=0.01)

    match_id = "no-backend-live-state-001"
    with session_factory() as session:
        spectator_session = SpectatorSession(match_id=match_id, user_id=_viewer().id)
        session.add(spectator_session)
        session.commit()
        session.refresh(spectator_session)
        access_token, _ = issue_legacy_match_runtime_access_token(
            match_id=match_id,
            spectator_session_id=spectator_session.id,
            viewer_user_id=_viewer().id,
        )
    return app, session_factory, match_id, access_token


def _configure_env(monkeypatch, *, generated_streams_enabled: bool) -> None:
    monkeypatch.setenv("GTE_AUTH_SECRET", TEST_AUTH_SECRET)
    monkeypatch.setenv("GTE_MEDIA_SIGNING_SECRET", MEDIA_SIGNING_TEST_SECRET)
    monkeypatch.setenv("GTEX_ENABLE_LEGACY_MATCH_RUNTIME", "1")
    if generated_streams_enabled:
        monkeypatch.setenv("GTEX_ENABLE_GENERATED_LIVE_MATCHES", "1")
    else:
        monkeypatch.delenv("GTEX_ENABLE_GENERATED_LIVE_MATCHES", raising=False)
    monkeypatch.setattr("app.live_matches.router._INFINITE_LEAGUE_TARGET_RUNTIME_SECONDS", 1.0)
    reset_settings_cache()


def test_spectate_does_not_autostart_generated_stream_without_internal_flag(monkeypatch) -> None:
    _configure_env(monkeypatch, generated_streams_enabled=False)
    fake_runtime = _FakeInfiniteLeagueRuntime()
    monkeypatch.setattr("app.live_matches.router.ensure_infinite_league_runtime", lambda _app: fake_runtime)
    app = _build_app()
    match_id = "no-backend-live-state-001"

    with TestClient(app) as client:
        response = client.post(f"/api/matches/{match_id}/spectate")

    assert response.status_code == 409
    assert response.json()["detail"] == "Match is not currently live for spectating."
    assert fake_runtime.live_stream_calls == []
    assert app.state.live_match_hub.get_state(match_id) is None


def test_live_payload_does_not_autostart_generated_stream_without_internal_flag(monkeypatch) -> None:
    _configure_env(monkeypatch, generated_streams_enabled=False)
    fake_runtime = _FakeInfiniteLeagueRuntime()
    monkeypatch.setattr("app.live_matches.router.ensure_infinite_league_runtime", lambda _app: fake_runtime)
    app, _session_factory, match_id, access_token = _build_app_with_session()

    with TestClient(app) as client:
        response = client.get(
            f"/match/{match_id}/live",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Match stream was not found."
    assert fake_runtime.live_stream_calls == []
    assert app.state.live_match_hub.get_state(match_id) is None


def test_spectate_can_autostart_generated_stream_with_internal_flag(monkeypatch) -> None:
    _configure_env(monkeypatch, generated_streams_enabled=True)
    fake_runtime = _FakeInfiniteLeagueRuntime()
    monkeypatch.setattr("app.live_matches.router.ensure_infinite_league_runtime", lambda _app: fake_runtime)
    app = _build_app()
    match_id = "generated-live-state-001"

    with TestClient(app) as client:
        response = client.post(f"/api/matches/{match_id}/spectate")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["match_id"] == match_id
    assert body["access_source"] == "infinite_league"
    assert fake_runtime.live_stream_calls == [match_id]
    assert app.state.live_match_hub.get_state(match_id) is not None
