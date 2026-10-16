from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class FanPredictionRuleView(BaseModel):
    key: str
    label: str
    points: int
    description: str


class FanPredictionScoringView(BaseModel):
    rules: list[FanPredictionRuleView]
    perfect_card_bonus: int
    daily_refill_tokens: int
    season_pass_bonus_tokens_per_pass: int


class FanPredictionFixtureConfigRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    opens_at: datetime | None = None
    locks_at: datetime | None = None
    token_cost: int = Field(default=1, ge=1, le=20)
    promo_pool_fancoin: Decimal = Field(default=Decimal("0.0000"), ge=0)
    badge_code: str | None = Field(default=None, max_length=64)
    max_reward_winners: int = Field(default=3, ge=1, le=20)
    allow_creator_club_segmentation: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class FanPredictionOutcomeOverrideRequest(BaseModel):
    winner_club_id: str | None = Field(default=None, min_length=1, max_length=36)
    first_goal_scorer_player_id: str | None = Field(default=None, min_length=1, max_length=36)
    total_goals: int | None = Field(default=None, ge=0, le=30)
    mvp_player_id: str | None = Field(default=None, min_length=1, max_length=36)
    note: str | None = Field(default=None, max_length=500)
    disburse_rewards: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class FanPredictionSubmissionRequest(BaseModel):
    winner_club_id: str = Field(min_length=1, max_length=36)
    first_goal_scorer_player_id: str = Field(min_length=1, max_length=36)
    total_goals: int = Field(ge=0, le=30)
    mvp_player_id: str = Field(min_length=1, max_length=36)
    fan_segment_club_id: str | None = Field(default=None, min_length=1, max_length=36)
    fan_group_id: str | None = Field(default=None, min_length=1, max_length=36)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class FanPredictionOutcomeView(BaseModel):
    winner_club_id: str | None = None
    first_goal_scorer_player_id: str | None = None
    total_goals: int
    mvp_player_id: str | None = None
    source: str
    settled_by_user_id: str | None = None
    note: str | None = None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class FanPredictionRewardGrantView(BaseModel):
    id: str
    user_id: str
    fixture_id: str | None = None
    submission_id: str | None = None
    club_id: str | None = None
    reward_settlement_id: str | None = None
    leaderboard_scope: str
    reward_type: str
    rank: int | None = None
    week_start: date | None = None
    badge_code: str | None = None
    fancoin_amount: Decimal
    promo_pool_reference: str | None = None
    metadata_json: dict[str, Any]
    created_at: datetime


class FanPredictionSubmissionView(BaseModel):
    id: str
    fixture_id: str
    user_id: str
    fan_segment_club_id: str | None = None
    fan_group_id: str | None = None
    leaderboard_week_start: date
    winner_club_id: str
    first_goal_scorer_player_id: str
    total_goals: int
    mvp_player_id: str
    tokens_spent: int
    status: str
    points_awarded: int
    correct_pick_count: int
    perfect_card: bool
    reward_rank: int | None = None
    settled_at: datetime | None = None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class FanPredictionFixtureView(BaseModel):
    id: str
    match_id: str
    competition_id: str
    season_id: str | None = None
    home_club_id: str
    away_club_id: str
    created_by_user_id: str | None = None
    title: str
    description: str | None = None
    status: str
    opens_at: datetime
    locks_at: datetime
    settled_at: datetime | None = None
    rewards_disbursed_at: datetime | None = None
    token_cost: int
    promo_pool_fancoin: Decimal
    reward_funding_source: str
    badge_code: str | None = None
    max_reward_winners: int
    allow_creator_club_segmentation: bool
    settlement_rule_version: str
    metadata_json: dict[str, Any]
    scoring: FanPredictionScoringView
    outcome: FanPredictionOutcomeView | None = None
    my_submission: FanPredictionSubmissionView | None = None
    reward_grants: list[FanPredictionRewardGrantView] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class FanPredictionTokenLedgerView(BaseModel):
    id: str
    reason: str
    amount: int
    effective_date: date
    season_pass_id: str | None = None
    submission_id: str | None = None
    reference: str | None = None
    note: str | None = None
    metadata_json: dict[str, Any]
    created_at: datetime


class FanPredictionTokenSummaryView(BaseModel):
    available_tokens: int
    daily_refill_tokens: int
    season_pass_bonus_tokens: int
    today_token_grants: int
    latest_effective_date: date | None = None
    ledger: list[FanPredictionTokenLedgerView] = Field(default_factory=list)


class FanPredictionLeaderboardEntryView(BaseModel):
    rank: int
    user_id: str
    username: str
    display_name: str | None = None
    fan_segment_club_id: str | None = None
    total_points: int
    settled_predictions: int
    correct_pick_count: int
    perfect_cards: int


class FanPredictionLeaderboardView(BaseModel):
    scope: str
    week_start: date
    fixture_id: str | None = None
    club_id: str | None = None
    entries: list[FanPredictionLeaderboardEntryView]
