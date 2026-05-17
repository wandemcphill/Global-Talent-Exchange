from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
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
from app.ingestion.models import Club, Country, Player
from app.ingestion.normalizers import slugify
from app.models.real_player_profile import RealPlayerProfile
from app.players.read_models import PlayerSummaryReadModel
from backend.scripts.backfill_transfermarkt_player_metadata import (
    ExistingPlayerCandidate,
    _chunks,
    _first_profile_dob,
    _index_candidates,
    _name_aliases,
    _normalize_label,
    _normalize_name,
    _parse_date,
    _resolve_country_by_name,
    _update_profiles,
    _update_summary,
    EntityCache,
    MetadataBackfillStats,
    TransfermarktMetadataFact,
)
from backend.scripts.backfill_transfermarkt_market_values import _any_label_matches, _equivalent_labels
from backend.scripts.import_transfermarkt_real_players import (
    _TM_BASE_URL,
    _TM_HEADERS,
    _clean_text,
    _get_html,
    _parse_youth_team_payloads,
    _resolve_youth_team_reference,
)

DEFAULT_COUNTRIES = (
    "Denmark",
    "Poland",
    "Austria",
    "Germany",
    "Spain",
    "Italy",
    "United States",
    "England",
    "Russia",
    "France",
    "Netherlands",
    "Portugal",
    "Sweden",
    "Ukraine",
    "Nigeria",
)
DEFAULT_AGE_GROUPS = ("U21", "U20", "U19", "U18", "U17")


@dataclass(slots=True)
class YouthTeamStats(MetadataBackfillStats):
    countries_scanned: int = 0
    youth_teams_scanned: int = 0
    youth_team_fetch_failed: int = 0
    club_without_competition_created: int = 0
    matched_by_national_team_context: int = 0
    skipped_no_national_team_context: int = 0


