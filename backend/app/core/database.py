from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from importlib import import_module
import logging
import os
from pathlib import Path
import threading
import time

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import BACKEND_ROOT, PROJECT_ROOT, Settings, get_settings, normalize_database_url

MIGRATIONS_ROOT = BACKEND_ROOT / "migrations"
ALEMBIC_INI_PATH = MIGRATIONS_ROOT / "alembic.ini"
MODEL_MODULES = (
    "app.models",
    "app.agents.models",
    "app.ledger.models",
    "app.leaderboards.models",
    "app.matching.models",
    "app.models.economy_governor",
    "app.models.fx_pricing",
    "app.models.player_token_market",
    "app.models.event_backbone",
    "app.models.projections",
    "app.club_finance.models",
    "app.club_identity.models.reputation",
    "app.fast_cups.repositories.database",
    "app.ingestion.models",
    "app.ingestion.real_player_import_models",
    "app.leagues.repository",
    "app.live_ops.models",
    "app.market.read_models",
    "app.orders.models",
    "app.players.read_models",
    "app.predictions.models",
    "app.regen_universe.models",
    "app.replay_archive.persistence",
    "app.team_dynamics.models",
    "app.talent.models",
    "app.value_engine.read_models",
    "app.owner_console.models",
    "app.owner_console.institutional_models",
)
DEFAULT_DATABASE_CONNECT_TIMEOUT_SECONDS = 10
DEFAULT_DATABASE_INIT_RETRIES = 3
DEFAULT_DATABASE_INIT_RETRY_DELAY_SECONDS = 2.0
RUNTIME_SCHEMA_SMOKE_TABLES = (
    "wallets",
    "ledger_entries",
    "ledger_balance_projections",
    "player_share_markets",
    "player_share_events",
    "leaderboard_seasons",
    "leaderboard_player_ratings",
    "leaderboard_match_results",
    "leaderboard_season_snapshots",
    "leaderboard_season_rewards",
    "national_regen_seeds",
    "historical_records",
    "historical_leaderboard_entries",
    "achievements",
    "user_achievements",
    "milestone_progress",
    "user_profiles",
    "user_follows",
    "social_activities",
    "daily_tasks",
    "weekly_tasks",
    "season_pass_seasons",
    "season_pass_rewards",
    "season_pass_missions",
    "user_objective_progress",
    "user_season_progress",
    "user_season_reward_claims",
    "user_season_mission_progress",
    "user_streaks",
)
logger = logging.getLogger(__name__)
_SCHEMA_MIGRATION_LOCK = threading.RLock()
_ENGINE_POOL_STATS: dict[int, dict[str, float | int]] = {}


@lru_cache
def _resolved_model_modules() -> tuple[str, ...]:
    resolved_modules = list(MODEL_MODULES)
    models_package_root = BACKEND_ROOT / "app" / "models"
    for module_path in sorted(models_package_root.glob("*.py")):
        if module_path.stem in {"__init__", "base"}:
            continue
        dotted_path = f"app.models.{module_path.stem}"
        if dotted_path not in resolved_modules:
            resolved_modules.append(dotted_path)
    return tuple(resolved_modules)


def get_database_url() -> str:
    return get_settings().database_url


def get_database_read_url() -> str:
    return get_settings().database_read_url


def load_model_modules() -> None:
    for module_path in _resolved_model_modules():
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
        # TCP keepalives: connect_timeout only bounds the initial handshake, not a
        # connection that goes silently dead afterward (observed on the Supabase
        # transaction-mode pooler, which drops idle connections without a clean
        # FIN/RST). Without these, pool_pre_ping's liveness check can block forever
        # on recv() against a half-open socket instead of detecting the dead
        # connection and reconnecting.
        connect_args.setdefault("keepalives", 1)
        connect_args.setdefault("keepalives_idle", _get_int_env("GTE_DATABASE_KEEPALIVES_IDLE", 30, minimum=1))
        connect_args.setdefault("keepalives_interval", _get_int_env("GTE_DATABASE_KEEPALIVES_INTERVAL", 10, minimum=1))
        connect_args.setdefault("keepalives_count", _get_int_env("GTE_DATABASE_KEEPALIVES_COUNT", 3, minimum=1))
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_recycle"] = _get_int_env("GTE_DB_POOL_RECYCLE", 300, minimum=30)
        engine_kwargs["pool_timeout"] = _get_int_env("GTE_DB_POOL_TIMEOUT", 30, minimum=1)
        # Supabase session-mode pooler limit is about 30 connections, shared by the
        # API and every always-on worker. Read and write URLs that point at the same
        # database reuse one engine (see DatabaseRuntime.build). Do not raise these
        # defaults to hide a leak: size the Render workers explicitly instead.
        engine_kwargs["pool_size"] = _get_int_env("GTE_DB_POOL_SIZE", 3, minimum=1)
        engine_kwargs["max_overflow"] = _get_int_env("GTE_DB_MAX_OVERFLOW", 2, minimum=0)
        # Disable psycopg3 server-side prepared statements.  The Supabase
        # transaction-mode pooler (port 6543) routes each transaction to a
        # potentially different physical backend, so a prepared statement
        # ("_pg3_N") created on one backend is absent on the next -> psycopg
        # raises InvalidSqlStatementName.  prepare_threshold=None makes psycopg
        # never auto-prepare, which is required for transaction-pooled Postgres.
        if "psycopg" in resolved_url and "prepare_threshold" not in resolved_engine_url.query:
            connect_args["prepare_threshold"] = None
    engine = create_engine(resolved_url, **engine_kwargs)
    if isinstance(engine, Engine):
        _install_pool_telemetry(engine)
    return engine


