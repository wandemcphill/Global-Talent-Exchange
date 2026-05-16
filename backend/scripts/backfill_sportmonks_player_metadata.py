from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime, timedelta
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Sequence
from uuid import uuid4

from sqlalchemy import case, exists, func, or_, select, text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session

SCRIPT_PATH = Path(__file__).resolve()
BACKEND_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = BACKEND_ROOT.parent
for candidate in (REPO_ROOT, BACKEND_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from app.core.database import create_database_engine, create_session_factory, load_model_modules
from app.ingestion.models import Club, Competition, Country, Player, PlayerImageMetadata
from app.ingestion.normalizers import clean_name, normalize_position, slugify
from app.models.real_player_profile import RealPlayerProfile
from app.players.read_models import PlayerSummaryReadModel
from app.providers.sportmonks_adapter import SportMonksAdapter


@dataclass(slots=True)
class PlayerMetadataFacts:
    player_id: str
    provider_player_id: str
    full_name: str | None = None
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    position: str | None = None
    detailed_position: str | None = None
    nationality_name: str | None = None
    nationality_code: str | None = None
    nationality_provider_id: str | None = None
    date_of_birth: date | None = None
    club_name: str | None = None
    club_provider_id: str | None = None
    club_country_name: str | None = None
    competition_name: str | None = None
    competition_provider_id: str | None = None
    season_provider_id: str | None = None
    photo_url: str | None = None
    raw_payload: dict[str, Any] | None = None


@dataclass(slots=True)
class BackfillStats:
    selected: int = 0
    fetched: int = 0
    fetch_failed: int = 0
    no_provider_facts: int = 0
    players_updated: int = 0
    countries_created: int = 0
    competitions_created: int = 0
    clubs_created: int = 0
    images_updated: int = 0
    profiles_updated: int = 0
    summaries_updated: int = 0
    missing_country: int = 0
    missing_club: int = 0
    missing_competition: int = 0
    missing_date_of_birth: int = 0
    missing_photo: int = 0
    samples: list[dict[str, Any]] | None = None

    def add_sample(self, payload: dict[str, Any], *, limit: int) -> None:
        if self.samples is None:
            self.samples = []
        if len(self.samples) < limit:
            self.samples.append(payload)


@dataclass(slots=True)
class EntityCache:
    countries: dict[tuple[Any, ...], Country | None]
    competitions: dict[tuple[Any, ...], Competition | None]
    clubs: dict[tuple[Any, ...], Club | None]


_COUNTRY_LEAGUE_LABEL_OVERRIDES: dict[tuple[str, str], str] = {
    ("argentina", "primera division"): "Argentinian Primera Division",
    ("belgium", "pro league"): "Belgian Pro League",
    ("brazil", "serie a"): "Brazilian Serie A",
    ("egypt", "premier league"): "Egypt Premier League",
    ("england", "premier league"): "Premier League",
    ("france", "ligue 1"): "French Ligue 1",
    ("france", "ligue 2"): "French Ligue 2",
    ("greece", "super league"): "Greek Super League",
    ("italy", "serie a"): "Italian Serie A",
    ("italy", "serie b"): "Italian Serie B",
    ("saudi arabia", "pro league"): "Saudi Pro League",
    ("south africa", "premier league"): "South Africa Premier League",
    ("spain", "la liga 2"): "Spanish La Liga 2",
    ("switzerland", "super league"): "Swiss Super League",
    ("russia", "premier league"): "Russian Premier League",
}

_DEFAULT_API_TARGET_FIELDS: tuple[str, ...] = ("country", "club", "competition", "date_of_birth")
_API_TARGET_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "all": (*_DEFAULT_API_TARGET_FIELDS, "photo"),
    "metadata": _DEFAULT_API_TARGET_FIELDS,
    "facts": _DEFAULT_API_TARGET_FIELDS,
    "country": ("country",),
    "nationality": ("country",),
    "club": ("club",),
    "team": ("club",),
    "competition": ("competition",),
    "league": ("competition",),
    "dob": ("date_of_birth",),
    "birth": ("date_of_birth",),
    "date_of_birth": ("date_of_birth",),
    "date-of-birth": ("date_of_birth",),
    "photo": ("photo",),
    "image": ("photo",),
    "portrait": ("photo",),
}

_DEFAULT_PRIORITY_LEAGUES: tuple[str, ...] = (
    "Premier League",
    "La Liga",
    "Italian Serie A",
    "French Ligue 1",
    "Bundesliga",
    "Super Lig",
)

_PRIORITY_LEAGUE_ALIASES: dict[str, tuple[str, ...]] = {
    "top": _DEFAULT_PRIORITY_LEAGUES,
    "top_europe": _DEFAULT_PRIORITY_LEAGUES,
    "top-first-divisions": _DEFAULT_PRIORITY_LEAGUES,
    "top_first_divisions": _DEFAULT_PRIORITY_LEAGUES,
    "priority": _DEFAULT_PRIORITY_LEAGUES,
    "epl": ("Premier League",),
    "english_premier_league": ("Premier League",),
    "premier_league": ("Premier League",),
    "premier league": ("Premier League",),
    "la_liga": ("La Liga",),
    "la liga": ("La Liga",),
    "spanish_first_division": ("La Liga",),
    "spanish first division": ("La Liga",),
    "italian_first_division": ("Italian Serie A",),
    "italian first division": ("Italian Serie A",),
    "italian_serie_a": ("Italian Serie A",),
    "serie_a": ("Italian Serie A",),
    "serie a": ("Italian Serie A",),
    "french_first_division": ("French Ligue 1",),
    "french first division": ("French Ligue 1",),
    "french_ligue_1": ("French Ligue 1",),
    "ligue_1": ("French Ligue 1",),
    "ligue 1": ("French Ligue 1",),
    "german_first_division": ("Bundesliga",),
    "german first division": ("Bundesliga",),
    "german_bundesliga": ("Bundesliga",),
    "bundesliga": ("Bundesliga",),
    "turkish_first_division": ("Super Lig",),
    "turkish first division": ("Super Lig",),
    "turkish_super_lig": ("Super Lig",),
    "super_lig": ("Super Lig",),
    "super lig": ("Super Lig",),
    "süper_lig": ("Super Lig",),
    "süper lig": ("Super Lig",),
}

_PRIORITY_LEAGUE_MATCH_LABELS: dict[str, tuple[str, ...]] = {
    "Premier League": ("Premier League", "English Premier League"),
    "La Liga": ("La Liga", "Spanish La Liga"),
    "Italian Serie A": ("Italian Serie A",),
    "French Ligue 1": ("French Ligue 1", "Ligue 1"),
    "Bundesliga": ("Bundesliga", "German Bundesliga"),
    "Super Lig": ("Super Lig", "Süper Lig", "Turkish Super Lig"),
}


def _parse_api_target_fields(value: str | Sequence[str] | None) -> tuple[str, ...]:
    if value is None:
        return _DEFAULT_API_TARGET_FIELDS
    if isinstance(value, str):
        raw_items = [
            item.strip().lower().replace(" ", "_")
            for chunk in value.split(";")
            for item in chunk.split(",")
        ]
    else:
        raw_items = [str(item).strip().lower().replace(" ", "_") for item in value]
    fields: list[str] = []
    for item in raw_items:
        if not item:
            continue
        aliases = _API_TARGET_FIELD_ALIASES.get(item)
        if aliases is None:
            valid = ", ".join(sorted(_API_TARGET_FIELD_ALIASES))
            raise argparse.ArgumentTypeError(f"unknown API target field '{item}'. Valid values: {valid}")
        for alias in aliases:
            if alias not in fields:
                fields.append(alias)
    return tuple(fields) or _DEFAULT_API_TARGET_FIELDS


