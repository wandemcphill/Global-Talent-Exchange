from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.common.schemas.base import CommonSchema
from app.core.pagination import PaginationMeta
from app.schemas.regen_core import RegenCardView, RegenProfileView, RegenValueSnapshotView


class RegenSeasonCreateRequest(CommonSchema):
    season_number: int = Field(ge=1)
    start_date: date
    end_date: date
    is_active: bool = True
    source_ingestion_season_ids: list[str] = Field(default_factory=list)


class RegenSeasonCloseRequest(CommonSchema):
    close_date: date | None = None
    start_next_season: bool = True


class RegenPortraitOverrideRequest(CommonSchema):
    portrait_url: str | None = Field(default=None, max_length=255)
    image_data_uri: str | None = None


class RegenPortraitBanRequest(CommonSchema):
    reason: str | None = Field(default=None, max_length=500)


class RegenPortraitAdminView(CommonSchema):
    player_id: str
    face_seed: str | None = None
    face_recipe: dict[str, object] | None = None
    portrait_url: str | None = None
    status: str
    storage_key: str | None = None


class RegenSeasonView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    season_number: int
    start_date: date
    end_date: date
    is_active: bool
    closed_at: datetime | None = None
    source_ingestion_season_ids: list[str] = Field(default_factory=list)


class RegenSeasonPageView(CommonSchema):
    items: list[RegenSeasonView] = Field(default_factory=list)
    pagination: PaginationMeta


class RegenAwardDefinitionView(CommonSchema):
    id: str
    code: str
    name: str
    description: str
    category: str
    ranking_category: str | None = None
    eligibility_rules_json: dict[str, object] = Field(default_factory=dict)
    is_regen_only: bool = True


class RegenAwardWinnerView(CommonSchema):
    id: str
    player_id: str
    player_name: str
    ranking_score: float
    rank: int | None = None
    awarded_at: datetime
    metadata_json: dict[str, object] = Field(default_factory=dict)


class RegenAwardResultView(CommonSchema):
    award: RegenAwardDefinitionView
    season: RegenSeasonView
    winners: list[RegenAwardWinnerView] = Field(default_factory=list)


class RegenAwardResultPageView(CommonSchema):
    items: list[RegenAwardResultView] = Field(default_factory=list)
    pagination: PaginationMeta


class RegenRankingEntryView(CommonSchema):
    id: str
    player_id: str
    player_name: str
    category: str
    score: float
    rank: int
    metadata_json: dict[str, object] = Field(default_factory=dict)


class RegenRankingLeaderboardView(CommonSchema):
    season: RegenSeasonView | None = None
    category: str
    entries: list[RegenRankingEntryView] = Field(default_factory=list)
    pagination: PaginationMeta | None = None


class RegenHallOfFameEntryView(CommonSchema):
    id: str
    player_id: str
    player_name: str
    total_awards: int
    peak_rank: int | None = None
    seasons_active: int
    legacy_score: float
    metadata_json: dict[str, object] = Field(default_factory=dict)


class RegenHallOfFameView(CommonSchema):
    entries: list[RegenHallOfFameEntryView] = Field(default_factory=list)
    pagination: PaginationMeta | None = None


class RegenUniverseCloseResultView(CommonSchema):
    season_id: str
    season_number: int
    performance_records_created: int
    ranking_snapshots_created: int
    award_winners_created: int
    hall_of_fame_entries_tracked: int
    next_season_id: str | None = None
    source_ingestion_season_ids: list[str] = Field(default_factory=list)


class RegenSeasonRankingReferenceView(CommonSchema):
    season_number: int
    rank: int
    score: float


class RegenRecentAwardView(CommonSchema):
    award_code: str
    award_name: str
    season_number: int
    rank: int | None = None
    ranking_score: float


class RegenPlayerPrestigeSummaryView(CommonSchema):
    player_id: str
    total_awards: int
    peak_rank: int | None = None
    seasons_active: int
    legacy_score: float
    current_overall_ranking: RegenSeasonRankingReferenceView | None = None
    latest_overall_ranking: RegenSeasonRankingReferenceView | None = None
    recent_awards: list[RegenRecentAwardView] = Field(default_factory=list)


class RegenAchievementView(CommonSchema):
    id: str
    achievement_key: str
    subject_key: str
    player_id: str
    player_name: str | None = None
    achievement_type: str
    title: str
    description: str
    earned_at: datetime
    metadata_json: dict[str, object] = Field(default_factory=dict)


