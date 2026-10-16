from __future__ import annotations

import argparse
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.players.market_integrity_service import PlayerShareMarketIntegrityService


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only player-share economic reconciliation audit"
    )
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--limit", type=int, default=5000)
    args = parser.parse_args()

    engine = create_engine(args.database_url, pool_pre_ping=True)
    with Session(engine) as session:
        report = PlayerShareMarketIntegrityService(session).audit(limit=args.limit)

    payload = {
        "markets_scanned": report.markets_scanned,
        "active_markets": report.active_markets,
        "healthy_markets": report.healthy_markets,
        "issue_count": report.issue_count,
        "healthy": report.healthy,
        "issues": [
            {
                "code": issue.code,
                "severity": issue.severity,
                "player_id": issue.player_id,
                "market_id": issue.market_id,
                "detail": issue.detail,
                "metadata": issue.metadata,
            }
            for issue in report.issues
        ],
    }
    print(json.dumps(payload, sort_keys=True, indent=2))
    return 0 if report.healthy else 2


if __name__ == "__main__":
    raise SystemExit(main())