def _parse_priority_leagues(value: str | Sequence[str] | None) -> tuple[str, ...]:
    if value is None:
        return tuple()
    if isinstance(value, str):
        raw_items = [
            item.strip().lower().replace("-", "_").replace(" ", "_")
            for chunk in value.split(";")
            for item in chunk.split(",")
        ]
    else:
        raw_items = [str(item).strip().lower().replace("-", "_").replace(" ", "_") for item in value]
    leagues: list[str] = []
    for item in raw_items:
        if not item:
            continue
        aliases = _PRIORITY_LEAGUE_ALIASES.get(item)
        if aliases is None:
            valid = ", ".join(sorted(_PRIORITY_LEAGUE_ALIASES))
            raise argparse.ArgumentTypeError(f"unknown priority league '{item}'. Valid values: {valid}")
        for alias in aliases:
            if alias not in leagues:
                leagues.append(alias)
    return tuple(leagues)


def _priority_league_match_labels(leagues: Sequence[str]) -> tuple[str, ...]:
    labels: list[str] = []
    for league in leagues:
        for label in _PRIORITY_LEAGUE_MATCH_LABELS.get(league, (league,)):
            if label not in labels:
                labels.append(label)
    return tuple(labels)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill GTEX real-player metadata from SportMonks without generating fake market values. "
            "Repairs nationality, age/DOB, club, league, and approved SportMonks photos only."
        )
    )
    parser.add_argument("--database-url", default=os.environ.get("GTE_DATABASE_URL"))
    parser.add_argument("--apply", action="store_true", help="Write updates. Default is dry-run.")
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--source", choices=("staging", "api"), default="staging")
    parser.add_argument("--force", action="store_true", help="Overwrite existing club/league/DOB/name facts.")
    parser.add_argument("--update-names", action="store_true", help="Use provider full names/display names.")
    parser.add_argument("--pause-ms", type=int, default=0, help="Pause between SportMonks player requests.")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=100,
        help=(
            "For API apply runs, commit in chunks to avoid long idle database transactions while provider calls run."
        ),
    )
    parser.add_argument(
        "--skip-recent-hours",
        type=int,
        default=24,
        help=(
            "For API mode, skip players whose provider facts were refreshed within this many hours. "
            "Use 0 to disable."
        ),
    )
    parser.add_argument(
        "--target-fields",
        type=_parse_api_target_fields,
        default=_DEFAULT_API_TARGET_FIELDS,
        help=(
            "For API mode, select players missing these fields. Comma-separated values: "
            "metadata, country, club, competition, dob, photo, or all."
        ),
    )
    parser.add_argument(
        "--priority-leagues",
        type=_parse_priority_leagues,
        default=tuple(),
        help=(
            "For API mode, restrict selection to priority league players. Use top-first-divisions for "
            "Premier League, La Liga, Italian Serie A, French Ligue 1, Bundesliga, and Super Lig."
        ),
    )
    parser.add_argument("--db-retry-attempts", type=int, default=4)
    parser.add_argument("--db-retry-base-seconds", type=float, default=4.0)
    parser.add_argument(
        "--provider-fetch-attempts",
        type=int,
        default=2,
        help="Retry transient SportMonks player fetch failures this many times before skipping the player.",
    )
    parser.add_argument(
        "--provider-retry-base-ms",
        type=int,
        default=250,
        help="Base delay between transient SportMonks player fetch retries.",
    )
    parser.add_argument("--sample-size", type=int, default=10)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.database_url:
        raise SystemExit("--database-url or GTE_DATABASE_URL is required.")

    load_model_modules()
    engine = create_database_engine(args.database_url)
    session_factory = create_session_factory(engine)
    try:
        limit = max(int(args.limit), 1)
        chunk_size = max(int(args.chunk_size), 1)
        target_fields = tuple(args.target_fields)
        priority_leagues = tuple(args.priority_leagues)
        if args.apply and args.source == "api" and limit > chunk_size:
            stats = _backfill_api_in_committed_chunks(
                session_factory,
                limit=limit,
                offset=max(int(args.offset), 0),
                chunk_size=chunk_size,
                force=bool(args.force),
                update_names=bool(args.update_names),
                pause_ms=max(int(args.pause_ms), 0),
                skip_recent_hours=max(int(args.skip_recent_hours), 0),
                target_fields=target_fields,
                priority_leagues=priority_leagues,
                db_retry_attempts=max(int(args.db_retry_attempts), 1),
                db_retry_base_seconds=max(float(args.db_retry_base_seconds), 0.0),
                provider_fetch_attempts=max(int(args.provider_fetch_attempts), 1),
                provider_retry_base_ms=max(int(args.provider_retry_base_ms), 0),
                sample_size=max(int(args.sample_size), 0),
            )
        else:
            with session_factory() as session:
                stats = backfill_metadata(
                    session,
                    source=args.source,
                    apply=args.apply,
                    limit=limit,
                    offset=max(int(args.offset), 0),
                    force=bool(args.force),
                    update_names=bool(args.update_names),
                    pause_ms=max(int(args.pause_ms), 0),
                    skip_recent_hours=max(int(args.skip_recent_hours), 0),
                    target_fields=target_fields,
                    priority_leagues=priority_leagues,
                    provider_fetch_attempts=max(int(args.provider_fetch_attempts), 1),
                    provider_retry_base_ms=max(int(args.provider_retry_base_ms), 0),
                    sample_size=max(int(args.sample_size), 0),
                )
                if args.apply:
                    session.commit()

        payload = {
            **asdict(stats),
            "apply": bool(args.apply),
            "source": args.source,
            "limit": max(int(args.limit), 1),
            "offset": max(int(args.offset), 0),
            "chunk_size": max(int(args.chunk_size), 1),
            "force": bool(args.force),
            "update_names": bool(args.update_names),
            "skip_recent_hours": max(int(args.skip_recent_hours), 0),
            "target_fields": list(target_fields),
            "priority_leagues": list(priority_leagues),
            "db_retry_attempts": max(int(args.db_retry_attempts), 1),
            "db_retry_base_seconds": max(float(args.db_retry_base_seconds), 0.0),
            "provider_fetch_attempts": max(int(args.provider_fetch_attempts), 1),
            "provider_retry_base_ms": max(int(args.provider_retry_base_ms), 0),
        }
        print(json.dumps(payload, sort_keys=True, default=str))
        return 0
    finally:
        engine.dispose()


def _backfill_api_in_committed_chunks(
    session_factory,
    *,
    limit: int,
    offset: int,
    chunk_size: int,
    force: bool,
    update_names: bool,
    pause_ms: int,
    skip_recent_hours: int,
    target_fields: Sequence[str],
    priority_leagues: Sequence[str],
    db_retry_attempts: int,
    db_retry_base_seconds: float,
    provider_fetch_attempts: int,
    provider_retry_base_ms: int,
    sample_size: int,
) -> BackfillStats:
    aggregate = BackfillStats(samples=[])
    remaining = limit
    current_offset = offset
    while remaining > 0:
        current_limit = min(chunk_size, remaining)
        chunk_stats = _run_api_chunk_with_retries(
            session_factory,
            limit=current_limit,
            offset=current_offset,
            force=force,
            update_names=update_names,
            pause_ms=pause_ms,
            skip_recent_hours=skip_recent_hours,
            target_fields=target_fields,
            priority_leagues=priority_leagues,
            provider_fetch_attempts=provider_fetch_attempts,
            provider_retry_base_ms=provider_retry_base_ms,
            sample_size=sample_size,
            attempts=db_retry_attempts,
            base_seconds=db_retry_base_seconds,
        )
        if chunk_stats.selected == 0:
            break
        _merge_stats(aggregate, chunk_stats, sample_size=sample_size)
        remaining -= chunk_stats.selected
        if force or skip_recent_hours <= 0:
            current_offset += chunk_stats.selected
    if not aggregate.samples:
        aggregate.samples = None
    return aggregate