@dataclass(frozen=True, slots=True)
class YouthTeamSpec:
    country_name: str
    search_name: str
    age_group: str

    @property
    def team_label(self) -> str:
        return f"{self.country_name} {self.age_group}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Repair existing GTEX real-player DOB, country, and current club fields from "
            "Transfermarkt youth national-team squad pages. This does not import new players."
        )
    )
    parser.add_argument("--database-url", default=os.environ.get("GTE_DATABASE_URL"))
    parser.add_argument("--apply", action="store_true", help="Write updates. Default is dry-run.")
    parser.add_argument(
        "--create-clubs",
        action="store_true",
        help="Create provider-backed Transfermarkt club rows when an exact club ID is present.",
    )
    parser.add_argument(
        "--include-transfermarkt-provider",
        action="store_true",
        help="Allow matching against ingestion_players rows whose source_provider is transfermarkt.",
    )
    parser.add_argument("--country", dest="countries", action="append", default=[])
    parser.add_argument("--age-group", dest="age_groups", action="append", default=[])
    parser.add_argument("--pause-ms", type=int, default=250)
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
        stats = _run_with_retries(
            session_factory,
            tm_session=tm_session,
            countries=args.countries or list(DEFAULT_COUNTRIES),
            age_groups=args.age_groups or list(DEFAULT_AGE_GROUPS),
            apply=bool(args.apply),
            create_clubs=bool(args.create_clubs),
            include_transfermarkt_provider=bool(args.include_transfermarkt_provider),
            pause_ms=max(int(args.pause_ms), 0),
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
                    "create_clubs": bool(args.create_clubs),
                    "include_transfermarkt_provider": bool(args.include_transfermarkt_provider),
                    "countries": args.countries or list(DEFAULT_COUNTRIES),
                    "age_groups": args.age_groups or list(DEFAULT_AGE_GROUPS),
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


def _run_with_retries(
    session_factory,
    *,
    tm_session: requests.Session,
    countries: Sequence[str],
    age_groups: Sequence[str],
    apply: bool,
    create_clubs: bool,
    include_transfermarkt_provider: bool,
    pause_ms: int,
    timeout_seconds: int,
    sample_size: int,
    attempts: int,
    base_seconds: float,
) -> YouthTeamStats:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with session_factory() as session:
                stats = backfill_transfermarkt_youth_metadata(
                    session,
                    tm_session=tm_session,
                    countries=countries,
                    age_groups=age_groups,
                    apply=apply,
                    create_clubs=create_clubs,
                    include_transfermarkt_provider=include_transfermarkt_provider,
                    pause_ms=pause_ms,
                    timeout_seconds=timeout_seconds,
                    sample_size=sample_size,
                )
                if apply:
                    session.commit()
                return stats
        except (DBAPIError, OperationalError) as exc:
            last_error = exc
            if attempt >= attempts:
                raise
            delay_seconds = base_seconds * attempt
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


def backfill_transfermarkt_youth_metadata(
    session: Session,
    *,
    tm_session: requests.Session,
    countries: Sequence[str],
    age_groups: Sequence[str],
    apply: bool,
    create_clubs: bool,
    include_transfermarkt_provider: bool,
    pause_ms: int,
    timeout_seconds: int,
    sample_size: int,
) -> YouthTeamStats:
    stats = YouthTeamStats()
    cache = EntityCache()
    for spec in _youth_specs(countries=countries, age_groups=age_groups):
        stats.countries_scanned += 1
        try:
            team_ref = _resolve_youth_team_reference(
                tm_session=tm_session,
                query=f"{spec.search_name} {spec.age_group}",
                age_group=spec.age_group,
                timeout_seconds=timeout_seconds,
            )
            squad_url = f"{_TM_BASE_URL}/{team_ref['slug']}/kader/verein/{team_ref['id']}/saison_id/2025"
            squad_html = _get_html(
                tm_session,
                squad_url,
                description=f"youth team {spec.team_label}",
                timeout_seconds=timeout_seconds,
            )
        except Exception as exc:  # pragma: no cover - live provider dependent
            stats.youth_team_fetch_failed += 1
            stats.add_sample(
                {"reason": "youth_team_fetch_failed", "team": spec.team_label, "error": str(exc)},
                limit=sample_size,
            )
            continue

        stats.youth_teams_scanned += 1
        payloads = _parse_youth_team_payloads(
            squad_html=squad_html,
            country_name=spec.country_name,
            age_group=spec.age_group,
        )
        candidates = _load_existing_candidates_for_team(
            session,
            team_label=spec.team_label,
            include_transfermarkt_provider=include_transfermarkt_provider,
        )
        candidates_by_name = _index_candidates(candidates)
        for payload in payloads:
            stats.transfermarkt_players_seen += 1
            fact = _fact_from_youth_payload(payload, spec)
            if fact is None:
                continue
            _apply_youth_fact(
                session,
                fact=fact,
                team_label=spec.team_label,
                candidates_by_name=candidates_by_name,
                cache=cache,
                stats=stats,
                apply=apply,
                create_clubs=create_clubs,
                sample_size=sample_size,
            )
        if pause_ms:
            time.sleep(pause_ms / 1000)
    return stats


def _load_existing_candidates_for_team(
    session: Session,
    *,
    team_label: str,
    include_transfermarkt_provider: bool,
) -> list[ExistingPlayerCandidate]:
    labels = _team_label_variants(team_label)
    criteria = [
        Player.is_real_player.is_(True),
        Player.is_tradable.is_(True),
        (
            (Player.country_id.is_(None))
            | (Player.current_club_id.is_(None))
            | (Player.current_competition_id.is_(None))
            | (Player.date_of_birth.is_(None))
        ),
        or_(
            func.lower(Player.real_world_club_name).in_(labels),
            func.lower(Club.name).in_(labels),
            func.lower(PlayerSummaryReadModel.current_club_name).in_(labels),
        ),
    ]
    if not include_transfermarkt_provider:
        criteria.append(Player.source_provider != "transfermarkt")

    rows = session.execute(
        select(Player, Club.name, Country.name, PlayerSummaryReadModel)
        .outerjoin(Club, Club.id == Player.current_club_id)
        .outerjoin(Country, Country.id == Player.country_id)
        .outerjoin(PlayerSummaryReadModel, PlayerSummaryReadModel.player_id == Player.id)
        .where(*criteria)
    ).all()
    return _candidates_from_rows(session, rows)


def _load_existing_candidates(
    session: Session,
    *,
    include_transfermarkt_provider: bool,
) -> list[ExistingPlayerCandidate]:
    criteria = [
        Player.is_real_player.is_(True),
        Player.is_tradable.is_(True),
        (
            (Player.country_id.is_(None))
            | (Player.current_club_id.is_(None))
            | (Player.current_competition_id.is_(None))
            | (Player.date_of_birth.is_(None))
        ),
    ]
    if not include_transfermarkt_provider:
        criteria.append(Player.source_provider != "transfermarkt")

    rows = session.execute(
        select(Player, Club.name, Country.name, PlayerSummaryReadModel)
        .outerjoin(Club, Club.id == Player.current_club_id)
        .outerjoin(Country, Country.id == Player.country_id)
        .outerjoin(PlayerSummaryReadModel, PlayerSummaryReadModel.player_id == Player.id)
        .where(*criteria)
    ).all()
    return _candidates_from_rows(session, rows)


def _candidates_from_rows(session: Session, rows: Sequence[tuple[Any, ...]]) -> list[ExistingPlayerCandidate]:
    player_ids = [row[0].id for row in rows]
    profiles_by_player_id: dict[str, list[RealPlayerProfile]] = {player_id: [] for player_id in player_ids}
    for chunk in _chunks(player_ids, 1000):
        for profile in session.scalars(select(RealPlayerProfile).where(RealPlayerProfile.gtex_player_id.in_(chunk))):
            profiles_by_player_id.setdefault(profile.gtex_player_id, []).append(profile)

    candidates: list[ExistingPlayerCandidate] = []
    for player, club_name, country_name, summary in rows:
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

        nationality_labels = set[str]()
        for label in (
            country_name,
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
                league_labels=frozenset(),
                nationality_labels=frozenset(nationality_labels),
                date_of_birth=player.date_of_birth or _first_profile_dob(profiles),
                full_name=player.full_name,
                player=player,
                summary=summary,
                profiles=profiles,
            )
        )
    return candidates


