from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
from typing import Any, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.base import utcnow

from .market_profile import PlayerMarketProfileService
from .constants import DEFAULT_CURSOR_KEY, SYNC_RUN_STATUS_SUCCESS
from .models import (
    Club,
    Competition,
    Country,
    IngestionJobLock,
    InjuryStatus,
    InternalLeague,
    LiquidityBand,
    MarketSignal,
    Match,
    Player,
    PlayerClubTenure,
    PlayerMatchStat,
    PlayerSeasonStat,
    ProviderRawPayload,
    ProviderSyncCursor,
    ProviderSyncRun,
    Season,
    SupplyTier,
    SyncRunStatus,
    TeamStanding,
)
from .schemas import (
    ClubUpsert,
    CompetitionUpsert,
    CountryUpsert,
    InjuryStatusUpsert,
    MarketSignalUpsert,
    MatchUpsert,
    PlayerClubTenureUpsert,
    PlayerMatchStatUpsert,
    PlayerSeasonStatUpsert,
    PlayerUpsert,
    SeasonUpsert,
    TeamStandingUpsert,
)

ModelT = TypeVar("ModelT")


@dataclass(slots=True)
class MutationStats:
    records_seen: int = 0
    inserted_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    touched_ids: set[str] = field(default_factory=set)

    def merge(self, other: "MutationStats") -> None:
        self.records_seen += other.records_seen
        self.inserted_count += other.inserted_count
        self.updated_count += other.updated_count
        self.skipped_count += other.skipped_count
        self.failed_count += other.failed_count
        self.touched_ids.update(other.touched_ids)


