from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from importlib import import_module
import logging
import os
from pathlib import Path
import time

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import BACKEND_ROOT, PROJECT_ROOT, Settings, get_settings, normalize_database_url

MIGRATIONS_ROOT = BACKEND_ROOT / "migrations"
ALEMBIC_INI_PATH = MIGRATIONS_ROOT / "alembic.ini"
MODEL_MODULES = (
    "app.models",
    "app.club_identity.models.reputation",
    "app.fast_cups.repositories.database",
    "app.ingestion.models",
    "app.leagues.repository",
    "app.market.read_models",
    "app.players.read_models",
    "app.regen_universe.models",
    "app.replay_archive.persistence",
    "app.value_engine.read_models",
)
DEFAULT_DATABASE_CONNECT_TIMEOUT_SECONDS = 10
DEFAULT_DATABASE_INIT_RETRIES = 3
DEFAULT_DATABASE_INIT_RETRY_DELAY_SECONDS = 2.0
logger = logging.getLogger(__name__)


def get_database_url() -> str:
    return get_settings().database_url


def load_model_modules() -> None:
    for module_path in MODEL_MODULES:
        import_module(module_path)


def create_database_engine(database_url: str | None = None) -> Engine:
    resolved_url = normalize_database_url(database_url or get_database_url())
    resolved_engine_url = make_url(resolved_url)
    _ensure_sqlite_database_path(resolved_url)
    connect_args = {"check_same_thread": False} if resolved_url.startswith("sqlite") else {}
    engine_kwargs: dict[str, object] = {"connect_args": connect_args}
    if not resolved_url.startswith("sqlite"):
        if "connect_timeout" not in resolved_engine_url.query:
            connect_args["connect_timeout"] = _get_int_env(
                "GTE_DATABASE_CONNECT_TIMEOUT_SECONDS",
                DEFAULT_DATABASE_CONNECT_TIMEOUT_SECONDS,
                minimum=1,
            )
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
    config = Config(str(ALEMBIC_INI_PATH.resolve()))
    config.set_main_option("script_location", str(MIGRATIONS_ROOT.resolve()))
    config.set_main_option("prepend_sys_path", str(PROJECT_ROOT.resolve()))
    config.set_main_option("sqlalchemy.url", normalize_database_url(database_url or get_database_url()))
    return config


def initialize_database_connection(
    engine: Engine | None = None,
    *,
    run_migration_check: bool = True,
) -> Engine:
    database_engine = engine or get_engine()
    max_attempts = _get_int_env("GTE_DATABASE_INIT_RETRIES", DEFAULT_DATABASE_INIT_RETRIES, minimum=1)
    retry_delay_seconds = _get_float_env(
        "GTE_DATABASE_INIT_RETRY_DELAY_SECONDS",
        DEFAULT_DATABASE_INIT_RETRY_DELAY_SECONDS,
        minimum=0.0,
    )

    logger.info(
        "database.initialize.begin engine_url=%s run_migration_check=%s max_attempts=%s",
        database_engine.url.render_as_string(hide_password=True),
        run_migration_check,
        max_attempts,
    )
    logger.info("database.initialize.model_import.begin")
    load_model_modules()
    logger.info("database.initialize.model_import.complete")

    last_error: OperationalError | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info("database.initialize.attempt.begin attempt=%s max_attempts=%s", attempt, max_attempts)
            if run_migration_check:
                logger.info("database.initialize.migration_check.begin attempt=%s", attempt)
                ensure_database_schema_current(database_engine)
                logger.info("database.initialize.migration_check.complete attempt=%s", attempt)
            with database_engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("database.initialize.attempt.complete attempt=%s max_attempts=%s", attempt, max_attempts)
            logger.info("database.initialize.complete")
            return database_engine
        except OperationalError as exc:
            last_error = exc
            logger.warning(
                "database.initialize.attempt.failed attempt=%s max_attempts=%s error=%s",
                attempt,
                max_attempts,
                exc,
            )
            if attempt >= max_attempts:
                break
            if retry_delay_seconds > 0:
                time.sleep(retry_delay_seconds)
        except Exception:
            logger.exception("database.initialize.failed")
            raise

    logger.error("database.initialize.exhausted_retries max_attempts=%s", max_attempts)
    assert last_error is not None
    raise last_error


def ensure_database_schema_current(engine: Engine | None = None) -> tuple[str, ...]:
    load_model_modules()
    database_engine = engine or get_engine()
    config = build_alembic_config(str(database_engine.url))
    script = ScriptDirectory.from_config(config)
    target_head = script.get_current_head()
    target_heads = (target_head,) if target_head is not None else tuple()

    with database_engine.connect() as connection:
        current_heads = tuple(sorted(MigrationContext.configure(connection).get_current_heads()))

    if current_heads != target_heads:
        command.upgrade(config, "head")
        with database_engine.connect() as connection:
            current_heads = tuple(sorted(MigrationContext.configure(connection).get_current_heads()))

    if current_heads != target_heads:
        raise RuntimeError(
            "Database schema is not up to date. "
            f"Current revisions: {current_heads or ('<none>',)}. Expected: {target_heads or ('<none>',)}."
        )

    return current_heads


def get_target_metadata() -> MetaData:
    load_model_modules()
    from app.models import Base

    return Base.metadata


def _ensure_sqlite_database_path(database_url: str) -> None:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        return
    if not url.database or url.database == ":memory:":
        return
    database_path = Path(url.database)
    if not database_path.is_absolute():
        database_path = (Path.cwd() / database_path).resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)


def _get_int_env(name: str, default: int, *, minimum: int | None = None) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        logger.warning("database.config.invalid_int name=%s value=%s default=%s", name, raw_value, default)
        return default
    if minimum is not None and value < minimum:
        logger.warning("database.config.int_below_minimum name=%s value=%s minimum=%s", name, value, minimum)
        return minimum
    return value


def _get_float_env(name: str, default: float, *, minimum: float | None = None) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = float(raw_value)
    except ValueError:
        logger.warning("database.config.invalid_float name=%s value=%s default=%s", name, raw_value, default)
        return default
    if minimum is not None and value < minimum:
        logger.warning("database.config.float_below_minimum name=%s value=%s minimum=%s", name, value, minimum)
        return minimum
    return value


@dataclass(slots=True)
class DatabaseRuntime:
    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]

    @classmethod
    def build(
        cls,
        *,
        settings: Settings | None = None,
        engine: Engine | None = None,
        session_factory: sessionmaker[Session] | None = None,
    ) -> "DatabaseRuntime":
        resolved_settings = settings or get_settings()
        resolved_engine = engine or create_database_engine(resolved_settings.database_url)
        resolved_session_factory = session_factory or create_session_factory(resolved_engine)
        return cls(
            settings=resolved_settings,
            engine=resolved_engine,
            session_factory=resolved_session_factory,
        )

    def initialize(self, *, run_migration_check: bool | None = None) -> Engine:
        return initialize_database_connection(
            self.engine,
            run_migration_check=self.settings.run_migration_check if run_migration_check is None else run_migration_check,
        )

    def get_session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
        finally:
            session.close()

    def ping(self) -> bool:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