def _apply_youth_fact(
    session: Session,
    *,
    fact: TransfermarktMetadataFact,
    team_label: str,
    candidates_by_name: dict[str, list[ExistingPlayerCandidate]],
    cache: EntityCache,
    stats: YouthTeamStats,
    apply: bool,
    create_clubs: bool,
    sample_size: int,
) -> None:
    match_result = _match_youth_fact(fact, team_label, candidates_by_name)
    if match_result is None:
        stats.skipped_no_match += 1
        stats.add_sample(
            {"reason": "no_match", "name": fact.display_name, "team": team_label, "club": fact.club_name},
            limit=sample_size,
        )
        return
    if isinstance(match_result, list):
        stats.skipped_ambiguous += 1
        stats.add_sample(
            {
                "reason": "ambiguous",
                "name": fact.display_name,
                "team": team_label,
                "candidate_names": [candidate.full_name for candidate in match_result[:5]],
            },
            limit=sample_size,
        )
        return

    candidate, confidence = match_result
    stats.matched_players += 1
    stats.matched_by_national_team_context += int("national_team" in confidence)
    player = candidate.player
    country = (
        _resolve_country_by_name(
            session,
            fact.nationality,
            cache=cache,
            stats=stats,
            apply=False,
        )
        if player.country_id is None
        else None
    )
    club = (
        _resolve_transfermarkt_club_without_competition(
            session,
            fact=fact,
            cache=cache,
            stats=stats,
            apply=create_clubs,
        )
        if player.current_club_id is None
        else None
    )

    desired_updates = {
        "country": player.country_id is None and country is not None,
        "club": player.current_club_id is None and club is not None,
        "date_of_birth": player.date_of_birth is None and fact.date_of_birth is not None,
    }
    if not any(desired_updates.values()):
        if player.current_club_id is None and fact.club_name and club is None:
            stats.skipped_missing_entities += 1
        else:
            stats.skipped_no_updates += 1
        return

    now = datetime.now(UTC)
    if apply:
        if desired_updates["country"] and country is not None:
            player.country_id = country.id
        if desired_updates["club"] and club is not None:
            player.current_club_id = club.id
        if desired_updates["date_of_birth"] and fact.date_of_birth is not None:
            player.date_of_birth = fact.date_of_birth
        player.source_last_refreshed_at = now
        player.last_synced_at = now
        _update_profiles(candidate.profiles, fact=fact, as_of=now, stats=stats)
        _update_summary(
            candidate.summary, fact=fact, competition=None, club=club, confidence=confidence, as_of=now, stats=stats
        )

    stats.players_updated += 1
    stats.country_fixed += int(desired_updates["country"])
    stats.club_fixed += int(desired_updates["club"])
    stats.date_of_birth_fixed += int(desired_updates["date_of_birth"])
    stats.add_sample(
        {
            "reason": "updated" if apply else "would_update",
            "player_id": candidate.player_id,
            "gtex_name": candidate.full_name,
            "transfermarkt_name": fact.display_name,
            "team": team_label,
            "club": fact.club_name,
            "nationality": fact.nationality,
            "date_of_birth": fact.date_of_birth,
            "confidence": confidence,
            "updates": [key for key, enabled in desired_updates.items() if enabled],
        },
        limit=sample_size,
    )


