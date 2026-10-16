"""Seed regen award definitions and open a regen season if none is active.

The regen metagame surfaces (rankings, hall of fame, awards, bloodlines) all
hang off an active `RegenSeason`.  With no active season, `/api/regen-universe/
rankings` returns `season: null` and zero entries no matter how many regens
exist, so the Regen World screen renders empty.

Idempotent: if a season is already active this exits 0 without touching it.

Run from the repo root:

    python backend/scripts/open_regen_season.py --database-url "$DATABASE_URL"
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
for candidate in (str(ROOT_DIR), str(BACKEND_DIR)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from sqlalchemy import func, select

# `app.models` is the aggregate registry and must be imported before any
# individual model module, otherwise importing app.regen_universe.models
# directly re-enters it mid-initialization and raises a circular ImportError.
import app.models  # noqa: F401
from app.core.database import (
    create_database_engine,
    create_session_factory,
    ensure_database_schema_current,
)
from app.regen_universe.models import RegenSeason
from app.regen_universe.service import RegenUniverseService


def open_regen_season(*, database_url: str, season_days: int) -> dict[str, object]:
    engine = create_database_engine(database_url)
    try:
        ensure_database_schema_current(engine)
        session_factory = create_session_factory(engine)
        with session_factory() as session:
            service = RegenUniverseService(session)

            # Sample before seeding: seed_defaults() opens a season itself when
            # none is active, so checking afterwards cannot tell "already there"
            # from "just created" and would report a no-op for real work.
            pre_existing = session.scalar(select(RegenSeason).where(RegenSeason.is_active.is_(True)))

            # Award definitions are a prerequisite for the awards/hall-of-fame
            # surfaces and are upserted in place, so this is safe to re-run.
            service.seed_defaults()

            active = session.scalar(select(RegenSeason).where(RegenSeason.is_active.is_(True)))
            if active is not None:
                session.commit()
                return {
                    "created": pre_existing is None,
                    "reason": ("seeded_by_defaults" if pre_existing is None else "active_season_already_exists"),
                    "season_number": active.season_number,
                    "start_date": active.start_date.isoformat(),
                    "end_date": active.end_date.isoformat(),
                }

            highest = int(session.scalar(select(func.max(RegenSeason.season_number))) or 0)
            start_date = date.today()
            season = service.create_season(
                season_number=highest + 1,
                start_date=start_date,
                end_date=start_date + timedelta(days=season_days),
                is_active=True,
            )
            session.commit()
            return {
                "created": True,
                "season_number": season.season_number,
                "start_date": season.start_date.isoformat(),
                "end_date": season.end_date.isoformat(),
            }
    finally:
        engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True, help="Target database URL.")
    parser.add_argument(
        "--season-days",
        type=int,
        default=365,
        help="Length of the season window in days (default: 365).",
    )
    args = parser.parse_args(argv)

    result = open_regen_season(database_url=args.database_url, season_days=args.season_days)
    if result["created"]:
        print(f"Opened regen season {result['season_number']} " f"({result['start_date']} -> {result['end_date']})")
    else:
        print(
            f"Regen season {result['season_number']} is already active "
            f"({result['start_date']} -> {result['end_date']}); nothing to do."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
