from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Sequence

from sqlalchemy.engine.url import make_url

from backend.app.core.config import DEFAULT_DATABASE_URL, PROJECT_ROOT
from backend.app.core.database import create_database_engine, create_session_factory, ensure_database_schema_current
from backend.app.ingestion.demo_bootstrap import (
    DEFAULT_DEMO_BATCH_SIZE,
    DEFAULT_DEMO_PASSWORD,
    DEFAULT_DEMO_PLAYER_COUNT,
    DEFAULT_DEMO_PROVIDER_NAME,
    DEFAULT_DEMO_RANDOM_SEED,
    DEFAULT_DEMO_SIGNAL_PROVIDER,
    seed_demo_data,
)
from backend.app.simulation.service import (
    DEFAULT_ILLIQUID_PLAYER_COUNT,
    DEFAULT_LIQUID_PLAYER_COUNT,
    DEFAULT_TICK_COUNT,
    DemoMarketSimulationService,
)


class _HelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    pass


DEV_CLI_EPILOG = """Common local demo flows:
  Fresh demo market:
    python backend/scripts/dev.py rebuild-demo-market --seed 20260311
    python backend/scripts/dev.py runserver --demo-simulation --seed 20260311

  Refresh exchange activity without rebuilding demo users/players:
    python backend/scripts/dev.py seed-demo-liquidity --seed 20260311
    python backend/scripts/dev.py simulation-ticks --count 5 --start-tick 1 --seed 20260311
"""


def resolve_sqlite_database_path(database_url: str) -> Path | None:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        return None
    if not url.database or url.database == ":memory:":
        return None
    path = Path(url.database)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path.resolve()


def reset_local_database(database_url: str) -> list[Path]:
    database_path = resolve_sqlite_database_path(database_url)
    if database_path is None:
        return []

    candidates = (
        database_path,
        Path(f"{database_path}-wal"),
        Path(f"{database_path}-shm"),
        Path(f"{database_path}-journal"),
    )
    removed_paths: list[Path] = []
    for candidate in candidates:
        if candidate.exists():
            candidate.unlink()
            removed_paths.append(candidate)
    return removed_paths


def migrate_database(database_url: str) -> tuple[str, ...]:
    engine = create_database_engine(database_url)
    try:
        return ensure_database_schema_current(engine)
    finally:
        engine.dispose()


def bootstrap_demo_database(
    *,
    database_url: str,
    player_count: int,
    provider: str,
    signal_provider: str,
    password: str,
    seed: int,
    batch_size: int,
    reset_db: bool,
    with_liquidity: bool = False,
    liquid_player_count: int = DEFAULT_LIQUID_PLAYER_COUNT,
    illiquid_player_count: int = DEFAULT_ILLIQUID_PLAYER_COUNT,
) -> dict[str, Any]:
    removed_paths = [str(path) for path in reset_local_database(database_url)] if reset_db else []
    heads = list(migrate_database(database_url))
    summary = seed_demo_data(
        database_url=database_url,
        player_target_count=player_count,
        provider_name=provider,
        signal_provider=signal_provider,
        demo_password=password,
        random_seed=seed,
        batch_size=batch_size,
        with_liquidity=with_liquidity,
        liquid_player_count=liquid_player_count,
        illiquid_player_count=illiquid_player_count,
    )
    return {
        "removed_paths": removed_paths,
        "migration_heads": heads,
        "seed_summary": summary.to_dict(),
    }


def seed_demo_liquidity_database(
    *,
    database_url: str,
    seed: int,
    liquid_player_count: int,
    illiquid_player_count: int,
) -> dict[str, Any]:
    engine = create_database_engine(database_url)
    try:
        ensure_database_schema_current(engine)
        summary = DemoMarketSimulationService(
            session_factory=create_session_factory(engine),
        ).seed_demo_liquidity(
            random_seed=seed,
            liquid_player_count=liquid_player_count,
            illiquid_player_count=illiquid_player_count,
        )
        return summary.to_dict()
    finally:
        engine.dispose()


