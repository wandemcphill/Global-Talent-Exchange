from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import date
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Sequence, TypeVar

from sqlalchemy import inspect
from sqlalchemy import func, select, tuple_
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session, selectinload

SCRIPT_PATH = Path(__file__).resolve()
BACKEND_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = BACKEND_ROOT.parent
for candidate in (REPO_ROOT, BACKEND_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from app.core.database import create_database_engine, create_session_factory, load_model_modules
from app.ingestion.models import Club, Competition, Country, Player
from app.ingestion.normalizers import clean_name, normalize_club_name, normalize_competition_name, normalize_country_name
from app.ingestion.real_player_canonical_mapping_service import RealPlayerCanonicalMappingService
from app.ingestion.real_player_import_models import RealPlayerImportStagingRecord
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_source_link import RealPlayerSourceLink
from app.players.read_models import PlayerSummaryReadModel
from app.value_engine.scoring import credits_from_real_world_value


REAL_VALUE_SOURCE_FIELDS = {
    "player.current_market_reference_value",
    "player.market_value_eur",
    "profile.current_market_reference_value",
    "staging.rough_market_value",
}
T = TypeVar("T")
TValue = TypeVar("TValue")


@dataclass(slots=True)
class IntegrityStats:
    scanned: int = 0
    country_fixed: int = 0
    competition_fixed: int = 0
    club_fixed: int = 0
    date_of_birth_fixed: int = 0
    value_fixed: int = 0
    summary_fixed: int = 0
    missing_country: int = 0
    missing_competition: int = 0
    missing_club: int = 0
    missing_date_of_birth: int = 0
    missing_real_value: int = 0
    unresolved_samples: list[dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PlayerFacts:
    nationality_name: str | None = None
    nationality_code: str | None = None
    competition_name: str | None = None
    competition_key: str | None = None
    club_name: str | None = None
    club_key: str | None = None
    date_of_birth: date | None = None
    market_value_eur: float | None = None
    market_value_source: str | None = None


@dataclass(slots=True)
class IntegrityRelatedRows:
    source_links_by_player_id: dict[str, RealPlayerSourceLink]
    profiles_by_player_id: dict[str, RealPlayerProfile]
    profiles_by_source_link_id: dict[str, RealPlayerProfile]
    staging_by_source_key: dict[tuple[str, str], RealPlayerImportStagingRecord]
    summaries_by_player_id: dict[str, PlayerSummaryReadModel]

    def source_link_for(self, player: Player) -> RealPlayerSourceLink | None:
        return self.source_links_by_player_id.get(player.id)

    def profile_for(
        self,
        player: Player,
        source_link: RealPlayerSourceLink | None,
    ) -> RealPlayerProfile | None:
        if source_link is not None:
            linked = self.profiles_by_source_link_id.get(source_link.id)
            if linked is not None:
                return linked
        return self.profiles_by_player_id.get(player.id)

    def staging_for(
        self,
        player: Player,
        source_link: RealPlayerSourceLink | None,
        profile: RealPlayerProfile | None,
    ) -> RealPlayerImportStagingRecord | None:
        source_name = (
            source_link.source_name
            if source_link is not None
            else profile.source_name
            if profile is not None
            else player.source_provider
        )
        source_key = (
            source_link.source_player_key
            if source_link is not None
            else profile.source_player_key
            if profile is not None
            else player.provider_external_id
        )
        if not source_name or not source_key:
            return None
        return self.staging_by_source_key.get((source_name, source_key))

    def summary_for(self, player: Player) -> PlayerSummaryReadModel | None:
        return self.summaries_by_player_id.get(player.id)


@dataclass(slots=True)
class CanonicalEntityCache:
    countries_by_code: dict[str, Country]
    countries_by_name: dict[str, Country]
    competitions_by_external_id: dict[str, Competition]
    competitions_by_name: dict[str, Competition | None]
    clubs_by_external_id: dict[str, Club]
    clubs_by_name_and_competition: dict[tuple[str, str], Club]
    clubs_by_name: dict[str, Club | None]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit and optionally repair real-player GTEX market metadata: nationality, "
            "current league, current club, date of birth, and imported real-life market value."
        )
    )
    parser.add_argument("--database-url", default=os.environ.get("GTE_DATABASE_URL"))
    parser.add_argument("--apply", action="store_true", help="Write repairs. Default is audit-only.")
    parser.add_argument("--auto-create", action="store_true", help="Create missing canonical countries/leagues/clubs when safe.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0, help="Skip this many ordered players before auditing/repairing.")
    parser.add_argument("--min-count", type=int, default=17000)
    parser.add_argument("--sample-size", type=int, default=25)
    parser.add_argument(
        "--skip-summaries",
        action="store_true",
        help="Skip player_summary_read_models prefetch/repair for faster market-field repair passes.",
    )
    parser.add_argument("--db-retry-attempts", type=int, default=4)
    parser.add_argument("--db-retry-base-seconds", type=float, default=5.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.database_url:
        raise SystemExit("--database-url or GTE_DATABASE_URL is required.")

    load_model_modules()
    engine = create_database_engine(args.database_url)
    session_factory = create_session_factory(engine)
    mapper = RealPlayerCanonicalMappingService(auto_create_missing_entities=args.auto_create)

    attempts = max(int(args.db_retry_attempts), 1)
    base_seconds = max(float(args.db_retry_base_seconds), 0.0)
    stats: IntegrityStats | None = None
    tradable_count = 0
    for attempt in range(1, attempts + 1):
        try:
            with session_factory() as session:
                schema_errors = _schema_errors(session)
                if schema_errors:
                    print(
                        json.dumps(
                            {
                                "ok": False,
                                "apply": bool(args.apply),
                                "auto_create": bool(args.auto_create),
                                "schema_errors": schema_errors,
                                "message": (
                                    "Database schema is not current enough for real-player market integrity repair. "
                                    "Run Alembic migrations on this database or point --database-url at the migrated backend DB."
                                ),
                            },
                            sort_keys=True,
                        )
                    )
                    return 3
                stats = audit_or_repair(
                    session,
                    mapper=mapper,
                    apply=args.apply,
                    limit=args.limit,
                    offset=max(int(args.offset), 0),
                    repair_summaries=not bool(args.skip_summaries),
                    sample_size=args.sample_size,
                )
                tradable_count = session.scalar(
                    select(func.count()).select_from(Player).where(Player.is_real_player.is_(True), Player.is_tradable.is_(True))
                ) or 0
                if args.apply:
                    session.commit()
            break
        except (DBAPIError, OperationalError) as exc:
            engine.dispose()
            if attempt >= attempts:
                raise
            delay_seconds = base_seconds * attempt
            print(
                json.dumps(
                    {
                        "attempt": attempt,
                        "attempts": attempts,
                        "delay_seconds": delay_seconds,
                        "error": str(exc).splitlines()[0],
                        "warning": "db_retry",
                    },
                    sort_keys=True,
                ),
                file=sys.stderr,
            )
            if delay_seconds:
                time.sleep(delay_seconds)

    assert stats is not None

    payload = {
        **asdict(stats),
        "apply": bool(args.apply),
        "auto_create": bool(args.auto_create),
        "tradable_real_players": int(tradable_count),
        "min_count": int(args.min_count),
        "count_ok": int(tradable_count) >= int(args.min_count),
    }
    print(json.dumps(payload, sort_keys=True, default=str))
    return 0 if payload["count_ok"] else 2


def _schema_errors(session: Session) -> list[str]:
    inspector = inspect(session.get_bind())
    required_tables = {
        "ingestion_players",
        "ingestion_countries",
        "ingestion_competitions",
        "ingestion_clubs",
        "real_player_profiles",
        "real_player_source_links",
        "real_player_import_staging",
        "player_summary_read_models",
    }
    errors: list[str] = []
    existing_tables = set(inspector.get_table_names())
    for table_name in sorted(required_tables - existing_tables):
        errors.append(f"missing table: {table_name}")
    if "ingestion_players" in existing_tables:
        player_columns = {column["name"] for column in inspector.get_columns("ingestion_players")}
        for column_name in (
            "is_real_player",
            "is_tradable",
            "country_id",
            "current_club_id",
            "current_competition_id",
            "date_of_birth",
            "market_value_eur",
            "current_market_reference_value",
            "market_reference_currency",
            "real_world_club_name",
            "real_world_league_name",
        ):
            if column_name not in player_columns:
                errors.append(f"missing ingestion_players column: {column_name}")
    return errors


def audit_or_repair(
    session: Session,
    *,
    mapper: RealPlayerCanonicalMappingService,
    apply: bool,
    limit: int | None = None,
    offset: int = 0,
    repair_summaries: bool = True,
    sample_size: int = 25,
) -> IntegrityStats:
    statement = (
        select(Player)
        .options(
            selectinload(Player.country),
            selectinload(Player.current_club),
            selectinload(Player.current_competition),
        )
        .where(Player.is_real_player.is_(True), Player.is_tradable.is_(True))
        .order_by(Player.full_name.asc(), Player.id.asc())
    )
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)

    players = list(session.scalars(statement))
    related = _prefetch_related_rows(session, players, load_summaries=repair_summaries)
    entity_cache = _build_entity_cache(session)
    stats = IntegrityStats()
    for player in players:
        stats.scanned += 1
        source_link = related.source_link_for(player)
        profile = related.profile_for(player, source_link)
        staging = related.staging_for(player, source_link, profile)
        summary = related.summary_for(player)
        facts = _facts(player=player, source_link=source_link, profile=profile, staging=staging, summary=summary)

        country = _resolve_country(session, mapper=mapper, entity_cache=entity_cache, player=player, facts=facts)
        if country is None:
            stats.missing_country += 1
            _sample(stats, player=player, issue="missing_country", facts=facts, sample_size=sample_size)
        elif player.country_id != country.id:
            stats.country_fixed += 1
            if apply:
                player.country_id = country.id

        competition = _resolve_competition(session, mapper=mapper, entity_cache=entity_cache, player=player, facts=facts)
        if competition is None:
            stats.missing_competition += 1
            _sample(stats, player=player, issue="missing_competition", facts=facts, sample_size=sample_size)
        elif player.current_competition_id != competition.id:
            stats.competition_fixed += 1
            if apply:
                player.current_competition_id = competition.id

        club = _resolve_club(session, mapper=mapper, entity_cache=entity_cache, player=player, facts=facts, competition=competition)
        if club is None:
            stats.missing_club += 1
            _sample(stats, player=player, issue="missing_club", facts=facts, sample_size=sample_size)
        elif player.current_club_id != club.id:
            stats.club_fixed += 1
            if apply:
                player.current_club_id = club.id

        if player.date_of_birth is None and facts.date_of_birth is not None:
            stats.date_of_birth_fixed += 1
            if apply:
                player.date_of_birth = facts.date_of_birth
        elif player.date_of_birth is None:
            stats.missing_date_of_birth += 1
            _sample(stats, player=player, issue="missing_date_of_birth", facts=facts, sample_size=sample_size)

        if facts.market_value_eur is not None:
            if _positive_float(player.current_market_reference_value) is None:
                stats.value_fixed += 1
                if apply:
                    player.current_market_reference_value = facts.market_value_eur
                    player.market_reference_currency = "EUR"
            if _positive_float(player.market_value_eur) is None:
                if apply:
                    player.market_value_eur = facts.market_value_eur
        else:
            stats.missing_real_value += 1
            _sample(stats, player=player, issue="missing_real_value", facts=facts, sample_size=sample_size)

        if repair_summaries and summary is not None and _summary_needs_update(summary, player=player, facts=facts, competition=competition, club=club):
            stats.summary_fixed += 1
            if apply:
                _repair_summary(summary, player=player, facts=facts, competition=competition, club=club)

    return stats


def _prefetch_related_rows(
    session: Session,
    players: Sequence[Player],
    *,
    load_summaries: bool = True,
) -> IntegrityRelatedRows:
    player_ids = [player.id for player in players]
    if not player_ids:
        return IntegrityRelatedRows(
            source_links_by_player_id={},
            profiles_by_player_id={},
            profiles_by_source_link_id={},
            staging_by_source_key={},
            summaries_by_player_id={},
        )

    source_links_by_player_id: dict[str, RealPlayerSourceLink] = {}
    for chunk in _chunks(player_ids):
        for source_link in session.scalars(
            select(RealPlayerSourceLink).where(RealPlayerSourceLink.gtex_player_id.in_(chunk))
        ):
            source_links_by_player_id[source_link.gtex_player_id] = source_link

    source_link_ids = [source_link.id for source_link in source_links_by_player_id.values()]
    profiles_by_player_id: dict[str, RealPlayerProfile] = {}
    profiles_by_source_link_id: dict[str, RealPlayerProfile] = {}
    for chunk in _chunks(player_ids):
        for profile in session.scalars(
            select(RealPlayerProfile).where(RealPlayerProfile.gtex_player_id.in_(chunk))
        ):
            if profile.gtex_player_id:
                profiles_by_player_id[profile.gtex_player_id] = profile
            if profile.source_link_id:
                profiles_by_source_link_id[profile.source_link_id] = profile
    for chunk in _chunks(source_link_ids):
        for profile in session.scalars(
            select(RealPlayerProfile).where(RealPlayerProfile.source_link_id.in_(chunk))
        ):
            if profile.gtex_player_id:
                profiles_by_player_id[profile.gtex_player_id] = profile
            if profile.source_link_id:
                profiles_by_source_link_id[profile.source_link_id] = profile

    staging_keys: set[tuple[str, str]] = set()
    for player in players:
        source_link = source_links_by_player_id.get(player.id)
        profile = (
            profiles_by_source_link_id.get(source_link.id)
            if source_link is not None
            else profiles_by_player_id.get(player.id)
        )
        source_name = (
            source_link.source_name
            if source_link is not None
            else profile.source_name
            if profile is not None
            else player.source_provider
        )
        source_key = (
            source_link.source_player_key
            if source_link is not None
            else profile.source_player_key
            if profile is not None
            else player.provider_external_id
        )
        if source_name and source_key:
            staging_keys.add((source_name, source_key))

    staging_by_source_key: dict[tuple[str, str], RealPlayerImportStagingRecord] = {}
    for chunk in _chunks(list(staging_keys), size=500):
        for staging in session.scalars(
            select(RealPlayerImportStagingRecord).where(
                tuple_(
                    RealPlayerImportStagingRecord.provider_name,
                    RealPlayerImportStagingRecord.provider_player_id,
                ).in_(chunk)
            )
        ):
            staging_by_source_key[(staging.provider_name, staging.provider_player_id)] = staging

    summaries_by_player_id: dict[str, PlayerSummaryReadModel] = {}
    if load_summaries:
        for chunk in _chunks(player_ids):
            for summary in session.scalars(
                select(PlayerSummaryReadModel).where(PlayerSummaryReadModel.player_id.in_(chunk))
            ):
                summaries_by_player_id[summary.player_id] = summary

    return IntegrityRelatedRows(
        source_links_by_player_id=source_links_by_player_id,
        profiles_by_player_id=profiles_by_player_id,
        profiles_by_source_link_id=profiles_by_source_link_id,
        staging_by_source_key=staging_by_source_key,
        summaries_by_player_id=summaries_by_player_id,
    )


def _chunks(values: Sequence[T], size: int = 500) -> list[Sequence[T]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def _build_entity_cache(session: Session) -> CanonicalEntityCache:
    countries_by_code: dict[str, Country] = {}
    countries_by_name: dict[str, Country] = {}
    for country in session.scalars(select(Country)):
        for code in (
            country.provider_external_id,
            country.alpha2_code,
            country.alpha3_code,
            country.fifa_code,
        ):
            if code:
                countries_by_code.setdefault(code.strip().upper(), country)
        normalized_name = normalize_country_name(country.name)
        if normalized_name:
            countries_by_name.setdefault(normalized_name, country)

    competitions_by_external_id: dict[str, Competition] = {}
    competitions_by_name: dict[str, Competition | None] = {}
    for competition in session.scalars(select(Competition)):
        if competition.provider_external_id:
            competitions_by_external_id.setdefault(competition.provider_external_id.strip(), competition)
        normalized_name = normalize_competition_name(competition.name)
        if normalized_name:
            _put_unique(competitions_by_name, normalized_name, competition)

    clubs_by_external_id: dict[str, Club] = {}
    clubs_by_name_and_competition: dict[tuple[str, str], Club] = {}
    clubs_by_name: dict[str, Club | None] = {}
    for club in session.scalars(select(Club)):
        if club.provider_external_id:
            clubs_by_external_id.setdefault(club.provider_external_id.strip(), club)
        normalized_name = normalize_club_name(club.name)
        if normalized_name:
            _put_unique(clubs_by_name, normalized_name, club)
            if club.current_competition_id:
                clubs_by_name_and_competition.setdefault((normalized_name, club.current_competition_id), club)

    return CanonicalEntityCache(
        countries_by_code=countries_by_code,
        countries_by_name=countries_by_name,
        competitions_by_external_id=competitions_by_external_id,
        competitions_by_name=competitions_by_name,
        clubs_by_external_id=clubs_by_external_id,
        clubs_by_name_and_competition=clubs_by_name_and_competition,
        clubs_by_name=clubs_by_name,
    )


def _put_unique(mapping: dict[str, TValue | None], key: str, value: TValue) -> None:
    if key not in mapping:
        mapping[key] = value
    elif mapping[key] is not value:
        mapping[key] = None


def _source_link(session: Session, player: Player) -> RealPlayerSourceLink | None:
    return session.scalar(select(RealPlayerSourceLink).where(RealPlayerSourceLink.gtex_player_id == player.id))


def _profile(
    session: Session,
    player: Player,
    source_link: RealPlayerSourceLink | None,
) -> RealPlayerProfile | None:
    if source_link is not None:
        linked = session.scalar(select(RealPlayerProfile).where(RealPlayerProfile.source_link_id == source_link.id))
        if linked is not None:
            return linked
    return session.scalar(select(RealPlayerProfile).where(RealPlayerProfile.gtex_player_id == player.id))


def _staging(
    session: Session,
    player: Player,
    source_link: RealPlayerSourceLink | None,
    profile: RealPlayerProfile | None,
) -> RealPlayerImportStagingRecord | None:
    source_name = source_link.source_name if source_link is not None else profile.source_name if profile is not None else player.source_provider
    source_key = (
        source_link.source_player_key
        if source_link is not None
        else profile.source_player_key
        if profile is not None
        else player.provider_external_id
    )
    if not source_name or not source_key:
        return None
    return session.scalar(
        select(RealPlayerImportStagingRecord).where(
            RealPlayerImportStagingRecord.provider_name == source_name,
            RealPlayerImportStagingRecord.provider_player_id == source_key,
        )
    )


def _facts(
    *,
    player: Player,
    source_link: RealPlayerSourceLink | None,
    profile: RealPlayerProfile | None,
    staging: RealPlayerImportStagingRecord | None,
    summary: PlayerSummaryReadModel | None,
) -> PlayerFacts:
    payload = staging.latest_payload_json if staging is not None and isinstance(staging.latest_payload_json, dict) else {}
    current_club = _dict_value(payload, "currentClub")
    current_competition = _dict_value(payload, "currentCompetition")
    nationality_name = _first_clean(
        source_link.nationality if source_link is not None else None,
        profile.nationality if profile is not None else None,
        staging.nationality_name if staging is not None else None,
        _string_value(payload, "nationality"),
        _string_value(payload, "country"),
        _country_name(player.country),
    )
    nationality_code = _first_clean(
        staging.nationality_code if staging is not None else None,
        _string_value(payload, "nationalityCode"),
        _string_value(payload, "countryCode"),
        _country_code(player.country),
    )
    competition_name = _first_clean(
        player.real_world_league_name,
        profile.current_league_name if profile is not None else None,
        summary.current_competition_name if summary is not None else None,
        staging.provider_competition_name if staging is not None else None,
        _string_value(current_competition, "name"),
        _competition_name(player.current_competition),
    )
    competition_key = _first_clean(
        staging.provider_competition_id if staging is not None else None,
        _string_value(current_competition, "id"),
        _competition_key(player.current_competition),
    )
    club_name = _first_clean(
        player.real_world_club_name,
        source_link.current_real_world_club if source_link is not None else None,
        profile.current_club_name if profile is not None else None,
        summary.current_club_name if summary is not None else None,
        staging.provider_club_name if staging is not None else None,
        _string_value(current_club, "name"),
        _club_name(player.current_club),
    )
    club_key = _first_clean(
        staging.provider_club_id if staging is not None else None,
        _string_value(current_club, "id"),
        _club_key(player.current_club),
    )
    market_value_eur, market_value_source = _first_real_value(player=player, profile=profile, staging=staging)
    return PlayerFacts(
        nationality_name=nationality_name,
        nationality_code=nationality_code,
        competition_name=competition_name,
        competition_key=competition_key,
        club_name=club_name,
        club_key=club_key,
        date_of_birth=player.date_of_birth
        or (profile.date_of_birth if profile is not None else None)
        or (source_link.date_of_birth if source_link is not None else None)
        or (staging.date_of_birth if staging is not None else None),
        market_value_eur=market_value_eur,
        market_value_source=market_value_source,
    )


def _resolve_country(
    session: Session,
    *,
    mapper: RealPlayerCanonicalMappingService,
    entity_cache: CanonicalEntityCache,
    player: Player,
    facts: PlayerFacts,
) -> Country | None:
    if player.country is not None and _country_matches(player.country, facts):
        return player.country
    if not facts.nationality_name and not facts.nationality_code:
        return player.country
    cached = _cached_country(entity_cache, facts)
    if cached is not None:
        return cached
    if not mapper.auto_create_missing_entities:
        return player.country
    resolution = mapper.resolve_country(
        session,
        source_name=player.source_provider or "real_player_repair",
        provider_external_id=facts.nationality_code,
        name=facts.nationality_name,
        sample_payload={"repair_source": "real_player_market_integrity"},
    )
    return resolution.entity if isinstance(resolution.entity, Country) else player.country


def _resolve_competition(
    session: Session,
    *,
    mapper: RealPlayerCanonicalMappingService,
    entity_cache: CanonicalEntityCache,
    player: Player,
    facts: PlayerFacts,
) -> Competition | None:
    if player.current_competition is not None and _competition_matches(player.current_competition, facts):
        return player.current_competition
    if not facts.competition_name and not facts.competition_key:
        return player.current_competition
    cached = _cached_competition(entity_cache, facts)
    if cached is not None:
        return cached
    if not mapper.auto_create_missing_entities:
        return player.current_competition
    resolution = mapper.resolve_competition(
        session,
        source_name=player.source_provider or "real_player_repair",
        provider_external_id=facts.competition_key,
        name=facts.competition_name,
        country=None,
        country_code=None,
        country_name=None,
        sample_payload={"repair_source": "real_player_market_integrity"},
        auto_create_values={"format_type": "real_world", "is_tradable": True},
    )
    return resolution.entity if isinstance(resolution.entity, Competition) else player.current_competition


def _resolve_club(
    session: Session,
    *,
    mapper: RealPlayerCanonicalMappingService,
    entity_cache: CanonicalEntityCache,
    player: Player,
    facts: PlayerFacts,
    competition: Competition | None,
) -> Club | None:
    if player.current_club is not None and _club_matches(player.current_club, facts, competition=competition):
        return player.current_club
    if not facts.club_name and not facts.club_key:
        return player.current_club
    cached = _cached_club(entity_cache, facts, competition=competition)
    if cached is not None:
        return cached
    if not mapper.auto_create_missing_entities:
        return player.current_club
    resolution = mapper.resolve_club(
        session,
        source_name=player.source_provider or "real_player_repair",
        provider_external_id=facts.club_key,
        name=facts.club_name,
        country=competition.country if competition is not None else None,
        country_code=None,
        country_name=None,
        competition=competition,
        competition_external_id=facts.competition_key,
        competition_name=facts.competition_name,
        sample_payload={"repair_source": "real_player_market_integrity"},
        auto_create_values={"is_tradable": True},
    )
    return resolution.entity if isinstance(resolution.entity, Club) else player.current_club


def _country_matches(country: Country, facts: PlayerFacts) -> bool:
    if facts.nationality_code:
        expected_code = facts.nationality_code.strip().upper()
        if expected_code in {
            code.strip().upper()
            for code in (country.provider_external_id, country.alpha2_code, country.alpha3_code, country.fifa_code)
            if code
        }:
            return True
    if facts.nationality_name:
        return normalize_country_name(country.name) == normalize_country_name(facts.nationality_name)
    return True


def _competition_matches(competition: Competition, facts: PlayerFacts) -> bool:
    if facts.competition_key and competition.provider_external_id == facts.competition_key:
        return True
    if facts.competition_name:
        return normalize_competition_name(competition.name) == normalize_competition_name(facts.competition_name)
    return True


def _club_matches(club: Club, facts: PlayerFacts, *, competition: Competition | None) -> bool:
    if facts.club_key and club.provider_external_id == facts.club_key:
        return True
    if facts.club_name and normalize_club_name(club.name) == normalize_club_name(facts.club_name):
        return competition is None or club.current_competition_id in {None, competition.id}
    return True


def _cached_country(entity_cache: CanonicalEntityCache, facts: PlayerFacts) -> Country | None:
    if facts.nationality_code:
        country = entity_cache.countries_by_code.get(facts.nationality_code.strip().upper())
        if country is not None:
            return country
    if facts.nationality_name:
        normalized_name = normalize_country_name(facts.nationality_name)
        if normalized_name:
            return entity_cache.countries_by_name.get(normalized_name)
    return None


def _cached_competition(entity_cache: CanonicalEntityCache, facts: PlayerFacts) -> Competition | None:
    if facts.competition_key:
        competition = entity_cache.competitions_by_external_id.get(facts.competition_key.strip())
        if competition is not None:
            return competition
    if facts.competition_name:
        normalized_name = normalize_competition_name(facts.competition_name)
        if normalized_name:
            return entity_cache.competitions_by_name.get(normalized_name)
    return None


def _cached_club(
    entity_cache: CanonicalEntityCache,
    facts: PlayerFacts,
    *,
    competition: Competition | None,
) -> Club | None:
    if facts.club_key:
        club = entity_cache.clubs_by_external_id.get(facts.club_key.strip())
        if club is not None:
            return club
    if facts.club_name:
        normalized_name = normalize_club_name(facts.club_name)
        if normalized_name and competition is not None:
            club = entity_cache.clubs_by_name_and_competition.get((normalized_name, competition.id))
            if club is not None:
                return club
        if normalized_name:
            return entity_cache.clubs_by_name.get(normalized_name)
    return None


def _summary_needs_update(
    summary: PlayerSummaryReadModel,
    *,
    player: Player,
    facts: PlayerFacts,
    competition: Competition | None,
    club: Club | None,
) -> bool:
    value_credits = _credits_from_value(facts.market_value_eur)
    return any(
        (
            club is not None and summary.current_club_id != club.id,
            club is not None and summary.current_club_name != club.name,
            competition is not None and summary.current_competition_id != competition.id,
            competition is not None and summary.current_competition_name != competition.name,
            value_credits is not None and summary.current_value_credits <= 0,
            player.real_world_club_name and not summary.current_club_name,
            player.real_world_league_name and not summary.current_competition_name,
        )
    )


def _repair_summary(
    summary: PlayerSummaryReadModel,
    *,
    player: Player,
    facts: PlayerFacts,
    competition: Competition | None,
    club: Club | None,
) -> None:
    if club is not None:
        summary.current_club_id = club.id
        summary.current_club_name = club.name
    elif player.real_world_club_name:
        summary.current_club_name = player.real_world_club_name
    if competition is not None:
        summary.current_competition_id = competition.id
        summary.current_competition_name = competition.name
    elif player.real_world_league_name:
        summary.current_competition_name = player.real_world_league_name
    value_credits = _credits_from_value(facts.market_value_eur)
    if value_credits is not None and summary.current_value_credits <= 0:
        summary.current_value_credits = value_credits
        summary.previous_value_credits = value_credits
    payload = dict(summary.summary_json or {})
    real_player_profile = dict(payload.get("real_player_profile") or {})
    if facts.market_value_eur is not None:
        real_player_profile["current_market_reference_value"] = facts.market_value_eur
        real_player_profile["market_reference_currency"] = "EUR"
        real_player_profile["market_value_source"] = facts.market_value_source
    payload["real_player_profile"] = real_player_profile
    payload["club_assignment"] = {
        **dict(payload.get("club_assignment") or {}),
        "status": "club_assigned" if club is not None else "team_context_pending",
        "current_club_id": club.id if club is not None else None,
        "current_club_name": club.name if club is not None else summary.current_club_name,
        "current_competition_id": competition.id if competition is not None else None,
        "current_competition_name": (
            competition.name if competition is not None else summary.current_competition_name
        ),
    }
    summary.summary_json = payload


def _first_real_value(
    *,
    player: Player,
    profile: RealPlayerProfile | None,
    staging: RealPlayerImportStagingRecord | None,
) -> tuple[float | None, str | None]:
    values = (
        (player.current_market_reference_value, player.market_reference_currency, "player.current_market_reference_value"),
        (player.market_value_eur, "EUR", "player.market_value_eur"),
        (
            profile.current_market_reference_value if profile is not None else None,
            profile.market_reference_currency if profile is not None else None,
            "profile.current_market_reference_value",
        ),
        (
            staging.rough_market_value if staging is not None else None,
            staging.rough_market_value_currency if staging is not None else None,
            "staging.rough_market_value",
        ),
    )
    for value, currency, source in values:
        positive = _positive_float(value)
        if positive is not None and (currency is None or str(currency).upper() == "EUR") and source in REAL_VALUE_SOURCE_FIELDS:
            return positive, source
    return None, None


def _credits_from_value(value: float | None) -> float | None:
    if value is None or value <= 0:
        return None
    return credits_from_real_world_value(value)


def _positive_float(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _sample(
    stats: IntegrityStats,
    *,
    player: Player,
    issue: str,
    facts: PlayerFacts,
    sample_size: int,
) -> None:
    if len(stats.unresolved_samples) >= sample_size:
        return
    stats.unresolved_samples.append(
        {
            "player_id": player.id,
            "name": player.full_name,
            "issue": issue,
            "source_provider": player.source_provider,
            "provider_external_id": player.provider_external_id,
            "facts": asdict(facts),
        }
    )


def _first_clean(*values: object) -> str | None:
    for value in values:
        cleaned = clean_name(str(value)) if value is not None else None
        if cleaned:
            return cleaned
    return None


def _string_value(payload: object, key: str) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get(key)
    return str(value) if value is not None else None


def _dict_value(payload: object, key: str) -> dict[str, object] | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get(key)
    return value if isinstance(value, dict) else None


def _country_name(country: Country | None) -> str | None:
    return country.name if country is not None else None


def _country_code(country: Country | None) -> str | None:
    if country is None:
        return None
    return country.fifa_code or country.alpha3_code or country.alpha2_code


def _competition_name(competition: Competition | None) -> str | None:
    return competition.name if competition is not None else None


def _competition_key(competition: Competition | None) -> str | None:
    return competition.provider_external_id if competition is not None else None


def _club_name(club: Club | None) -> str | None:
    return club.name if club is not None else None


def _club_key(club: Club | None) -> str | None:
    return club.provider_external_id if club is not None else None


if __name__ == "__main__":
    raise SystemExit(main())
