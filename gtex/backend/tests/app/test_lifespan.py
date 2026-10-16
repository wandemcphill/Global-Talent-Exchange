from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.main as app_main
from app.observability import logging as observability_logging


class _FakeContainer:
    def __init__(self, *, settings, engine, session_factory) -> None:
        self.settings = settings
        self.database = SimpleNamespace(
            engine=engine,
            session_factory=session_factory,
            read_engine=engine,
            read_session_factory=session_factory,
        )
        self.metrics = SimpleNamespace()


def test_create_app_uses_lifespan_hooks(monkeypatch) -> None:
    lifecycle_calls: list[str] = []

    async def _fake_startup(app) -> None:
        del app
        lifecycle_calls.append("startup")

    async def _fake_shutdown(app) -> None:
        del app
        lifecycle_calls.append("shutdown")

    monkeypatch.setattr(app_main, "_startup_app", _fake_startup)
    monkeypatch.setattr(app_main, "_shutdown_app", _fake_shutdown)
    monkeypatch.setattr(app_main, "register_core", lambda app: None)
    monkeypatch.setattr(app_main, "install_api_contracts", lambda app: None)
    monkeypatch.setattr(app_main, "Container", _FakeContainer)
    monkeypatch.setattr(
        app_main,
        "RealPlayerBulkPublishJobRegistry",
        lambda **_kwargs: object(),
    )
    monkeypatch.setattr(
        observability_logging,
        "configure_logging",
        lambda **_kwargs: None,
    )

    engine = create_engine("sqlite+pysqlite:///:memory:")
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    settings = SimpleNamespace(
        app_name="GTEX Test",
        app_version="test-version",
        app_env="test",
        observability_service_name=None,
        kafka_client_id="gtex-tests",
        observability_log_json=False,
        observability_tracing_enabled=False,
        cors_allowed_origins=(),
        cors_allow_origin_regex=None,
        cors_allow_credentials=False,
    )

    app = app_main.create_app(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        modules=(),
        run_migration_check=False,
    )

    assert app.router.on_startup == []
    assert app.router.on_shutdown == []

    with TestClient(app):
        pass

    assert lifecycle_calls == ["startup", "shutdown"]
    engine.dispose()