def _run_api_chunk_with_retries(
    session_factory,
    *,
    limit: int,
    offset: int,
    force: bool,
    update_names: bool,
    pause_ms: int,
    skip_recent_hours: int,
    target_fields: Sequence[str],
    priority_leagues: Sequence[str],
    provider_fetch_attempts: int,
    provider_retry_base_ms: int,
    sample_size: int,
    attempts: int,
    base_seconds: float,
) -> BackfillStats:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with session_factory() as session:
                chunk_stats = backfill_metadata(
                    session,
                    source="api",
                    apply=True,
                    limit=limit,
                    offset=offset,
                    force=force,
                    update_names=update_names,
                    pause_ms=pause_ms,
                    skip_recent_hours=skip_recent_hours,
                    target_fields=target_fields,
                    priority_leagues=priority_leagues,
                    provider_fetch_attempts=provider_fetch_attempts,
                    provider_retry_base_ms=provider_retry_base_ms,
                    sample_size=sample_size,
                )
                if chunk_stats.selected:
                    session.commit()
                return chunk_stats
        except (OperationalError, DBAPIError) as exc:
            last_error = exc
            if attempt >= attempts:
                break
            delay_seconds = min(base_seconds * (2 ** (attempt - 1)), 30.0)
            print(
                json.dumps(
                    {
                        "warning": "db_retry",
                        "attempt": attempt,
                        "attempts": attempts,
                        "delay_seconds": delay_seconds,
                        "error": str(exc).splitlines()[0],
                    },
                    sort_keys=True,
                ),
                file=sys.stderr,
            )
            if delay_seconds:
                time.sleep(delay_seconds)
    assert last_error is not None
    raise last_error


def _merge_stats(target: BackfillStats, source: BackfillStats, *, sample_size: int) -> None:
    for field_name in (
        "selected",
        "fetched",
        "fetch_failed",
        "no_provider_facts",
        "players_updated",
        "countries_created",
        "competitions_created",
        "clubs_created",
        "images_updated",
        "profiles_updated",
        "summaries_updated",
        "missing_country",
        "missing_club",
        "missing_competition",
        "missing_date_of_birth",
        "missing_photo",
    ):
        setattr(target, field_name, int(getattr(target, field_name)) + int(getattr(source, field_name)))
    if source.samples:
        if target.samples is None:
            target.samples = []
        for sample in source.samples:
            if len(target.samples) >= sample_size:
                break
            target.samples.append(sample)


def backfill_metadata(
    session: Session,
    *,
    source: str,
    apply: bool,
    limit: int,
    offset: int,
    force: bool,
    update_names: bool,
    pause_ms: int,
    skip_recent_hours: int = 24,
    target_fields: Sequence[str] = _DEFAULT_API_TARGET_FIELDS,
    priority_leagues: Sequence[str] = (),
    provider_fetch_attempts: int = 2,
    provider_retry_base_ms: int = 250,
    sample_size: int,
) -> BackfillStats:
    if source == "staging":
        return _backfill_staging_fast(
            session,
            apply=apply,
            limit=limit,
            offset=offset,
            force=force,
            update_names=update_names,
            sample_size=sample_size,
        )

    stats = BackfillStats()
    players = _select_players(
        session,
        source=source,
        limit=limit,
        offset=offset,
        force=force,
        skip_recent_hours=skip_recent_hours,
        target_fields=target_fields,
        priority_leagues=priority_leagues,
    )
    stats.selected = len(players)
    if not players:
        return stats
    cache = EntityCache(countries={}, competitions={}, clubs={})

    facts = (
        _facts_from_staging(session, players=players)
        if source == "staging"
        else _facts_from_api(
            players=players,
            pause_ms=pause_ms,
            provider_fetch_attempts=provider_fetch_attempts,
            provider_retry_base_ms=provider_retry_base_ms,
            stats=stats,
            sample_size=sample_size,
        )
    )
    for player in players:
        item = facts.get(player.id)
        if item is None:
            stats.no_provider_facts += 1
            stats.add_sample(
                {
                    "player_id": player.id,
                    "provider_player_id": player.provider_external_id,
                    "name": player.full_name,
                    "issue": "no_provider_facts",
                },
                limit=sample_size,
            )
            continue
        _apply_facts(
            session,
            player=player,
            facts=item,
            stats=stats,
            cache=cache,
            apply=apply,
            force=force,
            update_names=update_names,
        )
    return stats


