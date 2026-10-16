from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, date, datetime
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time
from typing import Any, Iterable, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session, aliased

SCRIPT_PATH = Path(__file__).resolve()
BACKEND_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = BACKEND_ROOT.parent
for candidate in (REPO_ROOT, BACKEND_ROOT, SCRIPT_PATH.parent):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from app.core.database import create_database_engine, create_session_factory, load_model_modules
from app.ingestion.models import Club, Competition, Country, Player, PlayerSeasonStat
from app.models.real_player_profile import RealPlayerProfile
from app.players.read_models import PlayerSummaryReadModel
from app.value_engine.scoring import credits_from_real_world_value
from backfill_sportmonks_player_metadata import (
    _DEFAULT_PRIORITY_LEAGUES,
    _parse_priority_leagues,
    _priority_league_match_labels,
)


ESTIMATION_SOURCE = "gtex_estimated_value_v1"
UNKNOWN_LEAGUE = "Unknown League"
TARGET_LABELS: dict[str, tuple[str, ...]] = {
    "Premier League": ("Premier League", "English Premier League"),
    "La Liga": ("La Liga", "Spanish La Liga"),
    "Italian Serie A": ("Italian Serie A", "Serie A"),
    "French Ligue 1": ("French Ligue 1", "Ligue 1"),
    "Bundesliga": ("Bundesliga", "German Bundesliga"),
    "Super Lig": ("Super Lig", "Süper Lig", "Turkish Super Lig"),
    "Brazilian Serie A": ("Brazilian Serie A", "Campeonato Brasileiro Serie A", "Brasileirão Serie A"),
    "Allsvenskan": ("Allsvenskan", "Swedish Allsvenskan"),
    "Swiss Super League": ("Swiss Super League", "Brack Super League", "Super League Switzerland"),
    "Nigeria Professional Football League": ("Nigeria Professional Football League", "Npfl", "NPFL"),
    "Liga Profesional de Futbol": ("Liga Profesional de Futbol", "Liga Profesional de Fútbol", "Argentina Primera Division"),
    "French Ligue 2": ("French Ligue 2", "Ligue 2"),
    "Eliteserien": ("Eliteserien", "Norwegian Eliteserien"),
    "Russian Premier League": ("Russian Premier League", "Premier Liga Russia"),
    "South Africa Premier League": ("South Africa Premier League", "Betway Premiership", "ABSA Premiership"),
    "Liga MX": ("Liga MX", "Liga MX Clausura", "Liga MX Apertura"),
    "Major League Soccer": ("Major League Soccer", "MLS"),
    "Champions League": ("Champions League", "UEFA Champions League"),
    "Liga Portugal": ("Liga Portugal", "Portuguese Primeira Liga", "Primeira Liga"),
    "Championship": ("Championship", "English Championship"),
    "Egypt Premier League": ("Egypt Premier League", "Egyptian Premier League"),
    "Europa Conference League": ("Europa Conference League", "UEFA Europa Conference League"),
    "Ukraine Premier League": ("Ukraine Premier League", "Ukrainian Premier League"),
    "Saudi Pro League": ("Saudi Pro League", "Saudi Professional League"),
    "Ekstraklasa": ("Ekstraklasa", "Polish Ekstraklasa"),
    "CAF Champions League": ("CAF Champions League",),
    "Copa Libertadores": ("Copa Libertadores",),
    "Eredivisie": ("Eredivisie", "eredivisie"),
    "Belgian Pro League": ("Belgian Pro League", "Jupiler Pro League", "jupiler-pro-league"),
    "Copa Sudamericana": ("Copa Sudamericana",),
    "Eerste Divisie": ("Eerste Divisie",),
    "Austrian Bundesliga": ("Austrian Bundesliga", "Admiral Bundesliga"),
    "Spanish La Liga 2": ("Spanish La Liga 2", "LaLiga2"),
    "AFC Champions League Elite": ("AFC Champions League Elite",),
    "Greek Super League": ("Greek Super League", "super-league-1"),
    "Scottish Premiership": ("Scottish Premiership", "Premiership"),
    "2. Bundesliga": ("2. Bundesliga",),
    "Croatian HNL": ("Croatian HNL", "1. HNL"),
    "Czech First League": ("Czech First League", "Chance Liga"),
    "League One": ("League One", "English League One"),
    "Italian Serie B": ("Italian Serie B", "Serie B"),
    "Danish Superliga": ("Danish Superliga", "superligaen", "3F Superliga"),
    UNKNOWN_LEAGUE: (UNKNOWN_LEAGUE, "(missing league)"),
}
LEAGUE_DEFAULTS_EUR: dict[str, float] = {
    "Premier League": 8_000_000.0,
    "La Liga": 5_500_000.0,
    "Italian Serie A": 5_500_000.0,
    "French Ligue 1": 4_500_000.0,
    "Bundesliga": 5_500_000.0,
    "Super Lig": 2_400_000.0,
    "Brazilian Serie A": 2_200_000.0,
    "Allsvenskan": 650_000.0,
    "Swiss Super League": 1_300_000.0,
    "Nigeria Professional Football League": 125_000.0,
    "Liga Profesional de Futbol": 1_000_000.0,
    "French Ligue 2": 700_000.0,
    "Eliteserien": 550_000.0,
    "Russian Premier League": 1_000_000.0,
    "South Africa Premier League": 175_000.0,
    "Liga MX": 1_200_000.0,
    "Major League Soccer": 1_200_000.0,
    "Champions League": 1_500_000.0,
    "Liga Portugal": 1_400_000.0,
    "Championship": 1_200_000.0,
    "Egypt Premier League": 175_000.0,
    "Europa Conference League": 650_000.0,
    "Ukraine Premier League": 500_000.0,
    "Saudi Pro League": 1_000_000.0,
    "Ekstraklasa": 450_000.0,
    "CAF Champions League": 175_000.0,
    "Copa Libertadores": 900_000.0,
    "Eredivisie": 1_000_000.0,
    "Belgian Pro League": 900_000.0,
    "Copa Sudamericana": 550_000.0,
    "Eerste Divisie": 250_000.0,
    "Austrian Bundesliga": 650_000.0,
    "Spanish La Liga 2": 550_000.0,
    "AFC Champions League Elite": 500_000.0,
    "Greek Super League": 650_000.0,
    "Scottish Premiership": 600_000.0,
    "2. Bundesliga": 650_000.0,
    "Croatian HNL": 350_000.0,
    "Czech First League": 350_000.0,
    "League One": 250_000.0,
    "Italian Serie B": 500_000.0,
    "Danish Superliga": 500_000.0,
    UNKNOWN_LEAGUE: 300_000.0,
}
LEAGUE_FLOORS_EUR: dict[str, float] = {
    "Premier League": 250_000.0,
    "La Liga": 200_000.0,
    "Italian Serie A": 200_000.0,
    "French Ligue 1": 200_000.0,
    "Bundesliga": 200_000.0,
    "Super Lig": 150_000.0,
    "Brazilian Serie A": 100_000.0,
    "Allsvenskan": 50_000.0,
    "Swiss Super League": 75_000.0,
    "Nigeria Professional Football League": 25_000.0,
    "Liga Profesional de Futbol": 50_000.0,
    "French Ligue 2": 50_000.0,
    "Eliteserien": 50_000.0,
    "Russian Premier League": 50_000.0,
    "South Africa Premier League": 25_000.0,
    "Liga MX": 50_000.0,
    "Major League Soccer": 50_000.0,
    "Champions League": 50_000.0,
    "Liga Portugal": 50_000.0,
    "Championship": 50_000.0,
    "Egypt Premier League": 25_000.0,
    "Europa Conference League": 50_000.0,
    "Ukraine Premier League": 25_000.0,
    "Saudi Pro League": 50_000.0,
    "Ekstraklasa": 25_000.0,
    "CAF Champions League": 25_000.0,
    "Copa Libertadores": 50_000.0,
    "Eredivisie": 50_000.0,
    "Belgian Pro League": 50_000.0,
    "Copa Sudamericana": 50_000.0,
    "Eerste Divisie": 25_000.0,
    "Austrian Bundesliga": 50_000.0,
    "Spanish La Liga 2": 50_000.0,
    "AFC Champions League Elite": 25_000.0,
    "Greek Super League": 50_000.0,
    "Scottish Premiership": 50_000.0,
    "2. Bundesliga": 50_000.0,
    "Croatian HNL": 25_000.0,
    "Czech First League": 25_000.0,
    "League One": 25_000.0,
    "Italian Serie B": 50_000.0,
    "Danish Superliga": 50_000.0,
    UNKNOWN_LEAGUE: 25_000.0,
}
POSITION_MULTIPLIERS = {
    "goalkeeper": 0.82,
    "defender": 0.88,
    "midfielder": 1.0,
    "forward": 1.12,
}


