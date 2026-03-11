from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
MIGRATIONS_ROOT = BACKEND_ROOT / "migrations"
ALEMBIC_INI_PATH = MIGRATIONS_ROOT / "alembic.ini"
DATABASE_URL_ENV = "DATABASE_URL"
DEFAULT_DATABASE_URL = f"sqlite:///{(PROJECT_ROOT / 'gte_backend.db').as_posix()}"


def get_database_url() -> str:
    return os.getenv(DATABASE_URL_ENV, DEFAULT_DATABASE_URL)


def create_database_engine(database_url: str | None = None) -> Engine:
    resolved_url = database_url or get_database_url()
    connect_args = {"check_same_thread": False} if resolved_url.startswith("sqlite") else {}
    engine_kwargs: dict[str, object] = {"connect_args": connect_args}
    if not resolved_url.startswith("sqlite"):
        engine_kwargs["pool_pre_ping"] = True
    return create_engine(resolved_url, **engine_kwargs)


def create_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine or get_engine(),
        autoflush=False,
        expire_on_commit=False,
    )


@lru_cache
def get_engine() -> Engine:
    return create_database_engine()


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return create_session_factory()


def get_session() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def build_alembic_config(database_url: str | None = None) -> Config:
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(MIGRATIONS_ROOT))
    config.set_main_option("prepend_sys_path", str(PROJECT_ROOT))
    config.set_main_option("sqlalchemy.url", database_url or get_database_url())
    return config


def ensure_database_schema_current(engine: Engine | None = None) -> tuple[str, ...]:
    database_engine = engine or get_engine()
    config = build_alembic_config(str(database_engine.url))
    script = ScriptDirectory.from_config(config)
    target_heads = tuple(script.get_heads())

    with database_engine.connect() as connection:
        current_heads = MigrationContext.configure(connection).get_current_heads()

    if current_heads != target_heads:
        command.upgrade(config, "head")
        with database_engine.connect() as connection:
            current_heads = MigrationContext.configure(connection).get_current_heads()

    if current_heads != target_heads:
        raise RuntimeError(
            "Database schema is not up to date. "
            f"Current revisions: {current_heads or ('<none>',)}. Expected: {target_heads or ('<none>',)}."
        )

    return current_heads
