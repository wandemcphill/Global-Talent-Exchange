from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import create_database_engine, create_session_factory
from app.talent.backfill import MAX_BATCH_SIZE, TalentBackfillRunner


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill Talent Exchange profiles and deterministic rankings.")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--batch-size", type=int, default=MAX_BATCH_SIZE)
    parser.add_argument("--after-player-id", default=None)
    parser.add_argument("--all", action="store_true", help="refresh existing profiles as well as missing ones")
    parser.add_argument("--no-recompute", action="store_true", help="sync profiles without recomputing rankings")
    parser.add_argument("--as-of", default=None, help="ranking date in YYYY-MM-DD format")
    parser.add_argument("--fail-fast", action="store_true")
    args = parser.parse_args()

    if not 1 <= args.batch_size <= MAX_BATCH_SIZE:
        raise SystemExit(f"--batch-size must be between 1 and {MAX_BATCH_SIZE}")

    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    engine = create_database_engine(args.database_url)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as session:
            report = TalentBackfillRunner(session, as_of=as_of).run(
                batch_size=args.batch_size,
                only_missing=not args.all,
                after_player_id=args.after_player_id,
                recompute_rankings=not args.no_recompute,
                continue_on_error=not args.fail_fast,
            )
            print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
            return 1 if report.failed else 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