class IngestionRepository:
    def __init__(
        self,
        session: Session,
        *,
        market_profile_service: PlayerMarketProfileService | None = None,
    ):
        self.session = session
        self.market_profile_service = market_profile_service or PlayerMarketProfileService()

    def start_sync_run(
        self,
        *,
        provider_name: str,
        job_name: str,
        entity_type: str,
        scope_value: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> ProviderSyncRun:
        run = ProviderSyncRun(
            provider_name=provider_name,
            job_name=job_name,
            entity_type=entity_type,
            scope_value=scope_value,
            status=SyncRunStatus.RUNNING.value,
            started_at=utcnow(),
            metadata_json=metadata_json,
        )
        self.session.add(run)
        self.session.flush()
        return run

    def finish_sync_run(
        self,
        run: ProviderSyncRun,
        *,
        stats: MutationStats,
        status: str = SYNC_RUN_STATUS_SUCCESS,
        error_message: str | None = None,
        cursor_value: str | None = None,
    ) -> ProviderSyncRun:
        finished_at = utcnow()
        run.status = status
        run.completed_at = finished_at
        run.duration_ms = int((finished_at - run.started_at).total_seconds() * 1000)
        run.records_seen = stats.records_seen
        run.inserted_count = stats.inserted_count
        run.updated_count = stats.updated_count
        run.skipped_count = stats.skipped_count
        run.failed_count = stats.failed_count
        run.error_message = error_message
        run.cursor_value = cursor_value
        self.session.flush()
        return run

    def store_raw_payloads(
        self,
        *,
        provider_name: str,
        entity_type: str,
        payloads: list[dict[str, Any]],
        sync_run_id: str | None = None,
        external_id_key: str = "id",
    ) -> int:
        if not payloads:
            return 0
        hashes = {
            hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest(): payload
            for payload in payloads
        }
        existing_hashes = {
            row.payload_hash
            for row in self.session.scalars(
                select(ProviderRawPayload).where(
                    ProviderRawPayload.provider_name == provider_name,
                    ProviderRawPayload.entity_type == entity_type,
                    ProviderRawPayload.payload_hash.in_(hashes.keys()),
                )
            )
        }
        created = 0
        for payload_hash, payload in hashes.items():
            if payload_hash in existing_hashes:
                continue
            self.session.add(
                ProviderRawPayload(
                    provider_name=provider_name,
                    entity_type=entity_type,
                    provider_external_id=str(payload.get(external_id_key)) if payload.get(external_id_key) is not None else None,
                    sync_run_id=sync_run_id,
                    payload_hash=payload_hash,
                    payload=payload,
                )
            )
            created += 1
        self.session.flush()
        return created

    def get_cursor(
        self,
        *,
        provider_name: str,
        entity_type: str,
        cursor_key: str = DEFAULT_CURSOR_KEY,
    ) -> ProviderSyncCursor | None:
        return self.session.scalar(
            select(ProviderSyncCursor).where(
                ProviderSyncCursor.provider_name == provider_name,
                ProviderSyncCursor.entity_type == entity_type,
                ProviderSyncCursor.cursor_key == cursor_key,
            )
        )

    def save_cursor(
        self,
        *,
        provider_name: str,
        entity_type: str,
        cursor_value: str | None,
        cursor_key: str = DEFAULT_CURSOR_KEY,
        last_run_id: str | None = None,
    ) -> ProviderSyncCursor:
        cursor = self.get_cursor(provider_name=provider_name, entity_type=entity_type, cursor_key=cursor_key)
        if cursor is None:
            cursor = ProviderSyncCursor(
                provider_name=provider_name,
                entity_type=entity_type,
                cursor_key=cursor_key,
            )
            self.session.add(cursor)
        cursor.cursor_value = cursor_value
        cursor.checkpoint_at = utcnow()
        cursor.last_run_id = last_run_id
        self.session.flush()
        return cursor

    def list_recent_sync_runs(self, *, provider_name: str | None = None, limit: int = 20) -> list[ProviderSyncRun]:
        statement = select(ProviderSyncRun).order_by(ProviderSyncRun.started_at.desc()).limit(limit)
        if provider_name:
            statement = statement.where(ProviderSyncRun.provider_name == provider_name)
        return list(self.session.scalars(statement))

    def get_latest_sync_run(self, *, provider_name: str | None = None) -> ProviderSyncRun | None:
        statement = select(ProviderSyncRun).order_by(ProviderSyncRun.started_at.desc()).limit(1)
        if provider_name:
            statement = statement.where(ProviderSyncRun.provider_name == provider_name)
        return self.session.scalar(statement)

    def list_cursors(self, *, provider_name: str | None = None) -> list[ProviderSyncCursor]:
        statement = select(ProviderSyncCursor).order_by(ProviderSyncCursor.updated_at.desc())
        if provider_name:
            statement = statement.where(ProviderSyncCursor.provider_name == provider_name)
        return list(self.session.scalars(statement))

    def list_active_locks(self, *, now: datetime | None = None) -> list[str]:
        now = now or utcnow()
        return list(self.session.scalars(select(IngestionJobLock.lock_key).where(IngestionJobLock.expires_at > now)))

    def _provider_lookup(self, model: type[ModelT], pairs: set[tuple[str, str]]) -> dict[tuple[str, str], ModelT]:
        if not pairs:
            return {}
        providers = {provider for provider, _ in pairs}
        external_ids = {external_id for _, external_id in pairs}
        rows = self.session.scalars(
            select(model).where(
                getattr(model, "source_provider").in_(providers),
                getattr(model, "provider_external_id").in_(external_ids),
            )
        )
        return {(getattr(row, "source_provider"), getattr(row, "provider_external_id")): row for row in rows}

    def _country_lookup_by_name(self, names: set[str]) -> dict[str, Country]:
        if not names:
            return {}
        rows = self.session.scalars(select(Country).where(Country.name.in_(names)))
        return {row.name: row for row in rows}

    def _lookup_by_attribute(self, model: type[ModelT], attribute_name: str, values: set[str]) -> dict[str, ModelT]:
        normalized_values = {value for value in values if value}
        if not normalized_values:
            return {}
        rows = self.session.scalars(select(model).where(getattr(model, attribute_name).in_(normalized_values)))
        return {getattr(row, attribute_name): row for row in rows}

    def refresh_player_market_profiles(self, player_ids: set[str] | None = None) -> None:
        if player_ids is not None and not player_ids:
            return
        self.market_profile_service.refresh_player_profiles(self.session, player_ids=player_ids)

    def _apply_update(self, instance: Any, values: dict[str, Any]) -> bool:
        changed = False
        for key, new_value in values.items():
            if key in {"id", "created_at", "updated_at", "last_synced_at"}:
                continue
            if not hasattr(instance, key):
                continue
            if new_value is None:
                continue
            if isinstance(new_value, str) and not new_value.strip():
                continue
            if getattr(instance, key) != new_value:
                setattr(instance, key, new_value)
                changed = True
        return changed

    def _upsert_models(self, model: type[ModelT], payloads: list[dict[str, Any]]) -> MutationStats:
        stats = MutationStats(records_seen=len(payloads))
        if not payloads:
            return stats
        lookup = self._provider_lookup(
            model,
            {
                (str(payload["source_provider"]), str(payload["provider_external_id"]))
                for payload in payloads
                if payload.get("provider_external_id")
            },
        )
        for payload in payloads:
            provider_key = (str(payload["source_provider"]), str(payload["provider_external_id"]))
            existing = lookup.get(provider_key)
            if existing is None:
                instance = model(**payload)
                self.session.add(instance)
                self.session.flush()
                lookup[provider_key] = instance
                stats.inserted_count += 1
                stats.touched_ids.add(getattr(instance, "id"))
                continue
            if self._apply_update(existing, payload):
                if "last_synced_at" in payload and hasattr(existing, "last_synced_at"):
                    setattr(existing, "last_synced_at", payload["last_synced_at"])
                self.session.flush()
                stats.updated_count += 1
                stats.touched_ids.add(getattr(existing, "id"))
            else:
                stats.skipped_count += 1
        return stats

    def upsert_countries(self, records: list[CountryUpsert]) -> MutationStats:
        return self._upsert_models(
            Country,
            [
                {
                    "source_provider": record.provider_name,
                    "provider_external_id": record.provider_external_id,
                    "name": record.name,
                    "alpha2_code": record.alpha2_code,
                    "alpha3_code": record.alpha3_code,
                    "fifa_code": record.fifa_code,
                    "confederation_code": record.confederation_code,
                    "market_region": record.market_region,
                    "is_enabled_for_universe": record.is_enabled_for_universe,
                    "flag_url": record.flag_url,
                    "last_synced_at": utcnow(),
                }
                for record in records
            ],
        )

    def upsert_competitions(self, records: list[CompetitionUpsert]) -> MutationStats:
        country_pairs = {
            (record.provider_name, record.country_provider_external_id)
            for record in records
            if record.country_provider_external_id
        }
        country_lookup = self._provider_lookup(Country, country_pairs)
        country_by_name = self._country_lookup_by_name({record.country_name for record in records if record.country_name})
        internal_league_lookup = self._lookup_by_attribute(
            InternalLeague,
            "code",
            {record.internal_league_code for record in records if record.internal_league_code},
        )
        payloads: list[dict[str, Any]] = []
        for record in records:
            country = None
            if record.country_provider_external_id:
                country = country_lookup.get((record.provider_name, record.country_provider_external_id))
            if country is None and record.country_name:
                country = country_by_name.get(record.country_name)
            internal_league = internal_league_lookup.get(record.internal_league_code or "")
            payloads.append(
                {
                    "source_provider": record.provider_name,
                    "provider_external_id": record.provider_external_id,
                    "country_id": country.id if country else None,
                    "internal_league_id": internal_league.id if internal_league else None,
                    "name": record.name,
                    "slug": record.slug,
                    "code": record.code,
                    "competition_type": record.competition_type.lower(),
                    "format_type": record.format_type,
                    "age_bracket": record.age_bracket,
                    "domestic_level": record.domestic_level,
                    "gender": record.gender,
                    "emblem_url": record.emblem_url,
                    "is_major": record.is_major,
                    "is_tradable": record.is_tradable,
                    "competition_strength": record.competition_strength,
                    "current_season_external_id": record.current_season_external_id,
                    "last_synced_at": utcnow(),
                }
            )
        return self._upsert_models(Competition, payloads)

    def upsert_seasons(self, records: list[SeasonUpsert]) -> MutationStats:
        competition_lookup = self._provider_lookup(
            Competition,
            {(record.provider_name, record.competition_provider_external_id) for record in records},
        )
        payloads: list[dict[str, Any]] = []
        stats = MutationStats(records_seen=len(records))
        for record in records:
            competition = competition_lookup.get((record.provider_name, record.competition_provider_external_id))
            if competition is None:
                stats.failed_count += 1
                continue
            payloads.append(
                {
                    "source_provider": record.provider_name,
                    "provider_external_id": record.provider_external_id,
                    "competition_id": competition.id,
                    "label": record.label,
                    "year_start": record.year_start,
                    "year_end": record.year_end,
                    "start_date": record.start_date,
                    "end_date": record.end_date,
                    "is_current": record.is_current,
                    "current_matchday": record.current_matchday,
                    "season_status": record.season_status,
                    "trading_window_opens_at": record.trading_window_opens_at,
                    "trading_window_closes_at": record.trading_window_closes_at,
                    "data_completeness_score": record.data_completeness_score,
                    "last_synced_at": utcnow(),
                }
            )
        stats.merge(self._upsert_models(Season, payloads))
        return stats

    def upsert_clubs(self, records: list[ClubUpsert]) -> MutationStats:
        country_pairs = {
            (record.provider_name, record.country_provider_external_id)
            for record in records
            if record.country_provider_external_id
        }
        country_lookup = self._provider_lookup(Country, country_pairs)
        country_by_name = self._country_lookup_by_name({record.country_name for record in records if record.country_name})
        competition_lookup = self._provider_lookup(
            Competition,
            {
                (record.provider_name, record.current_competition_provider_external_id)
                for record in records
                if record.current_competition_provider_external_id
            },
        )
        internal_league_lookup = self._lookup_by_attribute(
            InternalLeague,
            "code",
            {record.internal_league_code for record in records if record.internal_league_code},
        )
        payloads = []
        for record in records:
            country = None
            if record.country_provider_external_id:
                country = country_lookup.get((record.provider_name, record.country_provider_external_id))
            if country is None and record.country_name:
                country = country_by_name.get(record.country_name)
            competition = None
            if record.current_competition_provider_external_id:
                competition = competition_lookup.get((record.provider_name, record.current_competition_provider_external_id))
            internal_league = internal_league_lookup.get(record.internal_league_code or "")
            if internal_league is None and competition is not None and competition.internal_league_id:
                internal_league = competition.internal_league
            payloads.append(
                {
                    "source_provider": record.provider_name,
                    "provider_external_id": record.provider_external_id,
                    "country_id": country.id if country else None,
                    "current_competition_id": competition.id if competition else None,
                    "internal_league_id": internal_league.id if internal_league else None,
                    "name": record.name,
                    "slug": record.slug,
                    "short_name": record.short_name,
                    "code": record.code,
                    "gender": record.gender,
                    "founded_year": record.founded_year,
                    "website": record.website,
                    "venue": record.venue,
                    "crest_url": record.crest_url,
                    "popularity_score": record.popularity_score,
                    "is_tradable": record.is_tradable,
                    "last_synced_at": utcnow(),
                }
            )
        return self._upsert_models(Club, payloads)

    def upsert_players(self, records: list[PlayerUpsert]) -> MutationStats:
        self.market_profile_service.ensure_catalogs(self.session)
        country_pairs = {
            (record.provider_name, record.country_provider_external_id)
            for record in records
            if record.country_provider_external_id
        }
        country_lookup = self._provider_lookup(Country, country_pairs)
        country_by_name = self._country_lookup_by_name({record.country_name for record in records if record.country_name})
        club_lookup = self._provider_lookup(
            Club,
            {
                (record.provider_name, record.current_club_provider_external_id)
                for record in records
                if record.current_club_provider_external_id
            },
        )
        competition_lookup = self._provider_lookup(
            Competition,
            {
                (record.provider_name, record.current_competition_provider_external_id)
                for record in records
                if record.current_competition_provider_external_id
            },
        )
        internal_league_lookup = self._lookup_by_attribute(
            InternalLeague,
            "code",
            {record.internal_league_code for record in records if record.internal_league_code},
        )
        supply_tier_lookup = self._lookup_by_attribute(
            SupplyTier,
            "code",
            {record.supply_tier_code for record in records if record.supply_tier_code},
        )
        liquidity_band_lookup = self._lookup_by_attribute(
            LiquidityBand,
            "code",
            {record.liquidity_band_code for record in records if record.liquidity_band_code},
        )
        payloads = []
        for record in records:
            country = None
            if record.country_provider_external_id:
                country = country_lookup.get((record.provider_name, record.country_provider_external_id))
            if country is None and record.country_name:
                country = country_by_name.get(record.country_name)
            club = None
            if record.current_club_provider_external_id:
                club = club_lookup.get((record.provider_name, record.current_club_provider_external_id))
            competition = None
            if record.current_competition_provider_external_id:
                competition = competition_lookup.get((record.provider_name, record.current_competition_provider_external_id))
            internal_league = internal_league_lookup.get(record.internal_league_code or "")
            if internal_league is None and competition is not None and competition.internal_league_id:
                internal_league = competition.internal_league
            if internal_league is None and club is not None and club.internal_league_id:
                internal_league = club.internal_league
            supply_tier = supply_tier_lookup.get(record.supply_tier_code or "")
            liquidity_band = liquidity_band_lookup.get(record.liquidity_band_code or "")
            payloads.append(
                {
                    "source_provider": record.provider_name,
                    "provider_external_id": record.provider_external_id,
                    "country_id": country.id if country else None,
                    "current_club_id": club.id if club else None,
                    "current_competition_id": competition.id if competition else None,
                    "internal_league_id": internal_league.id if internal_league else None,
                    "supply_tier_id": supply_tier.id if supply_tier else None,
                    "liquidity_band_id": liquidity_band.id if liquidity_band else None,
                    "full_name": record.full_name,
                    "first_name": record.first_name,
                    "last_name": record.last_name,
                    "short_name": record.short_name,
                    "position": record.position,
                    "normalized_position": record.normalized_position,
                    "date_of_birth": record.date_of_birth,
                    "height_cm": record.height_cm,
                    "weight_kg": record.weight_kg,
                    "preferred_foot": record.preferred_foot,
                    "shirt_number": record.shirt_number,
                    "market_value_eur": record.market_value_eur,
                    "profile_completeness_score": record.profile_completeness_score,
                    "is_tradable": record.is_tradable,
                    "last_synced_at": utcnow(),
                }
            )
        stats = self._upsert_models(Player, payloads)
        player_lookup = self._provider_lookup(
            Player,
            {(record.provider_name, record.provider_external_id) for record in records},
        )
        self.refresh_player_market_profiles({player.id for player in player_lookup.values()})
        return stats

    def upsert_player_tenures(self, records: list[PlayerClubTenureUpsert]) -> MutationStats:
        player_lookup = self._provider_lookup(
            Player,
            {(record.provider_name, record.player_provider_external_id) for record in records},
        )
        club_lookup = self._provider_lookup(
            Club,
            {(record.provider_name, record.club_provider_external_id) for record in records},
        )
        season_lookup = self._provider_lookup(
            Season,
            {(record.provider_name, record.season_provider_external_id) for record in records if record.season_provider_external_id},
        )
        payloads: list[dict[str, Any]] = []
        stats = MutationStats(records_seen=len(records))
        for record in records:
            player = player_lookup.get((record.provider_name, record.player_provider_external_id))
            club = club_lookup.get((record.provider_name, record.club_provider_external_id))
            if player is None or club is None:
                stats.failed_count += 1
                continue
            season = None
            if record.season_provider_external_id:
                season = season_lookup.get((record.provider_name, record.season_provider_external_id))
            payloads.append(
                {
                    "source_provider": record.provider_name,
                    "provider_external_id": record.provider_external_id,
                    "player_id": player.id,
                    "club_id": club.id,
                    "season_id": season.id if season else None,
                    "start_date": record.start_date,
                    "end_date": record.end_date,
                    "squad_number": record.squad_number,
                    "is_current": record.is_current,
                }
            )
        stats.merge(self._upsert_models(PlayerClubTenure, payloads))
        return stats

    def upsert_matches(self, records: list[MatchUpsert]) -> MutationStats:
        competition_lookup = self._provider_lookup(
            Competition,
            {(record.provider_name, record.competition_provider_external_id) for record in records},
        )
        season_lookup = self._provider_lookup(
            Season,
            {(record.provider_name, record.season_provider_external_id) for record in records if record.season_provider_external_id},
        )
        club_lookup = self._provider_lookup(
            Club,
            {
                (record.provider_name, external_id)
                for record in records
                for external_id in (
                    record.home_club_provider_external_id,
                    record.away_club_provider_external_id,
                    record.winner_club_provider_external_id,
                )
                if external_id
            },
        )
        payloads: list[dict[str, Any]] = []
        stats = MutationStats(records_seen=len(records))
        for record in records:
            competition = competition_lookup.get((record.provider_name, record.competition_provider_external_id))
            home_club = club_lookup.get((record.provider_name, record.home_club_provider_external_id))
            away_club = club_lookup.get((record.provider_name, record.away_club_provider_external_id))
            if competition is None or home_club is None or away_club is None:
                stats.failed_count += 1
                continue
            season = None
            if record.season_provider_external_id:
                season = season_lookup.get((record.provider_name, record.season_provider_external_id))
            winner = None
            if record.winner_club_provider_external_id:
                winner = club_lookup.get((record.provider_name, record.winner_club_provider_external_id))
            payloads.append(
                {
                    "source_provider": record.provider_name,
                    "provider_external_id": record.provider_external_id,
                    "competition_id": competition.id,
                    "season_id": season.id if season else None,
                    "home_club_id": home_club.id,
                    "away_club_id": away_club.id,
                    "winner_club_id": winner.id if winner else None,
                    "venue": record.venue,
                    "kickoff_at": record.kickoff_at,
                    "status": record.status,
                    "stage": record.stage,
                    "matchday": record.matchday,
                    "home_score": record.home_score,
                    "away_score": record.away_score,
                    "last_provider_update_at": record.last_provider_update_at,
                }
            )
        stats.merge(self._upsert_models(Match, payloads))
        return stats

    def upsert_team_standings(self, records: list[TeamStandingUpsert]) -> MutationStats:
        competition_lookup = self._provider_lookup(
            Competition,
            {(record.provider_name, record.competition_provider_external_id) for record in records},
        )
        season_lookup = self._provider_lookup(
            Season,
            {(record.provider_name, record.season_provider_external_id) for record in records if record.season_provider_external_id},
        )
        club_lookup = self._provider_lookup(
            Club,
            {(record.provider_name, record.club_provider_external_id) for record in records},
        )
        payloads: list[dict[str, Any]] = []
        stats = MutationStats(records_seen=len(records))
        for record in records:
            competition = competition_lookup.get((record.provider_name, record.competition_provider_external_id))
            club = club_lookup.get((record.provider_name, record.club_provider_external_id))
            if competition is None or club is None:
                stats.failed_count += 1
                continue
            season = None
            if record.season_provider_external_id:
                season = season_lookup.get((record.provider_name, record.season_provider_external_id))
            payloads.append(
                {
                    "source_provider": record.provider_name,
                    "provider_external_id": record.provider_external_id,
                    "competition_id": competition.id,
                    "season_id": season.id if season else None,
                    "club_id": club.id,
                    "standing_type": record.standing_type,
                    "position": record.position,
                    "played": record.played,
                    "won": record.won,
                    "drawn": record.drawn,
                    "lost": record.lost,
                    "goals_for": record.goals_for,
                    "goals_against": record.goals_against,
                    "goal_difference": record.goal_difference,
                    "points": record.points,
                    "form": record.form,
                }
            )
        stats.merge(self._upsert_models(TeamStanding, payloads))
        return stats

    def upsert_player_match_stats(self, records: list[PlayerMatchStatUpsert]) -> MutationStats:
        player_lookup = self._provider_lookup(
            Player,
            {(record.provider_name, record.player_provider_external_id) for record in records},
        )
        match_lookup = self._provider_lookup(
            Match,
            {(record.provider_name, record.match_provider_external_id) for record in records},
        )
        club_lookup = self._provider_lookup(
            Club,
            {(record.provider_name, record.club_provider_external_id) for record in records if record.club_provider_external_id},
        )
        competition_lookup = self._provider_lookup(
            Competition,
            {
                (record.provider_name, record.competition_provider_external_id)
                for record in records
                if record.competition_provider_external_id
            },
        )
        season_lookup = self._provider_lookup(
            Season,
            {(record.provider_name, record.season_provider_external_id) for record in records if record.season_provider_external_id},
        )
        payloads: list[dict[str, Any]] = []
        player_ids_to_refresh: set[str] = set()
        stats = MutationStats(records_seen=len(records))
        for record in records:
            player = player_lookup.get((record.provider_name, record.player_provider_external_id))
            match = match_lookup.get((record.provider_name, record.match_provider_external_id))
            if player is None or match is None:
                stats.failed_count += 1
                continue
            player_ids_to_refresh.add(player.id)
            club = None
            competition = None
            season = None
            if record.club_provider_external_id:
                club = club_lookup.get((record.provider_name, record.club_provider_external_id))
            if record.competition_provider_external_id:
                competition = competition_lookup.get((record.provider_name, record.competition_provider_external_id))
            if record.season_provider_external_id:
                season = season_lookup.get((record.provider_name, record.season_provider_external_id))
            payloads.append(
                {
                    "source_provider": record.provider_name,
                    "provider_external_id": record.provider_external_id,
                    "player_id": player.id,
                    "match_id": match.id,
                    "club_id": club.id if club else None,
                    "competition_id": competition.id if competition else None,
                    "season_id": season.id if season else None,
                    "appearances": record.appearances,
                    "starts": record.starts,
                    "minutes": record.minutes,
                    "goals": record.goals,
                    "assists": record.assists,
                    "saves": record.saves,
                    "clean_sheet": record.clean_sheet,
                    "rating": record.rating,
                    "raw_position": record.raw_position,
                }
            )
        stats.merge(self._upsert_models(PlayerMatchStat, payloads))
        self.refresh_player_market_profiles(player_ids_to_refresh)
        return stats

    def upsert_player_season_stats(self, records: list[PlayerSeasonStatUpsert]) -> MutationStats:
        player_lookup = self._provider_lookup(
            Player,
            {(record.provider_name, record.player_provider_external_id) for record in records},
        )
        club_lookup = self._provider_lookup(
            Club,
            {(record.provider_name, record.club_provider_external_id) for record in records if record.club_provider_external_id},
        )
        competition_lookup = self._provider_lookup(
            Competition,
            {
                (record.provider_name, record.competition_provider_external_id)
                for record in records
                if record.competition_provider_external_id
            },
        )
        season_lookup = self._provider_lookup(
            Season,
            {(record.provider_name, record.season_provider_external_id) for record in records if record.season_provider_external_id},
        )
        payloads: list[dict[str, Any]] = []
        player_ids_to_refresh: set[str] = set()
        stats = MutationStats(records_seen=len(records))
        for record in records:
            player = player_lookup.get((record.provider_name, record.player_provider_external_id))
            if player is None:
                stats.failed_count += 1
                continue
            player_ids_to_refresh.add(player.id)
            club = None
            competition = None
            season = None
            if record.club_provider_external_id:
                club = club_lookup.get((record.provider_name, record.club_provider_external_id))
            if record.competition_provider_external_id:
                competition = competition_lookup.get((record.provider_name, record.competition_provider_external_id))
            if record.season_provider_external_id:
                season = season_lookup.get((record.provider_name, record.season_provider_external_id))
            payloads.append(
                {
                    "source_provider": record.provider_name,
                    "provider_external_id": record.provider_external_id,
                    "player_id": player.id,
                    "club_id": club.id if club else None,
                    "competition_id": competition.id if competition else None,
                    "season_id": season.id if season else None,
                    "appearances": record.appearances,
                    "starts": record.starts,
                    "minutes": record.minutes,
                    "goals": record.goals,
                    "assists": record.assists,
                    "yellow_cards": record.yellow_cards,
                    "red_cards": record.red_cards,
                    "clean_sheets": record.clean_sheets,
                    "saves": record.saves,
                    "average_rating": record.average_rating,
                }
            )
        stats.merge(self._upsert_models(PlayerSeasonStat, payloads))
        self.refresh_player_market_profiles(player_ids_to_refresh)
        return stats

    def upsert_injury_statuses(self, records: list[InjuryStatusUpsert]) -> MutationStats:
        player_lookup = self._provider_lookup(
            Player,
            {(record.provider_name, record.player_provider_external_id) for record in records},
        )
        club_lookup = self._provider_lookup(
            Club,
            {(record.provider_name, record.club_provider_external_id) for record in records if record.club_provider_external_id},
        )
        payloads: list[dict[str, Any]] = []
        stats = MutationStats(records_seen=len(records))
        for record in records:
            player = player_lookup.get((record.provider_name, record.player_provider_external_id))
            if player is None:
                stats.failed_count += 1
                continue
            club = None
            if record.club_provider_external_id:
                club = club_lookup.get((record.provider_name, record.club_provider_external_id))
            payloads.append(
                {
                    "source_provider": record.provider_name,
                    "provider_external_id": record.provider_external_id,
                    "player_id": player.id,
                    "club_id": club.id if club else None,
                    "status": record.status,
                    "detail": record.detail,
                    "expected_return_at": record.expected_return_at,
                }
            )
        stats.merge(self._upsert_models(InjuryStatus, payloads))
        return stats

    def upsert_market_signals(self, records: list[MarketSignalUpsert]) -> MutationStats:
        player_lookup = self._provider_lookup(
            Player,
            {(record.provider_name, record.player_provider_external_id) for record in records},
        )
        payloads: list[dict[str, Any]] = []
        player_ids_to_refresh: set[str] = set()
        stats = MutationStats(records_seen=len(records))
        for record in records:
            player = player_lookup.get((record.provider_name, record.player_provider_external_id))
            if player is None:
                stats.failed_count += 1
                continue
            player_ids_to_refresh.add(player.id)
            payloads.append(
                {
                    "source_provider": record.provider_name,
                    "provider_external_id": record.provider_external_id,
                    "player_id": player.id,
                    "signal_type": record.signal_type,
                    "score": record.score,
                    "as_of": record.as_of,
                    "notes": record.notes,
                }
            )
        stats.merge(self._upsert_models(MarketSignal, payloads))
        self.refresh_player_market_profiles(player_ids_to_refresh)
        return stats

    def get_entity_by_provider_external_id(
        self,
        model: type[ModelT],
        *,
        provider_name: str,
        provider_external_id: str,
    ) -> ModelT | None:
        statement: Select[tuple[ModelT]] = select(model).where(
            getattr(model, "source_provider") == provider_name,
            getattr(model, "provider_external_id") == provider_external_id,
        )
        return self.session.scalar(statement)
