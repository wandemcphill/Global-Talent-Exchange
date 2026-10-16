from __future__ import annotations

import argparse
from dataclasses import asdict
import json

from app.core.database import create_database_engine, create_session_factory
from app.players.football_integrity import repairPlayerPositions, repair_gsi_clusters


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair GTEX player positions and clustered GSI values.")
    parser.add_argument("--database-url", default=None, help="Override DATABASE_URL/GTE_DATABASE_URL.")
    parser.add_argument("--apply", action="store_true", help="Persist repairs. Defaults to dry run.")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    engine = create_database_engine(args.database_url)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        position_changes = repairPlayerPositions(session, dry_run=not args.apply, limit=args.limit)
        gsi_changes = repair_gsi_clusters(session, dry_run=not args.apply, limit=args.limit)
        if args.apply:
            session.commit()
        print(
            json.dumps(
                {
                    "dry_run": not args.apply,
                    "position_repairs": [asdict(change) for change in position_changes],
                    "gsi_repairs": gsi_changes,
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
