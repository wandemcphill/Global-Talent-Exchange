from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.common.schemas.base import CommonSchema
from app.leaderboards.models import ResetStrategy, RewardDeliveryStatus, SeasonStatus


class LeaderboardEntryView(CommonSchema):
    board: str
    player_id: str
    display_name: str
    region: str | None = None
    division: str | None = None
    tier: str
    rating: int = Field(ge=0)
    points: int = Field(ge=0)
    matches_played: int = Field(ge=0)
    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    draws: int = Field(ge=0)
    win_rate: float = Field(ge=0.0, le=1.0)
    earnings: Decimal = Decimal("0.0000")
    tournament_entries: int = Field(ge=0)
    tournament_titles: int = Field(ge=0)
    podium_finishes: int = Field(ge=0)
    best_placement: int | None = Field(default=None, ge=1)
    visibility_boost: int = Field(default=0, ge=0)
    exclusive_tournament_access: list[str] = Field(default_factory=list)
    rank: int = Field(ge=1)
    score: float = Field(ge=0.0)
    last_rating_delta: int = 0
    last_active_at: datetime | None = None


class LeaderboardView(CommonSchema):
    season_id: str
    board: str
    limit: int = Field(ge=1)
    generated_at: datetime
    entries: list[LeaderboardEntryView] = Field(default_factory=list)


class PlayerRanksView(CommonSchema):
    season_id: str
    player_id: str
    display_name: str
    region: str | None = None
    division: str | None = None
    tier: str
    rating: int = Field(ge=0)
    points: int = Field(ge=0)
    matches_played: int = Field(ge=0)
    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    draws: int = Field(ge=0)
    win_rate: float = Field(ge=0.0, le=1.0)
    earnings: Decimal = Decimal("0.0000")
    tournament_entries: int = Field(ge=0)
    tournament_titles: int = Field(ge=0)
    podium_finishes: int = Field(ge=0)
    best_placement: int | None = Field(default=None, ge=1)
    visibility_boost: int = Field(default=0, ge=0)
    exclusive_tournament_access: list[str] = Field(default_factory=list)
    last_rating_delta: int = 0
    global_rank: int | None = Field(default=None, ge=1)
    region_rank: int | None = Field(default=None, ge=1)
    division_rank: int | None = Field(default=None, ge=1)
    updated_at: datetime


class SeasonRewardView(CommonSchema):
    season_id: str
    board_key: str
    player_id: str
    display_name: str
    rank_position: int = Field(ge=1)
    title: str | None = None
    coins: Decimal = Decimal("0.0000")
    trophies: int = Field(ge=0)
    badges: list[str] = Field(default_factory=list)
    visibility_boost: int = Field(default=0, ge=0)
    exclusive_tournament_key: str | None = None
    status: RewardDeliveryStatus
    distributed_at: datetime | None = None


class RankTierView(CommonSchema):
    key: str
    label: str
    min_rating: int = Field(ge=0)


class SeasonRewardTierView(CommonSchema):
    rank_position: int = Field(ge=1)
    title: str
    coins: Decimal = Decimal("0.0000")
    trophies: int = Field(ge=0)
    badges: list[str] = Field(default_factory=list)
    visibility_boost: int = Field(default=0, ge=0)
    exclusive_tournament_key: str | None = None


class SeasonView(CommonSchema):
    id: str
    start_date: datetime
    end_date: datetime
    status: SeasonStatus
    default_rating: int = Field(ge=0)
    k_factor: int = Field(ge=1)
    reset_strategy: ResetStrategy
    soft_reset_factor: float = Field(ge=0.0, le=1.0)
    duration_days: int = Field(default=30, ge=1)
    days_remaining: int = Field(default=0, ge=0)
    rank_tiers: list[RankTierView] = Field(default_factory=list)
    reward_tiers: list[SeasonRewardTierView] = Field(default_factory=list)
    ended_at: datetime | None = None
    rewards_distributed_at: datetime | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)


class SeasonHistoryView(CommonSchema):
    seasons: list[SeasonView] = Field(default_factory=list)


class SeasonLifecycleView(CommonSchema):
    ended_season: SeasonView
    next_season: SeasonView | None = None
    rewards: list[SeasonRewardView] = Field(default_factory=list)
