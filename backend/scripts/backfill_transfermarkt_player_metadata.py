from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Iterable, Sequence
from uuid import uuid4

import requests
from sqlalchemy import func, or_, select
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
from app.ingestion.models import Club, Competition, Country, Player
from app.ingestion.normalizers import slugify
from app.models.real_player_profile import RealPlayerProfile
from app.players.read_models import PlayerSummaryReadModel
from backend.scripts.backfill_transfermarkt_market_values import (
    _any_label_matches,
    _equivalent_labels,
    _name_aliases,
    _normalize_label,
    _normalize_name,
    _select_value_competitions,
)
from backend.scripts.import_transfermarkt_real_players import (
    CompetitionSpec,
    _TM_BASE_URL,
    _TM_HEADERS,
    _clean_text,
    _enrich_payload_from_profile,
    _get_html,
    _parse_competition_clubs,
    _parse_domestic_squad_payloads,
)


_COMPETITION_COUNTRIES_BY_CODE: dict[str, str] = {
    "A1": "Austria",
    "AR1N": "Argentina",
    "BE1": "Belgium",
    "BRA1": "Brazil",
    "C1": "Switzerland",
    "DK1": "Denmark",
    "EGY1": "Egypt",
    "ES1": "Spain",
    "ES2": "Spain",
    "FR1": "France",
    "FR2": "France",
    "GB1": "England",
    "GB2": "England",
    "IT1": "Italy",
    "IT2": "Italy",
    "L1": "Germany",
    "L2": "Germany",
    "MEX1": "Mexico",
    "MLS1": "United States",
    "NL1": "Netherlands",
    "NO1": "Norway",
    "NPFL": "Nigeria",
    "PL1": "Poland",
    "PO1": "Portugal",
    "RU1": "Russia",
    "SA1": "Saudi Arabia",
    "SC1": "Scotland",
    "SE1": "Sweden",
    "SFA1": "South Africa",
    "TR1": "Turkey",
    "TS1": "Czech Republic",
    "UKR1": "Ukraine",
}


@dataclass(slots=True)
class ExistingPlayerCandidate:
    player_id: str
    name_keys: frozenset[str]
    club_labels: frozenset[str]
    league_labels: frozenset[str]
    nationality_labels: frozenset[str]
    date_of_birth: date | None
    full_name: str | None
    player: Player
    summary: PlayerSummaryReadModel | None
    profiles: tuple[RealPlayerProfile, ...]


@dataclass(slots=True)
class TransfermarktMetadataFact:
    source_player_key: str
    display_name: str
    club_name: str
    club_key: str
    league_name: str
    league_key: str
    league_country_name: str | None
    nationality: str | None
    date_of_birth: date | None
    profile_path: str | None
    raw_payload: dict[str, Any] = field(repr=False)


@dataclass(slots=True)
class EntityCache:
    countries_by_name: dict[str, Country | None] = field(default_factory=dict)
    competitions: dict[tuple[Any, ...], Competition | None] = field(default_factory=dict)
    clubs: dict[tuple[Any, ...], Club | None] = field(default_factory=dict)


