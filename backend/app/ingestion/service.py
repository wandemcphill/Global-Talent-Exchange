from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any

from backend.app.cache.redis_helpers import HotReadCache, NullCacheBackend
from backend.app.ingestion.constants import (
    BOOTSTRAP_ENTITY_TYPE,
    DEFAULT_CURSOR_KEY,
    DEFAULT_PROVIDER_NAME,
    INCREMENTAL_ENTITY_TYPE,
    MATCHES_ENTITY_TYPE,
    PLAYER_MATCH_STATS_ENTITY_TYPE,
    PLAYER_SEASON_STATS_ENTITY_TYPE,
    STANDINGS_ENTITY_TYPE,
    SYNC_RUN_STATUS_FAILED,
    SYNC_RUN_STATUS_PARTIAL,
    SYNC_RUN_STATUS_SUCCESS,
)
from backend.app.ingestion.models import Club, Competition, Match, Player, ProviderSyncRun, Season
from backend.app.ingestion.normalizers import (
    build_player_tenure_payload,
    flatten_standings,
    normalize_club_payload,
    normalize_competition_payload,
    normalize_country_payload,
    normalize_match_payload,
    normalize_player_payload,
    normalize_player_stats_payload,
    normalize_recent_update_feed,
    normalize_season_payload,
    normalize_team_standing_payload,
)
from backend.app.ingestion.repository import IngestionRepository, MutationStats
from backend.app.ingestion.schemas import (
    CursorRead,
    ProviderHealthSnapshot,
    SyncExecutionSummary,
    SyncRunRead,
    SyncStatusRead,
)
from backend.app.providers import ProviderRegistry

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SyncTracker:
    stats: MutationStats = field(default_factory=MutationStats)
    competition_ids: set[str] = field(default_factory=set)
    club_ids: set[str] = field(default_factory=set)
    player_ids: set[str] = field(default_factory=set)

    def merge(self, *, entity: str, stats: MutationStats) -> None:
        self.stats.merge(stats)
        if entity == "competition":
            self.competition_ids.update(stats.touched_ids)
        elif entity == "club":
            self.club_ids.update(stats.touched_ids)
        elif entity == "player":
            self.player_ids.update(stats.touched_ids)


