from __future__ import annotations

import argparse
import json
import os
from typing import Sequence

from sqlalchemy import func, select, update

from app.core.database import create_database_engine, create_session_factory, load_model_modules
from app.ingestion.models import Player


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Mark imported real players as GTEX tradeable and audit the visible player-market universe."
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("GTE_DATABASE_URL"),
        help="Target database URL. Defaults to GTE_DATABASE_URL.",
    )
    parser.add_argument(
        "--min-count",
        type=int,
        default=17000,
        help="Minimum real tradable player count required for a successful audit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report counts without updating player rows.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.database_url:
        raise SystemExit("--database-url or GTE_DATABASE_URL is required.")

    load_model_modules()
    engine = create_database_engine(args.database_url)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        real_count = session.scalar(
            select(func.count()).select_from(Player).where(Player.is_real_player.is_(True))
        ) or 0
        tradable_before = session.scalar(
            select(func.count())
            .select_from(Player)
            .where(Player.is_real_player.is_(True), Player.is_tradable.is_(True))
        ) or 0

        updated = 0
        if not args.dry_run:
            result = session.execute(
                update(Player)
                .where(Player.is_real_player.is_(True), Player.is_tradable.is_(False))
                .values(is_tradable=True)
            )
            updated = int(result.rowcount or 0)
            session.commit()

        tradable_after = session.scalar(
            select(func.count())
            .select_from(Player)
            .where(Player.is_real_player.is_(True), Player.is_tradable.is_(True))
        ) or 0

    payload = {
        "real_players": int(real_count),
        "tradable_before": int(tradable_before),
        "updated": updated,
        "tradable_after": int(tradable_after),
        "min_count": int(args.min_count),
        "ok": int(tradable_after) >= int(args.min_count),
        "dry_run": bool(args.dry_run),
    }
    print(json.dumps(payload, sort_keys=True))
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