@dataclass(slots=True)
class MetadataBackfillStats:
    competitions_scanned: int = 0
    clubs_scanned: int = 0
    clubs_failed: int = 0
    transfermarkt_players_seen: int = 0
    matched_players: int = 0
    players_updated: int = 0
    countries_created: int = 0
    competitions_created: int = 0
    clubs_created: int = 0
    country_fixed: int = 0
    club_fixed: int = 0
    competition_fixed: int = 0
    date_of_birth_fixed: int = 0
    real_world_labels_fixed: int = 0
    profiles_updated: int = 0
    summaries_updated: int = 0
    profile_fetches: int = 0
    profile_fetch_failed: int = 0
    skipped_no_match: int = 0
    skipped_ambiguous: int = 0
    skipped_no_updates: int = 0
    skipped_missing_entities: int = 0
    samples: list[dict[str, Any]] = field(default_factory=list)

    def add_sample(self, payload: dict[str, Any], *, limit: int) -> None:
        if limit <= 0 or len(self.samples) >= limit:
            return
        self.samples.append(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill missing GTEX real-player club, competition, country, and DOB metadata from "
            "bulk Transfermarkt squad/profile pages. Writes only deterministic existing-player matches."
        )
    )
    parser.add_argument("--database-url", default=os.environ.get("GTE_DATABASE_URL"))
    parser.add_argument("--apply", action="store_true", help="Write updates. Default is dry-run.")
    parser.add_argument(
        "--create-entities",
        action="store_true",
        help="Create missing country/competition/club rows from Transfermarkt facts when needed.",
    )
    parser.add_argument(
        "--include-transfermarkt-provider",
        action="store_true",
        help="Allow matching against ingestion_players rows whose source_provider is transfermarkt.",
    )
    parser.add_argument(
        "--enrich-dob",
        action="store_true",
        help="Fetch matched Transfermarkt profile pages only when the matched GTEX player is missing DOB.",
    )
    parser.add_argument(
        "--allow-unique-name-nationality",
        action="store_true",
        help="Allow exact unique name plus nationality matches when existing club/league context is absent.",
    )
    parser.add_argument("--league", dest="leagues", action="append", default=[], help="Repeat to limit leagues.")
    parser.add_argument("--limit-clubs", type=int, default=0, help="Limit clubs per selected league; 0 means all.")
    parser.add_argument("--pause-ms", type=int, default=250, help="Pause between Transfermarkt squad requests.")
    parser.add_argument("--profile-pause-ms", type=int, default=150, help="Pause between DOB profile requests.")
    parser.add_argument("--provider-timeout-seconds", type=int, default=30)
    parser.add_argument("--db-retry-attempts", type=int, default=4)
    parser.add_argument("--db-retry-base-seconds", type=float, default=5.0)
    parser.add_argument("--sample-size", type=int, default=12)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.database_url:
        raise SystemExit("--database-url or GTE_DATABASE_URL is required.")

    load_model_modules()
    engine = create_database_engine(args.database_url)
    session_factory = create_session_factory(engine)
    tm_session = requests.Session()
    tm_session.headers.update(_TM_HEADERS)
    try:
        stats = _run_backfill_with_db_retries(
            session_factory,
            tm_session=tm_session,
            leagues=args.leagues,
            apply=bool(args.apply),
            create_entities=bool(args.create_entities),
            include_transfermarkt_provider=bool(args.include_transfermarkt_provider),
            enrich_dob=bool(args.enrich_dob),
            allow_unique_name_nationality=bool(args.allow_unique_name_nationality),
            limit_clubs=max(int(args.limit_clubs), 0),
            pause_ms=max(int(args.pause_ms), 0),
            profile_pause_ms=max(int(args.profile_pause_ms), 0),
            timeout_seconds=max(int(args.provider_timeout_seconds), 1),
            sample_size=max(int(args.sample_size), 0),
            attempts=max(int(args.db_retry_attempts), 1),
            base_seconds=max(float(args.db_retry_base_seconds), 0.0),
        )
        print(
            json.dumps(
                {
                    **asdict(stats),
                    "apply": bool(args.apply),
                    "create_entities": bool(args.create_entities),
                    "include_transfermarkt_provider": bool(args.include_transfermarkt_provider),
                    "enrich_dob": bool(args.enrich_dob),
                    "allow_unique_name_nationality": bool(args.allow_unique_name_nationality),
                    "leagues": args.leagues,
                    "limit_clubs": max(int(args.limit_clubs), 0),
                    "db_retry_attempts": max(int(args.db_retry_attempts), 1),
                    "db_retry_base_seconds": max(float(args.db_retry_base_seconds), 0.0),
                },
                default=str,
                sort_keys=True,
            )
        )
        return 0
    finally:
        engine.dispose()
        tm_session.close()


def _run_backfill_with_db_retries(
    session_factory,
    *,
    tm_session: requests.Session,
    leagues: Sequence[str],
    apply: bool,
    create_entities: bool,
    include_transfermarkt_provider: bool,
    enrich_dob: bool,
    allow_unique_name_nationality: bool,
    limit_clubs: int,
    pause_ms: int,
    profile_pause_ms: int,
    timeout_seconds: int,
    sample_size: int,
    attempts: int,
    base_seconds: float,
) -> MetadataBackfillStats:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with session_factory() as db_session:
                stats = backfill_transfermarkt_metadata(
                    db_session,
                    tm_session=tm_session,
                    leagues=leagues,
                    apply=apply,
                    create_entities=create_entities,
                    include_transfermarkt_provider=include_transfermarkt_provider,
                    enrich_dob=enrich_dob,
                    allow_unique_name_nationality=allow_unique_name_nationality,
                    limit_clubs=limit_clubs,
                    pause_ms=pause_ms,
                    profile_pause_ms=profile_pause_ms,
                    timeout_seconds=timeout_seconds,
                    sample_size=sample_size,
                )
                if apply:
                    db_session.commit()
                return stats
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