def _backfill_staging_fast(
    session: Session,
    *,
    apply: bool,
    limit: int,
    offset: int,
    force: bool,
    update_names: bool,
    sample_size: int,
) -> BackfillStats:
    stats = BackfillStats()
    rows = list(
        session.execute(
            _staging_player_fact_sql(force=force),
            {"limit": limit, "offset": offset},
        ).mappings()
    )
    stats.selected = len(rows)
    if not rows:
        return stats

    cache = EntityCache(countries={}, competitions={}, clubs={})
    country_by_key: dict[tuple[str | None, str | None], Country | None] = {}
    competition_by_key: dict[tuple[str | None, str | None], Competition | None] = {}
    club_by_key: dict[tuple[str | None, str | None, str | None], Club | None] = {}

    with session.no_autoflush:
        for row in rows:
            nationality_name = _clean(row["nationality_name"])
            nationality_code = _clean(row["nationality_code"])
            country_key = (nationality_code, nationality_name)
            if country_key not in country_by_key:
                country_by_key[country_key] = _resolve_country(
                    session,
                    facts=PlayerMetadataFacts(
                        player_id=str(row["player_id"]),
                        provider_player_id=str(row["provider_player_id"]),
                        nationality_name=nationality_name,
                        nationality_code=nationality_code,
                    ),
                    stats=stats,
                    cache=cache,
                    apply=apply,
                )

        for row in rows:
            competition_name = _clean(row["provider_competition_name"])
            competition_provider_id = _clean(row["provider_competition_id"])
            competition_key = (competition_provider_id, competition_name)
            if competition_key not in competition_by_key:
                competition_by_key[competition_key] = _resolve_competition(
                    session,
                    facts=PlayerMetadataFacts(
                        player_id=str(row["player_id"]),
                        provider_player_id=str(row["provider_player_id"]),
                        competition_name=competition_name,
                        competition_provider_id=competition_provider_id,
                        season_provider_id=_clean(row["provider_season_id"]),
                    ),
                    country=None,
                    stats=stats,
                    cache=cache,
                    apply=apply,
                )

        for row in rows:
            club_name = _clean(row["provider_club_name"])
            club_provider_id = _clean(row["provider_club_id"])
            competition_key = (_clean(row["provider_competition_id"]), _clean(row["provider_competition_name"]))
            club_key = (club_provider_id, club_name, competition_key[0] or competition_key[1])
            if club_key not in club_by_key:
                competition = competition_by_key.get(competition_key)
                club_by_key[club_key] = _resolve_club(
                    session,
                    facts=PlayerMetadataFacts(
                        player_id=str(row["player_id"]),
                        provider_player_id=str(row["provider_player_id"]),
                        club_name=club_name,
                        club_provider_id=club_provider_id,
                    ),
                    country=None,
                    competition=competition,
                    stats=stats,
                    cache=cache,
                    apply=apply,
                )

    updates: list[dict[str, Any]] = []
    summary_updates: list[dict[str, Any]] = []
    for row in rows:
        country = country_by_key.get((_clean(row["nationality_code"]), _clean(row["nationality_name"])))
        competition_key = (_clean(row["provider_competition_id"]), _clean(row["provider_competition_name"]))
        competition = competition_by_key.get(competition_key)
        club_key = (
            _clean(row["provider_club_id"]),
            _clean(row["provider_club_name"]),
            competition_key[0] or competition_key[1],
        )
        club = club_by_key.get(club_key)
        if country is None:
            stats.missing_country += 1
        if competition is None and _clean(row["provider_competition_name"]):
            stats.missing_competition += 1
        if club is None and _clean(row["provider_club_name"]):
            stats.missing_club += 1
        if row["date_of_birth"] is None:
            stats.missing_date_of_birth += 1
        position = _clean(row["display_position"])
        updates.append(
            {
                "player_id": str(row["player_id"]),
                "force": force,
                "country_id": country.id if country is not None else None,
                "competition_id": competition.id if competition is not None else None,
                "club_id": club.id if club is not None else None,
                "date_of_birth": row["date_of_birth"],
                "real_world_club_name": _clean(row["provider_club_name"]),
                "real_world_league_name": _clean(row["provider_competition_name"]),
                "position": position,
                "normalized_position": normalize_position(position),
                "full_name": _clean(row["full_name"]),
                "first_name": _clean(row["first_name"]),
                "last_name": _clean(row["last_name"]),
                "short_name": _clean(row["short_name"]),
                "update_names": update_names,
            }
        )
        if competition is not None or club is not None:
            summary_updates.append(
                {
                    "player_id": str(row["player_id"]),
                    "club_id": club.id if club is not None else None,
                    "club_name": club.name if club is not None else _clean(row["provider_club_name"]),
                    "competition_id": competition.id if competition is not None else None,
                    "competition_name": (
                        competition.name if competition is not None else _clean(row["provider_competition_name"])
                    ),
                }
            )

    if not apply:
        stats.players_updated = len(updates)
        stats.summaries_updated = len(summary_updates)
        for row in rows[:sample_size]:
            stats.add_sample(
                {
                    "player_id": row["player_id"],
                    "name": row["player_name"],
                    "club": row["provider_club_name"],
                    "league": row["provider_competition_name"],
                    "nationality": row["nationality_name"],
                },
                limit=sample_size,
            )
        return stats

    session.flush()
    if updates:
        result = session.execute(_bulk_player_update_sql(), updates)
        stats.players_updated = int(result.rowcount or 0)
    if summary_updates:
        result = session.execute(_bulk_summary_update_sql(), summary_updates)
        stats.summaries_updated = int(result.rowcount or 0)
    return stats


def _select_players(
    session: Session,
    *,
    source: str,
    limit: int,
    offset: int,
    force: bool,
    skip_recent_hours: int = 24,
    target_fields: Sequence[str] = _DEFAULT_API_TARGET_FIELDS,
    priority_leagues: Sequence[str] = (),
) -> list[Player]:
    if source == "staging":
        missing_filter = (
            ""
            if force
            else """
              and (
                p.country_id is null
                or p.current_club_id is null
                or p.current_competition_id is null
                or p.date_of_birth is null
              )
            """
        )
        rows = session.execute(
            text(
                f"""
                select distinct p.id, p.full_name
                from ingestion_players p
                join real_player_import_staging s
                  on s.provider_name = p.source_provider
                 and s.provider_player_id = p.provider_external_id
                where p.is_real_player is true
                  and p.is_tradable is true
                  and lower(p.source_provider) = 'sportmonks'
                  {missing_filter}
                  and (
                    s.nationality_name is not null
                    or s.nationality_code is not null
                    or s.provider_club_name is not null
                    or s.provider_competition_name is not null
                    or s.date_of_birth is not null
                  )
                order by p.full_name asc, p.id asc
                limit :limit offset :offset
                """
            ),
            {"limit": limit, "offset": offset},
        ).all()
        ids = [str(row[0]) for row in rows]
        if not ids:
            return []
        players = {player.id: player for player in session.scalars(select(Player).where(Player.id.in_(ids)))}
        return [players[player_id] for player_id in ids if player_id in players]

    criteria = [
        Player.is_real_player.is_(True),
        Player.is_tradable.is_(True),
        func.lower(Player.source_provider) == "sportmonks",
    ]
    if priority_leagues:
        criteria.append(_priority_league_filter(priority_leagues))
    normalized_targets = _parse_api_target_fields(target_fields)
    missing_conditions = []
    missing_order_terms = []
    if "country" in normalized_targets:
        missing_conditions.append(Player.country_id.is_(None))
        missing_order_terms.append(case((Player.country_id.is_(None), 1), else_=0))
    if "club" in normalized_targets:
        missing_conditions.append(Player.current_club_id.is_(None))
        missing_order_terms.append(case((Player.current_club_id.is_(None), 1), else_=0))
    if "competition" in normalized_targets:
        missing_conditions.append(Player.current_competition_id.is_(None))
        missing_order_terms.append(case((Player.current_competition_id.is_(None), 1), else_=0))
    if "date_of_birth" in normalized_targets:
        missing_conditions.append(Player.date_of_birth.is_(None))
        missing_order_terms.append(case((Player.date_of_birth.is_(None), 1), else_=0))
    if "photo" in normalized_targets:
        portrait_exists = exists().where(
            PlayerImageMetadata.player_id == Player.id,
            PlayerImageMetadata.image_role == "portrait",
            func.lower(PlayerImageMetadata.source_provider) == "sportmonks",
            PlayerImageMetadata.moderation_status == "approved",
            PlayerImageMetadata.source_url.is_not(None),
            func.length(func.trim(PlayerImageMetadata.source_url)) > 0,
        )
        missing_conditions.append(~portrait_exists)
        missing_order_terms.append(case((~portrait_exists, 1), else_=0))
    if not force and missing_conditions:
        criteria.append(or_(*missing_conditions))
        if skip_recent_hours > 0:
            cutoff = datetime.now(UTC) - timedelta(hours=skip_recent_hours)
            criteria.append(
                or_(
                    Player.source_last_refreshed_at.is_(None),
                    Player.source_last_refreshed_at < cutoff,
                )
            )
    missing_score = sum(missing_order_terms[1:], missing_order_terms[0]) if missing_order_terms else None
    order_by = []
    if missing_score is not None:
        order_by.append(missing_score.desc())
    order_by.extend(
        [
            case((Player.source_last_refreshed_at.is_(None), 0), else_=1).asc(),
            Player.source_last_refreshed_at.asc(),
            Player.full_name.asc(),
            Player.id.asc(),
        ]
    )
    return list(
        session.scalars(
            select(Player)
            .where(*criteria)
            .order_by(*order_by)
            .offset(offset)
            .limit(limit)
        )
    )