def same_database_target(left: str, right: str) -> bool:
    return normalize_database_url(left) == normalize_database_url(right)


def resolve_read_engine(
    write_engine: Engine,
    *,
    write_url: str,
    read_url: str,
    read_engine: Engine | None = None,
) -> Engine:
    """A read URL that is the primary database must not open a second pool."""

    if read_engine is not None:
        return read_engine
    if same_database_target(write_url, read_url):
        return write_engine
    return create_database_engine(read_url)


def collect_database_pool_telemetry(engine: Engine) -> dict[str, object]:
    """Snapshot pool occupancy. SQLite pools do not expose checkout counters."""

    pool = engine.pool
    stats = dict(_ENGINE_POOL_STATS.get(id(engine)) or {})
    snapshot: dict[str, object] = {
        "dialect": engine.dialect.name,
        "pool_class": type(pool).__name__,
        "checkout_timeouts": int(stats.get("checkout_timeouts", 0) or 0),
        "long_transactions": int(stats.get("long_transactions", 0) or 0),
        "last_checkout_wait_ms": float(stats.get("last_checkout_wait_ms", 0.0) or 0.0),
        "max_checkout_wait_ms": float(stats.get("max_checkout_wait_ms", 0.0) or 0.0),
    }
    timeout = getattr(pool, "_timeout", None)
    if isinstance(timeout, (int, float)):
        snapshot["pool_timeout_seconds"] = timeout
    for method_name, key in (
        ("size", "pool_size"),
        ("checkedout", "checked_out"),
        ("checkedin", "checked_in"),
        ("overflow", "overflow"),
    ):
        method = getattr(pool, method_name, None)
        if not callable(method):
            continue
        try:
            snapshot[key] = method()
        except Exception:
            logger.debug("database.pool_telemetry_unavailable method=%s", method_name, exc_info=True)
    return snapshot


def _install_pool_telemetry(engine: Engine) -> None:
    stats = {
        "checkout_timeouts": 0,
        "long_transactions": 0,
        "last_checkout_wait_ms": 0.0,
        "max_checkout_wait_ms": 0.0,
    }
    _ENGINE_POOL_STATS[id(engine)] = stats
    long_seconds = _get_float_env("GTE_DB_LONG_TRANSACTION_SECONDS", 30.0, minimum=1.0)
    pool = engine.pool
    original_connect = pool.connect

    def timed_connect(*args, **kwargs):
        started = time.monotonic()
        try:
            return original_connect(*args, **kwargs)
        except Exception as exc:
            if exc.__class__.__name__ == "TimeoutError" or "QueuePool limit" in str(exc):
                stats["checkout_timeouts"] = int(stats["checkout_timeouts"]) + 1
                logger.warning(
                    "database.pool_checkout_timeout pool=%s timeout_seconds=%s error=%s",
                    type(pool).__name__,
                    getattr(pool, "_timeout", None),
                    exc,
                )
            raise
        finally:
            waited_ms = (time.monotonic() - started) * 1000.0
            stats["last_checkout_wait_ms"] = waited_ms
            stats["max_checkout_wait_ms"] = max(float(stats["max_checkout_wait_ms"]), waited_ms)

    pool.connect = timed_connect  # type: ignore[method-assign]

    @event.listens_for(engine, "checkin")
    def _note_long_transaction(dbapi_connection, connection_record) -> None:
        started = connection_record.info.pop("gte_checked_out_at", None)
        if started is None:
            return
        held = time.monotonic() - float(started)
        if held >= long_seconds:
            stats["long_transactions"] = int(stats["long_transactions"]) + 1
            logger.warning("database.long_running_transaction held_seconds=%.2f", held)

    @event.listens_for(engine, "checkout")
    def _note_checkout(dbapi_connection, connection_record, connection_proxy) -> None:
        connection_record.info["gte_checked_out_at"] = time.monotonic()


def create_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine or get_engine(),
        autoflush=False,
        expire_on_commit=False,
    )


@lru_cache
def get_engine() -> Engine:
    return create_database_engine()


