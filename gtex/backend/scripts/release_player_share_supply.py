from __future__ import annotations

import argparse
import json

from app.core.database import create_database_engine, create_session_factory
from app.models.user import User
from app.players.token_service import PlayerTokenMarketError, PlayerTokenMarketService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Release additional primary supply for one GTEX player-share market.")
    parser.add_argument("--player-id", required=True)
    parser.add_argument("--release-count", type=int, required=True)
    parser.add_argument("--actor-user-id", required=True)
    parser.add_argument("--activate", action="store_true", help="Persist the release; default is a dry run.")
    parser.add_argument("--database-url")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.release_count < 1:
        raise SystemExit("--release-count must be greater than zero")

    engine = create_database_engine(args.database_url)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        actor = session.get(User, args.actor_user_id)
        if actor is None:
            raise SystemExit(f"Admin actor {args.actor_user_id!r} was not found")

        service = PlayerTokenMarketService(session)
        try:
            market = service.release_shares(
                actor=actor,
                player_id=args.player_id,
                release_count=args.release_count,
            )
        except PlayerTokenMarketError as exc:
            raise SystemExit(f"{exc.reason}: {exc.detail}") from exc

        report = {
            "dry_run": not args.activate,
            "player_id": args.player_id,
            "market_id": market.id,
            "released_shares": market.released_shares,
            "circulating_shares": market.circulating_shares,
            "total_shares": market.total_shares,
        }
        if args.activate:
            session.commit()
        else:
            session.rollback()

    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
