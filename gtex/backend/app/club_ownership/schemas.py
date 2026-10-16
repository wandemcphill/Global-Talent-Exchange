from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from app.common.schemas.base import CommonSchema


class ClubTokenView(CommonSchema):
    club_id: str
    total_supply: int = Field(ge=0)
    circulating_supply: int = Field(ge=0)
    available_supply: int = Field(ge=0)
    holder_count: int = Field(ge=0)
    price: Decimal = Field(ge=Decimal("0.0000"))
    governance_enabled: bool
    performance_score: Decimal
    win_rate: Decimal
    fan_demand_score: Decimal
    treasury_balance_snapshot: Decimal
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubHoldingView(CommonSchema):
    user_id: str
    club_id: str
    tokens_owned: int = Field(ge=0)
    avg_price: Decimal
    reward_tokens_earned: int = Field(ge=0)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubTreasuryEntryView(CommonSchema):
    id: str
    reference_key: str
    entry_type: str
    direction: str
    amount_coin: Decimal
    balance_after_coin: Decimal
    summary: str | None = None
    proposal_id: str | None = None
    created_at: datetime
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubDividendDistributionView(CommonSchema):
    id: str
    reference_key: str
    user_id: str
    gross_amount_coin: Decimal
    tokens_snapshot: int = Field(ge=0)
    created_at: datetime
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubTreasuryView(CommonSchema):
    club_id: str
    balance_coin: Decimal
    lifetime_inflow_coin: Decimal
    lifetime_outflow_coin: Decimal
    winnings_pool_coin: Decimal
    sponsorship_pool_coin: Decimal
    entry_fee_pool_coin: Decimal
    reserve_ratio_bps: int = Field(ge=0)
    profit_share_bps: int = Field(ge=0)
    governance_budget_ratio_bps: int = Field(ge=0)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    recent_entries: list[ClubTreasuryEntryView] = Field(default_factory=list)
    recent_dividends: list[ClubDividendDistributionView] = Field(default_factory=list)


class ClubGovernanceStateView(CommonSchema):
    club_id: str
    formation: str
    playstyle: str
    budget_rules_json: dict[str, Any] = Field(default_factory=dict)
    transfer_policy_json: dict[str, Any] = Field(default_factory=dict)
    fan_mandate_summary: str | None = None
    active_proposal_id: str | None = None
    last_executed_proposal_id: str | None = None
    last_executed_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubGovernanceProposalView(CommonSchema):
    id: str
    club_id: str | None = None
    proposer_user_id: str
    scope: str
    status: str
    title: str
    summary: str
    category: str
    voting_starts_at_iso: str | None = None
    voting_ends_at_iso: str | None = None
    minimum_tokens_required: int = Field(ge=0)
    quorum_token_weight: int = Field(ge=0)
    yes_weight: int = Field(ge=0)
    no_weight: int = Field(ge=0)
    abstain_weight: int = Field(ge=0)
    unique_voter_count: int = Field(ge=0)
    result_summary: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubGovernanceVoteView(CommonSchema):
    id: str
    proposal_id: str
    voter_user_id: str
    club_id: str | None = None
    choice: str
    token_weight: int = Field(ge=0)
    influence_weight: int = Field(ge=0)
    comment: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubOwnershipView(CommonSchema):
    club_id: str
    club_name: str
    token: ClubTokenView
    my_holding: ClubHoldingView | None = None
    governance: ClubGovernanceStateView
    treasury: ClubTreasuryView
    proposals: list[ClubGovernanceProposalView] = Field(default_factory=list)


class ClubTokenTradeRequest(CommonSchema):
    quantity: int = Field(gt=0)


class ClubTokenTradeResultView(CommonSchema):
    club_id: str
    direction: str
    quantity: int = Field(gt=0)
    unit_price: Decimal
    gross_amount_coin: Decimal
    token: ClubTokenView
    holding: ClubHoldingView | None = None
    treasury: ClubTreasuryView


class ClubGovernanceProposalRequest(CommonSchema):
    title: str
    summary: str
    proposal_kind: str = "general"
    formation: str | None = None
    playstyle: str | None = None
    budget_rules_json: dict[str, Any] = Field(default_factory=dict)
    transfer_policy_json: dict[str, Any] = Field(default_factory=dict)
    minimum_tokens_required: int = Field(default=1, ge=1)
    quorum_token_weight: int | None = Field(default=None, ge=0)
    voting_ends_at_iso: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubGovernanceVoteRequest(CommonSchema):
    proposal_id: str
    choice: str
    comment: str | None = None


class ClubGovernanceActionView(CommonSchema):
    proposal: ClubGovernanceProposalView
    vote: ClubGovernanceVoteView | None = None
    governance: ClubGovernanceStateView
    executed: bool = False
    execution_summary: str | None = None


class ClubPortfolioHoldingView(CommonSchema):
    """A single club-share position held by a user, valued at the live token price.

    Every derived ratio is ``None`` rather than ``0`` when the denominator is
    genuinely unknown, so the client can state "unknown" instead of implying a
    real zero.
    """

    club_id: str
    club_name: str
    tokens_owned: int = Field(ge=0)
    avg_price_coin: Decimal
    share_price_coin: Decimal
    market_value_coin: Decimal
    cost_basis_coin: Decimal
    unrealized_pl_coin: Decimal
    unrealized_pl_pct: float | None = None
    reward_tokens_earned: int = Field(ge=0)
    holder_count: int = Field(ge=0)
    circulating_supply: int = Field(ge=0)
    total_supply: int = Field(ge=0)
    ownership_pct: float | None = None
    performance_score: Decimal
    win_rate: Decimal
    fan_demand_score: Decimal
    treasury_balance_coin: Decimal
    governance_enabled: bool
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubPortfolioView(CommonSchema):
    club_count: int = Field(ge=0)
    total_market_value_coin: Decimal
    total_cost_basis_coin: Decimal
    total_unrealized_pl_coin: Decimal
    holdings: list[ClubPortfolioHoldingView] = Field(default_factory=list)
