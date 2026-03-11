from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from backend.app.core.database import create_database_engine, create_session_factory, ensure_database_schema_current
from backend.app.ingestion.constants import DEFAULT_DATABASE_URL, ENV_DATABASE_URL
from backend.app.ingestion.player_universe_seeder import PHASE_THREE_PROVIDER_NAME, VerifiedPlayerUniverseSeeder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed the Phase 3 verified player universe.")
    parser.add_argument("--target-count", type=int, default=100_000)
    parser.add_argument("--provider", default=PHASE_THREE_PROVIDER_NAME)
    parser.add_argument("--seed", type=int, default=20260311)
    parser.add_argument("--batch-size", type=int, default=5_000)
    parser.add_argument("--database-url", default=os.getenv(ENV_DATABASE_URL, DEFAULT_DATABASE_URL))
    parser.add_argument("--keep-provider-data", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    engine = create_database_engine(args.database_url)
    ensure_database_schema_current(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        summary = VerifiedPlayerUniverseSeeder(session).seed(
            target_player_count=args.target_count,
            provider_name=args.provider,
            random_seed=args.seed,
            replace_provider_data=not args.keep_provider_data,
            batch_size=args.batch_size,
        )
        session.commit()

    print(json.dumps(summary.to_dict(), indent=2, default=str))


if __name__ == "__main__":
    main()
