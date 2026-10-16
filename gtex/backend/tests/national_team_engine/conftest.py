from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine

from app.modules import _module


@pytest.fixture(scope="module")
def test_settings(tmp_path_factory: pytest.TempPathFactory):
    from app.core.config import load_settings, reset_settings_cache

    database_path = tmp_path_factory.mktemp("gte-national-team-engine-app") / "gte_app.db"
    media_root = tmp_path_factory.mktemp("gte-national-team-engine-media")
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    managed_env = {
        "DATABASE_URL": database_url,
        "GTE_DATABASE_URL": database_url,
        "GTE_MEDIA_STORAGE_ROOT": str(media_root),
        "GTE_INGESTION_PROVIDER": "mock",
        "GTE_REAL_PLAYER_IMPORT_PROVIDER": "mock",
        "GTE_RUN_STARTUP_SEEDING": "0",
        "GTE_TASK_QUEUE_ENABLED": "0",
    }
    previous_env = {key: os.environ.get(key) for key in managed_env}

    try:
        for key, value in managed_env.items():
            os.environ[key] = value
        reset_settings_cache()
        yield load_settings()
    finally:
        reset_settings_cache()
        for key, previous_value in previous_env.items():
            if previous_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous_value
        reset_settings_cache()


@pytest.fixture(scope="module")
def app(test_settings):
    from app.main import create_app

    modules = (
        _module("auth", router_path="app.auth.router:router"),
        _module("competitions", router_path="app.routes.competitions:router"),
        _module("national_team_engine", router_path="app.national_team_engine.router:router", api_only=True),
        _module(
            "national_team_engine_admin",
            router_path="app.national_team_engine.router:admin_router",
            api_only=True,
        ),
        _module("national_rental", router_path="app.national_team_engine.router:national_router", api_only=True),
    )
    engine = create_engine(test_settings.database_url, connect_args={"check_same_thread": False})
    application = create_app(
        settings=test_settings,
        engine=engine,
        modules=modules,
        run_migration_check=True,
    )
    yield application
    startup_thread = getattr(application.state, "deferred_startup_thread", None)
    if startup_thread is not None and startup_thread.is_alive():
        startup_thread.join(timeout=5)
    engine.dispose()