def _match_youth_fact(
    fact: TransfermarktMetadataFact,
    team_label: str,
    candidates_by_name: dict[str, list[ExistingPlayerCandidate]],
) -> tuple[ExistingPlayerCandidate, str] | list[ExistingPlayerCandidate] | None:
    name_key = _normalize_name(fact.display_name)
    candidates = list(candidates_by_name.get(name_key, []))
    if not candidates:
        return None

    team_labels = {
        _normalize_label(team_label),
        _normalize_label(team_label.replace("United States", "USA")),
        _normalize_label(team_label.replace("USA", "United States")),
    }
    team_labels.update(_equivalent_labels(_normalize_label(team_label)))
    team_matches = [
        candidate
        for candidate in candidates
        if any(_any_label_matches(label, candidate.club_labels) for label in team_labels if label)
    ]
    if len(team_matches) == 1:
        return team_matches[0], "name+national_team_context"
    if len(team_matches) > 1:
        return team_matches
    return None


def _resolve_transfermarkt_club_without_competition(
    session: Session,
    *,
    fact: TransfermarktMetadataFact,
    cache: EntityCache,
    stats: YouthTeamStats,
    apply: bool,
) -> Club | None:
    name = _clean_text(fact.club_name)
    provider_external_id = _clean_text(fact.club_key)
    if not name and not provider_external_id:
        return None
    cache_key = ("transfermarkt_youth_club", provider_external_id, _normalize_label(name))
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
        club = session.scalar(select(Club).where(func.lower(Club.name) == name.lower()).limit(1))
    if club is None and apply:
        club = Club(
            id=str(uuid4()),
            source_provider="transfermarkt",
            provider_external_id=provider_external_id or slugify(name),
            name=name or provider_external_id or "Unknown Club",
            slug=slugify(name or provider_external_id),
            short_name=(name or provider_external_id or "Unknown Club")[:80],
            is_tradable=True,
            last_synced_at=datetime.now(UTC),
        )
        session.add(club)
        stats.clubs_created += 1
        stats.club_without_competition_created += 1
    elif club is None:
        stats.clubs_created += 1
    cache.clubs[cache_key] = club
    return club


def _fact_from_youth_payload(payload: dict[str, Any], spec: YouthTeamSpec) -> TransfermarktMetadataFact | None:
    display_name = str(payload.get("display_name") or payload.get("canonical_name") or "").strip()
    club_name = str(payload.get("current_real_world_club") or "").strip()
    club_key = str(payload.get("current_real_world_club_key") or "").strip()
    source_key = str(payload.get("source_player_key") or "").strip()
    if not display_name or not club_name or not club_key or not source_key:
        return None
    return TransfermarktMetadataFact(
        source_player_key=source_key,
        display_name=display_name,
        club_name=club_name,
        club_key=club_key,
        league_name=spec.team_label,
        league_key=f"{_normalize_label(spec.country_name)}-{spec.age_group.lower()}",
        league_country_name=spec.country_name,
        nationality=_clean_text(payload.get("nationality")) or spec.country_name,
        date_of_birth=_parse_date(payload.get("date_of_birth")),
        profile_path=str(payload.get("_tm_profile_path") or "").strip() or None,
        raw_payload=payload,
    )


def _youth_specs(*, countries: Sequence[str], age_groups: Sequence[str]) -> Iterable[YouthTeamSpec]:
    for country in countries:
        country_name = _canonical_country_name(country)
        search_name = "United States" if country_name == "USA" else country_name
        for age_group in age_groups:
            cleaned_age_group = age_group.strip().upper()
            if cleaned_age_group:
                yield YouthTeamSpec(country_name=country_name, search_name=search_name, age_group=cleaned_age_group)


def _canonical_country_name(value: str) -> str:
    cleaned = _clean_text(value)
    if cleaned.lower() in {"united states", "usa", "us"}:
        return "USA"
    return cleaned


def _team_label_variants(team_label: str) -> set[str]:
    labels = {team_label.strip()}
    labels.add(team_label.replace("United States", "USA").strip())
    labels.add(team_label.replace("USA", "United States").strip())
    normalized = {_normalize_label(label) for label in labels if label}
    normalized.update(_equivalent_labels(_normalize_label(team_label)))
    return {label.lower() for label in labels | normalized if label}


if __name__ == "__main__":
    raise SystemExit(main())
