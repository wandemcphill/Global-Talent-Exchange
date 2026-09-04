"""One-time backfill: resolve country/club for players ingestion never resolved.

services/player-ingestion's upsertAppPlayerMirror wrote every sportmonks player
into ingestion_players with country_id and current_club_id permanently null
(fixed going forward in the same PR that adds this script). That bug left
16,077 tradable real players unable to be issued a share market -- the strict
issuer requires both a country and a club/competition context.

The SportMonks subscription that fed this pipeline has since been revoked, so
there will be no further ingestion cycles to let that fix self-heal the
existing backlog. But the data was never actually missing: services/player-
ingestion's own internal `players` table already stores each player's
`nationality` and `team_id`, captured at original ingestion time and
untouched by the subscription revocation. This backfill reads that cached
data instead of calling SportMonks again.

Resolution mirrors resolveCountryIdByName / resolveClubIdBySportmonksTeamId in
services/player-ingestion/src/repository.js, so a player resolves identically
whether ingestion or this backfill processes it:
  - country_id: case-insensitive match against ingestion_countries
    name/alpha2_code/alpha3_code/fifa_code
  - current_club_id: source_provider='sportmonks' lookup against
    ingestion_clubs.provider_external_id

Verified against production (read-only) before writing this script: of the
16,077 unissued players, 15,555 (96.7%) have a resolvable country, and 100%
have a team name available via the Node service's own `teams` table (keyed by
team_id) even where the exact club is not in the much smaller ingestion_clubs
table (only 1,909 resolve there). real_world_club_name is populated from that
team name so the eligibility check's club-or-competition-context requirement
is satisfied for the full backlog, not just the players whose club has a
canonical ingestion_clubs row.

Idempotent: only writes to a column that is currently NULL, so it is safe to
re-run and cannot clobber a value ingestion or this script already resolved.

Batches and commits every COMMIT_BATCH_SIZE rows rather than one commit for
the whole run -- the regen name/portrait repair job OOM'd a 512Mi worker doing
exactly the single-big-commit pattern this avoids.

Run co-located with the database (a Render job), not from a laptop: pulling
tens of thousands of full player rows over a slow remote link is what the
issuance backfill script already warns is impractical at this volume.

Usage:
    python backend/scripts/backfill_ingested_player_country_club.py \
        --database-url "$DATABASE_URL"
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
for candidate in (str(ROOT_DIR), str(BACKEND_DIR)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from sqlalchemy import select, text

# `app.models` is the aggregate registry and must be imported before any
# individual model module, otherwise importing a model directly re-enters it
# mid-initialization and raises a circular ImportError.
import app.models  # noqa: F401, E402
from app.core.database import create_database_engine, create_session_factory  # noqa: E402
from app.ingestion.models import Country  # noqa: E402

COMMIT_BATCH_SIZE = 1000


def backfill(*, database_url: str, batch_size: int = COMMIT_BATCH_SIZE, dry_run: bool = False) -> dict[str, int]:
    engine = create_database_engine(database_url)
    summary = {
        "candidates": 0,
        "country_resolved": 0,
        "club_id_resolved": 0,
        "club_name_resolved": 0,
        "no_cached_data": 0,
    }
    try:
        session_factory = create_session_factory(engine)
        with session_factory() as session:
            # Country lookup, keyed every way a cached nationality string might
            # spell it -- mirrors resolveCountryIdByName's OR chain exactly.
            countries = list(session.scalars(select(Country)))
            country_id_by_key: dict[str, str] = {}
            for country in countries:
                for key in (country.name, country.alpha2_code, country.alpha3_code, country.fifa_code):
                    if key:
                        country_id_by_key.setdefault(key.strip().lower(), country.id)

            candidate_rows = session.execute(text("""
                    SELECT p.id, pl.nationality, pl.team_id
                    FROM ingestion_players p
                    LEFT JOIN player_share_markets m ON m.player_id = p.id
                    JOIN players pl ON pl.player_id::text = p.provider_external_id
                    WHERE p.is_tradable
                      AND m.id IS NULL
                      AND p.source_provider = 'sportmonks'
                      AND (p.country_id IS NULL OR p.current_club_id IS NULL OR p.real_world_club_name IS NULL)
                    """)).all()
            summary["candidates"] = len(candidate_rows)

            # ingestion_clubs (sportmonks rows) and teams are both small reference
            # tables (hundreds to low thousands of rows) -- fetch each whole and
            # index in memory, the same approach already used for countries above,
            # rather than parameterizing a Postgres array over the candidate set.
            club_rows = session.execute(
                text("SELECT provider_external_id, id FROM ingestion_clubs WHERE source_provider = 'sportmonks'")
            ).all()
            club_id_by_team_id: dict[int, str] = {}
            for row in club_rows:
                try:
                    club_id_by_team_id[int(row.provider_external_id)] = row.id
                except (TypeError, ValueError):
                    continue

            team_name_rows = session.execute(text("SELECT team_id, name FROM teams WHERE name IS NOT NULL")).all()
            team_name_by_team_id: dict[int, str] = {row.team_id: row.name for row in team_name_rows}

            pending = 0
            for row in candidate_rows:
                nationality = (row.nationality or "").strip().lower()
                country_id = country_id_by_key.get(nationality)
                club_id = club_id_by_team_id.get(row.team_id) if row.team_id is not None else None
                club_name = team_name_by_team_id.get(row.team_id) if row.team_id is not None else None

                if country_id is None and club_id is None and club_name is None:
                    summary["no_cached_data"] += 1
                    continue

                assignments = []
                params: dict[str, object] = {"player_id": row.id}
                if country_id is not None:
                    assignments.append("country_id = COALESCE(country_id, :country_id)")
                    params["country_id"] = country_id
                    summary["country_resolved"] += 1
                if club_id is not None:
                    assignments.append("current_club_id = COALESCE(current_club_id, :club_id)")
                    params["club_id"] = club_id
                    summary["club_id_resolved"] += 1
                if club_name is not None:
                    assignments.append("real_world_club_name = COALESCE(real_world_club_name, :club_name)")
                    params["club_name"] = club_name
                    summary["club_name_resolved"] += 1

                if dry_run:
                    continue
                session.execute(
                    text(f"UPDATE ingestion_players SET {', '.join(assignments)} WHERE id = :player_id"),
                    params,
                )
                pending += 1
                if pending >= batch_size:
                    session.commit()
                    session.expunge_all()
                    pending = 0

            if dry_run:
                session.rollback()
            else:
                session.commit()
    finally:
        engine.dispose()
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True, help="Target database URL.")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=COMMIT_BATCH_SIZE,
        help=f"Rows per commit (default: {COMMIT_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and print the summary without writing or committing anything.",
    )
    args = parser.parse_args(argv)

    summary = backfill(database_url=args.database_url, batch_size=args.batch_size, dry_run=args.dry_run)
    if args.dry_run:
        print("== DRY RUN: no changes written ==")
    print(f"candidates scanned      : {summary['candidates']}")
    print(f"country_id resolved     : {summary['country_resolved']}")
    print(f"current_club_id resolved: {summary['club_id_resolved']}")
    print(f"real_world_club_name set: {summary['club_name_resolved']}")
    print(f"no cached data at all   : {summary['no_cached_data']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