def _priority_league_filter(priority_leagues: Sequence[str]):
    labels = tuple(label.lower() for label in _priority_league_match_labels(priority_leagues))
    summary_match = exists().where(
        PlayerSummaryReadModel.player_id == Player.id,
        func.lower(PlayerSummaryReadModel.current_competition_name).in_(labels),
    )
    profile_match = exists().where(
        RealPlayerProfile.source_name == Player.source_provider,
        RealPlayerProfile.source_player_key == Player.provider_external_id,
        func.lower(RealPlayerProfile.current_league_name).in_(labels),
    )
    return or_(
        func.lower(Player.real_world_league_name).in_(labels),
        Player.current_competition.has(func.lower(Competition.name).in_(labels)),
        summary_match,
        profile_match,
    )


def _facts_from_staging(session: Session, *, players: list[Player]) -> dict[str, PlayerMetadataFacts]:
    if not players:
        return {}
    player_by_key = {str(player.provider_external_id): player for player in players if player.provider_external_id}
    rows = session.execute(
        select(
            Player.id,
            Player.provider_external_id,
            Player.full_name,
            Player.first_name,
            Player.last_name,
            Player.position,
            Player.date_of_birth,
            RealPlayerProfile.id,
            RealPlayerProfile.current_club_name,
            RealPlayerProfile.current_league_name,
            RealPlayerProfile.nationality,
            RealPlayerProfile.date_of_birth,
            RealPlayerProfile.metadata_json,
        )
        .outerjoin(
            RealPlayerProfile,
            (RealPlayerProfile.source_name == Player.source_provider)
            & (RealPlayerProfile.source_player_key == Player.provider_external_id),
        )
        .where(Player.id.in_([player.id for player in players]))
    )
    profile_facts: dict[str, PlayerMetadataFacts] = {}
    for row in rows:
        metadata = _dict(row[12])
        photo_url = _photo_url(metadata.get("photo_url") or (_dict(metadata.get("image")).get("source_url")))
        profile_facts[str(row[0])] = PlayerMetadataFacts(
            player_id=str(row[0]),
            provider_player_id=str(row[1]),
            full_name=_clean(row[2]),
            first_name=_clean(row[3]),
            last_name=_clean(row[4]),
            position=_clean(row[5]),
            nationality_name=_clean(row[10]),
            date_of_birth=row[11] or row[6],
            club_name=_clean(row[8]),
            competition_name=_clean(row[9]),
            photo_url=photo_url,
        )

    sql_rows = session.execute(
        _staging_sql(),
        {
            "source_name": "sportmonks",
            "provider_ids": list(player_by_key),
        },
    )
    facts = dict(profile_facts)
    for row in sql_rows.mappings():
        player = player_by_key.get(str(row["provider_player_id"]))
        if player is None:
            continue
        payload = _dict(row["latest_payload_json"])
        current_club = _dict(payload.get("currentClub"))
        current_competition = _dict(payload.get("currentCompetition"))
        metadata = _dict(row["metadata_json"])
        existing = facts.get(player.id)
        facts[player.id] = PlayerMetadataFacts(
            player_id=player.id,
            provider_player_id=str(row["provider_player_id"]),
            full_name=_first(_clean(row["full_name"]), existing.full_name if existing else None, player.full_name),
            display_name=_clean(row["short_name"]),
            first_name=_first(_clean(row["first_name"]), existing.first_name if existing else None, player.first_name),
            last_name=_first(_clean(row["last_name"]), existing.last_name if existing else None, player.last_name),
            position=_first(_clean(row["display_position"]), existing.position if existing else None, player.position),
            nationality_name=_first(
                _clean(row["nationality_name"]),
                _clean(payload.get("nationality")),
                existing.nationality_name if existing else None,
            ),
            nationality_code=_first(_clean(row["nationality_code"]), _clean(payload.get("nationalityCode"))),
            date_of_birth=row["date_of_birth"] or (existing.date_of_birth if existing else None),
            club_name=_first(
                _clean(row["provider_club_name"]),
                _clean(current_club.get("name")),
                existing.club_name if existing else None,
            ),
            club_provider_id=_first(_clean(row["provider_club_id"]), _clean(current_club.get("id"))),
            competition_name=_first(
                _clean(row["provider_competition_name"]),
                _clean(current_competition.get("name")),
                existing.competition_name if existing else None,
            ),
            competition_provider_id=_first(_clean(row["provider_competition_id"]), _clean(current_competition.get("id"))),
            season_provider_id=_clean(row["provider_season_id"]),
            photo_url=_first(
                _photo_url(metadata.get("photo_url")),
                _photo_url(payload.get("photo_url") or payload.get("image_path")),
                existing.photo_url if existing else None,
            ),
            raw_payload=payload,
        )
    return facts


def _facts_from_api(
    *,
    players: list[Player],
    pause_ms: int,
    provider_fetch_attempts: int,
    provider_retry_base_ms: int,
    stats: BackfillStats,
    sample_size: int,
) -> dict[str, PlayerMetadataFacts]:
    adapter = SportMonksAdapter()
    facts: dict[str, PlayerMetadataFacts] = {}
    include = "country;nationality;position;detailedPosition;teams.team;teams.team.country"
    for player in players:
        provider_player_id = str(player.provider_external_id or "").strip()
        if not provider_player_id:
            continue
        payload: dict[str, Any] | None = None
        last_error: Exception | None = None
        try:
            for attempt in range(1, max(provider_fetch_attempts, 1) + 1):
                try:
                    payload = adapter._get(f"/players/{provider_player_id}", params={"include": include})  # noqa: SLF001
                    break
                except Exception as exc:  # pragma: no cover - live provider dependent
                    last_error = exc
                    if attempt >= max(provider_fetch_attempts, 1):
                        raise
                    delay_seconds = (max(provider_retry_base_ms, 0) / 1000) * attempt
                    if delay_seconds:
                        time.sleep(delay_seconds)
        except Exception as exc:  # pragma: no cover - live provider dependent
            stats.fetch_failed += 1
            stats.add_sample(
                {
                    "player_id": player.id,
                    "provider_player_id": provider_player_id,
                    "name": player.full_name,
                    "issue": "fetch_failed",
                    "error_type": type(exc).__name__,
                    "attempts": max(provider_fetch_attempts, 1),
                },
                limit=sample_size,
            )
            continue
        if payload is None:
            stats.fetch_failed += 1
            stats.add_sample(
                {
                    "player_id": player.id,
                    "provider_player_id": provider_player_id,
                    "name": player.full_name,
                    "issue": "fetch_failed",
                    "error_type": type(last_error).__name__ if last_error is not None else "UnknownError",
                    "attempts": max(provider_fetch_attempts, 1),
                },
                limit=sample_size,
            )
            continue
        stats.fetched += 1
        data = _dict(payload.get("data"))
        facts[player.id] = _facts_from_sportmonks_payload(player=player, provider_player_id=provider_player_id, data=data, adapter=adapter)
        if pause_ms > 0:
            time.sleep(pause_ms / 1000)
    return facts