class IngestionService:
    def __init__(
        self,
        session,
        *,
        provider_registry: ProviderRegistry | None = None,
        cache_backend=None,
    ) -> None:
        self.repository = IngestionRepository(session)
        self.provider_registry = provider_registry or ProviderRegistry()
        self.cache = HotReadCache(cache_backend or NullCacheBackend())
        self.logger = logger

    def bootstrap_sync(
        self,
        *,
        provider_name: str = DEFAULT_PROVIDER_NAME,
        competition_external_id: str | None = None,
        season_external_id: str | None = None,
    ) -> SyncExecutionSummary:
        provider = self.provider_registry.create(provider_name)
        run = self.repository.start_sync_run(
            provider_name=provider_name,
            job_name="bootstrap_sync",
            entity_type=BOOTSTRAP_ENTITY_TYPE,
            scope_value=competition_external_id or season_external_id,
        )
        tracker = SyncTracker()
        self._log("ingestion.sync.started", provider_name=provider_name, job_name=run.job_name)
        try:
            self._bootstrap_scope(
                provider,
                run=run,
                tracker=tracker,
                competition_external_id=competition_external_id,
                season_external_id=season_external_id,
            )
            status = self._status_for(tracker.stats)
            self.repository.finish_sync_run(run, stats=tracker.stats, status=status)
            self.cache.invalidate(
                competition_ids=tracker.competition_ids,
                club_ids=tracker.club_ids,
                player_ids=tracker.player_ids,
            )
            self._log("ingestion.sync.completed", provider_name=provider_name, job_name=run.job_name, status=status)
            return self._summary_from_run(run)
        except Exception as exc:
            self.repository.finish_sync_run(run, stats=tracker.stats, status=SYNC_RUN_STATUS_FAILED, error_message=str(exc))
            self._log("ingestion.sync.failed", provider_name=provider_name, job_name=run.job_name, error=str(exc))
            return self._summary_from_run(run)

    def sync_matches(
        self,
        *,
        provider_name: str = DEFAULT_PROVIDER_NAME,
        competition_external_id: str | None = None,
        season_external_id: str | None = None,
    ) -> SyncExecutionSummary:
        provider = self.provider_registry.create(provider_name)
        run = self.repository.start_sync_run(
            provider_name=provider_name,
            job_name="match_sync",
            entity_type=MATCHES_ENTITY_TYPE,
            scope_value=competition_external_id or season_external_id,
        )
        tracker = SyncTracker()
        try:
            self._match_scope(
                provider,
                run=run,
                tracker=tracker,
                competition_external_id=competition_external_id,
                season_external_id=season_external_id,
            )
            status = self._status_for(tracker.stats)
            self.repository.finish_sync_run(run, stats=tracker.stats, status=status)
            self.cache.invalidate(competition_ids=tracker.competition_ids, club_ids=tracker.club_ids)
            return self._summary_from_run(run)
        except Exception as exc:
            self.repository.finish_sync_run(run, stats=tracker.stats, status=SYNC_RUN_STATUS_FAILED, error_message=str(exc))
            return self._summary_from_run(run)

    def sync_standings(
        self,
        *,
        provider_name: str = DEFAULT_PROVIDER_NAME,
        competition_external_id: str | None = None,
        season_external_id: str | None = None,
    ) -> SyncExecutionSummary:
        provider = self.provider_registry.create(provider_name)
        run = self.repository.start_sync_run(
            provider_name=provider_name,
            job_name="standings_sync",
            entity_type=STANDINGS_ENTITY_TYPE,
            scope_value=competition_external_id or season_external_id,
        )
        tracker = SyncTracker()
        try:
            self._standings_scope(
                provider,
                run=run,
                tracker=tracker,
                competition_external_id=competition_external_id,
                season_external_id=season_external_id,
            )
            status = self._status_for(tracker.stats)
            self.repository.finish_sync_run(run, stats=tracker.stats, status=status)
            self.cache.invalidate(competition_ids=tracker.competition_ids)
            return self._summary_from_run(run)
        except Exception as exc:
            self.repository.finish_sync_run(run, stats=tracker.stats, status=SYNC_RUN_STATUS_FAILED, error_message=str(exc))
            return self._summary_from_run(run)

    def sync_player_stats(
        self,
        *,
        provider_name: str = DEFAULT_PROVIDER_NAME,
        competition_external_id: str | None = None,
        club_external_id: str | None = None,
        player_external_id: str | None = None,
        season_external_id: str | None = None,
    ) -> SyncExecutionSummary:
        provider = self.provider_registry.create(provider_name)
        run = self.repository.start_sync_run(
            provider_name=provider_name,
            job_name="player_stats_sync",
            entity_type=PLAYER_SEASON_STATS_ENTITY_TYPE,
            scope_value=player_external_id or club_external_id or competition_external_id,
        )
        tracker = SyncTracker()
        try:
            self._player_stats_scope(
                provider,
                run=run,
                tracker=tracker,
                competition_external_id=competition_external_id,
                club_external_id=club_external_id,
                player_external_id=player_external_id,
                season_external_id=season_external_id,
            )
            status = self._status_for(tracker.stats)
            self.repository.finish_sync_run(run, stats=tracker.stats, status=status)
            self.cache.invalidate(competition_ids=tracker.competition_ids, club_ids=tracker.club_ids, player_ids=tracker.player_ids)
            return self._summary_from_run(run)
        except Exception as exc:
            self.repository.finish_sync_run(run, stats=tracker.stats, status=SYNC_RUN_STATUS_FAILED, error_message=str(exc))
            return self._summary_from_run(run)

    def sync_incremental(
        self,
        *,
        provider_name: str = DEFAULT_PROVIDER_NAME,
        cursor_key: str = DEFAULT_CURSOR_KEY,
    ) -> SyncExecutionSummary:
        provider = self.provider_registry.create(provider_name)
        existing_cursor = self.repository.get_cursor(
            provider_name=provider_name,
            entity_type=INCREMENTAL_ENTITY_TYPE,
            cursor_key=cursor_key,
        )
        run = self.repository.start_sync_run(
            provider_name=provider_name,
            job_name="incremental_sync",
            entity_type=INCREMENTAL_ENTITY_TYPE,
            scope_value=cursor_key,
        )
        tracker = SyncTracker()
        try:
            feed = provider.fetch_recent_updates(existing_cursor.cursor_value if existing_cursor else None)
            if isinstance(feed, dict):
                feed = normalize_recent_update_feed(provider_name, feed)
            tracker.stats.records_seen += len(feed.updates)
            for update in feed.updates:
                if update.entity_type == "competition":
                    self._bootstrap_scope(
                        provider,
                        run=run,
                        tracker=tracker,
                        competition_external_id=update.provider_external_id,
                        season_external_id=update.season_provider_external_id,
                    )
                    self._match_scope(
                        provider,
                        run=run,
                        tracker=tracker,
                        competition_external_id=update.provider_external_id,
                        season_external_id=update.season_provider_external_id,
                    )
                    self._standings_scope(
                        provider,
                        run=run,
                        tracker=tracker,
                        competition_external_id=update.provider_external_id,
                        season_external_id=update.season_provider_external_id,
                    )
                elif update.entity_type == "club":
                    self._player_stats_scope(
                        provider,
                        run=run,
                        tracker=tracker,
                        competition_external_id=update.competition_provider_external_id,
                        club_external_id=update.provider_external_id,
                        player_external_id=None,
                        season_external_id=update.season_provider_external_id,
                    )
                elif update.entity_type == "player":
                    self._player_stats_scope(
                        provider,
                        run=run,
                        tracker=tracker,
                        competition_external_id=update.competition_provider_external_id,
                        club_external_id=update.club_provider_external_id,
                        player_external_id=update.provider_external_id,
                        season_external_id=update.season_provider_external_id,
                    )
            self.repository.save_cursor(
                provider_name=provider_name,
                entity_type=INCREMENTAL_ENTITY_TYPE,
                cursor_key=cursor_key,
                cursor_value=feed.next_cursor or feed.cursor_value,
                last_run_id=run.id,
            )
            status = self._status_for(tracker.stats)
            self.repository.finish_sync_run(
                run,
                stats=tracker.stats,
                status=status,
                cursor_value=feed.next_cursor or feed.cursor_value,
            )
            self.cache.invalidate(competition_ids=tracker.competition_ids, club_ids=tracker.club_ids, player_ids=tracker.player_ids)
            return self._summary_from_run(run)
        except Exception as exc:
            self.repository.finish_sync_run(run, stats=tracker.stats, status=SYNC_RUN_STATUS_FAILED, error_message=str(exc))
            return self._summary_from_run(run)

    def refresh_competition(
        self,
        *,
        provider_name: str = DEFAULT_PROVIDER_NAME,
        competition_external_id: str,
        season_external_id: str | None = None,
    ) -> SyncExecutionSummary:
        summary = self.bootstrap_sync(
            provider_name=provider_name,
            competition_external_id=competition_external_id,
            season_external_id=season_external_id,
        )
        self.sync_matches(
            provider_name=provider_name,
            competition_external_id=competition_external_id,
            season_external_id=season_external_id,
        )
        self.sync_standings(
            provider_name=provider_name,
            competition_external_id=competition_external_id,
            season_external_id=season_external_id,
        )
        self.sync_player_stats(
            provider_name=provider_name,
            competition_external_id=competition_external_id,
            season_external_id=season_external_id,
        )
        return summary

    def refresh_club(
        self,
        *,
        provider_name: str = DEFAULT_PROVIDER_NAME,
        club_external_id: str,
        competition_external_id: str | None = None,
        season_external_id: str | None = None,
    ) -> SyncExecutionSummary:
        return self.sync_player_stats(
            provider_name=provider_name,
            competition_external_id=competition_external_id,
            club_external_id=club_external_id,
            season_external_id=season_external_id,
        )

    def refresh_player(
        self,
        *,
        provider_name: str = DEFAULT_PROVIDER_NAME,
        player_external_id: str,
        club_external_id: str | None = None,
        competition_external_id: str | None = None,
        season_external_id: str | None = None,
    ) -> SyncExecutionSummary:
        return self.sync_player_stats(
            provider_name=provider_name,
            competition_external_id=competition_external_id,
            club_external_id=club_external_id,
            player_external_id=player_external_id,
            season_external_id=season_external_id,
        )

    def list_recent_sync_runs(self, *, provider_name: str | None = None, limit: int = 20) -> list[SyncRunRead]:
        return [SyncRunRead.model_validate(run) for run in self.repository.list_recent_sync_runs(provider_name=provider_name, limit=limit)]

    def get_sync_status(self, *, provider_name: str = DEFAULT_PROVIDER_NAME) -> SyncStatusRead:
        latest_run = self.repository.get_latest_sync_run(provider_name=provider_name)
        cursors = self.repository.list_cursors(provider_name=provider_name)
        return SyncStatusRead(
            provider_name=provider_name,
            latest_run=SyncRunRead.model_validate(latest_run) if latest_run else None,
            active_locks=self.repository.list_active_locks(),
            cursors=[CursorRead.model_validate(cursor) for cursor in cursors],
        )

    def inspect_provider_health(self, *, provider_name: str = DEFAULT_PROVIDER_NAME) -> ProviderHealthSnapshot:
        provider = self.provider_registry.create(provider_name)
        return provider.healthcheck()

    def get_last_cursor(
        self,
        *,
        provider_name: str = DEFAULT_PROVIDER_NAME,
        cursor_key: str = DEFAULT_CURSOR_KEY,
    ) -> CursorRead | None:
        cursor = self.repository.get_cursor(
            provider_name=provider_name,
            entity_type=INCREMENTAL_ENTITY_TYPE,
            cursor_key=cursor_key,
        )
        return CursorRead.model_validate(cursor) if cursor else None

    def _bootstrap_scope(
        self,
        provider,
        *,
        run: ProviderSyncRun,
        tracker: SyncTracker,
        competition_external_id: str | None,
        season_external_id: str | None,
    ) -> None:
        countries_raw = provider.fetch_countries()
        self.repository.store_raw_payloads(provider_name=provider.name, entity_type="country", payloads=countries_raw, sync_run_id=run.id)
        country_stats = self.repository.upsert_countries([normalize_country_payload(provider.name, item) for item in countries_raw])
        tracker.stats.merge(country_stats)

        competitions_raw = provider.fetch_competitions()
        self.repository.store_raw_payloads(provider_name=provider.name, entity_type="competition", payloads=competitions_raw, sync_run_id=run.id)
        competitions = [normalize_competition_payload(provider.name, item) for item in competitions_raw]
        if competition_external_id:
            competitions = [item for item in competitions if item.provider_external_id == competition_external_id]
        competition_stats = self.repository.upsert_competitions(competitions)
        tracker.merge(entity="competition", stats=competition_stats)

        for competition in competitions:
            seasons_raw = provider.fetch_seasons(competition.provider_external_id)
            self.repository.store_raw_payloads(
                provider_name=provider.name,
                entity_type="season",
                payloads=seasons_raw,
                sync_run_id=run.id,
            )
            seasons = [
                normalize_season_payload(provider.name, item, competition_external_id=competition.provider_external_id)
                for item in seasons_raw
            ]
            if season_external_id:
                seasons = [item for item in seasons if item.provider_external_id == season_external_id]
            season_stats = self.repository.upsert_seasons(seasons)
            tracker.stats.merge(season_stats)
            for season in seasons:
                clubs_raw = provider.fetch_clubs(competition.provider_external_id, season.provider_external_id)
                self.repository.store_raw_payloads(
                    provider_name=provider.name,
                    entity_type="club",
                    payloads=clubs_raw,
                    sync_run_id=run.id,
                )
                clubs = [normalize_club_payload(provider.name, item) for item in clubs_raw]
                club_stats = self.repository.upsert_clubs(clubs)
                tracker.merge(entity="club", stats=club_stats)
                for club in clubs:
                    players_raw = provider.fetch_players(club.provider_external_id, season.provider_external_id)
                    self.repository.store_raw_payloads(
                        provider_name=provider.name,
                        entity_type="player",
                        payloads=players_raw,
                        sync_run_id=run.id,
                    )
                    players = [
                        normalize_player_payload(provider.name, item, club_external_id=club.provider_external_id)
                        for item in players_raw
                    ]
                    player_stats = self.repository.upsert_players(players)
                    tracker.merge(entity="player", stats=player_stats)
                    tenure_stats = self.repository.upsert_player_tenures(
                        [
                            build_player_tenure_payload(
                                provider.name,
                                player,
                                club_external_id=club.provider_external_id,
                                season_external_id=season.provider_external_id,
                            )
                            for player in players
                        ]
                    )
                    tracker.stats.merge(tenure_stats)

    def _match_scope(
        self,
        provider,
        *,
        run: ProviderSyncRun,
        tracker: SyncTracker,
        competition_external_id: str | None,
        season_external_id: str | None,
    ) -> None:
        competitions = self._target_competitions(provider, competition_external_id)
        for competition in competitions:
            seasons = self._target_seasons(provider, competition.provider_external_id, season_external_id)
            for season in seasons:
                matches_raw = provider.fetch_matches(competition.provider_external_id, season.provider_external_id)
                self.repository.store_raw_payloads(
                    provider_name=provider.name,
                    entity_type="match",
                    payloads=matches_raw,
                    sync_run_id=run.id,
                )
                match_stats = self.repository.upsert_matches(
                    [
                        normalize_match_payload(
                            provider.name,
                            item,
                            competition_external_id=competition.provider_external_id,
                            season_external_id=season.provider_external_id,
                        )
                        for item in matches_raw
                    ]
                )
                tracker.stats.merge(match_stats)
                persisted_competition = self.repository.get_entity_by_provider_external_id(
                    Competition,
                    provider_name=provider.name,
                    provider_external_id=competition.provider_external_id,
                )
                if persisted_competition is not None:
                    tracker.competition_ids.add(persisted_competition.id)

    def _standings_scope(
        self,
        provider,
        *,
        run: ProviderSyncRun,
        tracker: SyncTracker,
        competition_external_id: str | None,
        season_external_id: str | None,
    ) -> None:
        competitions = self._target_competitions(provider, competition_external_id)
        for competition in competitions:
            seasons = self._target_seasons(provider, competition.provider_external_id, season_external_id)
            for season in seasons:
                standings_raw = provider.fetch_team_standings(competition.provider_external_id, season.provider_external_id)
                self.repository.store_raw_payloads(
                    provider_name=provider.name,
                    entity_type="team_standing",
                    payloads=[standings_raw],
                    sync_run_id=run.id,
                )
                normalized_rows = [
                    normalize_team_standing_payload(
                        provider.name,
                        row,
                        competition_external_id=competition.provider_external_id,
                        season_external_id=season.provider_external_id,
                        standing_type=standing_type,
                    )
                    for standing_type, row in flatten_standings(standings_raw)
                ]
                standing_stats = self.repository.upsert_team_standings(normalized_rows)
                tracker.stats.merge(standing_stats)

    def _player_stats_scope(
        self,
        provider,
        *,
        run: ProviderSyncRun,
        tracker: SyncTracker,
        competition_external_id: str | None,
        club_external_id: str | None,
        player_external_id: str | None,
        season_external_id: str | None,
    ) -> None:
        if player_external_id:
            self._sync_single_player_stats(
                provider,
                run=run,
                tracker=tracker,
                player_external_id=player_external_id,
                club_external_id=club_external_id,
                competition_external_id=competition_external_id,
                season_external_id=season_external_id,
            )
            return
        if club_external_id:
            players_raw = provider.fetch_players(club_external_id, season_external_id)
            self.repository.store_raw_payloads(
                provider_name=provider.name,
                entity_type="player",
                payloads=players_raw,
                sync_run_id=run.id,
            )
            players = [normalize_player_payload(provider.name, item, club_external_id=club_external_id) for item in players_raw]
            player_stats = self.repository.upsert_players(players)
            tracker.merge(entity="player", stats=player_stats)
            tenure_stats = self.repository.upsert_player_tenures(
                [
                    build_player_tenure_payload(
                        provider.name,
                        player,
                        club_external_id=club_external_id,
                        season_external_id=season_external_id,
                    )
                    for player in players
                ]
            )
            tracker.stats.merge(tenure_stats)
            for player in players:
                self._sync_single_player_stats(
                    provider,
                    run=run,
                    tracker=tracker,
                    player_external_id=player.provider_external_id,
                    club_external_id=club_external_id,
                    competition_external_id=competition_external_id,
                    season_external_id=season_external_id,
                )
            return
        competitions = self._target_competitions(provider, competition_external_id)
        for competition in competitions:
            seasons = self._target_seasons(provider, competition.provider_external_id, season_external_id)
            for season in seasons:
                clubs_raw = provider.fetch_clubs(competition.provider_external_id, season.provider_external_id)
                clubs = [normalize_club_payload(provider.name, item) for item in clubs_raw]
                club_stats = self.repository.upsert_clubs(clubs)
                tracker.merge(entity="club", stats=club_stats)
                for club in clubs:
                    self._player_stats_scope(
                        provider,
                        run=run,
                        tracker=tracker,
                        competition_external_id=competition.provider_external_id,
                        club_external_id=club.provider_external_id,
                        player_external_id=None,
                        season_external_id=season.provider_external_id,
                    )

    def _sync_single_player_stats(
        self,
        provider,
        *,
        run: ProviderSyncRun,
        tracker: SyncTracker,
        player_external_id: str,
        club_external_id: str | None,
        competition_external_id: str | None,
        season_external_id: str | None,
    ) -> None:
        stats_raw = provider.fetch_player_stats(
            player_external_id,
            season_id=season_external_id,
            competition_id=competition_external_id,
            club_id=club_external_id,
        )
        raw_payload = {"playerId": player_external_id, **stats_raw}
        self.repository.store_raw_payloads(
            provider_name=provider.name,
            entity_type="player_stat_bundle",
            payloads=[raw_payload],
            sync_run_id=run.id,
            external_id_key="playerId",
        )
        season_stat, match_stats = normalize_player_stats_payload(
            provider.name,
            stats_raw,
            player_external_id=player_external_id,
            club_external_id=club_external_id,
            competition_external_id=competition_external_id,
            season_external_id=season_external_id,
        )
        if season_stat is not None:
            tracker.stats.merge(self.repository.upsert_player_season_stats([season_stat]))
        if match_stats:
            tracker.stats.merge(self.repository.upsert_player_match_stats(match_stats))
        player = self.repository.get_entity_by_provider_external_id(
            Player,
            provider_name=provider.name,
            provider_external_id=player_external_id,
        )
        if player is not None:
            tracker.player_ids.add(player.id)

    def _target_competitions(self, provider, competition_external_id: str | None) -> list[Any]:
        competitions = [normalize_competition_payload(provider.name, item) for item in provider.fetch_competitions()]
        if competition_external_id:
            competitions = [item for item in competitions if item.provider_external_id == competition_external_id]
        return competitions

    def _target_seasons(self, provider, competition_external_id: str, season_external_id: str | None) -> list[Any]:
        seasons = [
            normalize_season_payload(provider.name, item, competition_external_id=competition_external_id)
            for item in provider.fetch_seasons(competition_external_id)
        ]
        if season_external_id:
            seasons = [item for item in seasons if item.provider_external_id == season_external_id]
        if not seasons:
            return []
        current = [item for item in seasons if item.is_current]
        return current or seasons

    def _status_for(self, stats: MutationStats) -> str:
        if stats.failed_count > 0:
            return SYNC_RUN_STATUS_PARTIAL
        return SYNC_RUN_STATUS_SUCCESS

    def _summary_from_run(self, run: ProviderSyncRun) -> SyncExecutionSummary:
        status = run.status.value if hasattr(run.status, "value") else str(run.status)
        return SyncExecutionSummary(
            run_id=run.id,
            provider_name=run.provider_name,
            job_name=run.job_name,
            entity_type=run.entity_type,
            status=status,
            duration_ms=run.duration_ms or 0,
            records_seen=run.records_seen,
            inserted_count=run.inserted_count,
            updated_count=run.updated_count,
            skipped_count=run.skipped_count,
            failed_count=run.failed_count,
            cursor_value=run.cursor_value,
            error_message=run.error_message,
        )

    def _log(self, event: str, **fields: Any) -> None:
        self.logger.info(event, extra=fields)
