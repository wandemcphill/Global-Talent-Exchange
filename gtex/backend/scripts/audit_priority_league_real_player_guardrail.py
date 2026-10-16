from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Sequence

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError

SCRIPT_PATH = Path(__file__).resolve()
BACKEND_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = BACKEND_ROOT.parent
for candidate in (REPO_ROOT, BACKEND_ROOT, SCRIPT_PATH.parent):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from app.core.database import create_database_engine
from backfill_sportmonks_player_metadata import (
    _DEFAULT_PRIORITY_LEAGUES,
    _parse_priority_leagues,
    _priority_league_match_labels,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Report GTEX real-player data quality for priority first-division leagues without mutating data."
        )
    )
    parser.add_argument("--database-url", default=os.environ.get("GTE_DATABASE_URL"))
    parser.add_argument(
        "--priority-leagues",
        type=_parse_priority_leagues,
        default=_DEFAULT_PRIORITY_LEAGUES,
        help="Priority league set to audit. Use top-first-divisions for the default GTEX top-league lane.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when any priority league player is missing required metadata, photo, or real value.",
    )
    parser.add_argument("--db-retry-attempts", type=int, default=6)
    parser.add_argument("--db-retry-base-seconds", type=float, default=8.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.database_url:
        raise SystemExit("--database-url or GTE_DATABASE_URL is required.")

    reports = _audit_leagues_with_retries(
        database_url=args.database_url,
        priority_leagues=tuple(args.priority_leagues),
        attempts=max(1, int(args.db_retry_attempts)),
        base_seconds=max(0.0, float(args.db_retry_base_seconds)),
    )

    totals = {
        "players": sum(int(report["players"]) for report in reports),
        "missing_club": sum(int(report["missing_club"]) for report in reports),
        "missing_competition": sum(int(report["missing_competition"]) for report in reports),
        "missing_country": sum(int(report["missing_country"]) for report in reports),
        "missing_date_of_birth": sum(int(report["missing_date_of_birth"]) for report in reports),
        "missing_photo": sum(int(report["missing_photo"]) for report in reports),
        "missing_real_value": sum(int(report["missing_real_value"]) for report in reports),
    }
    payload = {
        "priority_leagues": list(args.priority_leagues),
        "leagues": reports,
        "totals": totals,
        "strict": bool(args.strict),
    }
    print(json.dumps(payload, sort_keys=True, default=str))
    if args.strict and any(value for key, value in totals.items() if key != "players"):
        return 1
    return 0


def _audit_leagues_with_retries(
    *,
    database_url: str,
    priority_leagues: Sequence[str],
    attempts: int,
    base_seconds: float,
) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        engine = create_database_engine(database_url)
        try:
            return [
                _audit_league(engine, canonical_league=league)
                for league in tuple(priority_leagues)
            ]
        except (OperationalError, DBAPIError) as exc:
            last_error = exc
            if attempt >= attempts:
                raise
            delay = min(base_seconds * (2 ** (attempt - 1)), 30.0)
            print(
                json.dumps(
                    {
                        "warning": "priority_guardrail_retry",
                        "attempt": attempt,
                        "delay_seconds": delay,
                        "error": str(exc).splitlines()[0],
                    },
                    sort_keys=True,
                ),
                file=sys.stderr,
            )
            time.sleep(delay)
        finally:
            engine.dispose()
    if last_error is not None:
        raise last_error
    return []


def _audit_league(engine, *, canonical_league: str) -> dict[str, Any]:
    labels = _priority_league_match_labels((canonical_league,))
    parameters = {f"label_{index}": label.lower() for index, label in enumerate(labels)}
    label_clause = ", ".join(f":label_{index}" for index in range(len(labels)))
    if canonical_league == "Premier League":
        league_predicate = """
              and (
                   lower(p.real_world_league_name) = 'english premier league'
                or lower(c.name) = 'english premier league'
                or lower(s.current_competition_name) = 'english premier league'
                or lower(r.current_league_name) = 'english premier league'
                or (
                    (
                         lower(p.real_world_league_name) = 'premier league'
                      or lower(c.name) = 'premier league'
                      or lower(s.current_competition_name) = 'premier league'
                      or lower(r.current_league_name) = 'premier league'
                    )
                    and (
                         lower(comp_country.name) in ('england', 'united kingdom')
                      or lower(club_country.name) in ('england', 'united kingdom')
                    )
                )
              )
        """
    else:
        league_predicate = f"""
              and (
                   lower(p.real_world_league_name) in ({label_clause})
                or lower(c.name) in ({label_clause})
                or lower(s.current_competition_name) in ({label_clause})
                or lower(r.current_league_name) in ({label_clause})
              )
        """
    query = text(
        f"""
        with matched_players as (
            select distinct p.id,
                   p.current_club_id,
                   p.current_competition_id,
                   p.country_id,
                   p.date_of_birth,
                   p.market_value_eur
            from ingestion_players p
            left join ingestion_competitions c
              on c.id = p.current_competition_id
            left join ingestion_countries comp_country
              on comp_country.id = c.country_id
            left join ingestion_clubs club
              on club.id = p.current_club_id
            left join ingestion_countries club_country
              on club_country.id = club.country_id
            left join player_summary_read_models s
              on s.player_id = p.id
            left join real_player_profiles r
              on r.source_name = p.source_provider
             and r.source_player_key = p.provider_external_id
            where p.is_real_player is true
              and p.is_tradable is true
              and lower(p.source_provider) = 'sportmonks'
              {league_predicate}
        )
        select count(*) as players,
               count(*) filter (where current_club_id is null) as missing_club,
               count(*) filter (where current_competition_id is null) as missing_competition,
               count(*) filter (where country_id is null) as missing_country,
               count(*) filter (where date_of_birth is null) as missing_date_of_birth,
               count(*) filter (
                 where not exists (
                   select 1
                   from ingestion_player_image_metadata image
                   where image.player_id = matched_players.id
                     and image.image_role = 'portrait'
                     and lower(image.source_provider) = 'sportmonks'
                     and image.moderation_status = 'approved'
                     and image.source_url is not null
                     and length(trim(image.source_url)) > 0
                 )
               ) as missing_photo,
               count(*) filter (where market_value_eur is null or market_value_eur <= 0) as missing_real_value
        from matched_players
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, parameters).mappings().one()
    return {
        "league": canonical_league,
        "match_labels": list(labels),
        **{key: int(row[key] or 0) for key in row.keys()},
    }


if __name__ == "__main__":
    raise SystemExit(main())