def backfill_transfermarkt_metadata(
    session: Session,
    *,
    tm_session: requests.Session,
    leagues: Sequence[str],
    apply: bool,
    create_entities: bool,
    include_transfermarkt_provider: bool,
    enrich_dob: bool,
    allow_unique_name_nationality: bool,
    limit_clubs: int,
    pause_ms: int,
    profile_pause_ms: int,
    timeout_seconds: int,
    sample_size: int,
) -> MetadataBackfillStats:
    stats = MetadataBackfillStats()
    candidates = _load_existing_candidates(session, include_transfermarkt_provider=include_transfermarkt_provider)
    candidates_by_name = _index_candidates(candidates)
    cache = EntityCache()
    selected_specs = _select_value_competitions(list(leagues))
    for spec in selected_specs:
        stats.competitions_scanned += 1
        competition_url = f"{_TM_BASE_URL}/{spec.slug}/startseite/wettbewerb/{spec.competition_code}"
        competition_html = _get_html(
            tm_session,
            competition_url,
            description=f"competition {spec.name}",
            timeout_seconds=timeout_seconds,
        )
        clubs = _parse_competition_clubs(competition_html)
        if limit_clubs:
            clubs = clubs[:limit_clubs]
        for club in clubs:
            stats.clubs_scanned += 1
            try:
                squad_url = f"{_TM_BASE_URL}/{club['slug']}/kader/verein/{club['id']}/saison_id/{club['season_id']}"
                squad_html = _get_html(
                    tm_session,
                    squad_url,
                    description=f"squad {spec.name} {club['name']}",
                    timeout_seconds=timeout_seconds,
                )
                payloads = _parse_domestic_squad_payloads(
                    squad_html=squad_html,
                    league_name=spec.name,
                    league_key=spec.competition_code,
                    competition_level=spec.competition_level,
                    club=club,
                )
            except Exception as exc:  # pragma: no cover - live provider dependent
                stats.clubs_failed += 1
                stats.add_sample(
                    {
                        "reason": "club_fetch_failed",
                        "league": spec.name,
                        "club": club.get("name"),
                        "error": str(exc),
                    },
                    limit=sample_size,
                )
                continue

            for payload in payloads:
                stats.transfermarkt_players_seen += 1
                fact = _fact_from_payload(payload, spec)
                if fact is None:
                    continue
                _apply_fact(
                    session,
                    tm_session=tm_session,
                    fact=fact,
                    candidates_by_name=candidates_by_name,
                    cache=cache,
                    stats=stats,
                    apply=apply,
                    create_entities=create_entities,
                    enrich_dob=enrich_dob,
                    allow_unique_name_nationality=allow_unique_name_nationality,
                    profile_pause_ms=profile_pause_ms,
                    timeout_seconds=timeout_seconds,
                    sample_size=sample_size,
                )
            if pause_ms:
                time.sleep(pause_ms / 1000)
    return stats


