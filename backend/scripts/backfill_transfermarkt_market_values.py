from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import sys
import time
import unicodedata
from typing import Any, Iterable, Sequence

import requests
from sqlalchemy import select
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
from app.ingestion.models import Club, Competition, Player
from app.models.real_player_profile import RealPlayerProfile
from app.players.read_models import PlayerSummaryReadModel
from app.value_engine.scoring import credits_from_real_world_value
from backend.scripts.import_transfermarkt_real_players import (
    CompetitionSpec,
    _TM_BASE_URL,
    _TM_HEADERS,
    _get_html,
    _parse_competition_clubs,
    _parse_domestic_squad_payloads,
)


_CLUB_STOP_WORDS = {
    "a",
    "ac",
    "afc",
    "as",
    "atletico",
    "bk",
    "calcio",
    "cf",
    "club",
    "de",
    "fc",
    "fk",
    "football",
    "if",
    "la",
    "sc",
    "sk",
    "sporting",
    "the",
}

_VALUE_ONLY_COMPETITIONS: tuple[CompetitionSpec, ...] = (
    CompetitionSpec("Premier League", "GB1", "premier-league", "elite"),
    CompetitionSpec("Championship", "GB2", "championship", "second_tier"),
    CompetitionSpec("La Liga", "ES1", "laliga", "elite"),
    CompetitionSpec("Italian Serie A", "IT1", "serie-a", "elite"),
    CompetitionSpec("French Ligue 1", "FR1", "ligue-1", "elite"),
    CompetitionSpec("Saudi Pro League", "SA1", "saudi-professional-league", "elite"),
    CompetitionSpec("Major League Soccer", "MLS1", "major-league-soccer", "elite"),
    CompetitionSpec("Brazilian Serie A", "BRA1", "campeonato-brasileiro-serie-a", "elite"),
    CompetitionSpec("Argentinian Primera Division", "AR1N", "liga-profesional-de-futbol", "elite"),
    CompetitionSpec("Belgian Pro League", "BE1", "jupiler-pro-league", "elite"),
    CompetitionSpec("Spanish La Liga 2", "ES2", "laliga2", "second_tier"),
    CompetitionSpec("Italian Serie B", "IT2", "serie-b", "second_tier"),
    CompetitionSpec("Eredivisie", "NL1", "eredivisie", "elite"),
    CompetitionSpec("Bundesliga", "L1", "bundesliga", "elite"),
    CompetitionSpec("Austrian Bundesliga", "A1", "bundesliga", "elite"),
    CompetitionSpec("Swiss Super League", "C1", "super-league", "elite"),
    CompetitionSpec("Danish Superliga", "DK1", "superligaen", "elite"),
    CompetitionSpec("Turkish Super Lig", "TR1", "super-lig", "elite"),
    CompetitionSpec("Czech First League", "TS1", "chance-liga", "elite"),
    CompetitionSpec("Portuguese Primeira Liga", "PO1", "liga-nos", "elite"),
)

_LEAGUE_LABEL_ALIASES: tuple[tuple[str, ...], ...] = (
    ("argentinian primera division", "liga profesional de futbol", "argentina primera division"),
    ("brazilian serie a", "serie a brasil", "brasileirao serie a"),
    ("czech first league", "chance liga"),
    ("french ligue 1", "ligue 1"),
    ("french ligue 2", "ligue 2"),
    ("italian serie a", "serie a"),
    ("italian serie b", "serie b"),
    ("portuguese primeira liga", "liga portugal", "liga portugal bwin"),
    ("spanish la liga 2", "la liga 2", "laliga2"),
    ("austrian bundesliga", "admiral bundesliga", "bundesliga austria"),
    ("swiss super league", "brack super league", "super league switzerland"),
    ("danish superliga", "superliga", "3f superliga", "superligaen"),
    ("turkish super lig", "super lig", "sueper lig", "trendyol super lig"),
)


@dataclass(slots=True)
class ExistingPlayerCandidate:
    player_id: str
    name_keys: frozenset[str]
    club_labels: frozenset[str]
    league_labels: frozenset[str]
    full_name: str | None
    current_value_eur: float | None
    player: Player
    summary: PlayerSummaryReadModel | None


@dataclass(slots=True)
class TransfermarktValueFact:
    source_player_key: str
    display_name: str
    club_name: str
    league_name: str
    value_eur: float
    raw_payload: dict[str, Any] = field(repr=False)