def create_read_database_engine(database_url: str | None = None) -> Engine:
    return create_database_engine(database_url or get_database_read_url())


@lru_cache
def get_read_engine() -> Engine:
    write_url = get_database_url()
    read_url = get_database_read_url()
    if same_database_target(write_url, read_url):
        return get_engine()
    return create_read_database_engine()


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return create_session_factory()


def create_read_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    return create_session_factory(engine or get_read_engine())


@lru_cache
def get_read_session_factory() -> sessionmaker[Session]:
    return create_read_session_factory()


def get_session() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def get_read_session() -> Iterator[Session]:
    read_session_factory = get_read_session_factory()
    primary_session_factory = get_session_factory()
    try:
        session = read_session_factory()
    except (OperationalError, DBAPIError) as exc:
        logger.warning("database.read_replica_fallback operation=get_read_session error=%s", exc)
        session = primary_session_factory()
    try:
        yield session
    finally:
        session.close()


def run_read_with_primary_fallback(
    *,
    read_session_factory: sessionmaker[Session] | None,
    primary_session_factory: sessionmaker[Session],
    operation_name: str,
    fn,
):
    if read_session_factory is None or read_session_factory is primary_session_factory:
        with primary_session_factory() as session:
            return fn(session)
    try:
        with read_session_factory() as session:
            return fn(session)
    except (OperationalError, DBAPIError) as exc:
        logger.warning(
            "database.read_replica_fallback operation=%s error=%s",
            operation_name,
            exc,
        )
    with primary_session_factory() as session:
        return fn(session)


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
    """Ensure the target database is migrated to the single Alembic head.

    Serialized with an in-process lock because Alembic's ``context`` and ``op``
    proxies are process-global and not thread-safe.
    """
    with _SCHEMA_MIGRATION_LOCK:
        load_model_modules()
        database_engine = engine or get_engine()
        # str(url) masks the password as "***" (SQLAlchemy default), which would make
        # alembic authenticate with an invalid password. Render with the real password.
        config = build_alembic_config(database_engine.url.render_as_string(hide_password=False))
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


def check_runtime_schema_smoke(
    engine: Engine | None = None,
    *,
    required_tables: tuple[str, ...] = RUNTIME_SCHEMA_SMOKE_TABLES,
) -> tuple[str, ...]:
    database_engine = engine or get_engine()
    inspector = inspect(database_engine)
    existing_tables = set(inspector.get_table_names())
    missing_tables = tuple(table_name for table_name in required_tables if table_name not in existing_tables)
    if missing_tables:
        raise RuntimeError("Database schema smoke check failed. Missing tables: " + ", ".join(missing_tables) + ".")
    return required_tables


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
    read_engine: Engine
    read_session_factory: sessionmaker[Session]

    @classmethod
    def build(
        cls,
        *,
        settings: Settings | None = None,
        engine: Engine | None = None,
        session_factory: sessionmaker[Session] | None = None,
        read_engine: Engine | None = None,
        read_session_factory: sessionmaker[Session] | None = None,
    ) -> "DatabaseRuntime":
        resolved_settings = settings or get_settings()
        resolved_engine = engine or create_database_engine(resolved_settings.database_url)
        resolved_session_factory = session_factory or create_session_factory(resolved_engine)
        resolved_read_engine = resolve_read_engine(
            resolved_engine,
            write_url=resolved_settings.database_url,
            read_url=resolved_settings.database_read_url,
            read_engine=read_engine,
        )
        if read_session_factory is not None:
            resolved_read_session_factory = read_session_factory
        elif resolved_read_engine is resolved_engine:
            resolved_read_session_factory = resolved_session_factory
        else:
            resolved_read_session_factory = create_read_session_factory(resolved_read_engine)
        return cls(
            settings=resolved_settings,
            engine=resolved_engine,
            session_factory=resolved_session_factory,
            read_engine=resolved_read_engine,
            read_session_factory=resolved_read_session_factory,
        )

    def initialize(self, *, run_migration_check: bool | None = None) -> Engine:
        return initialize_database_connection(
            self.engine,
            run_migration_check=(
                self.settings.run_migration_check if run_migration_check is None else run_migration_check
            ),
        )

    def get_session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
        finally:
            session.close()

    def get_read_session(self) -> Iterator[Session]:
        try:
            session = self.read_session_factory()
        except (OperationalError, DBAPIError) as exc:
            logger.warning("database.read_replica_fallback operation=DatabaseRuntime.get_read_session error=%s", exc)
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

    def close(self) -> None:
        self.read_engine.dispose()
        if self.read_engine is not self.engine:
            self.engine.dispose()

    def check_schema_smoke(self, *, required_tables: tuple[str, ...] = RUNTIME_SCHEMA_SMOKE_TABLES) -> tuple[str, ...]:
        return check_runtime_schema_smoke(self.engine, required_tables=required_tables)
