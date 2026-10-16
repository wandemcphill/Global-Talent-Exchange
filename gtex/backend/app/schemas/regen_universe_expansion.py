from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import Field

from app.common.schemas.base import CommonSchema
from app.core.pagination import PaginationMeta


class RivalryPlayerView(CommonSchema):
    player_id: str
    player_name: str
    club_id: str | None = None
    club_name: str | None = None
    position: str | None = None


class PlayerRivalryView(CommonSchema):
    id: str
    intensity_score: float
    players: list[RivalryPlayerView] = Field(default_factory=list)
    history: dict[str, Any] = Field(default_factory=dict)
    stats_comparison: dict[str, Any] = Field(default_factory=dict)


class StoryChapterView(CommonSchema):
    title: str
    summary: str
    source_keys: list[str] = Field(default_factory=list)


class StoryMomentView(CommonSchema):
    title: str
    event_type: str
    summary: str
    occurred_on: date | None = None
    importance: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class StoryMatchView(CommonSchema):
    match_id: str
    match_date: date | None = None
    competition: str | None = None
    club_name: str | None = None
    opponent_name: str | None = None
    rating: float | None = None
    goals: int = 0
    assists: int = 0
    summary: str


class PlayerStoryView(CommonSchema):
    id: str
    player_id: str
    chapters: list[StoryChapterView] = Field(default_factory=list)
    key_moments: list[StoryMomentView] = Field(default_factory=list)
    rivalries: list[PlayerRivalryView] = Field(default_factory=list)
    timeline_narrative: list[StoryMomentView] = Field(default_factory=list)
    key_matches: list[StoryMatchView] = Field(default_factory=list)
    defining_moments: list[StoryMomentView] = Field(default_factory=list)
    narrative_score: float
    created_at: datetime


class PlayerDNATraitsView(CommonSchema):
    tempo: float
    risk_taking: float
    creativity: float
    discipline: float


class PlayerDNAView(CommonSchema):
    player_id: str
    archetype: str
    traits: PlayerDNATraitsView
    evolution: list[dict[str, Any]] = Field(default_factory=list)


class YouthTournamentParticipantView(CommonSchema):
    team_id: str
    team_name: str
    source: str
    player_count: int
    average_age: float | None = None
    average_rating: float | None = None
    player_ids: list[str] = Field(default_factory=list)


class YouthTournamentFixtureView(CommonSchema):
    match_id: str
    stage: str
    group: str | None = None
    home_team_id: str
    home_team_name: str
    away_team_id: str
    away_team_name: str
    home_score: int
    away_score: int
    winner_team_id: str | None = None
    top_performers: list[dict[str, Any]] = Field(default_factory=list)


class YouthTournamentStandingView(CommonSchema):
    team_id: str
    team_name: str
    group: str | None = None
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_difference: int = 0
    points: int = 0


class YouthTournamentTopPlayerView(CommonSchema):
    player_id: str
    player_name: str
    team_id: str
    team_name: str
    source_type: str
    goals: int = 0
    assists: int = 0
    average_rating: float = 0.0
    award: str | None = None


class YouthTournamentView(CommonSchema):
    id: str
    name: str
    age_limit: str
    participants: list[YouthTournamentParticipantView] = Field(default_factory=list)
    rewards: dict[str, Any] = Field(default_factory=dict)
    start_date: date
    end_date: date
    fixtures: list[YouthTournamentFixtureView] = Field(default_factory=list)
    standings: list[YouthTournamentStandingView] = Field(default_factory=list)
    top_players: list[YouthTournamentTopPlayerView] = Field(default_factory=list)
    status: str


class YouthTournamentPageView(CommonSchema):
    items: list[YouthTournamentView] = Field(default_factory=list)
    pagination: PaginationMeta