@dataclass(slots=True)
class EstimateStats:
    apply: bool
    selected: int = 0
    estimated_players: int = 0
    skipped_existing_value: int = 0
    skipped_no_league: int = 0
    updated_profiles: int = 0
    updated_summaries: int = 0
    samples: list[dict[str, Any]] | None = None

    def add_sample(self, payload: dict[str, Any], *, limit: int) -> None:
        if limit <= 0:
            return
        if self.samples is None:
            self.samples = []
        if len(self.samples) < limit:
            self.samples.append(payload)

    def as_dict(self) -> dict[str, Any]:
        return {
            "apply": self.apply,
            "selected": self.selected,
            "estimated_players": self.estimated_players,
            "skipped_existing_value": self.skipped_existing_value,
            "skipped_no_league": self.skipped_no_league,
            "updated_profiles": self.updated_profiles,
            "updated_summaries": self.updated_summaries,
            "samples": self.samples,
        }


@dataclass(slots=True)
class PlayerContext:
    player: Player
    summary: PlayerSummaryReadModel | None
    profile: RealPlayerProfile | None
    season_stat: PlayerSeasonStat | None
    league: str
    league_labels: tuple[str, ...]
    club_name: str | None
    country_name: str | None
    age_years: float | None
    position_bucket: str
    gsi_score: float | None


