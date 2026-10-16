from __future__ import annotations

import argparse
import json
from typing import Sequence

from app.ingestion.demo_bootstrap import (
    DEFAULT_DEMO_BATCH_SIZE,
    DEFAULT_DEMO_PASSWORD,
    DEFAULT_DEMO_PLAYER_COUNT,
    DEFAULT_DEMO_PROVIDER_NAME,
    DEFAULT_DEMO_RANDOM_SEED,
    DEFAULT_DEMO_SIGNAL_PROVIDER,
)
from app.ingestion.dev_cli import resolve_seed_all_database_url, seed_all_database


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Idempotently seed the backend with demo teams, players, competitions, "
            "marketplace listings, federations, and national-team data."
        )
    )
    parser.add_argument(
        "--database-url",
        default="",
        help="Target database URL. Defaults to DATABASE_URL/GTE_DATABASE_URL or local gte_backend.db.",
    )
    parser.add_argument(
        "--player-count",
        type=int,
        default=DEFAULT_DEMO_PLAYER_COUNT,
        help="Number of demo players to ensure exist before world visibility seeding runs.",
    )
    parser.add_argument(
        "--provider",
        default=DEFAULT_DEMO_PROVIDER_NAME,
        help="Synthetic provider slug written onto seeded demo player records.",
    )
    parser.add_argument(
        "--signal-provider",
        default=DEFAULT_DEMO_SIGNAL_PROVIDER,
        help="Synthetic provider slug written onto seeded demo market signals.",
    )
    parser.add_argument(
        "--password",
        default=DEFAULT_DEMO_PASSWORD,
        help="Password assigned to deterministic seed users when auth fixtures are created.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_DEMO_RANDOM_SEED,
        help="Deterministic seed used for repeatable player universe seeding.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_DEMO_BATCH_SIZE,
        help="Batch size used while bootstrapping the demo player universe.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = seed_all_database(
        database_url=resolve_seed_all_database_url(args.database_url),
        player_count=args.player_count,
        provider=args.provider,
        signal_provider=args.signal_provider,
        password=args.password,
        seed=args.seed,
        batch_size=args.batch_size,
    )
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
