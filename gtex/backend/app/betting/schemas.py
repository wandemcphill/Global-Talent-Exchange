from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, Field

from app.common.schemas.base import CommonSchema


class BettingProfileView(CommonSchema):
    user_id: str
    region_code: str
    compliance_mode: str
    is_opted_in: bool
    is_enabled: bool
    main_balance: Decimal = Field(default=Decimal("0.0000"))
    bet_balance: Decimal = Field(default=Decimal("0.0000"))
    locked_bet_balance: Decimal = Field(default=Decimal("0.0000"))
    max_bet_amount: Decimal = Field(default=Decimal("0.0000"))
    daily_loss_cap: Decimal = Field(default=Decimal("0.0000"))
    cooldown_until: datetime | None = None
    self_excluded_until: datetime | None = None
    policy_notes: list[str] = Field(default_factory=list)


class BetPreferenceRequest(CommonSchema):
    region_code: str = Field(default="GLOBAL", min_length=2, max_length=32)
    opt_in: bool = True
    is_enabled: bool = True
    age_gate_confirmed: bool = False
    max_bet_amount: Decimal | None = None
    daily_loss_cap: Decimal | None = None


class BetMarketLineView(CommonSchema):
    bet_type: str
    selection_key: str
    label: str
    odds_decimal: Decimal
    implied_probability: Decimal
    market_demand_factor: Decimal
    risk_adjustment_factor: Decimal
    max_stake: Decimal


class BetOddsResponse(CommonSchema):
    match_id: str
    market_status: str
    profile: BettingProfileView
    markets: list[BetMarketLineView] = Field(default_factory=list)
    generated_at: datetime


class BetPlaceRequest(CommonSchema):
    match_id: str
    bet_type: str
    selection_key: str
    stake_amount: Decimal = Field(gt=Decimal("0.0000"))
    region_code: str = Field(default="GLOBAL", min_length=2, max_length=32)
    auto_fund_from_main: bool = True
    opt_in_acknowledged: bool = False
    age_gate_confirmed: bool = False


class BetTicketView(CommonSchema):
    id: str
    user_id: str
    match_id: str
    bet_type: str
    selection_key: str
    selection_label: str
    region_code: str
    status: str
    stake_amount: Decimal
    odds_decimal: Decimal
    implied_probability: Decimal
    potential_payout_amount: Decimal
    settled_amount: Decimal
    result_summary: str | None = None
    placed_at: datetime
    settled_at: datetime | None = None


class BetIntegrityAlertView(CommonSchema):
    model_config = ConfigDict(from_attributes=True)

    id: str
    match_id: str
    bet_id: str | None
    user_id: str | None
    issue_type: str
    risk_level: str
    status: str
    summary: str
    created_at: datetime
    updated_at: datetime


class BetPlaceResponse(CommonSchema):
    ticket: BetTicketView
    profile: BettingProfileView
    alerts: list[BetIntegrityAlertView] = Field(default_factory=list)


class BetHistoryResponse(CommonSchema):
    profile: BettingProfileView
    items: list[BetTicketView] = Field(default_factory=list)
    alerts: list[BetIntegrityAlertView] = Field(default_factory=list)
