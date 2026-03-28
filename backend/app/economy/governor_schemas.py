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


class EconomyGovernorActionView(BaseModel):
    type: str
    value: Decimal | int | str


class EconomyGovernorPolicyUpdate(BaseModel):
    mode: str | None = Field(default=None, pattern="^(auto|manual)$")
    tournament_entry_multiplier: Decimal | None = Field(default=None, ge=0)
    match_view_cost_multiplier: Decimal | None = Field(default=None, ge=0)
    reward_payout_multiplier: Decimal | None = Field(default=None, ge=0)
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
    conversion_bonus_bps: int
    burn_bonus_bps: int
    metrics: dict[str, str]
    recommended_actions: list[EconomyGovernorActionView]
    last_evaluated_at: datetime | None = None
    last_applied_at: datetime | None = None
    updated_at: datetime