def _facts_from_sportmonks_payload(
    *,
    player: Player,
    provider_player_id: str,
    data: dict[str, Any],
    adapter: SportMonksAdapter,
) -> PlayerMetadataFacts:
    country = _dict(data.get("country"))
    nationality = _dict(data.get("nationality"))
    position = _dict(data.get("position"))
    detailed_position = _dict(data.get("detailedposition") or data.get("detailedPosition"))
    team_context = adapter._select_directory_team_context(data)  # noqa: SLF001
    selected_membership = _selected_membership(data, team_context)
    team = _dict(selected_membership.get("team")) if selected_membership else {}
    club_country = _dict(team.get("country"))
    nationality_name = _first(_clean(nationality.get("name")), _clean(country.get("name")))
    nationality_code = _first(
        _clean(nationality.get("iso2")),
        _clean(nationality.get("iso3")),
        _clean(country.get("iso2")),
        _clean(country.get("iso3")),
    )
    return PlayerMetadataFacts(
        player_id=player.id,
        provider_player_id=provider_player_id,
        full_name=_first(_clean(data.get("name")), player.full_name),
        display_name=_clean(data.get("display_name") or data.get("displayName")),
        first_name=_clean(data.get("firstname") or data.get("firstName")),
        last_name=_clean(data.get("lastname") or data.get("lastName")),
        position=_clean(position.get("name")),
        detailed_position=_clean(detailed_position.get("name")),
        nationality_name=nationality_name,
        nationality_code=nationality_code,
        nationality_provider_id=_clean(data.get("nationality_id") or nationality.get("id") or country.get("id")),
        date_of_birth=adapter._parse_date(data.get("date_of_birth") or data.get("dateOfBirth")),  # noqa: SLF001
        club_name=_first(_clean(team_context.get("club_name") if team_context else None), _clean(team.get("name"))),
        club_provider_id=_first(_clean(team_context.get("club_id") if team_context else None), _clean(team.get("id"))),
        club_country_name=_clean(club_country.get("name")),
        competition_name=_clean(team_context.get("competition_name") if team_context else None),
        competition_provider_id=_clean(team_context.get("competition_id") if team_context else None),
        season_provider_id=_clean(team_context.get("season_id") if team_context else None),
        photo_url=_photo_url(data.get("image_path") or data.get("imagePath")),
        raw_payload=data,
    )


def _apply_facts(
    session: Session,
    *,
    player: Player,
    facts: PlayerMetadataFacts,
    stats: BackfillStats,
    cache: EntityCache,
    apply: bool,
    force: bool,
    update_names: bool,
) -> None:
    now = datetime.now(UTC)
    country = _resolve_country(session, facts=facts, stats=stats, cache=cache, apply=apply)
    competition_country = country
    if facts.club_country_name and facts.club_country_name != facts.nationality_name:
        competition_country = _resolve_country(
            session,
            facts=replace(
                facts,
                nationality_name=facts.club_country_name,
                nationality_code=None,
                nationality_provider_id=f"club-country:{slugify(facts.club_country_name)}",
            ),
            stats=stats,
            cache=cache,
            apply=apply,
        )
    competition = _resolve_competition(
        session,
        facts=facts,
        country=competition_country,
        stats=stats,
        cache=cache,
        apply=apply,
    )
    club = _resolve_club(
        session,
        facts=facts,
        country=competition_country or country,
        competition=competition,
        stats=stats,
        cache=cache,
        apply=apply,
    )
    league_display_name = _display_competition_name(facts.competition_name, facts.club_country_name)

    changed = False
    if country is None:
        stats.missing_country += 1
    elif _needs(player.country_id, country.id, force=force):
        changed = True
        if apply:
            player.country_id = country.id

    if competition is None and facts.competition_name:
        stats.missing_competition += 1
    elif competition is not None and _needs(player.current_competition_id, competition.id, force=force):
        changed = True
        if apply:
            player.current_competition_id = competition.id

    if club is None and facts.club_name:
        stats.missing_club += 1
    elif club is not None and _needs(player.current_club_id, club.id, force=force):
        changed = True
        if apply:
            player.current_club_id = club.id

    if facts.date_of_birth is None:
        stats.missing_date_of_birth += 1
    elif _needs(player.date_of_birth, facts.date_of_birth, force=force):
        changed = True
        if apply:
            player.date_of_birth = facts.date_of_birth

    position = _first(facts.detailed_position, facts.position)
    normalized_position = normalize_position(position)
    if position and _needs(player.position, position, force=force):
        changed = True
        if apply:
            player.position = position
            player.normalized_position = normalized_position

    if update_names:
        changed |= _apply_names(player, facts=facts, apply=apply)

    if facts.club_name and _needs(player.real_world_club_name, facts.club_name, force=force):
        changed = True
        if apply:
            player.real_world_club_name = facts.club_name
    if league_display_name and _needs(player.real_world_league_name, league_display_name, force=force):
        changed = True
        if apply:
            player.real_world_league_name = league_display_name

    if changed:
        stats.players_updated += 1
    if apply:
        player.source_last_refreshed_at = now
        player.last_synced_at = now

    if facts.photo_url is None:
        stats.missing_photo += 1
    elif _upsert_image(session, player=player, facts=facts, as_of=now, apply=apply):
        stats.images_updated += 1

    if apply and _update_profile(
        session,
        player=player,
        facts=facts,
        league_display_name=league_display_name,
        as_of=now,
        apply=apply,
    ):
        stats.profiles_updated += 1

    if apply and _update_summary(
        session,
        player=player,
        competition=competition,
        club=club,
        facts=facts,
        league_display_name=league_display_name,
        as_of=now,
        apply=apply,
    ):
        stats.summaries_updated += 1


def _resolve_country(
    session: Session,
    *,
    facts: PlayerMetadataFacts,
    stats: BackfillStats,
    cache: EntityCache,
    apply: bool,
) -> Country | None:
    name = _clean(facts.nationality_name)
    code = _clean(facts.nationality_code)
    provider_external_id = _clean(facts.nationality_provider_id) or code or name
    if not name and not code:
        return None
    cache_key = ("sportmonks", provider_external_id, (code or "").lower(), (name or "").lower())
    if cache_key in cache.countries:
        return cache.countries[cache_key]
    country = None
    if provider_external_id:
        country = session.scalar(
            select(Country).where(
                Country.source_provider == "sportmonks",
                Country.provider_external_id == provider_external_id,
            )
        )
    if country is None and code:
        country = session.scalar(
            select(Country).where(or_(func.lower(Country.alpha2_code) == code.lower(), func.lower(Country.alpha3_code) == code.lower()))
        )
    if country is None and name:
        country = session.scalar(select(Country).where(func.lower(Country.name) == name.lower()))
    if country is None and apply:
        country = Country(
            id=str(uuid4()),
            source_provider="sportmonks",
            provider_external_id=provider_external_id or slugify(name),
            name=name or code or "Unknown Country",
            alpha2_code=code if code and len(code) == 2 else None,
            alpha3_code=code if code and len(code) == 3 else None,
            last_synced_at=datetime.now(UTC),
        )
        session.add(country)
        stats.countries_created += 1
    elif country is None:
        stats.countries_created += 1
    cache.countries[cache_key] = country
    return country


