"""Give existing national-pool regen seeds their full generated profile.

New seeds get a profile snapshot at creation time. Seeds created before that
change carry only the flat scalars the old seeder kept, so their regen dossier
404s. This backfills them.

The profile is generated deterministically from each seed's immutable
``seed_key``, and every field the seed already publishes - name, age, position,
ratings, growth curve, country - is written back over the generated one, so a
backfilled dossier can never contradict the card it was opened from.

Idempotent: a seed that already carries a snapshot is skipped, so the job is
safe to re-run and safe to interrupt. Pass ``--regenerate`` to rewrite
snapshots after a version bump.

No ``ingestion_players``, ``player_cards`` or ``club_profiles`` rows are
created and nothing becomes tradable - see
``app/regen_universe/seed_profile_service.py`` for why seeds deliberately do
not get real ``regen_profiles`` rows.

Usage:
    python -m scripts.backfill_national_seed_profiles --dry-run
    python -m scripts.backfill_national_seed_profiles --limit 100000
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass

from sqlalchemy import select

from app.core.database import get_session_factory, load_model_modules
from app.models.regen_ecosystem import NationalRegenSeed
from app.regen_universe.seed_profile_service import (
    RegenSeedProfileService,
    build_seed_profile_view,
)

logger = logging.getLogger("backfill_national_seed_profiles")


@dataclass
class BackfillResult:
    scanned: int = 0
    written: int = 0
    skipped_existing: int = 0
    failed: int = 0

    def as_line(self) -> str:
        return (
            f"scanned={self.scanned} written={self.written} "
            f"skipped_existing={self.skipped_existing} failed={self.failed}"
        )


def run_backfill(
    *,
    limit: int,
    batch_size: int,
    regenerate: bool,
    dry_run: bool,
) -> BackfillResult:
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    load_model_modules()
    session_factory = get_session_factory()
    result = BackfillResult()
    last_seed_id: str | None = None

    with session_factory() as session:
        service = RegenSeedProfileService(session)
        while result.scanned < limit:
            remaining = min(batch_size, limit - result.scanned)
            statement = (
                select(NationalRegenSeed)
                .where(
                    NationalRegenSeed.id > last_seed_id
                    if last_seed_id is not None
                    else True
                )
                .order_by(NationalRegenSeed.id.asc())
                .limit(remaining)
            )
            seeds = list(session.scalars(statement).all())
            if not seeds:
                break

            for seed in seeds:
                result.scanned += 1
                last_seed_id = seed.id
                if not regenerate and service.snapshot_for(seed) is not None:
                    result.skipped_existing += 1
                    continue
                try:
                    # One seed per savepoint: a single bad row must not roll
                    # back a whole batch of good ones.
                    with session.begin_nested():
                        view = build_seed_profile_view(seed)
                        service.attach_snapshot(seed, view)
                    result.written += 1
                except Exception as exc:  # pragma: no cover - operational path
                    result.failed += 1
                    logger.warning("seed %s failed: %s", seed.id, exc)

            if dry_run:
                session.rollback()
            else:
                session.commit()
            logger.info("progress %s", result.as_line())

    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=1_000_000)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Rewrite snapshots that already exist (after a version bump).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing anything.",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args()
    result = run_backfill(
        limit=args.limit,
        batch_size=args.batch_size,
        regenerate=args.regenerate,
        dry_run=args.dry_run,
    )
    logger.info("done%s %s", " (dry run)" if args.dry_run else "", result.as_line())
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