@dataclass(slots=True)
class ValueBackfillStats:
    competitions_scanned: int = 0
    clubs_scanned: int = 0
    clubs_failed: int = 0
    transfermarkt_players_seen: int = 0
    transfermarkt_players_with_value: int = 0
    matched_players: int = 0
    updated_players: int = 0
    updated_summaries: int = 0
    updated_profiles: int = 0
    skipped_existing_value: int = 0
    skipped_no_value: int = 0
    skipped_no_match: int = 0
    skipped_ambiguous: int = 0
    samples: list[dict[str, Any]] = field(default_factory=list)

    def add_sample(self, payload: dict[str, Any], *, limit: int) -> None:
        if limit <= 0 or len(self.samples) >= limit:
            return
        self.samples.append(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill real GTEX player market values from Transfermarkt without creating players. "
            "Only updates existing real/tradable players when name plus club/league matching is safe."
        )
    )
    parser.add_argument("--database-url", default=os.environ.get("GTE_DATABASE_URL"))
    parser.add_argument("--apply", action="store_true", help="Write updates. Default is dry-run.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing positive market values on safe matches.")
    parser.add_argument(
        "--include-transfermarkt-provider",
        action="store_true",
        help=(
            "Allow matching against ingestion_players rows whose source_provider is transfermarkt. "
            "Default excludes them so this script enriches the SportMonks-backed player universe only."
        ),
    )
    parser.add_argument("--league", dest="leagues", action="append", default=[], help="Repeat to limit leagues.")
    parser.add_argument("--limit-clubs", type=int, default=0, help="Limit clubs per selected league; 0 means all.")
    parser.add_argument("--pause-ms", type=int, default=250, help="Pause between Transfermarkt squad requests.")
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
            force=bool(args.force),
            include_transfermarkt_provider=bool(args.include_transfermarkt_provider),
            limit_clubs=max(int(args.limit_clubs), 0),
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
                    "force": bool(args.force),
                    "include_transfermarkt_provider": bool(args.include_transfermarkt_provider),
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
    force: bool,
    include_transfermarkt_provider: bool,
    limit_clubs: int,
    pause_ms: int,
    timeout_seconds: int,
    sample_size: int,
    attempts: int,
    base_seconds: float,
) -> ValueBackfillStats:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with session_factory() as db_session:
                stats = backfill_transfermarkt_values(
                    db_session,
                    tm_session=tm_session,
                    leagues=leagues,
                    apply=apply,
                    force=force,
                    include_transfermarkt_provider=include_transfermarkt_provider,
                    limit_clubs=limit_clubs,
                    pause_ms=pause_ms,
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


def backfill_transfermarkt_values(
    session: Session,
    *,
    tm_session: requests.Session,
    leagues: Sequence[str],
    apply: bool,
    force: bool,
    include_transfermarkt_provider: bool,
    limit_clubs: int,
    pause_ms: int,
    timeout_seconds: int,
    sample_size: int,
) -> ValueBackfillStats:
    stats = ValueBackfillStats()
    candidates = _load_existing_candidates(session, include_transfermarkt_provider=include_transfermarkt_provider)
    index = _index_candidates(candidates)
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
                fact = _fact_from_payload(payload)
                if fact is None:
                    stats.skipped_no_value += 1
                    continue
                stats.transfermarkt_players_with_value += 1
                _apply_fact(
                    session,
                    fact=fact,
                    candidates_by_name=index,
                    stats=stats,
                    apply=apply,
                    force=force,
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
    criteria = [Player.is_real_player.is_(True), Player.is_tradable.is_(True)]
    if not include_transfermarkt_provider:
        criteria.append(Player.source_provider != "transfermarkt")
    rows = session.execute(
        select(Player, Club.name, Competition.name, PlayerSummaryReadModel)
        .outerjoin(Club, Club.id == Player.current_club_id)
        .outerjoin(Competition, Competition.id == Player.current_competition_id)
        .outerjoin(PlayerSummaryReadModel, PlayerSummaryReadModel.player_id == Player.id)
        .where(*criteria)
    ).all()
    candidates: list[ExistingPlayerCandidate] = []
    for player, club_name, competition_name, summary in rows:
        name_keys = set[str]()
        for raw_name in (player.full_name, player.canonical_display_name, player.short_name):
            name_keys.update(_name_aliases(raw_name))
        if player.first_name or player.last_name:
            name_keys.update(_name_aliases(f"{player.first_name or ''} {player.last_name or ''}"))
        name_keys = {key for key in name_keys if key}
        if not name_keys:
            continue
        club_labels = {
            _normalize_label(player.real_world_club_name),
            _normalize_label(club_name),
            _normalize_label(summary.current_club_name if summary is not None else None),
        }
        league_labels = set[str]()
        for label in (
            player.real_world_league_name,
            competition_name,
            summary.current_competition_name if summary is not None else None,
        ):
            league_labels.update(_equivalent_labels(_normalize_label(label)))
        candidates.append(
            ExistingPlayerCandidate(
                player_id=player.id,
                name_keys=frozenset(name_keys),
                club_labels=frozenset(label for label in club_labels if label),
                league_labels=frozenset(label for label in league_labels if label),
                full_name=player.full_name,
                current_value_eur=_positive_float(player.current_market_reference_value)
                or _positive_float(player.market_value_eur),
                player=player,
                summary=summary,
            )
        )
    return candidates


def _select_value_competitions(requested_leagues: list[str]) -> tuple[CompetitionSpec, ...]:
    if not requested_leagues:
        return _VALUE_ONLY_COMPETITIONS
    requested = {_normalize_label(value) for value in requested_leagues if _normalize_label(value)}
    selected = tuple(
        spec
        for spec in _VALUE_ONLY_COMPETITIONS
        if _normalize_label(spec.name) in requested
        or _normalize_label(spec.competition_code) in requested
        or _normalize_label(spec.slug) in requested
    )
    if not selected:
        available = ", ".join(spec.name for spec in _VALUE_ONLY_COMPETITIONS)
        raise ValueError(f"None of the requested leagues matched value-only competitions. Available: {available}")
    return selected


def _index_candidates(candidates: Iterable[ExistingPlayerCandidate]) -> dict[str, list[ExistingPlayerCandidate]]:
    indexed: dict[str, list[ExistingPlayerCandidate]] = {}
    for candidate in candidates:
        for name_key in candidate.name_keys:
            indexed.setdefault(name_key, []).append(candidate)
    return indexed


def _fact_from_payload(payload: dict[str, Any]) -> TransfermarktValueFact | None:
    value = _positive_float(payload.get("current_market_reference_value"))
    if value is None:
        return None
    display_name = str(payload.get("display_name") or payload.get("canonical_name") or "").strip()
    club_name = str(payload.get("current_real_world_club") or "").strip()
    league_name = str(payload.get("current_real_world_league") or "").strip()
    source_key = str(payload.get("source_player_key") or "").strip()
    if not display_name or not club_name or not league_name or not source_key:
        return None
    return TransfermarktValueFact(
        source_player_key=source_key,
        display_name=display_name,
        club_name=club_name,
        league_name=league_name,
        value_eur=value,
        raw_payload=payload,
    )


def _apply_fact(
    session: Session,
    *,
    fact: TransfermarktValueFact,
    candidates_by_name: dict[str, list[ExistingPlayerCandidate]],
    stats: ValueBackfillStats,
    apply: bool,
    force: bool,
    sample_size: int,
) -> None:
    match_result = _match_fact(fact, candidates_by_name)
    if match_result is None:
        stats.skipped_no_match += 1
        stats.add_sample(
            {
                "reason": "no_match",
                "name": fact.display_name,
                "club": fact.club_name,
                "league": fact.league_name,
                "value_eur": fact.value_eur,
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
    if candidate.current_value_eur is not None and not force:
        stats.skipped_existing_value += 1
        return

    now = datetime.now(UTC)
    if apply:
        player = candidate.player
        player.current_market_reference_value = fact.value_eur
        player.market_reference_currency = "EUR"
        player.market_value_eur = fact.value_eur
        player.source_last_refreshed_at = now
        player.last_synced_at = now
        if force or not player.real_world_club_name:
            player.real_world_club_name = fact.club_name
        if force or not player.real_world_league_name:
            player.real_world_league_name = fact.league_name
        _update_summary(candidate.summary, fact=fact, confidence=confidence, as_of=now, force=force)
        stats.updated_summaries += int(candidate.summary is not None)
        profiles = session.scalars(
            select(RealPlayerProfile).where(RealPlayerProfile.gtex_player_id == candidate.player_id)
        ).all()
        for profile in profiles:
            profile.current_market_reference_value = fact.value_eur
            profile.market_reference_currency = "EUR"
            profile.source_last_refreshed_at = now
            if force or not profile.current_club_name:
                profile.current_club_name = fact.club_name
            if force or not profile.current_league_name:
                profile.current_league_name = fact.league_name
        stats.updated_profiles += len(profiles)
    stats.updated_players += 1
    stats.add_sample(
        {
            "reason": "updated" if apply else "would_update",
            "player_id": candidate.player_id,
            "gtex_name": candidate.full_name,
            "transfermarkt_name": fact.display_name,
            "club": fact.club_name,
            "league": fact.league_name,
            "value_eur": fact.value_eur,
            "confidence": confidence,
        },
        limit=sample_size,
    )


def _update_summary(
    summary: PlayerSummaryReadModel | None,
    *,
    fact: TransfermarktValueFact,
    confidence: str,
    as_of: datetime,
    force: bool,
) -> None:
    if summary is None:
        return
    credits = float(credits_from_real_world_value(fact.value_eur))
    if force or summary.current_value_credits <= 0:
        summary.current_value_credits = credits
    if force or summary.previous_value_credits <= 0:
        summary.previous_value_credits = credits
    if force or not summary.current_club_name:
        summary.current_club_name = fact.club_name
    if force or not summary.current_competition_name:
        summary.current_competition_name = fact.league_name
    payload = dict(summary.summary_json or {})
    real_player_profile = dict(payload.get("real_player_profile") or {})
    real_player_profile.update(
        {
            "current_market_reference_value": fact.value_eur,
            "market_reference_currency": "EUR",
            "market_value_source": "transfermarkt_value_backfill",
            "market_value_match_confidence": confidence,
            "market_value_last_refreshed_at": as_of.isoformat(),
            "real_world_club_name": fact.club_name,
            "real_world_league_name": fact.league_name,
        }
    )
    payload["real_player_profile"] = real_player_profile
    summary.summary_json = payload


def _match_fact(
    fact: TransfermarktValueFact,
    candidates_by_name: dict[str, list[ExistingPlayerCandidate]],
) -> tuple[ExistingPlayerCandidate, str] | list[ExistingPlayerCandidate] | None:
    name_key = _normalize_name(fact.display_name)
    exact_match = _match_candidates(
        fact,
        candidates_by_name.get(name_key, []),
        allow_league_only=True,
        confidence_prefix="name",
    )
    if exact_match is not None:
        return exact_match

    alias_candidates: dict[str, ExistingPlayerCandidate] = {}
    for alias in _name_aliases(fact.display_name):
        if alias == name_key:
            continue
        for candidate in candidates_by_name.get(alias, []):
            alias_candidates.setdefault(candidate.player_id, candidate)
    return _match_candidates(
        fact,
        alias_candidates.values(),
        allow_league_only=False,
        confidence_prefix="name_alias",
    )


def _match_candidates(
    fact: TransfermarktValueFact,
    candidates: Iterable[ExistingPlayerCandidate],
    *,
    allow_league_only: bool,
    confidence_prefix: str,
) -> tuple[ExistingPlayerCandidate, str] | list[ExistingPlayerCandidate] | None:
    candidates = list(candidates)
    if not candidates:
        return None

    club_key = _normalize_label(fact.club_name)
    league_key = _normalize_label(fact.league_name)
    club_matches = [candidate for candidate in candidates if _any_label_matches(club_key, candidate.club_labels)]
    if len(club_matches) == 1:
        return club_matches[0], f"{confidence_prefix}+club"
    if len(club_matches) > 1:
        league_filtered = [candidate for candidate in club_matches if _any_label_matches(league_key, candidate.league_labels)]
        if len(league_filtered) == 1:
            return league_filtered[0], f"{confidence_prefix}+club+league"
        return club_matches

    if not allow_league_only:
        return None
    league_matches = [candidate for candidate in candidates if _any_label_matches(league_key, candidate.league_labels)]
    if len(league_matches) == 1:
        return league_matches[0], f"{confidence_prefix}+league"
    if len(league_matches) > 1:
        return league_matches
    return None


def _any_label_matches(reference: str, candidates: Iterable[str]) -> bool:
    references = _equivalent_labels(reference)
    return any(_labels_match(item, candidate) for item in references for candidate in candidates if candidate)


def _labels_match(left: str, right: str) -> bool:
    if not left or not right:
        return False
    if left == right:
        return True
    if min(len(left), len(right)) >= 4 and (left in right or right in left):
        return True
    left_tokens = _meaningful_tokens(left)
    right_tokens = _meaningful_tokens(right)
    if not left_tokens or not right_tokens:
        return False
    intersection = left_tokens & right_tokens
    if len(intersection) >= 2:
        return True
    return len(intersection) == 1 and min(len(left_tokens), len(right_tokens)) == 1 and len(next(iter(intersection))) >= 3


def _equivalent_labels(value: str) -> set[str]:
    if not value:
        return set()
    labels = {value}
    for group in _LEAGUE_LABEL_ALIASES:
        if value in group:
            labels.update(group)
    return labels


def _meaningful_tokens(value: str) -> set[str]:
    return {token for token in value.split() if len(token) > 1 and token not in _CLUB_STOP_WORDS}


def _normalize_name(value: Any) -> str:
    normalized = _normalize_text(value)
    return re.sub(r"\s+", " ", normalized).strip()


def _name_aliases(value: Any) -> set[str]:
    normalized = _normalize_name(value)
    if not normalized:
        return set()
    aliases = {normalized}
    tokens = normalized.split()
    if len(tokens) >= 2:
        first = tokens[0]
        last = tokens[-1]
        if first:
            aliases.add(f"{first[0]} {last}")
        aliases.add(last)
        if len(tokens) >= 3:
            aliases.add(" ".join(tokens[-2:]))
    return aliases


def _normalize_label(value: Any) -> str:
    normalized = _normalize_text(value)
    return re.sub(r"\s+", " ", normalized).strip()


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _positive_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