@dataclass(slots=True)
class ReferenceBook:
    league_values: dict[str, list[float]]
    league_position_values: dict[tuple[str, str], list[float]]
    league_age_values: dict[tuple[str, str], list[float]]
    club_values: dict[tuple[str, str], list[float]]
    country_values: dict[str, list[float]]
    global_values: list[float]
    global_position_values: dict[str, list[float]]
    global_age_values: dict[str, list[float]]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Estimate missing GTEX real-player market values when provider-backed values are unavailable. "
            "Writes explicit estimation provenance and never overwrites positive values unless --force is used."
        )
    )
    parser.add_argument("--database-url", default=os.environ.get("GTE_DATABASE_URL"))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--all-missing-values",
        action="store_true",
        help=(
            "Estimate every remaining missing real-player market value. Rows without a usable league label "
            "are tagged as Unknown League and receive lower-confidence estimates."
        ),
    )
    parser.add_argument("--league", dest="leagues", action="append", default=[])
    parser.add_argument("--priority-leagues", type=_parse_priority_leagues, default=tuple())
    parser.add_argument("--source-provider", default="sportmonks")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--sample-size", type=int, default=5)
    parser.add_argument("--db-retry-attempts", type=int, default=6)
    parser.add_argument("--db-retry-base-seconds", type=float, default=8.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.database_url:
        raise SystemExit("--database-url or GTE_DATABASE_URL is required.")
    target_leagues = _resolve_target_leagues(args.leagues, args.priority_leagues)
    all_missing_values = bool(args.all_missing_values)
    if not target_leagues and not all_missing_values:
        raise SystemExit("Provide --league, --priority-leagues, or --all-missing-values.")

    load_model_modules()
    result = _run_with_retries(
        database_url=args.database_url,
        target_leagues=target_leagues,
        all_missing_values=all_missing_values,
        source_provider=args.source_provider,
        apply=bool(args.apply),
        force=bool(args.force),
        limit=max(0, int(args.limit)),
        sample_size=max(0, int(args.sample_size)),
        attempts=max(1, int(args.db_retry_attempts)),
        base_seconds=max(0.0, float(args.db_retry_base_seconds)),
    )
    payload = result.as_dict()
    payload["target_leagues"] = list(target_leagues)
    payload["all_missing_values"] = all_missing_values
    payload["source"] = ESTIMATION_SOURCE
    print(json.dumps(payload, sort_keys=True, default=str))
    return 0


def _run_with_retries(
    *,
    database_url: str,
    target_leagues: Sequence[str],
    all_missing_values: bool,
    source_provider: str,
    apply: bool,
    force: bool,
    limit: int,
    sample_size: int,
    attempts: int,
    base_seconds: float,
) -> EstimateStats:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        engine = create_database_engine(database_url)
        session_factory = create_session_factory(engine)
        try:
            with session_factory() as session:
                stats = estimate_missing_values(
                    session,
                    target_leagues=target_leagues,
                    all_missing_values=all_missing_values,
                    source_provider=source_provider,
                    apply=apply,
                    force=force,
                    limit=limit,
                    sample_size=sample_size,
                )
                if apply:
                    session.commit()
                else:
                    session.rollback()
                return stats
        except (OperationalError, DBAPIError) as exc:
            last_error = exc
            if attempt >= attempts:
                raise
            delay = min(base_seconds * (2 ** (attempt - 1)), 30.0)
            print(
                json.dumps(
                    {
                        "warning": "db_retry",
                        "attempt": attempt,
                        "attempts": attempts,
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
    raise RuntimeError("estimate retry loop exited unexpectedly")


def estimate_missing_values(
    session: Session,
    *,
    target_leagues: Sequence[str],
    all_missing_values: bool = False,
    source_provider: str,
    apply: bool,
    force: bool,
    limit: int,
    sample_size: int,
) -> EstimateStats:
    contexts = _select_missing_player_contexts(
        session,
        target_leagues=target_leagues,
        all_missing_values=all_missing_values,
        source_provider=source_provider,
        force=force,
        limit=limit,
    )
    reference_book = _build_reference_book(
        session,
        target_leagues=target_leagues,
        all_missing_values=all_missing_values,
        source_provider=source_provider,
    )
    stats = EstimateStats(apply=apply)
    stats.selected = len(contexts)
    now = datetime.now(UTC)
    for context in contexts:
        player = context.player
        if _positive_float(player.market_value_eur) is not None and not force:
            stats.skipped_existing_value += 1
            continue
        estimate = _estimate_value(context, reference_book)
        if estimate <= 0:
            stats.skipped_no_league += 1
            continue
        confidence = _estimate_confidence(context, reference_book)
        reason = _estimate_reason(context, reference_book)
        credits = float(credits_from_real_world_value(estimate))
        if apply:
            player.dna_profile = {
                **dict(player.dna_profile or {}),
                "estimated_market_value": {
                    "source": ESTIMATION_SOURCE,
                    "value_eur": estimate,
                    "currency": "EUR",
                    "confidence": confidence,
                    "estimated_at": now.isoformat(),
                    "basis": reason,
                },
            }
            player.market_value_eur = estimate
            player.current_market_reference_value = estimate
            player.market_reference_currency = "EUR"
            player.source_last_refreshed_at = now
            player.last_synced_at = now
            _update_profile(
                context.profile,
                estimate=estimate,
                confidence=confidence,
                reason=reason,
                as_of=now,
            )
            stats.updated_profiles += int(context.profile is not None)
            _update_summary(
                context.summary,
                estimate=estimate,
                credits=credits,
                confidence=confidence,
                reason=reason,
                as_of=now,
            )
            stats.updated_summaries += int(context.summary is not None)
        stats.estimated_players += 1
        stats.add_sample(
            {
                "reason": "estimated" if apply else "would_estimate",
                "player_id": player.id,
                "name": player.full_name,
                "league": context.league,
                "club": context.club_name,
                "age_years": context.age_years,
                "position_bucket": context.position_bucket,
                "estimated_value_eur": estimate,
                "confidence": confidence,
                "basis": reason,
            },
            limit=sample_size,
        )
    return stats


def _select_missing_player_contexts(
    session: Session,
    *,
    target_leagues: Sequence[str],
    all_missing_values: bool,
    source_provider: str,
    force: bool,
    limit: int,
) -> list[PlayerContext]:
    labels_by_league = {league: _labels_for_league(league) for league in target_leagues}
    all_labels = tuple(label.lower() for labels in labels_by_league.values() for label in labels)
    if not all_labels and not all_missing_values:
        return []
    competition_country = aliased(Country)
    club_country = aliased(Country)
    player_country = aliased(Country)

    stmt = (
        select(
            Player,
            PlayerSummaryReadModel,
            RealPlayerProfile,
            PlayerSeasonStat,
            Club,
            competition_country,
            club_country,
            player_country,
        )
        .outerjoin(PlayerSummaryReadModel, PlayerSummaryReadModel.player_id == Player.id)
        .outerjoin(RealPlayerProfile, RealPlayerProfile.gtex_player_id == Player.id)
        .outerjoin(PlayerSeasonStat, PlayerSeasonStat.player_id == Player.id)
        .outerjoin(Competition, Competition.id == Player.current_competition_id)
        .outerjoin(competition_country, competition_country.id == Competition.country_id)
        .outerjoin(Club, Club.id == Player.current_club_id)
        .outerjoin(club_country, club_country.id == Club.country_id)
        .outerjoin(player_country, player_country.id == Player.country_id)
        .where(Player.is_real_player.is_(True), Player.is_tradable.is_(True))
        .order_by(Player.full_name.asc(), Player.id.asc())
    )
    if all_labels:
        stmt = stmt.where(
            _league_criteria(
                all_labels,
                target_leagues=target_leagues,
                competition_country=competition_country,
                club_country=club_country,
            )
        )
    if source_provider:
        stmt = stmt.where(func.lower(Player.source_provider) == source_provider.lower())
    if not force:
        stmt = stmt.where(or_(Player.market_value_eur.is_(None), Player.market_value_eur <= 0))
    if limit > 0:
        stmt = stmt.limit(limit)

    contexts: list[PlayerContext] = []
    seen: set[str] = set()
    for (
        player,
        summary,
        profile,
        season_stat,
        club,
        comp_country,
        current_club_country,
        current_player_country,
    ) in session.execute(stmt).all():
        if player.id in seen:
            continue
        seen.add(player.id)
        league = _canonical_league_for_player(
            player,
            summary,
            profile,
            labels_by_league,
            allow_unknown=all_missing_values,
            competition_country=comp_country,
            club_country=current_club_country,
        )
        if league is None:
            continue
        club_name = (
            player.real_world_club_name
            or (profile.current_club_name if profile is not None else None)
            or (summary.current_club_name if summary is not None else None)
            or (club.name if club is not None else None)
        )
        contexts.append(
            PlayerContext(
                player=player,
                summary=summary,
                profile=profile,
                season_stat=season_stat,
                league=league,
                league_labels=labels_by_league.get(league, _labels_for_league(league)),
                club_name=club_name,
                country_name=_country_name_for_player(player, profile, summary, country=current_player_country),
                age_years=_age_years(player.date_of_birth or (profile.date_of_birth if profile else None)),
                position_bucket=_position_bucket(player.normalized_position or player.position or (profile.primary_position if profile else None)),
                gsi_score=_gsi_score_for_player(player, summary),
            )
        )
    return contexts


def _build_reference_book(
    session: Session,
    *,
    target_leagues: Sequence[str],
    all_missing_values: bool,
    source_provider: str,
) -> ReferenceBook:
    labels_by_league = {league: _labels_for_league(league) for league in target_leagues}
    all_labels = tuple(label.lower() for labels in labels_by_league.values() for label in labels)
    competition_country = aliased(Country)
    club_country = aliased(Country)
    player_country = aliased(Country)
    stmt = (
        select(Player, PlayerSummaryReadModel, RealPlayerProfile, Club, competition_country, club_country, player_country)
        .outerjoin(PlayerSummaryReadModel, PlayerSummaryReadModel.player_id == Player.id)
        .outerjoin(RealPlayerProfile, RealPlayerProfile.gtex_player_id == Player.id)
        .outerjoin(Competition, Competition.id == Player.current_competition_id)
        .outerjoin(competition_country, competition_country.id == Competition.country_id)
        .outerjoin(Club, Club.id == Player.current_club_id)
        .outerjoin(club_country, club_country.id == Club.country_id)
        .outerjoin(player_country, player_country.id == Player.country_id)
        .where(
            Player.is_real_player.is_(True),
            Player.is_tradable.is_(True),
            Player.market_value_eur.is_not(None),
            Player.market_value_eur > 0,
        )
    )
    if all_labels:
        stmt = stmt.where(
            _league_criteria(
                all_labels,
                target_leagues=target_leagues,
                competition_country=competition_country,
                club_country=club_country,
            )
        )
    if source_provider:
        stmt = stmt.where(func.lower(Player.source_provider) == source_provider.lower())

    league_values: dict[str, list[float]] = {}
    league_position_values: dict[tuple[str, str], list[float]] = {}
    league_age_values: dict[tuple[str, str], list[float]] = {}
    club_values: dict[tuple[str, str], list[float]] = {}
    country_values: dict[str, list[float]] = {}
    global_values: list[float] = []
    global_position_values: dict[str, list[float]] = {}
    global_age_values: dict[str, list[float]] = {}
    seen: set[str] = set()
    for player, summary, profile, club, comp_country, current_club_country, current_player_country in session.execute(stmt).all():
        if player.id in seen:
            continue
        seen.add(player.id)
        value = _positive_float(player.market_value_eur)
        if value is None:
            continue
        league = _canonical_league_for_player(
            player,
            summary,
            profile,
            labels_by_league,
            allow_unknown=all_missing_values,
            competition_country=comp_country,
            club_country=current_club_country,
        )
        if league is None:
            continue
        position = _position_bucket(player.normalized_position or player.position or (profile.primary_position if profile else None))
        age_bucket = _age_bucket(_age_years(player.date_of_birth or (profile.date_of_birth if profile else None)))
        club_name = (
            player.real_world_club_name
            or (profile.current_club_name if profile is not None else None)
            or (summary.current_club_name if summary is not None else None)
            or (club.name if club is not None else None)
        )
        league_values.setdefault(league, []).append(value)
        league_position_values.setdefault((league, position), []).append(value)
        league_age_values.setdefault((league, age_bucket), []).append(value)
        global_values.append(value)
        global_position_values.setdefault(position, []).append(value)
        global_age_values.setdefault(age_bucket, []).append(value)
        country_name = _country_name_for_player(player, profile, summary, country=current_player_country)
        if country_name:
            country_values.setdefault(_normalize_label(country_name), []).append(value)
        if club_name:
            club_values.setdefault((league, _normalize_label(club_name)), []).append(value)
    return ReferenceBook(
        league_values=league_values,
        league_position_values=league_position_values,
        league_age_values=league_age_values,
        club_values=club_values,
        country_values=country_values,
        global_values=global_values,
        global_position_values=global_position_values,
        global_age_values=global_age_values,
    )


def _estimate_value(context: PlayerContext, reference_book: ReferenceBook) -> float:
    league = context.league
    position = context.position_bucket
    age_bucket = _age_bucket(context.age_years)
    bases: list[tuple[float, float]] = []
    position_values = reference_book.league_position_values.get((league, position), [])
    if len(position_values) >= 8:
        bases.append((_median(position_values), 0.32))
    age_values = reference_book.league_age_values.get((league, age_bucket), [])
    if len(age_values) >= 8:
        bases.append((_median(age_values), 0.18))
    league_values = reference_book.league_values.get(league, [])
    if len(league_values) >= 8:
        bases.append((_median(league_values), 0.30))
    country_values = reference_book.country_values.get(_normalize_label(context.country_name), [])
    if len(country_values) >= 8:
        bases.append((_median(country_values), 0.10))
    if not bases or league == UNKNOWN_LEAGUE:
        global_position_values = reference_book.global_position_values.get(position, [])
        if len(global_position_values) >= 8:
            bases.append((_median(global_position_values), 0.24))
        global_age_values = reference_book.global_age_values.get(age_bucket, [])
        if len(global_age_values) >= 8:
            bases.append((_median(global_age_values), 0.14))
        if len(reference_book.global_values) >= 8:
            bases.append((_median(reference_book.global_values), 0.12))
    bases.append((LEAGUE_DEFAULTS_EUR.get(league, 1_000_000.0), 0.10))

    total_weight = sum(weight for _, weight in bases)
    base_value = sum(value * weight for value, weight in bases) / max(total_weight, 0.01)
    club_multiplier = _club_multiplier(context, reference_book, league_values=league_values)
    country_multiplier = _country_multiplier(context, reference_book)
    age_multiplier = _age_multiplier(context.age_years, position)
    gsi_multiplier = _gsi_multiplier(context.gsi_score)
    rating_multiplier = _rating_multiplier(context)
    output_multiplier = _output_multiplier(context)
    interest_multiplier = _interest_multiplier(context.summary)
    position_multiplier = POSITION_MULTIPLIERS.get(position, 1.0)
    unknown_league_discount = 0.58 if league == UNKNOWN_LEAGUE else 1.0
    estimate = (
        base_value
        * club_multiplier
        * country_multiplier
        * age_multiplier
        * gsi_multiplier
        * rating_multiplier
        * output_multiplier
        * interest_multiplier
        * position_multiplier
        * unknown_league_discount
    )
    floor = LEAGUE_FLOORS_EUR.get(league, 50_000.0)
    ceiling = _league_ceiling(league, league_values or reference_book.global_values)
    return _round_value(min(max(estimate, floor), ceiling))


def _club_multiplier(context: PlayerContext, reference_book: ReferenceBook, *, league_values: Sequence[float]) -> float:
    if not context.club_name:
        return 1.0
    club_values = reference_book.club_values.get((context.league, _normalize_label(context.club_name)), [])
    if len(club_values) < 4 or len(league_values) < 8:
        return 1.0
    league_median = max(_median(league_values), 1.0)
    return _clamp(_median(club_values) / league_median, 0.65, 1.85)


def _country_multiplier(context: PlayerContext, reference_book: ReferenceBook) -> float:
    if not context.country_name or len(reference_book.global_values) < 8:
        return 1.0
    country_values = reference_book.country_values.get(_normalize_label(context.country_name), [])
    if len(country_values) < 8:
        return 1.0
    global_median = max(_median(reference_book.global_values), 1.0)
    return _clamp(_median(country_values) / global_median, 0.78, 1.28)


def _age_multiplier(age_years: float | None, position: str) -> float:
    if age_years is None:
        return 0.92
    if age_years <= 19:
        return 1.22
    if age_years <= 22:
        return 1.28
    if age_years <= 25:
        return 1.18
    if age_years <= 28:
        return 1.05
    if age_years <= 31:
        return 0.92 if position != "goalkeeper" else 1.0
    if age_years <= 34:
        return 0.68 if position != "goalkeeper" else 0.82
    return 0.45 if position != "goalkeeper" else 0.58


def _rating_multiplier(context: PlayerContext) -> float:
    rating = None
    if context.season_stat is not None and context.season_stat.average_rating is not None:
        rating = float(context.season_stat.average_rating)
    elif context.summary is not None and context.summary.average_rating is not None:
        rating = float(context.summary.average_rating)
    if rating is None or rating <= 0:
        return 1.0
    return _clamp(1.0 + ((rating - 6.7) * 0.16), 0.82, 1.24)


def _gsi_multiplier(gsi_score: float | None) -> float:
    if gsi_score is None or gsi_score <= 0:
        return 1.0
    return _clamp(1.0 + ((float(gsi_score) - 55.0) * 0.01), 0.78, 1.35)


def _output_multiplier(context: PlayerContext) -> float:
    stat = context.season_stat
    if stat is None:
        return 1.0
    appearances = max(0, int(stat.appearances or 0))
    goals = max(0, int(stat.goals or 0))
    assists = max(0, int(stat.assists or 0))
    if appearances <= 0 and goals <= 0 and assists <= 0:
        return 1.0
    output = min(goals * 0.018 + assists * 0.014, 0.22)
    availability = min(appearances, 35) / 35.0
    if context.position_bucket in {"defender", "goalkeeper"}:
        clean_sheets = max(0, int(stat.clean_sheets or 0))
        saves = max(0, int(stat.saves or 0))
        output += min(clean_sheets * 0.008 + saves * 0.0008, 0.12)
    return _clamp(1.0 + output + (availability * 0.04), 0.94, 1.30)


def _interest_multiplier(summary: PlayerSummaryReadModel | None) -> float:
    if summary is None:
        return 1.0
    score = max(0, int(summary.market_interest_score or 0))
    return _clamp(1.0 + min(score, 100) / 1000.0, 1.0, 1.10)


def _estimate_confidence(context: PlayerContext, reference_book: ReferenceBook) -> str:
    league_values = len(reference_book.league_values.get(context.league, []))
    position_values = len(reference_book.league_position_values.get((context.league, context.position_bucket), []))
    club_values = len(reference_book.club_values.get((context.league, _normalize_label(context.club_name or "")), []))
    if context.league == UNKNOWN_LEAGUE:
        if context.age_years is not None and context.country_name and context.gsi_score is not None:
            return "estimated+unknown_league+age+nationality+gsi"
        if context.age_years is not None and context.country_name:
            return "estimated+unknown_league+age+nationality"
        return "estimated+unknown_league_low_context"
    if club_values >= 4 and position_values >= 8:
        return "estimated+club+position+league"
    if position_values >= 8:
        return "estimated+position+league"
    if league_values >= 8:
        return "estimated+league"
    return "estimated+league_default"


def _estimate_reason(context: PlayerContext, reference_book: ReferenceBook) -> dict[str, Any]:
    return {
        "formula": ESTIMATION_SOURCE,
        "league": context.league,
        "position_bucket": context.position_bucket,
        "age_bucket": _age_bucket(context.age_years),
        "age_years": context.age_years,
        "country": context.country_name,
        "gsi_score": context.gsi_score,
        "rating_multiplier": _rating_multiplier(context),
        "gsi_multiplier": _gsi_multiplier(context.gsi_score),
        "output_multiplier": _output_multiplier(context),
        "interest_multiplier": _interest_multiplier(context.summary),
        "league_reference_count": len(reference_book.league_values.get(context.league, [])),
        "position_reference_count": len(
            reference_book.league_position_values.get((context.league, context.position_bucket), [])
        ),
        "club_reference_count": len(
            reference_book.club_values.get((context.league, _normalize_label(context.club_name or "")), [])
        ),
        "country_reference_count": len(reference_book.country_values.get(_normalize_label(context.country_name), [])),
        "global_reference_count": len(reference_book.global_values),
    }


def _update_profile(
    profile: RealPlayerProfile | None,
    *,
    estimate: float,
    confidence: str,
    reason: dict[str, Any],
    as_of: datetime,
) -> None:
    if profile is None:
        return
    profile.current_market_reference_value = estimate
    profile.market_reference_currency = "EUR"
    profile.source_last_refreshed_at = as_of
    metadata = dict(profile.metadata_json or {})
    metadata["estimated_market_value"] = {
        "source": ESTIMATION_SOURCE,
        "value_eur": estimate,
        "currency": "EUR",
        "confidence": confidence,
        "estimated_at": as_of.isoformat(),
        "basis": reason,
    }
    profile.metadata_json = metadata


def _update_summary(
    summary: PlayerSummaryReadModel | None,
    *,
    estimate: float,
    credits: float,
    confidence: str,
    reason: dict[str, Any],
    as_of: datetime,
) -> None:
    if summary is None:
        return
    if summary.current_value_credits <= 0:
        summary.current_value_credits = credits
    if summary.previous_value_credits <= 0:
        summary.previous_value_credits = credits
    payload = dict(summary.summary_json or {})
    real_player_profile = dict(payload.get("real_player_profile") or {})
    real_player_profile.update(
        {
            "current_market_reference_value": estimate,
            "market_reference_currency": "EUR",
            "market_value_source": ESTIMATION_SOURCE,
            "market_value_match_confidence": confidence,
            "market_value_last_refreshed_at": as_of.isoformat(),
            "market_value_estimation_basis": reason,
        }
    )
    payload["real_player_profile"] = real_player_profile
    summary.summary_json = payload


def _league_criteria(
    labels: Sequence[str],
    *,
    target_leagues: Sequence[str],
    competition_country,
    club_country,
):
    normalized_labels = tuple(label.lower() for label in labels)
    criteria = []
    non_ambiguous_labels = tuple(
        label for label in normalized_labels if label not in {"premier league"}
    )
    if non_ambiguous_labels:
        criteria.append(
            or_(
                func.lower(Player.real_world_league_name).in_(non_ambiguous_labels),
                func.lower(Competition.name).in_(non_ambiguous_labels),
                func.lower(PlayerSummaryReadModel.current_competition_name).in_(non_ambiguous_labels),
                func.lower(RealPlayerProfile.current_league_name).in_(non_ambiguous_labels),
            )
        )
    if "Premier League" in target_leagues:
        premier_labels = ("premier league", "english premier league")
        english_context = or_(
            func.lower(competition_country.name).in_(("england", "united kingdom")),
            func.lower(club_country.name).in_(("england", "united kingdom")),
        )
        explicit_english_label = or_(
            func.lower(Player.real_world_league_name) == "english premier league",
            func.lower(Competition.name) == "english premier league",
            func.lower(PlayerSummaryReadModel.current_competition_name) == "english premier league",
            func.lower(RealPlayerProfile.current_league_name) == "english premier league",
        )
        generic_premier_label = or_(
            func.lower(Player.real_world_league_name).in_(premier_labels),
            func.lower(Competition.name).in_(premier_labels),
            func.lower(PlayerSummaryReadModel.current_competition_name).in_(premier_labels),
            func.lower(RealPlayerProfile.current_league_name).in_(premier_labels),
        )
        criteria.append(or_(explicit_english_label, generic_premier_label & english_context))
    return or_(*criteria)


def _canonical_league_for_player(
    player: Player,
    summary: PlayerSummaryReadModel | None,
    profile: RealPlayerProfile | None,
    labels_by_league: dict[str, tuple[str, ...]],
    *,
    allow_unknown: bool = False,
    competition_country: Country | None,
    club_country: Country | None,
) -> str | None:
    candidates = (
        player.real_world_league_name,
        profile.current_league_name if profile else None,
        summary.current_competition_name if summary else None,
        player.current_competition.name if player.current_competition else None,
    )
    normalized_candidates = {_normalize_label(value) for value in candidates if value}
    for league, labels in labels_by_league.items():
        matching_labels = {_normalize_label(label) for label in labels} & normalized_candidates
        if not matching_labels:
            continue
        if league == "Premier League" and "english premier league" not in matching_labels:
            if not _is_english_context(competition_country=competition_country, club_country=club_country):
                continue
        return league
    if allow_unknown:
        for value in candidates:
            if value:
                return _canonical_league_name(str(value))
        return UNKNOWN_LEAGUE
    return None


def _country_name_for_player(
    player: Player,
    profile: RealPlayerProfile | None,
    summary: PlayerSummaryReadModel | None,
    *,
    country: Country | None = None,
) -> str | None:
    if country is not None and country.name:
        return str(country.name)
    try:
        player_country = player.country
    except Exception:
        player_country = None
    if player_country is not None and player_country.name:
        return str(player_country.name)
    if profile is not None and profile.nationality_name:
        return str(profile.nationality_name)
    payload = dict(summary.summary_json or {}) if summary is not None else {}
    nationality = payload.get("nationality")
    if isinstance(nationality, dict) and nationality.get("name"):
        return str(nationality["name"])
    return None


def _gsi_score_for_player(player: Player, summary: PlayerSummaryReadModel | None) -> float | None:
    for payload in (player.dna_profile, summary.summary_json if summary is not None else None):
        score = _nested_number(payload, ("gsi",))
        if score is not None:
            return score
        score = _nested_number(payload, ("global_scouting_index",))
        if score is not None:
            return score
        score = _nested_number(payload, ("real_player_profile", "global_scouting_index"))
        if score is not None:
            return score
    return None


def _nested_number(payload: Any, path: Sequence[str]) -> float | None:
    current = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    if current is None:
        return None
    try:
        value = float(current)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return value


def _is_english_context(*, competition_country: Country | None, club_country: Country | None) -> bool:
    country_names = {
        _normalize_label(competition_country.name if competition_country is not None else None),
        _normalize_label(club_country.name if club_country is not None else None),
    }
    return bool(country_names & {"england", "united kingdom"})


def _resolve_target_leagues(leagues: Sequence[str], priority_leagues: Sequence[str]) -> tuple[str, ...]:
    targets: list[str] = []
    for league in priority_leagues:
        _append_unique(targets, league)
    for league in leagues:
        canonical = _canonical_league_name(league)
        _append_unique(targets, canonical)
    return tuple(targets)


def _canonical_league_name(value: str) -> str:
    normalized = _normalize_label(value)
    for league, labels in TARGET_LABELS.items():
        if normalized == _normalize_label(league) or normalized in {_normalize_label(label) for label in labels}:
            return league
    if normalized in {"(missing league)", "missing league", "unknown league", "unknown"}:
        return UNKNOWN_LEAGUE
    if normalized in {"brazilian league", "brazil league"}:
        return "Brazilian Serie A"
    if normalized in {"swedish league", "sweden league"}:
        return "Allsvenskan"
    if normalized in {"swiss league", "switzerland league"}:
        return "Swiss Super League"
    if normalized in {"npfl", "nigeria premier league"}:
        return "Nigeria Professional Football League"
    if normalized in {"argentinian primera division", "liga profesional de futbol"}:
        return "Liga Profesional de Futbol"
    if normalized in {"premier liga russia"}:
        return "Russian Premier League"
    if normalized in {"premiership"}:
        return "Scottish Premiership"
    if normalized in {"jupiler pro league", "jupiler pro league"}:
        return "Belgian Pro League"
    if normalized in {"super league 1"}:
        return "Greek Super League"
    if normalized in {"superligaen", "3f superliga"}:
        return "Danish Superliga"
    return value.strip()


def _labels_for_league(league: str) -> tuple[str, ...]:
    if league in TARGET_LABELS:
        return TARGET_LABELS[league]
    if league in _DEFAULT_PRIORITY_LEAGUES:
        return _priority_league_match_labels((league,))
    return (league,)


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _positive_float(value: float | None) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or parsed <= 0:
        return None
    return parsed


def _position_bucket(position: str | None) -> str:
    normalized = (position or "").strip().lower()
    if "goal" in normalized:
        return "goalkeeper"
    if "def" in normalized or "back" in normalized:
        return "defender"
    if "wing" in normalized or "forward" in normalized or "striker" in normalized or "attack" in normalized:
        return "forward"
    return "midfielder"


def _age_years(birth_date: date | None) -> float | None:
    if birth_date is None:
        return None
    return round((datetime.now(UTC).date() - birth_date).days / 365.25, 2)


def _age_bucket(age_years: float | None) -> str:
    if age_years is None:
        return "unknown"
    if age_years <= 20:
        return "u20"
    if age_years <= 23:
        return "u23"
    if age_years <= 27:
        return "prime"
    if age_years <= 31:
        return "late_prime"
    return "veteran"


def _median(values: Iterable[float]) -> float:
    return float(statistics.median([float(value) for value in values]))


def _league_ceiling(league: str, league_values: Sequence[float]) -> float:
    if league == UNKNOWN_LEAGUE:
        return 2_000_000.0
    if len(league_values) < 8:
        return LEAGUE_DEFAULTS_EUR.get(league, 1_000_000.0) * 4.0
    sorted_values = sorted(float(value) for value in league_values)
    index = min(len(sorted_values) - 1, max(0, int(len(sorted_values) * 0.92)))
    return max(sorted_values[index] * 1.25, LEAGUE_DEFAULTS_EUR.get(league, 1_000_000.0) * 2.5)


def _round_value(value: float) -> float:
    if value >= 10_000_000:
        step = 500_000
    elif value >= 1_000_000:
        step = 100_000
    elif value >= 250_000:
        step = 50_000
    else:
        step = 25_000
    return float(round(value / step) * step)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _normalize_label(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(str(value).strip().lower().replace("-", " ").split())


if __name__ == "__main__":
    raise SystemExit(main())
