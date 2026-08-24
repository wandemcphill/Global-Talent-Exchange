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
from app.models.player_token_market import PlayerShareHolding, PlayerShareMarket
from scripts.audit_player_share_event_reconciliation import audit as audit_event_reconciliation
from scripts.audit_player_share_issuer_boundary import audit as audit_issuer_boundary
from scripts.audit_player_share_lifecycle import audit_lifecycle
from scripts.audit_player_share_trade_boundary import audit as audit_trade_boundary
from scripts.audit_player_share_trade_idempotency import audit as audit_trade_idempotency


def audit_holdings(*, database_url: str | None) -> dict[str, Any]:
    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as session:
            negative_holdings = int(
                session.scalar(select(func.count(PlayerShareHolding.id)).where(PlayerShareHolding.share_count < 0)) or 0
            )
            negative_costs = int(
                session.scalar(
                    select(func.count(PlayerShareHolding.id)).where(PlayerShareHolding.average_cost_coin < 0)
                )
                or 0
            )
            negative_dividends = int(
                session.scalar(
                    select(func.count(PlayerShareHolding.id)).where(PlayerShareHolding.dividends_earned_coin < 0)
                )
                or 0
            )

            market_rows = session.scalars(select(PlayerShareMarket)).all()
            market_by_player = {row.player_id: row for row in market_rows}
            active_markets = [row for row in market_rows if row.status == "active"]
            negative_market_supply = sum(
                int((row.total_shares or 0) < 0 or (row.circulating_shares or 0) < 0) for row in market_rows
            )
            circulation_over_supply = sum(
                int((row.circulating_shares or 0) > (row.total_shares or 0)) for row in market_rows
            )
            active_zero_price = sum(
                int(row.share_price_coin is None or row.share_price_coin <= 0) for row in active_markets
            )
            active_negative_liquidity = sum(int(row.liquidity_coin < 0) for row in active_markets)

            holdings_by_player: dict[str, int] = {}
            for player_id, share_count in session.execute(
                select(PlayerShareHolding.player_id, func.sum(PlayerShareHolding.share_count)).group_by(
                    PlayerShareHolding.player_id
                )
            ).all():
                holdings_by_player[str(player_id)] = int(share_count or 0)

            holdings_without_market = 0
            holdings_on_inactive_market = 0
            holdings_over_circulation = 0
            holdings_over_supply = 0
            for player_id, held in holdings_by_player.items():
                market = market_by_player.get(player_id)
                if market is None:
                    holdings_without_market += int(held > 0)
                    continue
                if market.status != "active" and held > 0:
                    holdings_on_inactive_market += 1
                circulating = int(market.circulating_shares or 0)
                total = int(market.total_shares or 0)
                holdings_over_circulation += int(held > circulating)
                holdings_over_supply += int(held > total)

            gates = {
                "no_negative_holdings": negative_holdings == 0,
                "no_negative_average_costs": negative_costs == 0,
                "no_negative_dividend_balances": negative_dividends == 0,
                "no_negative_market_supply": negative_market_supply == 0,
                "market_circulation_does_not_exceed_supply": circulation_over_supply == 0,
                "no_active_zero_price_markets": active_zero_price == 0,
                "no_active_negative_liquidity": active_negative_liquidity == 0,
                "no_positive_holdings_without_market": holdings_without_market == 0,
                "no_positive_holdings_on_inactive_market": holdings_on_inactive_market == 0,
                "holdings_do_not_exceed_circulation": holdings_over_circulation == 0,
                "holdings_do_not_exceed_total_supply": holdings_over_supply == 0,
            }
            return {
                "negative_holdings": negative_holdings,
                "negative_average_costs": negative_costs,
                "negative_dividend_balances": negative_dividends,
                "negative_market_supply": negative_market_supply,
                "markets_with_circulation_over_supply": circulation_over_supply,
                "active_zero_price_markets": active_zero_price,
                "active_negative_liquidity_markets": active_negative_liquidity,
                "players_with_positive_holdings_without_market": holdings_without_market,
                "players_with_positive_holdings_on_inactive_market": holdings_on_inactive_market,
                "players_with_holdings_over_circulation": holdings_over_circulation,
                "players_with_holdings_over_total_supply": holdings_over_supply,
                "gates": gates,
                "read_only": True,
            }
    finally:
        engine.dispose()


def certify(*, database_url: str | None, batch_size: int) -> dict[str, Any]:
    lifecycle = audit_lifecycle(database_url=database_url, batch_size=batch_size)
    holdings = audit_holdings(database_url=database_url)
    event_reconciliation = audit_event_reconciliation(database_url=database_url)
    trade_boundary = audit_trade_boundary()
    trade_idempotency = audit_trade_idempotency()
    issuer_boundary = audit_issuer_boundary()
    gates = {
        "trade_boundary": bool(trade_boundary["pass"]),
        "trade_idempotency": bool(trade_idempotency["pass"]),
        "issuer_boundary": bool(issuer_boundary["pass"]),
        "event_reconciliation": bool(event_reconciliation["pass"]),
        **{f"lifecycle_{name}": bool(value) for name, value in lifecycle["gates"].items()},
        **{f"holdings_{name}": bool(value) for name, value in holdings["gates"].items()},
    }
    return {
        "certification": "player-share-economic-foundation",
        "read_only": True,
        "lifecycle": lifecycle,
        "holdings": holdings,
        "event_reconciliation": event_reconciliation,
        "trade_boundary": trade_boundary,
        "trade_idempotency": trade_idempotency,
        "issuer_boundary": issuer_boundary,
        "gates": gates,
        "pass": all(gates.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the read-only player-share economic certification gate.")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be positive")
    report = certify(database_url=args.database_url, batch_size=args.batch_size)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
