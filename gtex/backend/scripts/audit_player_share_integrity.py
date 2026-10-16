from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.models.player_token_market import PlayerShareMarket


@dataclass(frozen=True)
class IntegrityReport:
    players: int
    markets: int
    active_markets: int
    active_ineligible_markets: int
    zero_price_markets: int
    negative_supply_markets: int
    over_circulated_markets: int

    @property
    def healthy(self) -> bool:
        return not any(
            (
                self.active_ineligible_markets,
                self.zero_price_markets,
                self.negative_supply_markets,
                self.over_circulated_markets,
            )
        )


def audit(session: Session) -> IntegrityReport:
    players = int(session.scalar(select(func.count(Player.id))) or 0)
    markets = int(session.scalar(select(func.count(PlayerShareMarket.id))) or 0)
    active_markets = int(
        session.scalar(
            select(func.count(PlayerShareMarket.id)).where(PlayerShareMarket.status == "active")
        )
        or 0
    )
    active_ineligible_markets = int(
        session.scalar(
            select(func.count(PlayerShareMarket.id))
            .join(Player, Player.id == PlayerShareMarket.player_id)
            .where(
                PlayerShareMarket.status == "active",
                Player.is_tradable.is_not(True),
            )
        )
        or 0
    )
    zero_price_markets = int(
        session.scalar(
            select(func.count(PlayerShareMarket.id)).where(PlayerShareMarket.share_price_coin <= 0)
        )
        or 0
    )
    negative_supply_markets = int(
        session.scalar(
            select(func.count(PlayerShareMarket.id)).where(
                PlayerShareMarket.total_shares < 0,
                )
        )
        or 0
    )
    over_circulated_markets = int(
        session.scalar(
            select(func.count(PlayerShareMarket.id)).where(
                PlayerShareMarket.circulating_shares > PlayerShareMarket.total_shares,
            )
        )
        or 0
    )
    return IntegrityReport(
        players=players,
        markets=markets,
        active_markets=active_markets,
        active_ineligible_markets=active_ineligible_markets,
        zero_price_markets=zero_price_markets,
        negative_supply_markets=negative_supply_markets,
        over_circulated_markets=over_circulated_markets,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only player-share market integrity audit")
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()

    engine = create_engine(args.database_url, pool_pre_ping=True)
    with Session(engine) as session:
        report = audit(session)
    print(json.dumps(asdict(report), sort_keys=True, indent=2))
    return 0 if report.healthy else 2


if __name__ == "__main__":
    raise SystemExit(main())