class RegenAchievementPageView(CommonSchema):
    items: list[RegenAchievementView] = Field(default_factory=list)
    pagination: PaginationMeta | None = None


class RegenStoryEventView(CommonSchema):
    id: str
    event_key: str
    subject_key: str
    player_id: str
    player_name: str | None = None
    event_type: str
    title: str
    summary: str
    occurred_at: datetime
    metadata_json: dict[str, object] = Field(default_factory=dict)


class RegenPlayerTimelineView(CommonSchema):
    player_id: str
    items: list[RegenStoryEventView] = Field(default_factory=list)
    pagination: PaginationMeta | None = None


class RegenLegacySnapshotView(CommonSchema):
    regen_id: str
    player_id: str
    total_matches: int = 0
    goals: int = 0
    assists: int = 0
    trophies: int = 0
    peak_rating: int = 0
    seasons_total: int = 0
    awards_total: int = 0
    legacy_score: float = 0.0
    legacy_tier: str = "standard"
    is_legend: bool = False
    narrative_summary: str | None = None
    career_path: list[dict[str, object]] = Field(default_factory=list)


class RegenUniversePlayerShowcaseView(CommonSchema):
    player_id: str
    profile: RegenProfileView
    card: RegenCardView
    prestige: RegenPlayerPrestigeSummaryView | None = None
    legacy: RegenLegacySnapshotView | None = None
    latest_value: RegenValueSnapshotView | None = None
    discovery_badges: list[str] = Field(default_factory=list)
    timeline: list[RegenStoryEventView] = Field(default_factory=list)
    achievements: list[RegenAchievementView] = Field(default_factory=list)


class RegenPlayerMarketAccessView(CommonSchema):
    market_eligible: bool = True
    share_market_eligible: bool = True
    tradable: bool = True
    buyable: bool = True
    transferable: bool = True
    card_mint_eligible: bool = True
    buy_cta_allowed: bool = True
    is_preseeded_national_regen: bool = False
    national_pool_only: bool = False


class RegenPlayerView(CommonSchema):
    id: str
    name: str
    image_url: str | None = None
    portrait_url: str | None = None
    age: int
    nationality: str
    nationality_code: str | None = None
    position: str
    potential: int
    current_rating: int
    growth_curve: float
    club_id: str | None = None
    source_type: str = "regen"
    market_access: RegenPlayerMarketAccessView = Field(default_factory=RegenPlayerMarketAccessView)


class RegenUniversePlayerLookupView(CommonSchema):
    player: RegenPlayerView
    profile: RegenProfileView
    card: RegenCardView
    scouting_note: str | None = None
    discovery_badges: list[str] = Field(default_factory=list)
    market_value_coin: int | None = None
    prestige: RegenPlayerPrestigeSummaryView | None = None
    timeline: list[RegenStoryEventView] = Field(default_factory=list)
    achievements: list[RegenAchievementView] = Field(default_factory=list)


class RegenRisingStarEntryView(CommonSchema):
    player_id: str
    player: RegenPlayerView | None = None
    profile: RegenProfileView
    card: RegenCardView
    legacy_score: float = 0.0
    market_value_coin: int | None = None
    momentum_label: str


class RegenRisingStarsView(CommonSchema):
    entries: list[RegenRisingStarEntryView] = Field(default_factory=list)
    pagination: PaginationMeta | None = None


class RegenBloodlinePlayerView(CommonSchema):
    player_id: str
    regen_id: str
    display_name: str
    regen_type: str
    generation_index: int = 1
    primary_position: str
    current_rating: int
    potential: int
    uniqueness_score: float
    legacy_score: float = 0.0
    story_snippet: str | None = None


class RegenBloodlineChainView(CommonSchema):
    bloodline_key: str
    origin_label: str
    origin_ref_id: str
    origin_type: str
    drift_score: float = 0.0
    entries: list[RegenBloodlinePlayerView] = Field(default_factory=list)


class RegenBloodlinesView(CommonSchema):
    entries: list[RegenBloodlineChainView] = Field(default_factory=list)
    pagination: PaginationMeta | None = None


class RegenScoutingFeedItemView(CommonSchema):
    feed_id: str
    feed_type: str
    player_id: str
    regen_id: str
    player: RegenPlayerView | None = None
    title: str
    summary: str
    occurred_at: datetime
    importance: float = 0.0
    badges: list[str] = Field(default_factory=list)


class RegenScoutingFeedView(CommonSchema):
    items: list[RegenScoutingFeedItemView] = Field(default_factory=list)
    pagination: PaginationMeta | None = None
