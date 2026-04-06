from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import sys

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

import app.ingestion.models  # noqa: F401
import app.ledger.models  # noqa: F401
import app.matching.models  # noqa: F401
import app.models  # noqa: F401
import app.orders.models  # noqa: F401
import app.players.read_models  # noqa: F401
import app.value_engine.read_models  # noqa: F401
from app.ingestion.demo_bootstrap import DEFAULT_DEMO_PASSWORD
from app.ingestion.dev_cli import (
    bootstrap_demo_database,
    build_parser,
    migrate_database,
    rebuild_demo_market,
    reset_local_database,
    resolve_sqlite_database_path,
    run_backend_server,
    run_pytest,
    run_simulation_tick_database,
    run_simulation_ticks_database,
    seed_all_database,
    seed_demo_liquidity_database,
    seed_world_visibility_database,
)
from app.ingestion.models import Country, Player
from app.matching.models import TradeExecution
from app.models.agent_marketplace import AgentMarketplaceListing
from app.models.federation import Federation
from app.models.national_team import NationalTeamCompetition
from app.models.regen_ecosystem import NationalRegenSeed
from app.models.transfer_market import TransferListing
from app.models.user import User
from app.models.wallet import PaymentEvent
from app.orders.models import Order
from app.value_engine.read_models import PlayerValueSnapshotRecord


def test_reset_local_database_removes_sqlite_database_and_sidecars(tmp_path: Path) -> None:
    database_path = tmp_path / "demo-cli.db"
    wal_path = Path(f"{database_path}-wal")
    shm_path = Path(f"{database_path}-shm")
    journal_path = Path(f"{database_path}-journal")
    for path in (database_path, wal_path, shm_path, journal_path):
        path.write_text("demo", encoding="utf-8")

    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    parsed_args = build_parser().parse_args(["reset-db", "--database-url", database_url])

    assert parsed_args.command == "reset-db"
    assert resolve_sqlite_database_path(database_url) == database_path.resolve()

    removed_paths = reset_local_database(database_url)

    assert set(removed_paths) == {
        database_path.resolve(),
        wal_path.resolve(),
        shm_path.resolve(),
        journal_path.resolve(),
    }
    assert all(not path.exists() for path in (database_path, wal_path, shm_path, journal_path))


def test_bootstrap_demo_database_seeds_file_backed_sqlite(tmp_path: Path) -> None:
    database_path = tmp_path / "seeded-demo.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"

    result = bootstrap_demo_database(
        database_url=database_url,
        player_count=10,
        provider="cli-demo",
        signal_provider="cli-demo-signals",
        password=DEFAULT_DEMO_PASSWORD,
        seed=20260311,
        batch_size=5,
        reset_db=True,
    )

    assert result["migration_heads"]
    assert result["seed_summary"]["players_seeded"] == 10
    assert result["seed_summary"]["value_snapshots_seeded"] == 20
    assert result["seed_summary"]["holdings_seeded"] == 5

    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        with SessionLocal() as session:
            assert session.scalar(select(func.count()).select_from(User)) == 3
            assert (
                session.scalar(select(func.count()).select_from(Player).where(Player.source_provider == "cli-demo"))
                == 10
            )
            assert session.scalar(select(func.count()).select_from(PaymentEvent)) == 3
            assert session.scalar(select(func.count()).select_from(PlayerValueSnapshotRecord)) == 20
    finally:
        engine.dispose()


def test_seed_demo_liquidity_database_seeds_orders_and_trade_history(tmp_path: Path) -> None:
    database_path = tmp_path / "liquidity-demo.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    bootstrap_demo_database(
        database_url=database_url,
        player_count=10,
        provider="cli-demo",
        signal_provider="cli-demo-signals",
        password=DEFAULT_DEMO_PASSWORD,
        seed=20260311,
        batch_size=5,
        reset_db=True,
    )

    summary = seed_demo_liquidity_database(
        database_url=database_url,
        seed=20260311,
        liquid_player_count=3,
        illiquid_player_count=1,
    )

    assert summary["player_count"] == 4
    assert summary["buy_orders_seeded"] > 0
    assert summary["sell_orders_seeded"] > 0
    assert summary["trade_executions_seeded"] > 0

    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        with SessionLocal() as session:
            assert session.scalar(select(func.count()).select_from(Order)) > 0
            assert session.scalar(select(func.count()).select_from(TradeExecution)) > 0
    finally:
        engine.dispose()