def run_simulation_tick_database(
    *,
    database_url: str,
    tick_number: int,
    seed: int,
    liquid_player_count: int,
    illiquid_player_count: int,
) -> dict[str, Any]:
    engine = create_database_engine(database_url)
    try:
        ensure_database_schema_current(engine)
        summary = DemoMarketSimulationService(
            session_factory=create_session_factory(engine),
        ).run_simulation_tick(
            tick_number=tick_number,
            random_seed=seed,
            liquid_player_count=liquid_player_count,
            illiquid_player_count=illiquid_player_count,
        )
        return summary.to_dict()
    finally:
        engine.dispose()


def run_simulation_ticks_database(
    *,
    database_url: str,
    tick_count: int,
    start_tick: int,
    seed: int,
    liquid_player_count: int,
    illiquid_player_count: int,
) -> dict[str, Any]:
    engine = create_database_engine(database_url)
    try:
        ensure_database_schema_current(engine)
        summaries = DemoMarketSimulationService(
            session_factory=create_session_factory(engine),
        ).run_simulation_ticks(
            tick_count=tick_count,
            start_tick=start_tick,
            random_seed=seed,
            liquid_player_count=liquid_player_count,
            illiquid_player_count=illiquid_player_count,
        )
        return {
            "tick_count": tick_count,
            "start_tick": start_tick,
            "summaries": [summary.to_dict() for summary in summaries],
        }
    finally:
        engine.dispose()


def rebuild_demo_market(
    *,
    database_url: str,
    player_count: int,
    provider: str,
    signal_provider: str,
    password: str,
    seed: int,
    batch_size: int,
    liquid_player_count: int,
    illiquid_player_count: int,
) -> dict[str, Any]:
    return bootstrap_demo_database(
        database_url=database_url,
        player_count=player_count,
        provider=provider,
        signal_provider=signal_provider,
        password=password,
        seed=seed,
        batch_size=batch_size,
        reset_db=True,
        with_liquidity=True,
        liquid_player_count=liquid_player_count,
        illiquid_player_count=illiquid_player_count,
    )


def run_backend_server(
    *,
    host: str,
    port: int,
    reload_enabled: bool,
    demo_simulation: bool,
    demo_bootstrap: bool,
    demo_seed_liquidity_on_boot: bool,
    demo_player_count: int,
    simulation_seed: int,
    liquid_player_count: int,
    illiquid_player_count: int,
    database_url: str,
) -> int:
    app_target = (
        "backend.app.simulation.app_factory:create_demo_simulation_app"
        if demo_simulation
        else "backend.app.main:app"
    )
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        app_target,
        "--host",
        host,
        "--port",
        str(port),
    ]
    if demo_simulation:
        command.append("--factory")
    if reload_enabled:
        command.append("--reload")
    environment = os.environ.copy()
    environment["GTE_DATABASE_URL"] = database_url
    if demo_simulation:
        environment["GTE_DEMO_SIMULATION_ENABLED"] = "1"
        environment["GTE_DEMO_SIMULATION_BOOTSTRAP"] = "1" if demo_bootstrap else "0"
        environment["GTE_DEMO_SIMULATION_SEED_ON_BOOT"] = "1" if demo_seed_liquidity_on_boot else "0"
        environment["GTE_DEMO_SIMULATION_PLAYER_COUNT"] = str(demo_player_count)
        environment["GTE_DEMO_SIMULATION_SEED"] = str(simulation_seed)
        environment["GTE_DEMO_SIMULATION_LIQUID_PLAYERS"] = str(liquid_player_count)
        environment["GTE_DEMO_SIMULATION_ILLIQUID_PLAYERS"] = str(illiquid_player_count)
    return subprocess.run(command, cwd=str(PROJECT_ROOT), check=False, env=environment).returncode