def _resolve_competition(
    session: Session,
    *,
    facts: PlayerMetadataFacts,
    country: Country | None,
    stats: BackfillStats,
    cache: EntityCache,
    apply: bool,
) -> Competition | None:
    name = _clean(facts.competition_name)
    provider_external_id = _clean(facts.competition_provider_id) or (slugify(name) if name else None)
    if not name and not provider_external_id:
        return None
    cache_key = ("sportmonks", provider_external_id, (name or "").lower(), country.id if country is not None else None)
    if cache_key in cache.competitions:
        return cache.competitions[cache_key]
    competition = None
    if provider_external_id:
        competition = session.scalar(
            select(Competition).where(
                Competition.source_provider == "sportmonks",
                Competition.provider_external_id == provider_external_id,
            )
        )
    if competition is None and name:
        criteria = [func.lower(Competition.name) == name.lower()]
        if country is not None:
            criteria.append(Competition.country_id == country.id)
        competition = session.scalar(select(Competition).where(*criteria))
    if competition is None and apply:
        competition = Competition(
            id=str(uuid4()),
            source_provider="sportmonks",
            provider_external_id=provider_external_id or slugify(name),
            country_id=country.id if country is not None else None,
            name=name or "Unknown League",
            slug=slugify(name),
            competition_type="league",
            format_type="real_world",
            is_tradable=True,
            current_season_external_id=facts.season_provider_id,
            last_synced_at=datetime.now(UTC),
        )
        session.add(competition)
        stats.competitions_created += 1
    elif competition is None:
        stats.competitions_created += 1
    elif apply and facts.season_provider_id and not competition.current_season_external_id:
        competition.current_season_external_id = facts.season_provider_id
    cache.competitions[cache_key] = competition
    return competition


def _resolve_club(
    session: Session,
    *,
    facts: PlayerMetadataFacts,
    country: Country | None,
    competition: Competition | None,
    stats: BackfillStats,
    cache: EntityCache,
    apply: bool,
) -> Club | None:
    name = _clean(facts.club_name)
    provider_external_id = _clean(facts.club_provider_id) or (slugify(name) if name else None)
    if not name and not provider_external_id:
        return None
    cache_key = (
        "sportmonks",
        provider_external_id,
        (name or "").lower(),
        country.id if country is not None else None,
        competition.id if competition is not None else None,
    )
    if cache_key in cache.clubs:
        return cache.clubs[cache_key]
    club = None
    if provider_external_id:
        club = session.scalar(
            select(Club).where(Club.source_provider == "sportmonks", Club.provider_external_id == provider_external_id)
        )
    if club is None and name:
        criteria = [func.lower(Club.name) == name.lower()]
        if competition is not None:
            criteria.append(Club.current_competition_id == competition.id)
        elif country is not None:
            criteria.append(Club.country_id == country.id)
        club = session.scalar(select(Club).where(*criteria))
    if club is None and competition is None:
        cache.clubs[cache_key] = None
        return None
    if club is None and apply:
        club = Club(
            id=str(uuid4()),
            source_provider="sportmonks",
            provider_external_id=provider_external_id or slugify(name),
            country_id=country.id if country is not None else None,
            current_competition_id=competition.id if competition is not None else None,
            name=name or "Unknown Club",
            slug=slugify(name),
            short_name=(name or "Unknown Club")[:80],
            is_tradable=True,
            last_synced_at=datetime.now(UTC),
        )
        session.add(club)
        stats.clubs_created += 1
    elif club is None:
        stats.clubs_created += 1
    elif apply:
        if competition is not None and not club.current_competition_id:
            club.current_competition_id = competition.id
        if country is not None and not club.country_id:
            club.country_id = country.id
    cache.clubs[cache_key] = club
    return club


def _apply_names(player: Player, *, facts: PlayerMetadataFacts, apply: bool) -> bool:
    changed = False
    full_name = _clean(facts.full_name)
    display_name = _clean(facts.display_name)
    if full_name and player.full_name != full_name:
        changed = True
        if apply:
            player.full_name = full_name
    if facts.first_name and player.first_name != facts.first_name:
        changed = True
        if apply:
            player.first_name = facts.first_name
    if facts.last_name and player.last_name != facts.last_name:
        changed = True
        if apply:
            player.last_name = facts.last_name
    if display_name and player.canonical_display_name != display_name:
        changed = True
        if apply:
            player.canonical_display_name = display_name
            player.short_name = display_name[:80]
    return changed


def _upsert_image(
    session: Session,
    *,
    player: Player,
    facts: PlayerMetadataFacts,
    as_of: datetime,
    apply: bool,
) -> bool:
    if facts.photo_url is None:
        return False
    image = session.scalar(
        select(PlayerImageMetadata).where(
            PlayerImageMetadata.source_provider == "sportmonks",
            PlayerImageMetadata.provider_external_id == facts.provider_player_id,
        )
    )
    if image is None:
        image = session.scalar(
            select(PlayerImageMetadata).where(
                PlayerImageMetadata.player_id == player.id,
                PlayerImageMetadata.image_role == "portrait",
            )
        )
    if image is not None and image.source_url == facts.photo_url and image.is_primary:
        return False
    if apply:
        if image is None:
            image = PlayerImageMetadata(
                id=str(uuid4()),
                source_provider="sportmonks",
                provider_external_id=facts.provider_player_id,
                player_id=player.id,
                image_role="portrait",
            )
            session.add(image)
        image.source_provider = "sportmonks"
        image.provider_external_id = facts.provider_player_id
        image.player_id = player.id
        image.image_role = "portrait"
        image.source_url = facts.photo_url
        image.storage_key = None
        image.moderation_status = "approved"
        image.rights_cleared = True
        image.is_primary = True
        image.last_processed_at = as_of
    return True


def _update_profile(
    session: Session,
    *,
    player: Player,
    facts: PlayerMetadataFacts,
    league_display_name: str | None,
    as_of: datetime,
    apply: bool,
) -> bool:
    profile = session.scalar(
        select(RealPlayerProfile).where(
            RealPlayerProfile.source_name == "sportmonks",
            RealPlayerProfile.source_player_key == facts.provider_player_id,
        )
    )
    if profile is None:
        return False
    changed = any(
        (
            facts.nationality_name and profile.nationality != facts.nationality_name,
            facts.date_of_birth and profile.date_of_birth != facts.date_of_birth,
            facts.club_name and profile.current_club_name != facts.club_name,
            league_display_name and profile.current_league_name != league_display_name,
        )
    )
    metadata = dict(profile.metadata_json or {})
    if facts.photo_url and metadata.get("photo_url") != facts.photo_url:
        changed = True
    if not changed:
        return False
    if apply:
        if facts.nationality_name:
            profile.nationality = facts.nationality_name
        if facts.date_of_birth:
            profile.date_of_birth = facts.date_of_birth
        if facts.club_name:
            profile.current_club_name = facts.club_name
        if league_display_name:
            profile.current_league_name = league_display_name
        if facts.photo_url:
            metadata["photo_url"] = facts.photo_url
            metadata["has_real_photo"] = True
            metadata["no_real_photos"] = False
            metadata["image"] = {
                "source_url": facts.photo_url,
                "source_provider": "sportmonks",
                "provider_external_id": facts.provider_player_id,
                "is_primary": True,
                "moderation_status": "approved",
                "rights_cleared": True,
            }
        profile.metadata_json = metadata
        profile.source_last_refreshed_at = as_of
    return True


