from __future__ import annotations

from alembic import command as alembic_command
from types import SimpleNamespace

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
    monkeypatch.setattr(database_module.ScriptDirectory, "from_config", staticmethod(lambda _config: _DummyScriptDirectory()))
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


def test_create_app_registers_world_simulation_routes_without_running_lifespan() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False})
    app = create_app(engine=engine, run_migration_check=False)
    route_paths = {getattr(route, "path", "") for route in app.routes}

    assert "/api/world/cultures" in route_paths


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