def run_pytest(pytest_args: Sequence[str]) -> int:
    resolved_args = list(pytest_args) if pytest_args else ["backend/tests/ingestion"]
    command = [sys.executable, "-m", "pytest", *resolved_args]
    return subprocess.run(command, cwd=str(PROJECT_ROOT), check=False).returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Local developer and QA commands for building a repeatable demo market.",
        epilog=DEV_CLI_EPILOG,
        formatter_class=_HelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="command")

    reset_parser = subparsers.add_parser(
        "reset-db",
        help="Delete the local SQLite database file and SQLite sidecars.",
        description="Remove the local SQLite database file plus its -wal, -shm, and -journal sidecars.",
        formatter_class=_HelpFormatter,
    )
    reset_parser.add_argument(
        "--database-url",
        default=DEFAULT_DATABASE_URL,
        help="Target database URL. These helpers are designed around local SQLite workflows.",
    )

    migrate_parser = subparsers.add_parser(
        "migrate",
        help="Upgrade the configured database to Alembic head.",
        description="Apply Alembic migrations to the configured database.",
        formatter_class=_HelpFormatter,
    )
    migrate_parser.add_argument(
        "--database-url",
        default=DEFAULT_DATABASE_URL,
        help="Target database URL. Local demo workflows usually point at the SQLite dev database.",
    )

    seed_parser = subparsers.add_parser(
        "seed-demo",
        help="Seed demo users, wallets, holdings, and a sample player subset.",
        description="Seed the core demo dataset without resetting the database first.",
        formatter_class=_HelpFormatter,
    )
    seed_parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL, help="Target database URL.")
    seed_parser.add_argument("--player-count", type=int, default=DEFAULT_DEMO_PLAYER_COUNT, help="Number of demo players to seed into the local universe.")
    seed_parser.add_argument("--provider", default=DEFAULT_DEMO_PROVIDER_NAME, help="Synthetic provider slug written onto demo player records.")
    seed_parser.add_argument("--signal-provider", default=DEFAULT_DEMO_SIGNAL_PROVIDER, help="Synthetic provider slug written onto demo market signals.")
    seed_parser.add_argument("--password", default=DEFAULT_DEMO_PASSWORD, help="Password assigned to the local demo users for login flows.")
    seed_parser.add_argument("--seed", type=int, default=DEFAULT_DEMO_RANDOM_SEED, help="Deterministic seed for repeatable demo users, players, holdings, and liquidity.")
    seed_parser.add_argument("--batch-size", type=int, default=DEFAULT_DEMO_BATCH_SIZE, help="Batch size used while seeding the demo player universe.")
    seed_parser.add_argument("--with-liquidity", action=argparse.BooleanOptionalAction, default=False, help="Also seed deterministic exchange-side liquidity and trade history.")
    seed_parser.add_argument("--liquid-player-count", type=int, default=DEFAULT_LIQUID_PLAYER_COUNT, help="Number of high-activity players to receive liquid demo markets.")
    seed_parser.add_argument("--illiquid-player-count", type=int, default=DEFAULT_ILLIQUID_PLAYER_COUNT, help="Number of low-activity players to receive illiquid demo markets.")

    bootstrap_parser = subparsers.add_parser(
        "bootstrap-demo",
        help="Reset the local SQLite database, migrate to head, and seed the demo dataset.",
        description="Cleanly rebuild the local SQLite database and seed demo users, players, and holdings.",
        formatter_class=_HelpFormatter,
    )
    bootstrap_parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL, help="Target database URL.")
    bootstrap_parser.add_argument("--player-count", type=int, default=DEFAULT_DEMO_PLAYER_COUNT, help="Number of demo players to seed into the local universe.")
    bootstrap_parser.add_argument("--provider", default=DEFAULT_DEMO_PROVIDER_NAME, help="Synthetic provider slug written onto demo player records.")
    bootstrap_parser.add_argument("--signal-provider", default=DEFAULT_DEMO_SIGNAL_PROVIDER, help="Synthetic provider slug written onto demo market signals.")
    bootstrap_parser.add_argument("--password", default=DEFAULT_DEMO_PASSWORD, help="Password assigned to the local demo users for login flows.")
    bootstrap_parser.add_argument("--seed", type=int, default=DEFAULT_DEMO_RANDOM_SEED, help="Deterministic seed for repeatable demo data.")
    bootstrap_parser.add_argument("--batch-size", type=int, default=DEFAULT_DEMO_BATCH_SIZE, help="Batch size used while seeding the demo player universe.")
    bootstrap_parser.add_argument("--reset-db", action=argparse.BooleanOptionalAction, default=True, help="Delete the SQLite database file before migrating and seeding.")
    bootstrap_parser.add_argument("--with-liquidity", action=argparse.BooleanOptionalAction, default=False, help="Also seed deterministic exchange-side liquidity and trade history.")
    bootstrap_parser.add_argument("--liquid-player-count", type=int, default=DEFAULT_LIQUID_PLAYER_COUNT, help="Number of high-activity players to receive liquid demo markets.")
    bootstrap_parser.add_argument("--illiquid-player-count", type=int, default=DEFAULT_ILLIQUID_PLAYER_COUNT, help="Number of low-activity players to receive illiquid demo markets.")

    liquidity_parser = subparsers.add_parser(
        "seed-demo-liquidity",
        help="Seed deterministic demo exchange liquidity into the local database.",
        description="Refresh only the exchange-side order ladder and trade history for an existing demo market.",
        formatter_class=_HelpFormatter,
    )
    liquidity_parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL, help="Target database URL.")
    liquidity_parser.add_argument("--seed", type=int, default=DEFAULT_DEMO_RANDOM_SEED, help="Deterministic seed for repeatable order ladders and seeded trades.")
    liquidity_parser.add_argument("--liquid-player-count", type=int, default=DEFAULT_LIQUID_PLAYER_COUNT, help="Number of high-activity players to receive liquid demo markets.")
    liquidity_parser.add_argument("--illiquid-player-count", type=int, default=DEFAULT_ILLIQUID_PLAYER_COUNT, help="Number of low-activity players to receive illiquid demo markets.")

    tick_parser = subparsers.add_parser(
        "simulation-tick",
        help="Run one deterministic simulation tick against the current demo market.",
        description="Generate one deterministic unit of demo market activity against the current local market state.",
        formatter_class=_HelpFormatter,
    )
    tick_parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL, help="Target database URL.")
    tick_parser.add_argument("--tick-number", type=int, default=1, help="1-based tick number. Combined with --seed to keep output repeatable.")
    tick_parser.add_argument("--seed", type=int, default=DEFAULT_DEMO_RANDOM_SEED, help="Deterministic seed for repeatable simulation output.")
    tick_parser.add_argument("--liquid-player-count", type=int, default=DEFAULT_LIQUID_PLAYER_COUNT, help="Number of high-activity players expected in the demo market.")
    tick_parser.add_argument("--illiquid-player-count", type=int, default=DEFAULT_ILLIQUID_PLAYER_COUNT, help="Number of low-activity players expected in the demo market.")

    ticks_parser = subparsers.add_parser(
        "simulation-ticks",
        help="Run N deterministic simulation ticks against the current demo market.",
        description="Generate a sequence of deterministic demo market ticks.",
        formatter_class=_HelpFormatter,
    )
    ticks_parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL, help="Target database URL.")
    ticks_parser.add_argument("--count", type=int, default=DEFAULT_TICK_COUNT, help="Number of ticks to run.")
    ticks_parser.add_argument("--start-tick", type=int, default=1, help="1-based tick number to use for the first generated tick.")
    ticks_parser.add_argument("--seed", type=int, default=DEFAULT_DEMO_RANDOM_SEED, help="Deterministic seed for repeatable simulation output.")
    ticks_parser.add_argument("--liquid-player-count", type=int, default=DEFAULT_LIQUID_PLAYER_COUNT, help="Number of high-activity players expected in the demo market.")
    ticks_parser.add_argument("--illiquid-player-count", type=int, default=DEFAULT_ILLIQUID_PLAYER_COUNT, help="Number of low-activity players expected in the demo market.")

    rebuild_parser = subparsers.add_parser(
        "rebuild-demo-market",
        help="Reset the local demo database, seed demo users/players/holdings, and add demo liquidity.",
        description="One-command rebuild for the local fake market used by frontend demos and QA.",
        formatter_class=_HelpFormatter,
    )
    rebuild_parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL, help="Target database URL.")
    rebuild_parser.add_argument("--player-count", type=int, default=DEFAULT_DEMO_PLAYER_COUNT, help="Number of demo players to seed into the local universe.")
    rebuild_parser.add_argument("--provider", default=DEFAULT_DEMO_PROVIDER_NAME, help="Synthetic provider slug written onto demo player records.")
    rebuild_parser.add_argument("--signal-provider", default=DEFAULT_DEMO_SIGNAL_PROVIDER, help="Synthetic provider slug written onto demo market signals.")
    rebuild_parser.add_argument("--password", default=DEFAULT_DEMO_PASSWORD, help="Password assigned to the local demo users for login flows.")
    rebuild_parser.add_argument("--seed", type=int, default=DEFAULT_DEMO_RANDOM_SEED, help="Deterministic seed for repeatable demo data and liquidity.")
    rebuild_parser.add_argument("--batch-size", type=int, default=DEFAULT_DEMO_BATCH_SIZE, help="Batch size used while seeding the demo player universe.")
    rebuild_parser.add_argument("--liquid-player-count", type=int, default=DEFAULT_LIQUID_PLAYER_COUNT, help="Number of high-activity players to receive liquid demo markets.")
    rebuild_parser.add_argument("--illiquid-player-count", type=int, default=DEFAULT_ILLIQUID_PLAYER_COUNT, help="Number of low-activity players to receive illiquid demo markets.")

    runserver_parser = subparsers.add_parser(
        "runserver",
        help="Start the FastAPI development server.",
        description="Run the backend locally, optionally replaying the seeded fake market into the in-memory engine.",
        formatter_class=_HelpFormatter,
    )
    runserver_parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL, help="Target database URL.")
    runserver_parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    runserver_parser.add_argument("--port", type=int, default=8000, help="Port to bind.")
    runserver_parser.add_argument("--reload", action=argparse.BooleanOptionalAction, default=True, help="Enable uvicorn autoreload for local development.")
    runserver_parser.add_argument("--demo-simulation", action=argparse.BooleanOptionalAction, default=False, help="Use the demo simulation app factory so the in-memory market engine replays seeded data on boot.")
    runserver_parser.add_argument("--demo-bootstrap", action=argparse.BooleanOptionalAction, default=False, help="Seed demo users, wallets, holdings, and players during app startup before replaying the market.")
    runserver_parser.add_argument("--demo-seed-liquidity-on-boot", action=argparse.BooleanOptionalAction, default=False, help="Refresh exchange-side liquidity on app boot instead of only replaying the database state.")
    runserver_parser.add_argument("--demo-player-count", type=int, default=DEFAULT_DEMO_PLAYER_COUNT, help="Player count used only when --demo-bootstrap is enabled.")
    runserver_parser.add_argument("--seed", type=int, default=DEFAULT_DEMO_RANDOM_SEED, help="Deterministic seed used for demo bootstrap and simulation replay settings.")
    runserver_parser.add_argument("--liquid-player-count", type=int, default=DEFAULT_LIQUID_PLAYER_COUNT, help="Number of high-activity players to replay or seed into the in-memory market engine.")
    runserver_parser.add_argument("--illiquid-player-count", type=int, default=DEFAULT_ILLIQUID_PLAYER_COUNT, help="Number of low-activity players to replay or seed into the in-memory market engine.")

    test_parser = subparsers.add_parser(
        "test",
        help="Run pytest. Defaults to backend/tests/ingestion when no args are supplied.",
        description="Pass through to pytest from the repository root.",
        formatter_class=_HelpFormatter,
    )
    test_parser.add_argument("pytest_args", nargs=argparse.REMAINDER, help="Arguments passed straight through to pytest.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "reset-db":
        result = {"removed_paths": [str(path) for path in reset_local_database(args.database_url)]}
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.command == "migrate":
        result = {"migration_heads": list(migrate_database(args.database_url))}
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.command == "seed-demo":
        summary = seed_demo_data(
            database_url=args.database_url,
            player_target_count=args.player_count,
            provider_name=args.provider,
            signal_provider=args.signal_provider,
            demo_password=args.password,
            random_seed=args.seed,
            batch_size=args.batch_size,
            with_liquidity=args.with_liquidity,
            liquid_player_count=args.liquid_player_count,
            illiquid_player_count=args.illiquid_player_count,
        )
        print(json.dumps(summary.to_dict(), indent=2, default=str))
        return 0

    if args.command == "bootstrap-demo":
        result = bootstrap_demo_database(
            database_url=args.database_url,
            player_count=args.player_count,
            provider=args.provider,
            signal_provider=args.signal_provider,
            password=args.password,
            seed=args.seed,
            batch_size=args.batch_size,
            reset_db=args.reset_db,
            with_liquidity=args.with_liquidity,
            liquid_player_count=args.liquid_player_count,
            illiquid_player_count=args.illiquid_player_count,
        )
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.command == "seed-demo-liquidity":
        result = seed_demo_liquidity_database(
            database_url=args.database_url,
            seed=args.seed,
            liquid_player_count=args.liquid_player_count,
            illiquid_player_count=args.illiquid_player_count,
        )
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.command == "simulation-tick":
        result = run_simulation_tick_database(
            database_url=args.database_url,
            tick_number=args.tick_number,
            seed=args.seed,
            liquid_player_count=args.liquid_player_count,
            illiquid_player_count=args.illiquid_player_count,
        )
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.command == "simulation-ticks":
        result = run_simulation_ticks_database(
            database_url=args.database_url,
            tick_count=args.count,
            start_tick=args.start_tick,
            seed=args.seed,
            liquid_player_count=args.liquid_player_count,
            illiquid_player_count=args.illiquid_player_count,
        )
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.command == "rebuild-demo-market":
        result = rebuild_demo_market(
            database_url=args.database_url,
            player_count=args.player_count,
            provider=args.provider,
            signal_provider=args.signal_provider,
            password=args.password,
            seed=args.seed,
            batch_size=args.batch_size,
            liquid_player_count=args.liquid_player_count,
            illiquid_player_count=args.illiquid_player_count,
        )
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.command == "runserver":
        return run_backend_server(
            database_url=args.database_url,
            host=args.host,
            port=args.port,
            reload_enabled=args.reload,
            demo_simulation=args.demo_simulation,
            demo_bootstrap=args.demo_bootstrap,
            demo_seed_liquidity_on_boot=args.demo_seed_liquidity_on_boot,
            demo_player_count=args.demo_player_count,
            simulation_seed=args.seed,
            liquid_player_count=args.liquid_player_count,
            illiquid_player_count=args.illiquid_player_count,
        )

    return run_pytest(args.pytest_args)


__all__ = [
    "bootstrap_demo_database",
    "build_parser",
    "main",
    "migrate_database",
    "rebuild_demo_market",
    "reset_local_database",
    "resolve_sqlite_database_path",
    "run_backend_server",
    "run_pytest",
    "run_simulation_tick_database",
    "run_simulation_ticks_database",
    "seed_demo_liquidity_database",
]
