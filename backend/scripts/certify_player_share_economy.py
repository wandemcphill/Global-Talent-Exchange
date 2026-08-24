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
from scripts.audit_player_share_issuer_boundary import audit as audit_issuer_boundary
from scripts.audit_player_share_lifecycle import audit_lifecycle
from scripts.audit_player_share_trade_boundary import audit as audit_trade_boundary


def audit_holdings(*, database_url: str | None) -> dict[str, Any]:
    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as session:
            negative_holdings = int(
                session.scalar(
                    select(func.count(PlayerShareHolding.id)).where(PlayerShareHolding.share_count < 0)
                )
                or 0
            )
            negative_costs = int(
                session.scalar(
                    select(func.count(PlayerShareHolding.id)).where(
                        PlayerShareHolding.average_cost_coin < 0
                    )
                )
                or 0
            )
            negative_dividends = int(
                session.scalar(
                    select(func.count(PlayerShareHolding.id)).where(
                        PlayerShareHolding.dividends_earned_coin < 0
                    )
                )
                or 0
            )

            holdings_by_player: dict[str, int] = {}
            for player_id, share_count in session.execute(
                select(PlayerShareHolding.player_id, func.sum(PlayerShareHolding.share_count)).group_by(
                    PlayerShareHolding.player_id
                )
            ).all():
                holdings_by_player[str(player_id)] = int(share_count or 0)

            market_by_player = {
                row.player_id: (int(row.circulating_shares or 0), int(row.total_shares or 0))
                for row in session.scalars(select(PlayerShareMarket)).all()
            }
            holdings_over_circulation = 0
            holdings_over_supply = 0
            for player_id, held in holdings_by_player.items():
                market = market_by_player.get(player_id)
                if market is None:
                    holdings_over_circulation += int(held > 0)
                    continue
                circulating, total = market
                holdings_over_circulation += int(held > circulating)
                holdings_over_supply += int(held > total)

            gates = {
                "no_negative_holdings": negative_holdings == 0,
                "no_negative_average_costs": negative_costs == 0,
                "no_negative_dividend_balances": negative_dividends == 0,
                "holdings_do_not_exceed_circulation": holdings_over_circulation == 0,
                "holdings_do_not_exceed_total_supply": holdings_over_supply == 0,
            }
            return {
                "negative_holdings": negative_holdings,
                "negative_average_costs": negative_costs,
                "negative_dividend_balances": negative_dividends,
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
    trade_boundary = audit_trade_boundary()
    issuer_boundary = audit_issuer_boundary()
    gates = {
        "trade_boundary": bool(trade_boundary["pass"]),
        "issuer_boundary": bool(issuer_boundary["pass"]),
        **{f"lifecycle_{name}": bool(value) for name, value in lifecycle["gates"].items()},
        **{f"holdings_{name}": bool(value) for name, value in holdings["gates"].items()},
    }
    return {
        "certification": "player-share-economic-foundation",
        "read_only": True,
        "lifecycle": lifecycle,
        "holdings": holdings,
        "trade_boundary": trade_boundary,
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