def _load_existing_candidates(
    session: Session,
    *,
    include_transfermarkt_provider: bool = False,
) -> list[ExistingPlayerCandidate]:
    criteria = [
        Player.is_real_player.is_(True),
        Player.is_tradable.is_(True),
        or_(
            Player.country_id.is_(None),
            Player.current_club_id.is_(None),
            Player.current_competition_id.is_(None),
            Player.date_of_birth.is_(None),
        ),
    ]
    if not include_transfermarkt_provider:
        criteria.append(Player.source_provider != "transfermarkt")

    rows = session.execute(
        select(Player, Club.name, Competition.name, PlayerSummaryReadModel)
        .outerjoin(Club, Club.id == Player.current_club_id)
        .outerjoin(Competition, Competition.id == Player.current_competition_id)
        .outerjoin(PlayerSummaryReadModel, PlayerSummaryReadModel.player_id == Player.id)
        .where(*criteria)
    ).all()
    player_ids = [row[0].id for row in rows]
    profiles_by_player_id: dict[str, list[RealPlayerProfile]] = {player_id: [] for player_id in player_ids}
    for chunk in _chunks(player_ids, 1000):
        for profile in session.scalars(select(RealPlayerProfile).where(RealPlayerProfile.gtex_player_id.in_(chunk))):
            profiles_by_player_id.setdefault(profile.gtex_player_id, []).append(profile)

    candidates: list[ExistingPlayerCandidate] = []
    for player, club_name, competition_name, summary in rows:
        profiles = tuple(profiles_by_player_id.get(player.id, ()))
        name_keys = set[str]()
        for raw_name in (player.full_name, player.canonical_display_name, player.short_name):
            name_keys.update(_name_aliases(raw_name))
        if player.first_name or player.last_name:
            name_keys.update(_name_aliases(f"{player.first_name or ''} {player.last_name or ''}"))
        for profile in profiles:
            name_keys.update(_name_aliases(profile.canonical_name))
            for alias in profile.known_aliases_json or []:
                name_keys.update(_name_aliases(alias))
        name_keys = {key for key in name_keys if key}
        if not name_keys:
            continue

        club_labels = set[str]()
        for label in (
            player.real_world_club_name,
            club_name,
            summary.current_club_name if summary is not None else None,
            *(profile.current_club_name for profile in profiles),
        ):
            normalized = _normalize_label(label)
            if normalized:
                club_labels.add(normalized)

        league_labels = set[str]()
        for label in (
            player.real_world_league_name,
            competition_name,
            summary.current_competition_name if summary is not None else None,
            *(profile.current_league_name for profile in profiles),
        ):
            league_labels.update(_equivalent_labels(_normalize_label(label)))

        nationality_labels = set[str]()
        for label in (
            player.country.name if player.country is not None else None,
            *(profile.nationality for profile in profiles),
        ):
            normalized = _normalize_label(label)
            if normalized:
                nationality_labels.add(normalized)

        candidates.append(
            ExistingPlayerCandidate(
                player_id=player.id,
                name_keys=frozenset(name_keys),
                club_labels=frozenset(club_labels),
                league_labels=frozenset(label for label in league_labels if label),
                nationality_labels=frozenset(nationality_labels),
                date_of_birth=player.date_of_birth or _first_profile_dob(profiles),
                full_name=player.full_name,
                player=player,
                summary=summary,
                profiles=profiles,
            )
        )
    return candidates


def _index_candidates(candidates: Iterable[ExistingPlayerCandidate]) -> dict[str, list[ExistingPlayerCandidate]]:
    indexed: dict[str, list[ExistingPlayerCandidate]] = {}
    for candidate in candidates:
        for name_key in candidate.name_keys:
            indexed.setdefault(name_key, []).append(candidate)
    return indexed


def _fact_from_payload(payload: dict[str, Any], spec: CompetitionSpec) -> TransfermarktMetadataFact | None:
    display_name = str(payload.get("display_name") or payload.get("canonical_name") or "").strip()
    club_name = str(payload.get("current_real_world_club") or "").strip()
    club_key = str(payload.get("current_real_world_club_key") or "").strip()
    league_name = str(payload.get("current_real_world_league") or spec.name or "").strip()
    league_key = str(payload.get("current_real_world_league_key") or spec.competition_code or "").strip()
    source_key = str(payload.get("source_player_key") or "").strip()
    if not display_name or not club_name or not club_key or not league_name or not league_key or not source_key:
        return None
    return TransfermarktMetadataFact(
        source_player_key=source_key,
        display_name=display_name,
        club_name=club_name,
        club_key=club_key,
        league_name=league_name,
        league_key=league_key,
        league_country_name=_COMPETITION_COUNTRIES_BY_CODE.get(spec.competition_code),
        nationality=_clean_text(payload.get("nationality")),
        date_of_birth=_parse_date(payload.get("date_of_birth")),
        profile_path=str(payload.get("_tm_profile_path") or "").strip() or None,
        raw_payload=payload,
    )


