from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import create_database_engine, create_session_factory
from app.models.player_token_market import PlayerShareEvent, PlayerShareMarket


def audit(*, database_url: str | None) -> dict[str, Any]:
    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as session:
            event_deltas = {
                str(player_id): int(delta or 0)
                for player_id, delta in session.execute(
                    select(PlayerShareEvent.player_id, func.sum(PlayerShareEvent.share_delta)).group_by(
                        PlayerShareEvent.player_id
                    )
                ).all()
            }
            markets = session.scalars(select(PlayerShareMarket)).all()
            mismatches: list[dict[str, Any]] = []
            for market in markets:
                expected = int(market.circulating_shares or 0)
                observed = int(event_deltas.get(str(market.player_id), 0))
                if expected != observed:
                    mismatches.append(
                        {
                            "player_id": market.player_id,
                            "market_id": market.id,
                            "circulating_shares": expected,
                            "event_share_delta_sum": observed,
                            "difference": expected - observed,
                        }
                    )

            orphan_event_players = sorted(
                player_id for player_id in event_deltas if player_id not in {m.player_id for m in markets}
            )
            report = {
                "pass": not mismatches and not orphan_event_players,
                "read_only": True,
                "markets_checked": len(markets),
                "mismatches": mismatches,
                "orphan_event_players": orphan_event_players,
                "gates": {
                    "market_circulation_reconciles_to_event_deltas": not mismatches,
                    "no_events_without_market": not orphan_event_players,
                },
            }
            return report
    finally:
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit player-share event deltas against market circulation.")
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args()
    report = audit(database_url=args.database_url)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
