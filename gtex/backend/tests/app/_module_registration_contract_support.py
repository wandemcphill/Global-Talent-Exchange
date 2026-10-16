from __future__ import annotations

import importlib
import os
from pathlib import Path
import shutil
import sys
from unittest.mock import patch
from uuid import uuid4

import pytest


def _create_sqlite_engine(database_url: str):
    from sqlalchemy import create_engine

    return create_engine(database_url, connect_args={"check_same_thread": False})


def _load_config_module():
    from app.core import config

    return config


def _load_database_module():
    from app.core import database

    return database


def _copy_sqlite_database(template_path: Path, database_path: Path) -> str:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template_path, database_path)
    return f"sqlite+pysqlite:///{database_path.as_posix()}"


@pytest.fixture(scope="session")
def migrated_sqlite_template(tmp_path_factory):
    database_root = tmp_path_factory.mktemp(f"gte_migrated_template_{uuid4().hex}")
    database_path = database_root / "app_template.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    engine = _create_sqlite_engine(database_url)
    database = _load_database_module()

    try:
        database.ensure_database_schema_current(engine)
        yield database_path
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def mounted_app_runtime(tmp_path_factory, migrated_sqlite_template):
    temp_root = tmp_path_factory.mktemp(f"gte_module_registration_{uuid4().hex}")
    database_path = temp_root / "app.db"
    database_url = _copy_sqlite_database(migrated_sqlite_template, database_path)
    media_root = temp_root / "media"
    media_root.mkdir(parents=True, exist_ok=True)
    engine = _create_sqlite_engine(database_url)
    managed_env = {
        "DATABASE_URL": database_url,
        "GTE_DATABASE_URL": database_url,
        "GTE_MEDIA_STORAGE_ROOT": str(media_root),
        "RUN_STARTUP_SEEDING": "false",
        "SKIP_SCHEMA_CHECK": "1",
        "GTE_DISTRIBUTED_RATE_LIMIT_ENABLED": "false",
    }
    previous_env = {key: os.environ.get(key) for key in managed_env}
    config = None

    try:
        for key, value in managed_env.items():
            os.environ[key] = value
        config = _load_config_module()
        database = _load_database_module()
        # app.main can resolve settings during import, so the test env must be
        # installed before importing the real application module. Reload only
        # when another test imported app.main earlier in the same session.
        config.reset_settings_cache()
        existing_app_main = sys.modules.get("app.main")
        if existing_app_main is None:
            app_main = importlib.import_module("app.main")
        else:
            app_main = importlib.reload(existing_app_main)
        yield {
            "database_url": database_url,
            "media_root": media_root,
            "app_main": app_main,
        }
    finally:
        for key, previous_value in previous_env.items():
            if previous_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous_value
        if config is not None:
            config.reset_settings_cache()
        engine.dispose()
        try:
            database_path.unlink()
        except FileNotFoundError:
            pass
        except PermissionError:
            pass
        shutil.rmtree(media_root, ignore_errors=True)


@pytest.fixture(scope="module")
def mounted_app(mounted_app_runtime):
    config = _load_config_module()
    settings = config.load_settings()
    engine = _create_sqlite_engine(mounted_app_runtime["database_url"])

    try:
        with patch.object(mounted_app_runtime["app_main"], "_start_deferred_startup", autospec=True):
            application = mounted_app_runtime["app_main"].create_app(
                settings=settings,
                engine=engine,
                run_migration_check=False,
            )
            application.state.metrics.refresh_from_database = lambda: None
            application.state.container.metrics.refresh_from_database = lambda: None
            yield application
    finally:
        engine.dispose()


@pytest.fixture(scope="module")
def mounted_app_client(mounted_app):
    from fastapi.testclient import TestClient

    # Reuse one TestClient per contract module so each parametrized case does
    # not pay full FastAPI lifespan startup/shutdown cost.
    with TestClient(mounted_app) as client:
        yield client


@pytest.fixture(scope="module")
def mounted_app_contract_snapshot(mounted_app_runtime):
    config = _load_config_module()
    settings = config.load_settings()
    engine = _create_sqlite_engine(mounted_app_runtime["database_url"])

    try:
        with patch.object(mounted_app_runtime["app_main"], "_start_deferred_startup", autospec=True):
            application = mounted_app_runtime["app_main"].create_app(
                settings=settings,
                engine=engine,
                run_migration_check=False,
            )
            application.state.metrics.refresh_from_database = lambda: None
            application.state.container.metrics.refresh_from_database = lambda: None

            yield {
                "openapi_paths": set(application.openapi()["paths"]),
                "registered_modules": set(application.state.domain_modules),
            }
    finally:
        engine.dispose()


def request_route(
    mounted_app_client,
    method: str,
    path: str,
    json_body: dict[str, object] | None = None,
    params: dict[str, object] | None = None,
):
    request_kwargs: dict[str, object] = {}
    if json_body is not None:
        request_kwargs["json"] = json_body
    if params is not None:
        request_kwargs["params"] = params

    return mounted_app_client.request(method, path, **request_kwargs)