def _apply_fact(
    session: Session,
    *,
    tm_session: requests.Session,
    fact: TransfermarktMetadataFact,
    candidates_by_name: dict[str, list[ExistingPlayerCandidate]],
    cache: EntityCache,
    stats: MetadataBackfillStats,
    apply: bool,
    create_entities: bool,
    enrich_dob: bool,
    allow_unique_name_nationality: bool,
    profile_pause_ms: int,
    timeout_seconds: int,
    sample_size: int,
) -> None:
    match_result = _match_fact(
        fact,
        candidates_by_name,
        allow_unique_name_nationality=allow_unique_name_nationality,
    )
    if match_result is None:
        stats.skipped_no_match += 1
        stats.add_sample(
            {
                "reason": "no_match",
                "name": fact.display_name,
                "club": fact.club_name,
                "league": fact.league_name,
            },
            limit=sample_size,
        )
        return
    if isinstance(match_result, list):
        stats.skipped_ambiguous += 1
        stats.add_sample(
            {
                "reason": "ambiguous",
                "name": fact.display_name,
                "club": fact.club_name,
                "league": fact.league_name,
                "candidate_names": [candidate.full_name for candidate in match_result[:5]],
            },
            limit=sample_size,
        )
        return

    candidate, confidence = match_result
    stats.matched_players += 1
    if enrich_dob and candidate.player.date_of_birth is None and fact.date_of_birth is None:
        enriched = _enrich_fact_dob(tm_session, fact, timeout_seconds=timeout_seconds)
        stats.profile_fetches += 1
        if enriched is None:
            stats.profile_fetch_failed += 1
        else:
            fact = enriched
        if profile_pause_ms:
            time.sleep(profile_pause_ms / 1000)

    player = candidate.player
    needs_country = player.country_id is None and bool(fact.nationality)
    needs_competition = player.current_competition_id is None and bool(fact.league_name)
    needs_club = player.current_club_id is None and bool(fact.club_name)
    needs_league_country = needs_competition or needs_club

    league_country = (
        _resolve_country_by_name(
            session,
            fact.league_country_name,
            cache=cache,
            stats=stats,
            apply=create_entities,
        )
        if needs_league_country
        else None
    )
    nationality_country = (
        _resolve_country_by_name(
            session,
            fact.nationality,
            cache=cache,
            stats=stats,
            apply=create_entities,
        )
        if needs_country
        else None
    )
    competition = (
        _resolve_competition(
            session,
            fact=fact,
            country=league_country,
            cache=cache,
            stats=stats,
            apply=create_entities,
        )
        if needs_competition or needs_club
        else None
    )
    club = (
        _resolve_club(
            session,
            fact=fact,
            country=league_country,
            competition=competition,
            cache=cache,
            stats=stats,
            apply=create_entities,
        )
        if needs_club
        else None
    )

    desired_updates = _desired_update_flags(candidate, fact=fact, nationality_country=nationality_country, competition=competition, club=club)
    if not any(desired_updates.values()):
        if _has_unresolved_missing_entity(candidate, fact=fact, nationality_country=nationality_country, competition=competition, club=club):
            stats.skipped_missing_entities += 1
        else:
            stats.skipped_no_updates += 1
        return

    now = datetime.now(UTC)
    if apply:
        player = candidate.player
        if desired_updates["country"] and nationality_country is not None:
            player.country_id = nationality_country.id
        if desired_updates["competition"] and competition is not None:
            player.current_competition_id = competition.id
        if desired_updates["club"] and club is not None:
            player.current_club_id = club.id
        if desired_updates["date_of_birth"] and fact.date_of_birth is not None:
            player.date_of_birth = fact.date_of_birth
        if desired_updates["real_world_labels"]:
            if not player.real_world_club_name:
                player.real_world_club_name = fact.club_name
            if not player.real_world_league_name:
                player.real_world_league_name = fact.league_name
        player.source_last_refreshed_at = now
        player.last_synced_at = now
        _update_profiles(candidate.profiles, fact=fact, as_of=now, stats=stats)
        _update_summary(candidate.summary, fact=fact, competition=competition, club=club, confidence=confidence, as_of=now, stats=stats)

    stats.players_updated += 1
    stats.country_fixed += int(desired_updates["country"])
    stats.competition_fixed += int(desired_updates["competition"])
    stats.club_fixed += int(desired_updates["club"])
    stats.date_of_birth_fixed += int(desired_updates["date_of_birth"])
    stats.real_world_labels_fixed += int(desired_updates["real_world_labels"])
    stats.add_sample(
        {
            "reason": "updated" if apply else "would_update",
            "player_id": candidate.player_id,
            "gtex_name": candidate.full_name,
            "transfermarkt_name": fact.display_name,
            "club": fact.club_name,
            "league": fact.league_name,
            "nationality": fact.nationality,
            "date_of_birth": fact.date_of_birth,
            "confidence": confidence,
            "updates": [key for key, enabled in desired_updates.items() if enabled],
        },
        limit=sample_size,
    )