def test_run_simulation_tick_database_writes_expected_records(tmp_path: Path) -> None:
    database_path = tmp_path / "tick-demo.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    rebuild_demo_market(
        database_url=database_url,
        player_count=10,
        provider="cli-demo",
        signal_provider="cli-demo-signals",
        password=DEFAULT_DEMO_PASSWORD,
        seed=20260311,
        batch_size=5,
        liquid_player_count=3,
        illiquid_player_count=1,
    )

    summary = run_simulation_tick_database(
        database_url=database_url,
        tick_number=2,
        seed=20260311,
        liquid_player_count=3,
        illiquid_player_count=1,
    )

    assert summary["tick_number"] == 2
    assert summary["orders_created"] > 0
    assert summary["trade_executions_created"] > 0
    assert summary["players_touched"]


def test_rebuild_demo_market_seeds_world_visibility_counts(tmp_path: Path) -> None:
    database_path = tmp_path / "rebuild-world-visibility.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"

    result = rebuild_demo_market(
        database_url=database_url,
        player_count=10,
        provider="cli-demo",
        signal_provider="cli-demo-signals",
        password=DEFAULT_DEMO_PASSWORD,
        seed=20260311,
        batch_size=5,
        liquid_player_count=3,
        illiquid_player_count=1,
    )

    assert result["world_visibility_seed"]["marketplace_listing_count"] > 0
    assert result["world_visibility_seed"]["transfer_listing_count"] > 0
    assert result["world_visibility_seed"]["federation_count"] > 0
    assert result["world_visibility_seed"]["national_team_competition_count"] > 0

    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        with SessionLocal() as session:
            assert session.scalar(select(func.count()).select_from(AgentMarketplaceListing)) > 0
            assert session.scalar(select(func.count()).select_from(TransferListing)) > 0
            assert session.scalar(select(func.count()).select_from(Federation)) > 0
            assert session.scalar(select(func.count()).select_from(NationalTeamCompetition)) > 0
    finally:
        engine.dispose()


def test_seed_world_visibility_database_refreshes_bootstrapped_db(tmp_path: Path) -> None:
    database_path = tmp_path / "seed-world-visibility.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"

    bootstrap_demo_database(
        database_url=database_url,
        player_count=10,
        provider="cli-demo",
        signal_provider="cli-demo-signals",
        password=DEFAULT_DEMO_PASSWORD,
        seed=20260311,
        batch_size=5,
        reset_db=True,
        with_liquidity=True,
        liquid_player_count=3,
        illiquid_player_count=1,
    )

    summary = seed_world_visibility_database(
        database_url=database_url,
        provider="cli-demo",
    )
    second_summary = seed_world_visibility_database(
        database_url=database_url,
        provider="cli-demo",
    )

    assert summary["marketplace_listing_count"] > 0
    assert summary["transfer_listing_count"] > 0
    assert summary["federation_count"] > 0
    assert summary["national_team_competition_count"] > 0
    assert second_summary["marketplace_listing_count"] == summary["marketplace_listing_count"]
    assert second_summary["transfer_listing_count"] == summary["transfer_listing_count"]
    assert second_summary["federation_count"] == summary["federation_count"]
    assert second_summary["national_team_competition_count"] == summary["national_team_competition_count"]


def test_seed_world_visibility_database_skips_players_with_missing_country_rows(tmp_path: Path) -> None:
    database_path = tmp_path / "seed-world-visibility-missing-country.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"

    bootstrap_demo_database(
        database_url=database_url,
        player_count=12,
        provider="cli-demo",
        signal_provider="cli-demo-signals",
        password=DEFAULT_DEMO_PASSWORD,
        seed=20260311,
        batch_size=6,
        reset_db=True,
        with_liquidity=True,
        liquid_player_count=3,
        illiquid_player_count=1,
    )

    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        with SessionLocal() as session:
            player = session.scalar(
                select(Player)
                .where(Player.source_provider == "cli-demo", Player.country_id.is_not(None))
                .order_by(Player.market_value_eur.desc().nullslast(), Player.id.asc())
                .limit(1)
            )
            assert player is not None
            assert player.country_id is not None
            country = session.get(Country, player.country_id)
            assert country is not None
            session.delete(country)
            session.commit()

        summary = seed_world_visibility_database(
            database_url=database_url,
            provider="cli-demo",
        )
    finally:
        engine.dispose()

    assert summary["marketplace_listing_count"] > 0
    assert summary["transfer_listing_count"] > 0
    assert summary["federation_count"] > 0
    assert summary["national_team_competition_count"] > 0


