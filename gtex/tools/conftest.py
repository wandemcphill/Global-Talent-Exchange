from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine

from backend.tests.support.secrets import (
    BOOTSTRAP_TEST_ADMIN_PASSWORD,
    MEDIA_SIGNING_TEST_SECRET,
    TEST_AUTH_SECRET,
)

DEFAULT_TEST_DATABASE_URL = (
    f"sqlite+pysqlite:///{(Path(__file__).resolve().parent / '.tmp_pytest_tools.db').as_posix()}"
)

os.environ.setdefault("GTE_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
os.environ.setdefault("GTE_AUTH_SECRET", TEST_AUTH_SECRET)
os.environ.setdefault("GTE_MEDIA_SIGNING_SECRET", MEDIA_SIGNING_TEST_SECRET)
os.environ.setdefault("GTE_BOOTSTRAP_ADMIN_ENABLED", "1")
os.environ.setdefault("GTE_BOOTSTRAP_ADMIN_EMAIL", "admin@test.gtex.local")
os.environ.setdefault("GTE_BOOTSTRAP_ADMIN_PASSWORD", BOOTSTRAP_TEST_ADMIN_PASSWORD)
os.environ.setdefault("GTE_BOOTSTRAP_ADMIN_USERNAME", "gtex_test_admin")
os.environ.setdefault("GTE_BOOTSTRAP_ADMIN_DISPLAY_NAME", "GTEX Test Admin")
os.environ.setdefault("GTE_DEFERRED_STARTUP_ENABLED", "0")
os.environ.setdefault("GTE_COMPETITIVE_INTEGRITY_WORKER_ENABLED", "0")
os.environ.setdefault("GTE_FEDERATION_WORKER_ENABLED", "0")
os.environ.setdefault("GTE_HISTORY_ENGAGEMENT_WORKER_ENABLED", "0")
os.environ.setdefault("GTE_OUTBOX_RELAY_ENABLED", "0")
os.environ.setdefault("GTE_PORTRAIT_PRELOAD_ENABLED", "0")
os.environ.setdefault("GTE_PROJECTION_WORKERS_ENABLED", "0")
os.environ.setdefault("GTE_REGEN_PRELOAD_ENABLED", "0")
os.environ.setdefault("GTE_REAL_WORLD_SYNC_ENABLED", "0")
os.environ.setdefault("GTE_RUN_STARTUP_SEEDING", "0")
os.environ.setdefault("GTE_STARTUP_PROFILE", "test")
os.environ.setdefault("GTE_TASK_QUEUE_ENABLED", "0")
os.environ.setdefault("GTE_TEST_AUTH_FIXTURE_MODE", "1")
os.environ.setdefault("GTE_VIRAL_RANKING_WORKER_ENABLED", "0")


@pytest.fixture(scope="module")
def test_settings(tmp_path_factory: pytest.TempPathFactory):
    from app.core.config import load_settings, reset_settings_cache

    database_path = tmp_path_factory.mktemp("gte-app-tools") / "gte_app.db"
    media_root = tmp_path_factory.mktemp("gte-media-tools")
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    managed_env = {
        "DATABASE_URL": database_url,
        "GTE_DATABASE_URL": database_url,
        "GTE_MEDIA_STORAGE_ROOT": str(media_root),
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

    engine = create_engine(test_settings.database_url, connect_args={"check_same_thread": False})
    application = create_app(settings=test_settings, engine=engine, run_migration_check=True)
    yield application
    engine.dispose()


@pytest.fixture(scope="module")
def client(app):
    with TestClient(app) as test_client:
        yield test_client