def _update_summary(
    session: Session,
    *,
    player: Player,
    competition: Competition | None,
    club: Club | None,
    facts: PlayerMetadataFacts,
    league_display_name: str | None,
    as_of: datetime,
    apply: bool,
) -> bool:
    summary = session.get(PlayerSummaryReadModel, player.id)
    if summary is None:
        return False
    current_club_id = club.id if club is not None else summary.current_club_id
    current_club_name = club.name if club is not None else facts.club_name or summary.current_club_name
    current_competition_id = competition.id if competition is not None else summary.current_competition_id
    current_competition_name = (
        league_display_name
        or (competition.name if competition is not None else None)
        or summary.current_competition_name
    )
    changed = any(
        (
            current_club_id != summary.current_club_id,
            current_club_name != summary.current_club_name,
            current_competition_id != summary.current_competition_id,
            current_competition_name != summary.current_competition_name,
        )
    )
    if not changed:
        return False
    if apply:
        summary.current_club_id = current_club_id
        summary.current_club_name = current_club_name
        summary.current_competition_id = current_competition_id
        summary.current_competition_name = current_competition_name
        payload = dict(summary.summary_json or {})
        payload["club_assignment"] = {
            **dict(payload.get("club_assignment") or {}),
            "status": "club_assigned" if current_club_name else "team_context_pending",
            "current_club_id": current_club_id,
            "current_club_name": current_club_name,
            "current_competition_id": current_competition_id,
            "current_competition_name": current_competition_name,
            "metadata_backfilled_at": as_of.isoformat(),
        }
        summary.summary_json = payload
        summary.updated_at = as_of
    return True


def _display_competition_name(competition_name: str | None, club_country_name: str | None) -> str | None:
    name = _clean(competition_name)
    country = _clean(club_country_name)
    if not name:
        return None
    if not country:
        return name
    override = _COUNTRY_LEAGUE_LABEL_OVERRIDES.get((country.casefold(), name.casefold()))
    if override:
        return override
    if name.casefold() in {"premier league", "pro league", "super league", "serie a", "serie b", "liga 1", "liga 2"}:
        return f"{country} {name}"
    return name


def _selected_membership(data: dict[str, Any], team_context: dict[str, str | None] | None) -> dict[str, Any] | None:
    memberships = list(data.get("teams") or [])
    if not memberships:
        return None
    if team_context and team_context.get("club_id"):
        for item in memberships:
            team = _dict(item.get("team"))
            if str(team.get("id") or item.get("team_id") or "").strip() == str(team_context["club_id"]):
                return item
    return memberships[0]


def _staging_sql():
    return text(
        """
        select distinct on (provider_player_id)
            provider_player_id,
            provider_club_id,
            provider_club_name,
            provider_competition_id,
            provider_competition_name,
            provider_season_id,
            full_name,
            first_name,
            last_name,
            short_name,
            display_position,
            nationality_name,
            nationality_code,
            date_of_birth,
            latest_payload_json,
            metadata_json
        from real_player_import_staging
        where provider_name = :source_name
          and provider_player_id = any(:provider_ids)
        order by provider_player_id, updated_at desc nulls last, created_at desc nulls last
        """
    )


def _staging_player_fact_sql(*, force: bool):
    missing_filter = (
        ""
        if force
        else """
          and (
            p.country_id is null
            or p.current_club_id is null
            or p.current_competition_id is null
            or p.date_of_birth is null
          )
        """
    )
    return text(
        f"""
        with latest_staging as (
            select distinct on (provider_name, provider_player_id)
                provider_name,
                provider_player_id,
                provider_club_id,
                provider_club_name,
                provider_competition_id,
                provider_competition_name,
                provider_season_id,
                full_name,
                first_name,
                last_name,
                short_name,
                display_position,
                nationality_name,
                nationality_code,
                date_of_birth
            from real_player_import_staging
            where provider_name = 'sportmonks'
              and (
                nationality_name is not null
                or nationality_code is not null
                or provider_club_name is not null
                or provider_competition_name is not null
                or date_of_birth is not null
              )
            order by provider_name, provider_player_id, updated_at desc nulls last, created_at desc nulls last
        )
        select
            p.id as player_id,
            p.full_name as player_name,
            p.provider_external_id as provider_player_id,
            s.provider_club_id,
            s.provider_club_name,
            s.provider_competition_id,
            s.provider_competition_name,
            s.provider_season_id,
            s.full_name,
            s.first_name,
            s.last_name,
            s.short_name,
            s.display_position,
            s.nationality_name,
            s.nationality_code,
            s.date_of_birth
        from ingestion_players p
        join latest_staging s
          on s.provider_name = p.source_provider
         and s.provider_player_id = p.provider_external_id
        where p.is_real_player is true
          and p.is_tradable is true
          and lower(p.source_provider) = 'sportmonks'
          {missing_filter}
        order by p.full_name asc, p.id asc
        limit :limit offset :offset
        """
    )


def _bulk_player_update_sql():
    return text(
        """
        update ingestion_players
        set
            country_id = case
                when (cast(:force as boolean) or country_id is null) and cast(:country_id as varchar) is not null
                    then cast(:country_id as varchar)
                else country_id
            end,
            current_competition_id = case
                when (cast(:force as boolean) or current_competition_id is null)
                    and cast(:competition_id as varchar) is not null then cast(:competition_id as varchar)
                else current_competition_id
            end,
            current_club_id = case
                when (cast(:force as boolean) or current_club_id is null) and cast(:club_id as varchar) is not null
                    then cast(:club_id as varchar)
                else current_club_id
            end,
            date_of_birth = case
                when (cast(:force as boolean) or date_of_birth is null) and cast(:date_of_birth as date) is not null
                    then cast(:date_of_birth as date)
                else date_of_birth
            end,
            real_world_club_name = coalesce(cast(:real_world_club_name as varchar), real_world_club_name),
            real_world_league_name = coalesce(cast(:real_world_league_name as varchar), real_world_league_name),
            position = case
                when (cast(:force as boolean) or position is null) and cast(:position as varchar) is not null
                    then cast(:position as varchar)
                else position
            end,
            normalized_position = case
                when (cast(:force as boolean) or normalized_position is null)
                    and cast(:normalized_position as varchar) is not null then cast(:normalized_position as varchar)
                else normalized_position
            end,
            full_name = case
                when cast(:update_names as boolean) and cast(:full_name as varchar) is not null
                    then cast(:full_name as varchar)
                else full_name
            end,
            first_name = case
                when cast(:update_names as boolean) and cast(:first_name as varchar) is not null
                    then cast(:first_name as varchar)
                else first_name
            end,
            last_name = case
                when cast(:update_names as boolean) and cast(:last_name as varchar) is not null
                    then cast(:last_name as varchar)
                else last_name
            end,
            short_name = case
                when cast(:update_names as boolean) and cast(:short_name as varchar) is not null
                    then cast(:short_name as varchar)
                else short_name
            end,
            canonical_display_name = case
                when cast(:update_names as boolean) and cast(:short_name as varchar) is not null
                    then cast(:short_name as varchar)
                else canonical_display_name
            end,
            source_last_refreshed_at = now(),
            last_synced_at = now(),
            updated_at = now()
        where id = :player_id
        """
    )


def _bulk_summary_update_sql():
    return text(
        """
        update player_summary_read_models
        set
            current_club_id = coalesce(cast(:club_id as varchar), current_club_id),
            current_club_name = coalesce(cast(:club_name as varchar), current_club_name),
            current_competition_id = coalesce(cast(:competition_id as varchar), current_competition_id),
            current_competition_name = coalesce(cast(:competition_name as varchar), current_competition_name),
            updated_at = now()
        where player_id = :player_id
        """
    )


def _needs(current: Any, desired: Any, *, force: bool) -> bool:
    if desired is None:
        return False
    if force:
        return current != desired
    return current in (None, "")


def _first(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _clean(value: Any) -> str | None:
    return clean_name(str(value)) if value not in (None, "") else None


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _photo_url(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    lowered = text.lower()
    if "placeholder" in lowered or lowered.endswith("/player.png"):
        return None
    return text


if __name__ == "__main__":
    raise SystemExit(main())