def _match_fact(
    fact: TransfermarktMetadataFact,
    candidates_by_name: dict[str, list[ExistingPlayerCandidate]],
    *,
    allow_unique_name_nationality: bool = False,
) -> tuple[ExistingPlayerCandidate, str] | list[ExistingPlayerCandidate] | None:
    name_key = _normalize_name(fact.display_name)
    exact_candidates = candidates_by_name.get(name_key, [])
    exact_match = _match_candidates(
        fact,
        exact_candidates,
        allow_league_only=True,
        allow_unique_name_nationality=allow_unique_name_nationality,
        confidence_prefix="name",
    )
    if exact_match is not None:
        return exact_match

    alias_candidates: dict[str, ExistingPlayerCandidate] = {}
    for alias in _name_aliases(fact.display_name):
        if alias == name_key:
            continue
        if len(alias.split()) < 2:
            continue
        for candidate in candidates_by_name.get(alias, []):
            alias_candidates.setdefault(candidate.player_id, candidate)
    return _match_candidates(
        fact,
        alias_candidates.values(),
        allow_league_only=False,
        allow_unique_name_nationality=False,
        confidence_prefix="name_alias",
    )


def _match_candidates(
    fact: TransfermarktMetadataFact,
    candidates: Iterable[ExistingPlayerCandidate],
    *,
    allow_league_only: bool,
    allow_unique_name_nationality: bool,
    confidence_prefix: str,
) -> tuple[ExistingPlayerCandidate, str] | list[ExistingPlayerCandidate] | None:
    candidates = list(candidates)
    if not candidates:
        return None

    club_key = _normalize_label(fact.club_name)
    league_key = _normalize_label(fact.league_name)
    nationality_key = _normalize_label(fact.nationality)
    club_matches = [candidate for candidate in candidates if _any_label_matches(club_key, candidate.club_labels)]
    if len(club_matches) == 1:
        return club_matches[0], f"{confidence_prefix}+club"
    if len(club_matches) > 1:
        league_filtered = [candidate for candidate in club_matches if _any_label_matches(league_key, candidate.league_labels)]
        if len(league_filtered) == 1:
            return league_filtered[0], f"{confidence_prefix}+club+league"
        return club_matches

    if allow_league_only:
        league_matches = [candidate for candidate in candidates if _any_label_matches(league_key, candidate.league_labels)]
        if len(league_matches) == 1:
            return league_matches[0], f"{confidence_prefix}+league"
        if len(league_matches) > 1:
            return league_matches

    if allow_unique_name_nationality and len(candidates) == 1 and nationality_key:
        candidate = candidates[0]
        if _any_label_matches(nationality_key, candidate.nationality_labels):
            return candidate, f"{confidence_prefix}+unique+nationality"
    return None


def _desired_update_flags(
    candidate: ExistingPlayerCandidate,
    *,
    fact: TransfermarktMetadataFact,
    nationality_country: Country | None,
    competition: Competition | None,
    club: Club | None,
) -> dict[str, bool]:
    player = candidate.player
    return {
        "country": player.country_id is None and nationality_country is not None,
        "competition": player.current_competition_id is None and competition is not None,
        "club": player.current_club_id is None and club is not None,
        "date_of_birth": player.date_of_birth is None and fact.date_of_birth is not None,
        "real_world_labels": (not player.real_world_club_name and bool(fact.club_name))
        or (not player.real_world_league_name and bool(fact.league_name)),
    }