def test_seed_world_visibility_database_prefers_canonical_country_codes(tmp_path: Path) -> None:
    database_path = tmp_path / "seed-world-visibility-country-preference.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"

    bootstrap_demo_database(
        database_url=database_url,
        player_count=12,
        provider="cli-demo",
        signal_provider="cli-demo-signals",
        password=DEFAULT_DEMO_PASSWORD,
        seed=20260311,
        batch_size=6,
        reset_db=True,
        with_liquidity=True,
        liquid_player_count=3,
        illiquid_player_count=1,
    )

    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        with SessionLocal() as session:
            session.add_all(
                [
                    Country(
                        source_provider="cli-duplicate",
                        provider_external_id="dup-nigeria",
                        name="Nigeria",
                        alpha2_code=None,
                        alpha3_code="NPFL",
                        fifa_code=None,
                        is_enabled_for_universe=True,
                    ),
                    Country(
                        source_provider="cli-duplicate",
                        provider_external_id="dup-brazil",
                        name="Brazil",
                        alpha2_code=None,
                        alpha3_code="BRA1",
                        fifa_code=None,
                        is_enabled_for_universe=True,
                    ),
                    Country(
                        source_provider="cli-duplicate",
                        provider_external_id="dup-spain",
                        name="Spain",
                        alpha2_code=None,
                        alpha3_code="ES1",
                        fifa_code=None,
                        is_enabled_for_universe=True,
                    ),
                ]
            )
            session.commit()

        summary = seed_world_visibility_database(
            database_url=database_url,
            provider="cli-demo",
        )
    finally:
        engine.dispose()

    assert summary["marketplace_listing_count"] > 0
    assert summary["transfer_listing_count"] > 0
    assert summary["federation_count"] > 0
    assert summary["national_team_competition_count"] > 0


def test_seed_all_database_is_idempotent_and_populates_backend_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "seed-all.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"

    first = seed_all_database(
        database_url=database_url,
        player_count=12,
        provider="cli-demo",
        signal_provider="cli-demo-signals",
        password=DEFAULT_DEMO_PASSWORD,
        seed=20260311,
        batch_size=6,
    )
    second = seed_all_database(
        database_url=database_url,
        player_count=12,
        provider="cli-demo",
        signal_provider="cli-demo-signals",
        password=DEFAULT_DEMO_PASSWORD,
        seed=20260311,
        batch_size=6,
    )

    assert first["seed_summary"]["players_seeded"] == 12
    assert second["seed_summary"]["players_seeded"] == first["seed_summary"]["players_seeded"]
    assert second["world_visibility_seed"]["marketplace_listing_count"] == first["world_visibility_seed"]["marketplace_listing_count"]
    assert second["world_visibility_seed"]["transfer_listing_count"] == first["world_visibility_seed"]["transfer_listing_count"]
    assert second["world_visibility_seed"]["federation_count"] == first["world_visibility_seed"]["federation_count"]
    assert second["world_visibility_seed"]["national_team_competition_count"] == first["world_visibility_seed"]["national_team_competition_count"]

    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        with SessionLocal() as session:
            assert session.scalar(select(func.count()).select_from(Player).where(Player.source_provider == "cli-demo")) == 12
            assert session.scalar(select(func.count()).select_from(AgentMarketplaceListing)) > 0
            assert session.scalar(select(func.count()).select_from(TransferListing)) > 0
            assert session.scalar(select(func.count()).select_from(Federation)) > 0
            assert session.scalar(select(func.count()).select_from(NationalTeamCompetition)) > 0
            assert session.scalar(select(func.count()).select_from(NationalRegenSeed)) > 0
    finally:
        engine.dispose()


def test_seed_all_module_runs_from_repo_root(tmp_path: Path) -> None:
    database_path = tmp_path / "seed-all-module.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    project_root = Path(__file__).resolve().parents[3]

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.bootstrap.seed_all",
            "--database-url",
            database_url,
            "--player-count",
            "10",
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["database_url"] == database_url
    assert payload["world_visibility_seed"]["marketplace_listing_count"] > 0
    assert payload["world_visibility_seed"]["transfer_listing_count"] > 0


def test_run_simulation_ticks_database_is_deterministic_for_same_seed(tmp_path: Path) -> None:
    first_database_url = f"sqlite+pysqlite:///{(tmp_path / 'tick-seed-first.db').as_posix()}"
    second_database_url = f"sqlite+pysqlite:///{(tmp_path / 'tick-seed-second.db').as_posix()}"

    rebuild_kwargs = {
        "player_count": 10,
        "provider": "cli-demo",
        "signal_provider": "cli-demo-signals",
        "password": DEFAULT_DEMO_PASSWORD,
        "seed": 20260311,
        "batch_size": 5,
        "liquid_player_count": 3,
        "illiquid_player_count": 1,
    }

    rebuild_demo_market(database_url=first_database_url, **rebuild_kwargs)
    rebuild_demo_market(database_url=second_database_url, **rebuild_kwargs)

    first = run_simulation_ticks_database(
        database_url=first_database_url,
        tick_count=3,
        start_tick=1,
        seed=20260311,
        liquid_player_count=3,
        illiquid_player_count=1,
    )
    second = run_simulation_ticks_database(
        database_url=second_database_url,
        tick_count=3,
        start_tick=1,
        seed=20260311,
        liquid_player_count=3,
        illiquid_player_count=1,
    )

    assert _stable_tick_projection(first_database_url, first) == _stable_tick_projection(second_database_url, second)


