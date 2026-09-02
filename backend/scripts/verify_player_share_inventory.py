from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import func, or_, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import create_database_engine, create_session_factory
from app.ingestion.models import Player
from app.market.player_eligibility_policy import is_share_market_eligible
from app.models.player_token_market import PlayerShareMarket

DEFAULT_MINIMUM = 5000
DEFAULT_BATCH_SIZE = 1000
DEFAULT_LIQUIDITY_FLOOR = Decimal("25.0000")


def _has_context(player: Player) -> bool:
    return bool(
        player.current_club_id
        or player.current_competition_id
        or player.internal_league_id
        or (player.real_world_club_name or "").strip()
        or (player.real_world_league_name or "").strip()
    )


def _searchable(player: Player) -> bool:
    return bool(
        player.is_real_player
        and player.is_tradable
        and (player.canonical_display_name or player.full_name or "").strip()
        and player.country_id
        and _has_context(player)
    )


def _market_buyable(market: PlayerShareMarket) -> bool:
    available = int(market.total_shares or 0) - int(market.circulating_shares or 0)
    metadata = market.metadata_json or {}
    liquidity = Decimal(str(metadata.get("liquidity_coin", "0")))
    required = max(Decimal(str(metadata.get("initial_liquidity_coin", "0"))), DEFAULT_LIQUIDITY_FLOOR)
    return bool(
        market.status == "active"
        and is_share_market_eligible(market.player)
        and available > 0
        and liquidity >= required
    )


def _market_tradeable(market: PlayerShareMarket) -> bool:
    return bool(
        market.status == "active"
        and is_share_market_eligible(market.player)
        and int(market.total_shares or 0) > int(market.circulating_shares or 0)
    )


def verify_inventory(
    *,
    database_url: str | None,
    minimum: int,
    batch_size: int,
) -> dict[str, Any]:
    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as session:
            searchable_filters = [
                Player.is_real_player.is_(True),
                Player.is_tradable.is_(True),
                or_(Player.canonical_display_name.is_not(None), Player.full_name.is_not(None)),
                Player.country_id.is_not(None),
                or_(
                    Player.current_club_id.is_not(None),
                    Player.current_competition_id.is_not(None),
                    Player.internal_league_id.is_not(None),
                    Player.real_world_club_name.is_not(None),
                    Player.real_world_league_name.is_not(None),
                ),
            ]
            searchable = int(session.scalar(select(func.count(Player.id)).where(*searchable_filters)) or 0)
            total_markets = int(session.scalar(select(func.count(PlayerShareMarket.id))) or 0)
            active_markets = int(
                session.scalar(select(func.count(PlayerShareMarket.id)).where(PlayerShareMarket.status == "active")) or 0
            )

            buyable = 0
            tradeable = 0
            blocked_active = 0
            liquidity_shortfall = 0
            checked = 0
            last_id: str | None = None

            while True:
                statement = (
                    select(PlayerShareMarket)
                    .join(Player, Player.id == PlayerShareMarket.player_id)
                    .where(PlayerShareMarket.status.in_(["active", "paused", "closed"]))
                    .order_by(PlayerShareMarket.player_id.asc())
                    .limit(batch_size)
                )
                if last_id is not None:
                    statement = statement.where(PlayerShareMarket.player_id > last_id)
                markets = list(session.scalars(statement).all())
                if not markets:
                    break
                for market in markets:
                    checked += 1
                    if market.status == "active" and not is_share_market_eligible(market.player):
                        blocked_active += 1
                    if market.status == "active" and _market_tradeable(market):
                        tradeable += 1
                        if _market_buyable(market):
                            buyable += 1
                        else:
                            liquidity_shortfall += 1
                last_id = markets[-1].player_id

            report = {
                "minimum_required": minimum,
                "searchable_universe": searchable,
                "total_share_markets": total_markets,
                "active_share_markets": active_markets,
                "tradeable_share_markets": tradeable,
                "buyable_share_markets": buyable,
                "blocked_active_markets": blocked_active,
                "liquidity_or_supply_failures": liquidity_shortfall,
                "markets_checked": checked,
                "gates": {
                    "searchable": searchable >= minimum,
                    "buyable": buyable >= minimum,
                    "tradeable": tradeable >= minimum,
                    "no_blocked_active_markets": blocked_active == 0,
                },
            }
            report["pass"] = all(report["gates"].values())
            return report
    finally:
        engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only certification of the GTEX player-share inventory.")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--minimum", type=int, default=DEFAULT_MINIMUM)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.minimum < 1 or args.batch_size < 1:
        raise SystemExit("--minimum and --batch-size must be positive")
    report = verify_inventory(database_url=args.database_url, minimum=args.minimum, batch_size=args.batch_size)
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