def _has_unresolved_missing_entity(
    candidate: ExistingPlayerCandidate,
    *,
    fact: TransfermarktMetadataFact,
    nationality_country: Country | None,
    competition: Competition | None,
    club: Club | None,
) -> bool:
    player = candidate.player
    return any(
        (
            player.country_id is None and bool(fact.nationality) and nationality_country is None,
            player.current_competition_id is None and bool(fact.league_name) and competition is None,
            player.current_club_id is None and bool(fact.club_name) and club is None,
        )
    )


def _resolve_country_by_name(
    session: Session,
    raw_name: str | None,
    *,
    cache: EntityCache,
    stats: MetadataBackfillStats,
    apply: bool,
) -> Country | None:
    name = _clean_text(raw_name)
    if not name:
        return None
    key = _normalize_label(name)
    if key in cache.countries_by_name:
        return cache.countries_by_name[key]
    country = session.scalar(select(Country).where(func.lower(Country.name) == name.lower()).limit(1))
    if country is None and apply:
        country = Country(
            id=str(uuid4()),
            source_provider="transfermarkt",
            provider_external_id=slugify(name),
            name=name,
            last_synced_at=datetime.now(UTC),
        )
        session.add(country)
        stats.countries_created += 1
    elif country is None:
        stats.countries_created += 1
    cache.countries_by_name[key] = country
    return country


def _resolve_competition(
    session: Session,
    *,
    fact: TransfermarktMetadataFact,
    country: Country | None,
    cache: EntityCache,
    stats: MetadataBackfillStats,
    apply: bool,
) -> Competition | None:
    name = _clean_text(fact.league_name)
    provider_external_id = _clean_text(fact.league_key)
    if not name and not provider_external_id:
        return None
    cache_key = ("transfermarkt", provider_external_id, _normalize_label(name), country.id if country else None)
    if cache_key in cache.competitions:
        return cache.competitions[cache_key]
    competition = None
    if provider_external_id:
        competition = session.scalar(
            select(Competition)
            .where(Competition.source_provider == "transfermarkt", Competition.provider_external_id == provider_external_id)
            .limit(1)
        )
    if competition is None and name:
        labels = _equivalent_labels(_normalize_label(name))
        rows = session.scalars(select(Competition)).all()
        for existing in rows:
            if _normalize_label(existing.name) in labels:
                competition = existing
                break
    if competition is None and apply:
        competition = Competition(
            id=str(uuid4()),
            source_provider="transfermarkt",
            provider_external_id=provider_external_id or slugify(name),
            country_id=country.id if country is not None else None,
            name=name or provider_external_id or "Unknown League",
            slug=slugify(name or provider_external_id),
            code=provider_external_id,
            competition_type="league",
            format_type="real_world",
            is_tradable=True,
            last_synced_at=datetime.now(UTC),
        )
        session.add(competition)
        stats.competitions_created += 1
    elif competition is None:
        stats.competitions_created += 1
    cache.competitions[cache_key] = competition
    return competition


