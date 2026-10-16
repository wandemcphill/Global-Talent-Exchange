from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class EconomyGovernorMetricsInput(BaseModel):
    gtex_supply: Decimal = Field(default=Decimal("0.0000"), ge=0)
    fan_supply: Decimal = Field(default=Decimal("0.0000"), ge=0)
    daily_burn: Decimal = Field(default=Decimal("0.0000"), ge=0)
    daily_mint: Decimal = Field(default=Decimal("0.0000"), ge=0)
    avg_user_spend: Decimal = Field(default=Decimal("0.0000"), ge=0)
    inflation_rate: Decimal = Field(default=Decimal("0.0000"))
    treasury_balance: Decimal | None = Field(default=None, ge=0)
    rewards_pool_balance: Decimal | None = Field(default=None, ge=0)
    liquidity_pool_balance: Decimal | None = Field(default=None, ge=0)
    treasury_reward_threshold: Decimal | None = Field(default=None, ge=0)
    whale_concentration: Decimal | None = Field(default=None, ge=0)
    active_users: int | None = Field(default=None, ge=0)
    market_volatility: Decimal | None = Field(default=None, ge=0)


class EconomyGovernorActionView(BaseModel):
    type: str
    value: Decimal | int | str


class EconomyGovernorPolicyUpdate(BaseModel):
    mode: str | None = Field(default=None, pattern="^(auto|manual)$")
    tournament_entry_multiplier: Decimal | None = Field(default=None, ge=0)
    match_view_cost_multiplier: Decimal | None = Field(default=None, ge=0)
    reward_payout_multiplier: Decimal | None = Field(default=None, ge=0)
    free_prize_multiplier: Decimal | None = Field(default=None, ge=0)
    agent_activity_multiplier: Decimal | None = Field(default=None, ge=0)
    price_change_limit: Decimal | None = Field(default=None, ge=0, le=1)
    conversion_bonus_bps: int | None = Field(default=None, ge=0, le=5000)
    burn_bonus_bps: int | None = Field(default=None, ge=0, le=5000)


class EconomyGovernorApplyRequest(BaseModel):
    metrics: EconomyGovernorMetricsInput | None = None
    actions: list[EconomyGovernorActionView] | None = None
    allow_manual_override: bool = True


class EconomyGovernorSnapshotView(BaseModel):
    policy_key: str
    mode: str
    tournament_entry_multiplier: Decimal
    match_view_cost_multiplier: Decimal
    reward_payout_multiplier: Decimal
    free_prize_multiplier: Decimal
    agent_activity_multiplier: Decimal
    price_change_limit: Decimal
    conversion_bonus_bps: int
    burn_bonus_bps: int
    metrics: dict[str, str]
    recommended_actions: list[EconomyGovernorActionView]
    last_evaluated_at: datetime | None = None
    last_applied_at: datetime | None = None
    updated_at: datetime
