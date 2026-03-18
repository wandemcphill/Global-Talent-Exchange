from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from backend.app.common.schemas.base import CommonSchema


class CreatorClubShareMarketIssueRequest(CommonSchema):
    share_price_coin: Decimal = Field(gt=0)
    max_shares_issued: int = Field(ge=1, le=1000000)
    max_shares_per_fan: int | None = Field(default=None, ge=1, le=1000000)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class CreatorClubSharePurchaseRequest(CommonSchema):
    share_count: int = Field(ge=1, le=1000000)


class CreatorClubShareMarketControlUpdateRequest(CommonSchema):
    max_shares_per_club: int = Field(ge=1, le=1000000)
    max_shares_per_fan: int = Field(ge=1, le=1000000)
    shareholder_revenue_share_bps: int = Field(ge=0, le=10000)
    issuance_enabled: bool = True
    purchase_enabled: bool = True
    max_primary_purchase_value_coin: Decimal = Field(default=Decimal("2500.0000"), gt=0)


class CreatorClubShareMarketControlView(CommonSchema):
    id: str
    control_key: str
    max_shares_per_club: int
    max_shares_per_fan: int
    shareholder_revenue_share_bps: int
    issuance_enabled: bool
    purchase_enabled: bool
    max_primary_purchase_value_coin: Decimal
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class CreatorClubShareHoldingView(CommonSchema):
    id: str
    market_id: str
    club_id: str
    user_id: str
    share_count: int
    total_spent_coin: Decimal
    revenue_earned_coin: Decimal
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class CreatorClubShareBenefitView(CommonSchema):
    shareholder: bool
    share_count: int
    has_priority_chat_visibility: bool
    has_early_ticket_access: bool
    has_cosmetic_voting_rights: bool
    tournament_qualification_method: str | None = None
    cosmetic_vote_power: int


class CreatorClubGovernancePolicyView(CommonSchema):
    governance_mode: str
    vote_weight_model: str
    anti_takeover_enabled: bool
    max_holder_bps: int
    owner_approval_threshold_bps: int
    proposal_share_threshold: int
    quorum_share_bps: int
    shareholder_rights_preserved_on_sale: bool


class CreatorClubOwnershipLedgerEntryView(CommonSchema):
    entry_type: str
    entry_reference_id: str
    user_id: str | None = None
    share_delta: int
    ownership_bps: int
    created_at: datetime
    summary: str
    metadata_json: dict[str, object] = Field(default_factory=dict)


class CreatorClubOwnershipLedgerView(CommonSchema):
    current_owner_user_id: str
    total_governance_shares: int
    shareholder_count: int
    circulating_share_count: int
    last_transfer_id: str | None = None
    last_transfer_at: datetime | None = None
    recent_entries: list[CreatorClubOwnershipLedgerEntryView] = Field(default_factory=list)


class CreatorClubShareMarketView(CommonSchema):
    id: str
    club_id: str
    creator_user_id: str
    issued_by_user_id: str
    status: str
    share_price_coin: Decimal
    max_shares_issued: int
    shares_sold: int
    shares_remaining: int
    max_shares_per_fan: int
    creator_controlled_shares: int
    creator_control_bps: int
    shareholder_revenue_share_bps: int
    shareholder_count: int
    total_purchase_volume_coin: Decimal
    total_revenue_distributed_coin: Decimal
    metadata_json: dict[str, object]
    governance_policy: CreatorClubGovernancePolicyView
    ownership_ledger: CreatorClubOwnershipLedgerView
    created_at: datetime
    updated_at: datetime
    viewer_holding: CreatorClubShareHoldingView | None = None
    viewer_benefits: CreatorClubShareBenefitView


class CreatorClubSharePurchaseView(CommonSchema):
    id: str
    market_id: str
    club_id: str
    creator_user_id: str
    user_id: str
    share_count: int
    share_price_coin: Decimal
    total_price_coin: Decimal
    ledger_transaction_id: str | None = None
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class CreatorClubSharePayoutView(CommonSchema):
    id: str
    distribution_id: str
    holding_id: str | None = None
    club_id: str
    user_id: str
    share_count: int
    payout_coin: Decimal
    ownership_bps: int
    ledger_transaction_id: str | None = None
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class CreatorClubShareDistributionView(CommonSchema):
    id: str
    market_id: str
    club_id: str
    creator_user_id: str
    source_type: str
    source_reference_id: str
    season_id: str | None = None
    competition_id: str | None = None
    match_id: str | None = None
    eligible_revenue_coin: Decimal
    shareholder_pool_coin: Decimal
    creator_retained_coin: Decimal
    shareholder_revenue_share_bps: int
    distributed_share_count: int
    recipient_count: int
    status: str
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime
    payouts: list[CreatorClubSharePayoutView] = Field(default_factory=list)
