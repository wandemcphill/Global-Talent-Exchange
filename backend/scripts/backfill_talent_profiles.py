"""Backfill the talent-discovery projection from canonical player records.

This command is deliberately boring: it only calls the existing deterministic
TalentExchangeService.sync_profile_from_player() projection path. It never
creates football facts, changes economic valuation, or bypasses manual fields.

Examples:
    python -m scripts.backfill_talent_profiles --dry-run --limit 100
    python -m scripts.backfill_talent_profiles --limit 1000 --batch-size 100
    python -m scripts.backfill_talent_profiles --after-id <player-id> --limit 500

The command is resumable by player id. A production run should normally start
with --dry-run, inspect the counts, then run with an explicit --limit.
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass

from sqlalchemy import select

from app.core.database import get_session_factory, load_model_modules
from app.ingestion.models import Player
from app.talent.models import TalentProfile
from app.talent.service import TalentExchangeError, TalentExchangeService

logger = logging.getLogger("gtex.talent_backfill")


@dataclass(frozen=True, slots=True)
class BackfillResult:
    scanned: int
    created: int
    refreshed: int
    failed: int
    last_player_id: str | None


def run_backfill(
    *,
    limit: int,
    batch_size: int,
    after_id: str | None,
    dry_run: bool,
) -> BackfillResult:
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    load_model_modules()
    session_factory = get_session_factory()
    scanned = created = refreshed = failed = 0
    last_player_id: str | None = after_id

    with session_factory() as session:
        while scanned < limit:
            remaining = min(batch_size, limit - scanned)
            statement = (
                select(Player.id)
                .where(Player.id > last_player_id if last_player_id else True)
                .order_by(Player.id.asc())
                .limit(remaining)
            )
            player_ids = list(session.scalars(statement).all())
            if not player_ids:
                break

            service = TalentExchangeService(session)
            batch_created = batch_refreshed = batch_failed = 0
            for player_id in player_ids:
                profile_before = session.scalar(
                    select(TalentProfile).where(TalentProfile.player_id == player_id)
                )
                try:
                    service.sync_profile_from_player(player_id)
                    if profile_before is None:
                        batch_created += 1
                    else:
                        batch_refreshed += 1
                    last_player_id = player_id
                    scanned += 1
                except TalentExchangeError:
                    batch_failed += 1
                    failed += 1
                    logger.exception("talent_backfill.player_failed player_id=%s", player_id)
                    last_player_id = player_id
                    scanned += 1

            if dry_run:
                session.rollback()
            else:
                session.commit()

            created += batch_created
            refreshed += batch_refreshed
            if dry_run:
                logger.info(
                    "talent_backfill.dry_run batch=%s scanned=%s would_create=%s would_refresh=%s failed=%s last=%s",
                    len(player_ids),
                    scanned,
                    batch_created,
                    batch_refreshed,
                    batch_failed,
                    last_player_id,
                )
            else:
                logger.info(
                    "talent_backfill.batch committed=%s scanned=%s created=%s refreshed=%s failed=%s last=%s",
                    len(player_ids),
                    scanned,
                    batch_created,
                    batch_refreshed,
                    batch_failed,
                    last_player_id,
                )

    return BackfillResult(scanned, created, refreshed, failed, last_player_id)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill GTEX talent-discovery profiles from canonical players.")
    parser.add_argument("--limit", type=int, default=100, help="maximum players to scan")
    parser.add_argument("--batch-size", type=int, default=50, help="commit/checkpoint size")
    parser.add_argument("--after-id", default=None, help="resume strictly after this player id")
    parser.add_argument("--dry-run", action="store_true", help="rollback every batch after calculating counts")
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    args = build_parser().parse_args()
    result = run_backfill(
        limit=args.limit,
        batch_size=args.batch_size,
        after_id=args.after_id,
        dry_run=args.dry_run,
    )
    logger.info(
        "talent_backfill.complete scanned=%s created=%s refreshed=%s failed=%s last_player_id=%s",
        result.scanned,
        result.created,
        result.refreshed,
        result.failed,
        result.last_player_id,
    )
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
