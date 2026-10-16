from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.player_token_market import PlayerShareEvent, PlayerShareHolding, PlayerShareMarket


@dataclass(frozen=True)
class ReconciliationReport:
    markets_checked: int
    holdings_checked: int
    event_rows_checked: int
    market_event_mismatches: int
    holding_event_mismatches: int
    negative_holdings: int

    @property
    def healthy(self) -> bool:
        return not any(
            (
                self.market_event_mismatches,
                self.holding_event_mismatches,
                self.negative_holdings,
            )
        )


def _share_event_delta(event: PlayerShareEvent) -> int:
    return int(event.share_delta or 0)


def audit(session: Session) -> ReconciliationReport:
    markets = list(session.scalars(select(PlayerShareMarket)).all())
    holdings = list(session.scalars(select(PlayerShareHolding)).all())
    events = list(
        session.scalars(
            select(PlayerShareEvent).order_by(PlayerShareEvent.created_at, PlayerShareEvent.id)
        ).all()
    )

    market_event_deltas: dict[str, int] = defaultdict(int)
    holding_event_deltas: dict[tuple[str, str], int] = defaultdict(int)
    for event in events:
        delta = _share_event_delta(event)
        market_event_deltas[event.player_id] += delta
        if event.user_id:
            holding_event_deltas[(event.user_id, event.player_id)] += delta

    market_mismatches = sum(
        1
        for market in markets
        if int(market.circulating_shares or 0) != market_event_deltas.get(market.player_id, 0)
        and any(event.player_id == market.player_id and event.share_delta for event in events)
    )

    holding_mismatches = sum(
        1
        for holding in holdings
        if int(holding.share_count or 0)
        != holding_event_deltas.get((holding.user_id, holding.player_id), 0)
        and any(
            event.user_id == holding.user_id
            and event.player_id == holding.player_id
            and event.share_delta
            for event in events
        )
    )

    negative_holdings = sum(1 for holding in holdings if int(holding.share_count or 0) < 0)

    return ReconciliationReport(
        markets_checked=len(markets),
        holdings_checked=len(holdings),
        event_rows_checked=len(events),
        market_event_mismatches=market_mismatches,
        holding_event_mismatches=holding_mismatches,
        negative_holdings=negative_holdings,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only player-share event reconciliation audit")
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()

    engine = create_engine(args.database_url, pool_pre_ping=True)
    with Session(engine) as session:
        report = audit(session)
    print(json.dumps(asdict(report), sort_keys=True, indent=2, default=str))
    return 0 if report.healthy else 2


if __name__ == "__main__":
    raise SystemExit(main())
