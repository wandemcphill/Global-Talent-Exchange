from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .constants import DEFAULT_PROVIDER_NAME, SYNC_RUN_STATUS_SUCCESS


class IngestionBaseModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True, extra="ignore")


class CountryUpsert(IngestionBaseModel):
    provider_name: str = DEFAULT_PROVIDER_NAME
    provider_external_id: str
    name: str
    alpha2_code: str | None = None
    alpha3_code: str | None = None
    flag_url: str | None = None


class CompetitionUpsert(IngestionBaseModel):
    provider_name: str = DEFAULT_PROVIDER_NAME
    provider_external_id: str
    name: str
    slug: str
    code: str | None = None
    country_provider_external_id: str | None = None
    country_name: str | None = None
    competition_type: str = "league"
    gender: str | None = None
    emblem_url: str | None = None
    is_major: bool = False
    current_season_external_id: str | None = None


class SeasonUpsert(IngestionBaseModel):
    provider_name: str = DEFAULT_PROVIDER_NAME
    provider_external_id: str
    competition_provider_external_id: str
    label: str
    year_start: int | None = None
    year_end: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    current_matchday: int | None = None


class ClubUpsert(IngestionBaseModel):
    provider_name: str = DEFAULT_PROVIDER_NAME
    provider_external_id: str
    name: str
    slug: str
    short_name: str | None = None
    code: str | None = None
    country_provider_external_id: str | None = None
    country_name: str | None = None
    founded_year: int | None = None
    website: str | None = None
    venue: str | None = None
    crest_url: str | None = None


class PlayerUpsert(IngestionBaseModel):
    provider_name: str = DEFAULT_PROVIDER_NAME
    provider_external_id: str
    full_name: str
    first_name: str | None = None
    last_name: str | None = None
    short_name: str | None = None
    country_name: str | None = None
    country_provider_external_id: str | None = None
    current_club_provider_external_id: str | None = None
    position: str | None = None
    normalized_position: str | None = None
    date_of_birth: date | None = None
    height_cm: int | None = None
    weight_kg: int | None = None
    preferred_foot: str | None = None
    shirt_number: int | None = None


class PlayerClubTenureUpsert(IngestionBaseModel):
    provider_name: str = DEFAULT_PROVIDER_NAME
    provider_external_id: str
    player_provider_external_id: str
    club_provider_external_id: str
    season_provider_external_id: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    squad_number: int | None = None
    is_current: bool = True


class MatchUpsert(IngestionBaseModel):
    provider_name: str = DEFAULT_PROVIDER_NAME
    provider_external_id: str
    competition_provider_external_id: str
    season_provider_external_id: str | None = None
    home_club_provider_external_id: str
    away_club_provider_external_id: str
    winner_club_provider_external_id: str | None = None
    venue: str | None = None
    kickoff_at: datetime | None = None
    status: str = "scheduled"
    stage: str | None = None
    matchday: int | None = None
    home_score: int | None = None
    away_score: int | None = None
    last_provider_update_at: datetime | None = None


class TeamStandingUpsert(IngestionBaseModel):
    provider_name: str = DEFAULT_PROVIDER_NAME
    provider_external_id: str
    competition_provider_external_id: str
    season_provider_external_id: str | None = None
    club_provider_external_id: str
    standing_type: str = "total"
    position: int
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_difference: int = 0
    points: int = 0
    form: str | None = None


class PlayerMatchStatUpsert(IngestionBaseModel):
    provider_name: str = DEFAULT_PROVIDER_NAME
    provider_external_id: str
    player_provider_external_id: str
    match_provider_external_id: str
    club_provider_external_id: str | None = None
    competition_provider_external_id: str | None = None
    season_provider_external_id: str | None = None
    appearances: int = 0
    starts: int = 0
    minutes: int | None = None
    goals: int | None = None
    assists: int | None = None
    saves: int | None = None
    clean_sheet: bool | None = None
    rating: float | None = None
    raw_position: str | None = None


class PlayerSeasonStatUpsert(IngestionBaseModel):
    provider_name: str = DEFAULT_PROVIDER_NAME
    provider_external_id: str
    player_provider_external_id: str
    club_provider_external_id: str | None = None
    competition_provider_external_id: str | None = None
    season_provider_external_id: str | None = None
    appearances: int | None = None
    starts: int | None = None
    minutes: int | None = None
    goals: int | None = None
    assists: int | None = None
    yellow_cards: int | None = None
    red_cards: int | None = None
    clean_sheets: int | None = None
    saves: int | None = None
    average_rating: float | None = None


class InjuryStatusUpsert(IngestionBaseModel):
    provider_name: str = DEFAULT_PROVIDER_NAME
    provider_external_id: str
    player_provider_external_id: str
    club_provider_external_id: str | None = None
    status: str
    detail: str | None = None
    expected_return_at: date | None = None


class MarketSignalUpsert(IngestionBaseModel):
    provider_name: str = DEFAULT_PROVIDER_NAME
    provider_external_id: str
    player_provider_external_id: str
    signal_type: str
    score: float
    as_of: datetime
    notes: str | None = None


class RecentUpdate(IngestionBaseModel):
    entity_type: str
    provider_external_id: str
    competition_provider_external_id: str | None = None
    club_provider_external_id: str | None = None
    season_provider_external_id: str | None = None


class RecentUpdateFeed(IngestionBaseModel):
    provider_name: str = DEFAULT_PROVIDER_NAME
    cursor_value: str | None = None
    next_cursor: str | None = None
    updates: list[RecentUpdate] = Field(default_factory=list)


class ProviderHealthSnapshot(IngestionBaseModel):
    provider_name: str
    ok: bool
    detail: str | None = None
    latency_ms: int | None = None
    configured: bool = True


class SyncExecutionSummary(IngestionBaseModel):
    run_id: str
    provider_name: str
    job_name: str
    entity_type: str
    status: str = SYNC_RUN_STATUS_SUCCESS
    duration_ms: int
    records_seen: int = 0
    inserted_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    cursor_value: str | None = None
    error_message: str | None = None


class SyncTriggerRequest(IngestionBaseModel):
    provider_name: str = DEFAULT_PROVIDER_NAME
    competition_external_id: str | None = None
    club_external_id: str | None = None
    player_external_id: str | None = None
    season_external_id: str | None = None
    cursor_key: str = "default"


class SyncRunRead(IngestionBaseModel):
    id: str
    provider_name: str
    job_name: str
    entity_type: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None
    records_seen: int
    inserted_count: int
    updated_count: int
    skipped_count: int
    failed_count: int
    scope_value: str | None = None
    cursor_value: str | None = None
    error_message: str | None = None


class CursorRead(IngestionBaseModel):
    id: str
    provider_name: str
    entity_type: str
    cursor_key: str
    cursor_value: str | None = None
    checkpoint_at: datetime | None = None
    last_run_id: str | None = None


class SyncStatusRead(IngestionBaseModel):
    provider_name: str
    latest_run: SyncRunRead | None = None
    active_locks: list[str] = Field(default_factory=list)
    cursors: list[CursorRead] = Field(default_factory=list)


class HotCachePayload(IngestionBaseModel):
    payload: dict[str, Any]
    cached_at: datetime