def _resolve_club(
    session: Session,
    *,
    fact: TransfermarktMetadataFact,
    country: Country | None,
    competition: Competition | None,
    cache: EntityCache,
    stats: MetadataBackfillStats,
    apply: bool,
) -> Club | None:
    name = _clean_text(fact.club_name)
    provider_external_id = _clean_text(fact.club_key)
    if not name and not provider_external_id:
        return None
    cache_key = (
        "transfermarkt",
        provider_external_id,
        _normalize_label(name),
        country.id if country else None,
        competition.id if competition else None,
    )
    if cache_key in cache.clubs:
        return cache.clubs[cache_key]
    club = None
    if provider_external_id:
        club = session.scalar(
            select(Club)
            .where(Club.source_provider == "transfermarkt", Club.provider_external_id == provider_external_id)
            .limit(1)
        )
    if club is None and name:
        criteria = [func.lower(Club.name) == name.lower()]
        if competition is not None:
            criteria.append(Club.current_competition_id == competition.id)
        elif country is not None:
            criteria.append(Club.country_id == country.id)
        club = session.scalar(select(Club).where(*criteria).limit(1))
    if club is None and competition is None:
        cache.clubs[cache_key] = None
        return None
    if club is None and apply:
        club = Club(
            id=str(uuid4()),
            source_provider="transfermarkt",
            provider_external_id=provider_external_id or slugify(name),
            country_id=country.id if country is not None else None,
            current_competition_id=competition.id if competition is not None else None,
            name=name or provider_external_id or "Unknown Club",
            slug=slugify(name or provider_external_id),
            short_name=(name or provider_external_id or "Unknown Club")[:80],
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


def _update_profiles(
    profiles: tuple[RealPlayerProfile, ...],
    *,
    fact: TransfermarktMetadataFact,
    as_of: datetime,
    stats: MetadataBackfillStats,
) -> None:
    changed_count = 0
    for profile in profiles:
        changed = False
        if fact.nationality and not profile.nationality:
            profile.nationality = fact.nationality
            changed = True
        if fact.date_of_birth and profile.date_of_birth is None:
            profile.date_of_birth = fact.date_of_birth
            profile.birth_year = fact.date_of_birth.year
            changed = True
        if fact.club_name and not profile.current_club_name:
            profile.current_club_name = fact.club_name
            changed = True
        if fact.league_name and not profile.current_league_name:
            profile.current_league_name = fact.league_name
            changed = True
        metadata = dict(profile.metadata_json or {})
        backfills = dict(metadata.get("metadata_backfills") or {})
        backfills["transfermarkt_metadata_backfill"] = {
            "source_player_key": fact.source_player_key,
            "club": fact.club_name,
            "league": fact.league_name,
            "refreshed_at": as_of.isoformat(),
        }
        metadata["metadata_backfills"] = backfills
        profile.metadata_json = metadata
        profile.source_last_refreshed_at = as_of
        changed_count += int(changed)
    stats.profiles_updated += changed_count


def _update_summary(
    summary: PlayerSummaryReadModel | None,
    *,
    fact: TransfermarktMetadataFact,
    competition: Competition | None,
    club: Club | None,
    confidence: str,
    as_of: datetime,
    stats: MetadataBackfillStats,
) -> None:
    if summary is None:
        return
    changed = False
    if club is not None and not summary.current_club_id:
        summary.current_club_id = club.id
        changed = True
    if fact.club_name and not summary.current_club_name:
        summary.current_club_name = fact.club_name
        changed = True
    if competition is not None and not summary.current_competition_id:
        summary.current_competition_id = competition.id
        changed = True
    if fact.league_name and not summary.current_competition_name:
        summary.current_competition_name = fact.league_name
        changed = True
    payload = dict(summary.summary_json or {})
    payload["transfermarkt_metadata_backfill"] = {
        "source_player_key": fact.source_player_key,
        "transfermarkt_name": fact.display_name,
        "club": fact.club_name,
        "league": fact.league_name,
        "nationality": fact.nationality,
        "date_of_birth": fact.date_of_birth.isoformat() if fact.date_of_birth else None,
        "match_confidence": confidence,
        "refreshed_at": as_of.isoformat(),
    }
    summary.summary_json = payload
    summary.updated_at = as_of
    stats.summaries_updated += int(changed)


def _enrich_fact_dob(
    tm_session: requests.Session,
    fact: TransfermarktMetadataFact,
    *,
    timeout_seconds: int,
) -> TransfermarktMetadataFact | None:
    enriched_payload = _enrich_payload_from_profile(
        tm_session=tm_session,
        payload=fact.raw_payload,
        timeout_seconds=timeout_seconds,
    )
    if not enriched_payload:
        return None
    enriched_dob = _parse_date(enriched_payload.get("date_of_birth"))
    if enriched_dob is None:
        return None
    return TransfermarktMetadataFact(
        source_player_key=fact.source_player_key,
        display_name=fact.display_name,
        club_name=fact.club_name,
        club_key=fact.club_key,
        league_name=fact.league_name,
        league_key=fact.league_key,
        league_country_name=fact.league_country_name,
        nationality=fact.nationality or _clean_text(enriched_payload.get("nationality")),
        date_of_birth=enriched_dob,
        profile_path=fact.profile_path,
        raw_payload=enriched_payload,
    )


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def _first_profile_dob(profiles: tuple[RealPlayerProfile, ...]) -> date | None:
    for profile in profiles:
        if profile.date_of_birth is not None:
            return profile.date_of_birth
    return None


def _chunks(values: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


if __name__ == "__main__":
    raise SystemExit(main())