class YouthTournamentCreateRequest(CommonSchema):
    name: str = Field(min_length=3, max_length=160)
    age_limit: str = Field(min_length=2, max_length=12)
    rewards: dict[str, Any] = Field(default_factory=dict)
    start_date: date
    end_date: date
    participant_club_ids: list[str] = Field(default_factory=list, max_length=16)
    participant_limit: int = Field(default=4, ge=4, le=8)
    simulate_immediately: bool = True


class RegenUniverseJobRunView(CommonSchema):
    job_id: str
    name: str
    status: str
    queued_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    result: dict[str, Any] | None = None


class NationalRegenSeedView(CommonSchema):
    id: str
    seed_key: str
    display_name: str
    image_url: str | None = None
    portrait_url: str | None = None
    face_seed: str | None = None
    age: int | None = None
    age_band: str = "senior"
    country_code: str
    country_name: str
    confederation_code: str | None = None
    seed_type: str
    generation_index: int = 1
    primary_position: str
    secondary_positions: list[str] = Field(default_factory=list)
    current_rating: int
    potential_rating: int
    growth_curve: float = 0.5
    personality_seed: dict[str, Any] = Field(default_factory=dict)
    rarity_tier: str
    status: str
    preseed_batch: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    market_eligible: bool = False
    share_market_eligible: bool = False
    tradable: bool = False
    buyable: bool = False
    transferable: bool = False
    card_mint_eligible: bool = False
    buy_cta_allowed: bool = False
    is_preseeded_national_regen: bool = True
    national_pool_only: bool = True
    admin_trade_enabled: bool = False


class NationalRegenPreseedSummaryView(CommonSchema):
    created: int = 0
    skipped_existing: int = 0
    skipped_disabled_country: int = 0
    failed: int = 0
    failures: list[str] = Field(default_factory=list)


class NationalRegenSeedPageView(CommonSchema):
    items: list[NationalRegenSeedView] = Field(default_factory=list)
    pagination: PaginationMeta
    summary: NationalRegenPreseedSummaryView | None = None


class NationalRegenPreseedRequest(CommonSchema):
    country_codes: list[str] = Field(default_factory=list, max_length=64)
    seeds_per_country: int = Field(default=10, ge=4, le=120)
    age_band: str | None = Field(default=None, max_length=16)
    age_min: int | None = Field(default=None, ge=14, le=30)
    age_max: int | None = Field(default=None, ge=14, le=30)
    include_legendary_regens: bool = True
    preseed_batch: str = Field(default="system_start", min_length=3, max_length=64)


class RegenGenerationTrackingEntryView(CommonSchema):
    bucket: str
    count: int = 0
    peak_rating: int = 0
    achievements: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RegenGenerationTrackingView(CommonSchema):
    total_seeded_players: int = 0
    seed_types: list[RegenGenerationTrackingEntryView] = Field(default_factory=list)
    rarity_breakdown: list[RegenGenerationTrackingEntryView] = Field(default_factory=list)
    country_distribution: list[RegenGenerationTrackingEntryView] = Field(default_factory=list)
    global_peak_rating: int = 0
    tracked_achievements: list[str] = Field(default_factory=list)


class RegenEvolutionResultView(CommonSchema):
    season_id: str
    updated_count: int = 0
    boosted_players: list[str] = Field(default_factory=list)
    rivalry_shifted_players: list[str] = Field(default_factory=list)


__all__ = [
    "NationalRegenPreseedRequest",
    "NationalRegenSeedView",
    "PlayerDNAView",
    "PlayerDNATraitsView",
    "PlayerRivalryView",
    "PlayerStoryView",
    "RegenEvolutionResultView",
    "RegenGenerationTrackingEntryView",
    "RegenGenerationTrackingView",
    "RegenUniverseJobRunView",
    "RivalryPlayerView",
    "StoryChapterView",
    "StoryMatchView",
    "StoryMomentView",
    "YouthTournamentCreateRequest",
    "YouthTournamentFixtureView",
    "YouthTournamentParticipantView",
    "YouthTournamentStandingView",
    "YouthTournamentTopPlayerView",
    "YouthTournamentView",
]
