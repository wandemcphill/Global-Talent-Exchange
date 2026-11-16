from __future__ import annotations

from contextlib import contextmanager
import runpy
import threading
import time
from types import SimpleNamespace

from alembic.autogenerate import api as alembic_autogenerate
from alembic import command as alembic_command
from alembic.migration import MigrationContext
from alembic.runtime.environment import EnvironmentContext
from alembic.script import ScriptDirectory
import sqlalchemy
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError

from app.core import database as database_module
from app.main import create_app


def test_ensure_database_schema_current_upgrades_single_head(monkeypatch, tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'migration-heads.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})

    class _DummyScriptDirectory:
        def get_current_head(self) -> str:
            return "rev-a"

    current_heads = [tuple(), ("rev-a",)]

    class _DummyMigrationContext:
        @staticmethod
        def configure(_connection):
            class _ConfiguredContext:
                def get_current_heads(self) -> tuple[str, ...]:
                    return current_heads.pop(0)

            return _ConfiguredContext()

    upgrade_targets: list[str] = []

    monkeypatch.setattr(database_module, "load_model_modules", lambda: None)
    monkeypatch.setattr(database_module, "build_alembic_config", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        database_module.ScriptDirectory, "from_config", staticmethod(lambda _config: _DummyScriptDirectory())
    )
    monkeypatch.setattr(database_module, "MigrationContext", _DummyMigrationContext)
    monkeypatch.setattr(
        database_module,
        "command",
        SimpleNamespace(upgrade=lambda _config, target: upgrade_targets.append(target)),
    )

    heads = database_module.ensure_database_schema_current(engine)

    assert upgrade_targets == ["head"]
    assert heads == ("rev-a",)


def test_history_engagement_schema_repair_restores_missing_season_pass_tables(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'history-engagement-repair.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    config = database_module.build_alembic_config(database_url)
    repair_target = "20260330_0078_user_role_width_repair"
    dropped_tables = (
        "user_season_mission_progress",
        "user_season_reward_claims",
        "user_season_progress",
        "season_pass_missions",
        "season_pass_rewards",
        "season_pass_seasons",
    )

    alembic_command.upgrade(config, repair_target)

    with engine.begin() as connection:
        for table_name in dropped_tables:
            connection.execute(text(f"DROP TABLE IF EXISTS {table_name}"))

    alembic_command.upgrade(config, "head")

    table_inspector = inspect(engine)
    for table_name in dropped_tables:
        assert table_inspector.has_table(table_name)

    checked_tables = database_module.check_runtime_schema_smoke(engine)
    assert "season_pass_seasons" in checked_tables
    assert "season_pass_rewards" in checked_tables
    assert "season_pass_missions" in checked_tables


def test_head_upgrade_materializes_model_tables_and_columns(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'migration-integrity.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})

    try:
        config = database_module.build_alembic_config(database_url)
        script = database_module.ScriptDirectory.from_config(config)

        assert script.get_heads() == [script.get_current_head()]

        alembic_command.upgrade(config, "head")

        metadata = database_module.get_target_metadata()
        table_inspector = inspect(engine)
        missing_tables: list[str] = []
        missing_columns: list[str] = []

        for table in metadata.sorted_tables:
            if not table_inspector.has_table(table.name):
                missing_tables.append(table.name)
                continue

            database_columns = {column["name"] for column in table_inspector.get_columns(table.name)}
            missing_columns.extend(
                f"{table.name}.{column.name}" for column in table.columns if column.name not in database_columns
            )

        assert not missing_tables, "Missing migrated tables: " + ", ".join(sorted(missing_tables))
        assert not missing_columns, "Missing migrated columns: " + ", ".join(sorted(missing_columns))
    finally:
        engine.dispose()


def test_head_upgrade_has_no_unmapped_tables_or_columns(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'migration-drift-coverage.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})

    try:
        config = database_module.build_alembic_config(database_url)
        alembic_command.upgrade(config, "head")

        metadata = database_module.get_target_metadata()
        with engine.connect() as connection:
            context = MigrationContext.configure(
                connection=connection,
                opts={"target_metadata": metadata, "compare_type": True},
            )
            diffs = alembic_autogenerate.compare_metadata(context, metadata)

        unmapped_tables = sorted(
            diff[1].name for diff in diffs if isinstance(diff, tuple) and diff[0] == "remove_table"
        )
        unmapped_columns = sorted(
            f"{diff[2]}.{diff[3].name}" for diff in diffs if isinstance(diff, tuple) and diff[0] == "remove_column"
        )
        structural_drift: list[str] = []
        for diff in diffs:
            if isinstance(diff, list):
                structural_drift.extend(
                    f"{item[2]}.{item[3]}:{item[0]}" for item in diff if item[0] == "modify_nullable"
                )
                continue
            if diff[0] == "remove_fk":
                structural_drift.append(
                    f"{diff[1].table.name}.{','.join(column.name for column in diff[1].columns)}:remove_fk"
                )

        assert not unmapped_tables, "Migrated tables missing from target metadata: " + ", ".join(unmapped_tables)
        assert not unmapped_columns, "Migrated columns missing from target metadata: " + ", ".join(unmapped_columns)
        assert not structural_drift, "Unexpected structural drift after head upgrade: " + ", ".join(
            sorted(structural_drift)
        )
    finally:
        engine.dispose()


def test_head_upgrade_has_expected_index_coverage(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'migration-index-coverage.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})

    try:
        config = database_module.build_alembic_config(database_url)
        alembic_command.upgrade(config, "head")

        metadata = database_module.get_target_metadata()
        inspector = inspect(engine)
        actual_unique: dict[str, set[tuple[str, ...]]] = {}
        actual_indexes: dict[str, set[tuple[str, ...]]] = {}

        for table_name in inspector.get_table_names():
            actual_unique[table_name] = {
                tuple(constraint.get("column_names") or ())
                for constraint in inspector.get_unique_constraints(table_name)
                if constraint.get("column_names")
            }
            actual_indexes[table_name] = set()
            for index in inspector.get_indexes(table_name):
                columns = tuple(index.get("column_names") or ())
                if not columns:
                    continue
                if index.get("unique"):
                    actual_unique[table_name].add(columns)
                else:
                    actual_indexes[table_name].add(columns)

        missing_indexes: list[str] = []
        for table in metadata.sorted_tables:
            available_columns = actual_indexes.get(table.name, set()) | actual_unique.get(table.name, set())
            for index in sorted(table.indexes, key=lambda item: item.name or ""):
                columns = tuple(column.name for column in index.columns)
                if not columns or index.unique:
                    continue
                if columns not in available_columns:
                    missing_indexes.append(f"{table.name}.{index.name}:{','.join(columns)}")

        assert not missing_indexes, "Missing migrated indexes: " + ", ".join(sorted(missing_indexes))
    finally:
        engine.dispose()


def test_create_app_registers_world_simulation_routes_without_running_lifespan() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False})
    app = create_app(engine=engine, run_migration_check=False)
    route_paths = {getattr(route, "path", "") for route in app.routes}

    assert any("/world/cultures" in path for path in route_paths)


def test_initialize_database_connection_retries_operational_error(monkeypatch) -> None:
    url = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}).url
    attempts = {"count": 0}

    class _Connection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def execute(self, _statement) -> None:
            return None

    def _connect():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise OperationalError("SELECT 1", None, RuntimeError("db unavailable"))
        return _Connection()

    engine = SimpleNamespace(url=url, connect=_connect)

    monkeypatch.setattr(database_module, "load_model_modules", lambda: None)
    monkeypatch.setattr(database_module, "ensure_database_schema_current", lambda _engine: ("rev-a",))
    monkeypatch.setattr(database_module.time, "sleep", lambda _seconds: None)
    monkeypatch.setenv("GTE_DATABASE_INIT_RETRIES", "3")
    monkeypatch.setenv("GTE_DATABASE_INIT_RETRY_DELAY_SECONDS", "0")

    initialized_engine = database_module.initialize_database_connection(engine=engine, run_migration_check=True)

    assert initialized_engine is engine
    assert attempts["count"] == 3


def test_ensure_database_schema_current_serializes_concurrent_threads(monkeypatch, tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'concurrent-heads.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    state_lock = threading.Lock()
    state = {"current_head": tuple(), "active_upgrades": 0, "max_active_upgrades": 0, "upgrade_calls": 0}

    class _DummyScriptDirectory:
        def get_current_head(self) -> str:
            return "rev-a"

    class _DummyMigrationContext:
        @staticmethod
        def configure(_connection):
            class _ConfiguredContext:
                def get_current_heads(self) -> tuple[str, ...]:
                    with state_lock:
                        return state["current_head"]

            return _ConfiguredContext()

    def _upgrade(_config, _target: str) -> None:
        with state_lock:
            state["active_upgrades"] += 1
            state["max_active_upgrades"] = max(state["max_active_upgrades"], state["active_upgrades"])
            state["upgrade_calls"] += 1
        time.sleep(0.05)
        with state_lock:
            state["current_head"] = ("rev-a",)
            state["active_upgrades"] -= 1

    monkeypatch.setattr(database_module, "load_model_modules", lambda: None)
    monkeypatch.setattr(database_module, "build_alembic_config", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        database_module.ScriptDirectory, "from_config", staticmethod(lambda _config: _DummyScriptDirectory())
    )
    monkeypatch.setattr(database_module, "MigrationContext", _DummyMigrationContext)
    monkeypatch.setattr(database_module, "command", SimpleNamespace(upgrade=_upgrade))

    barrier = threading.Barrier(4)
    results: list[tuple[str, ...]] = []
    errors: list[BaseException] = []

    def _worker() -> None:
        try:
            barrier.wait(timeout=5)
            results.append(database_module.ensure_database_schema_current(engine))
        except BaseException as exc:  # pragma: no cover - surfaced by assertion below
            errors.append(exc)

    threads = [threading.Thread(target=_worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
        assert not thread.is_alive()

    engine.dispose()

    assert not errors
    assert state["max_active_upgrades"] == 1
    assert state["upgrade_calls"] == 1
    assert results == [("rev-a",)] * 4


def test_alembic_env_acquires_postgres_advisory_lock_during_online_migrations(monkeypatch) -> None:
    config = database_module.build_alembic_config("postgresql+psycopg://user:pass@localhost:5432/gtex")
    script = ScriptDirectory.from_config(config)
    events: list[str] = []

    class _FakeConnection:
        dialect = SimpleNamespace(name="postgresql")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def execute(self, statement, params=None) -> None:
            sql_text = str(statement)
            if "pg_advisory_xact_lock" in sql_text:
                assert params and isinstance(params.get("lock_id"), int)
                events.append("lock")

        def commit(self) -> None:
            events.append("commit")

    class _FakeEngine:
        def connect(self):
            return _FakeConnection()

    class _FakeInspector:
        @staticmethod
        def has_table(table_name: str) -> bool:
            assert table_name == "alembic_version"
            events.append("inspect_version_table")
            return True

        @staticmethod
        def get_columns(table_name: str):
            assert table_name == "alembic_version"
            return [{"name": "version_num", "type": SimpleNamespace(length=255)}]

    @contextmanager
    def _begin_transaction(_self):
        events.append("begin_transaction")
        yield

    monkeypatch.setattr(sqlalchemy, "create_engine", lambda *_args, **_kwargs: _FakeEngine())
    monkeypatch.setattr(sqlalchemy, "inspect", lambda _connection: _FakeInspector())
    monkeypatch.setattr(EnvironmentContext, "configure", lambda *_args, **_kwargs: events.append("configure"))
    monkeypatch.setattr(EnvironmentContext, "begin_transaction", _begin_transaction)
    monkeypatch.setattr(EnvironmentContext, "run_migrations", lambda _self: events.append("run_migrations"))

    with EnvironmentContext(config, script):
        runpy.run_path(str(database_module.MIGRATIONS_ROOT / "env.py"), run_name="test_env")

    assert events == [
        "lock",
        "inspect_version_table",
        "commit",
        "configure",
        "begin_transaction",
        "lock",
        "run_migrations",
    ]