def test_run_pytest_defaults_to_ingestion_suite(monkeypatch) -> None:
    observed: dict[str, object] = {}

    def fake_run(command, cwd, check):
        observed["command"] = command
        observed["cwd"] = cwd
        observed["check"] = check
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("app.ingestion.dev_cli.subprocess.run", fake_run)

    result = run_pytest(())

    assert result == 0
    assert observed["command"] == [sys.executable, "-m", "pytest", "backend/tests/ingestion"]


def test_run_backend_server_invokes_uvicorn(monkeypatch) -> None:
    observed: dict[str, object] = {}

    def fake_run(command, cwd, check, env):
        observed["command"] = command
        observed["cwd"] = cwd
        observed["check"] = check
        observed["env"] = env
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("app.ingestion.dev_cli.subprocess.run", fake_run)

    result = run_backend_server(
        database_url="sqlite+pysqlite:///demo.db",
        host="127.0.0.1",
        port=9000,
        reload_enabled=True,
        demo_simulation=True,
        demo_bootstrap=False,
        demo_seed_liquidity_on_boot=False,
        demo_player_count=12,
        simulation_seed=20260311,
        liquid_player_count=3,
        illiquid_player_count=1,
    )

    assert result == 0
    assert observed["command"] == [
        sys.executable,
        "-m",
        "uvicorn",
        "app.simulation.app_factory:create_demo_simulation_app",
        "--host",
        "127.0.0.1",
        "--port",
        "9000",
        "--factory",
        "--reload",
    ]
    assert observed["env"]["PYTHONPATH"].split(os.pathsep)[0].endswith("backend")
    assert observed["env"]["GTE_DEMO_SIMULATION_ENABLED"] == "1"
    assert observed["env"]["GTE_DEMO_SIMULATION_SEED_ON_BOOT"] == "0"


def test_build_parser_help_includes_demo_operator_examples() -> None:
    help_output = build_parser().format_help()

    assert "Fresh demo market:" in help_output
    assert "rebuild-demo-market --seed 20260311" in help_output
    assert "seed-world-visibility --seed 20260311" in help_output
    assert "simulation-ticks --count 5 --start-tick 1 --seed 20260311" in help_output


def test_build_parser_supports_required_dev_commands() -> None:
    parser = build_parser()

    assert parser.parse_args(["reset-db"]).command == "reset-db"
    assert parser.parse_args(["migrate"]).command == "migrate"
    assert parser.parse_args(["seed-demo"]).command == "seed-demo"
    assert parser.parse_args(["bootstrap-demo"]).command == "bootstrap-demo"
    assert parser.parse_args(["seed-demo-liquidity"]).command == "seed-demo-liquidity"
    assert parser.parse_args(["seed-world-visibility"]).command == "seed-world-visibility"
    assert parser.parse_args(["simulation-tick"]).command == "simulation-tick"
    assert parser.parse_args(["simulation-ticks"]).command == "simulation-ticks"
    assert parser.parse_args(["rebuild-demo-market"]).command == "rebuild-demo-market"
    assert parser.parse_args(["runserver"]).command == "runserver"
    assert parser.parse_args(["test"]).command == "test"


def test_migrate_database_creates_schema_heads_for_sqlite_file(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'migrated-demo.db').as_posix()}"

    heads = migrate_database(database_url)

    assert heads


def _stable_tick_projection(database_url: str, summary: dict[str, object]) -> dict[str, object]:
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        with SessionLocal() as session:
            total_orders = session.scalar(select(func.count()).select_from(Order))
            total_trade_executions = session.scalar(select(func.count()).select_from(TradeExecution))
    finally:
        engine.dispose()

    return {
        "tick_count": summary["tick_count"],
        "start_tick": summary["start_tick"],
        "total_orders": total_orders,
        "total_trade_executions": total_trade_executions,
        "summaries": [
            {
                "tick_number": tick["tick_number"],
                "orders_created": tick["orders_created"],
                "trade_executions_created": tick["trade_executions_created"],
                "players_touched_count": len(tick["players_touched"]),
            }
            for tick in summary["summaries"]
        ],
    }
