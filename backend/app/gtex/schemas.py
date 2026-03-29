from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GtexSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HoldingView(GtexSchema):
    shares_owned: Decimal
    reserved_shares: Decimal
    avg_price: Decimal


class JackpotContributionRequest(BaseModel):
    source_type: str
    source_id: str | None = None
    entry_fee: Decimal = Field(gt=0)
    eligibility_score: Decimal = Field(default=Decimal("1.0000"), gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class JackpotContributionView(GtexSchema):
    id: str
    round_id: str
    participant_user_id: str | None
    source_type: str
    source_id: str | None
    entry_fee: Decimal
    contribution_amount: Decimal
    eligibility_score: Decimal
    created_at: datetime


class JackpotPayoutView(GtexSchema):
    id: str
    user_id: str
    rank: int
    payout_amount: Decimal
    payout_ratio: Decimal
    eligibility_weight: Decimal
    created_at: datetime


class JackpotHistoryItemView(GtexSchema):
    id: str
    round_number: int
    status: str
    distribution_mode: str
    trigger_mode: str | None
    current_balance: Decimal
    winning_user_id: str | None
    triggered_at: datetime | None
    settled_at: datetime | None
    payouts: list[JackpotPayoutView] = Field(default_factory=list)


class JackpotStateView(GtexSchema):
    round_id: str
    round_number: int
    status: str
    balance: Decimal
    threshold_amount: Decimal
    probability_limit: Decimal
    probability_cap: Decimal
    contribution_rate: Decimal
    participant_count: int
    failsafe_at: datetime
    distribution_mode: str
    last_winner_user_id: str | None = None
    last_trigger_mode: str | None = None


class CreatorPlayerView(GtexSchema):
    id: str
    subject_key: str
    subject_type: str
    display_name: str
    base_price: Decimal
    current_price: Decimal
    total_shares: int
    available_shares: int
    circulating_shares: int
    demand_score: Decimal
    momentum_score: Decimal
    win_rate: Decimal
    total_matches: int
    total_wins: int
    total_trades: int
    total_volume: Decimal
    holding: HoldingView | None = None


class CreatorTradeRequest(BaseModel):
    player_id: str
    shares: int = Field(ge=1, le=100000)


class CreatorTradeView(GtexSchema):
    id: str
    player_id: str
    side: str
    buyer_id: str | None
    seller_id: str | None
    shares: Decimal
    price: Decimal
    gross_amount: Decimal
    demand_impact: Decimal
    anomaly_flag: bool
    created_at: datetime


class MarketTrendingView(BaseModel):
    items: list[CreatorPlayerView]


class MatchFindRequest(BaseModel):
    league_id: str | None = None
    entry_fee: Decimal | None = Field(default=None, gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MatchFindResponse(BaseModel):
    queue_entry_id: str
    match_id: str | None
    status: str
    league_id: str
    expires_at: datetime


class AiLeagueStandingView(BaseModel):
    subject_key: str
    participant_type: str
    elo: int
    points: int
    matches_played: int
    wins: int
    losses: int
    draws: int
    win_rate: Decimal


class AiLeagueView(BaseModel):
    id: str
    code: str
    name: str
    league_type: str
    min_elo: int
    max_elo: int
    default_entry_fee: Decimal
    leaderboard: list[AiLeagueStandingView] = Field(default_factory=list)


class AiLeaguesView(BaseModel):
    leagues: list[AiLeagueView]


class AiMatchEventView(BaseModel):
    event_index: int
    phase: str
    actor_key: str | None
    event_type: str
    details: dict[str, Any]
    created_at: datetime


class AiMatchView(BaseModel):
    id: str
    league_id: str
    status: str
    home_participant_type: str
    home_user_id: str | None
    home_ai_id: str | None
    away_participant_type: str
    away_user_id: str | None
    away_ai_id: str | None
    entry_fee: Decimal
    effective_pot: Decimal
    jackpot_contribution: Decimal
    home_score: int
    away_score: int
    winner_participant_type: str | None
    winner_user_id: str | None
    winner_ai_id: str | None
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    match_storyline: str | None = None
    key_moments: list[str] = Field(default_factory=list)
    player_highlights: list[dict[str, Any]] = Field(default_factory=list)
    rivalry: dict[str, Any] = Field(default_factory=dict)
    match_context: dict[str, Any] = Field(default_factory=dict)
    home_manager: dict[str, Any] = Field(default_factory=dict)
    away_manager: dict[str, Any] = Field(default_factory=dict)
    commentary: list[str] = Field(default_factory=list)
    broadcast_package: dict[str, Any] = Field(default_factory=dict)
    news_article: dict[str, Any] = Field(default_factory=dict)
    career_summary: dict[str, Any] = Field(default_factory=dict)
    fan_experience: dict[str, Any] = Field(default_factory=dict)
    social_warfare: dict[str, Any] = Field(default_factory=dict)
    real_world_sync: dict[str, Any] = Field(default_factory=dict)
    events: list[AiMatchEventView] = Field(default_factory=list)
