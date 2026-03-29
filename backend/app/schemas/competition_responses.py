from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.competition_status import CompetitionStatus
from app.common.enums.competition_visibility import CompetitionVisibility
from app.common.schemas.base import CommonSchema


class PayoutBreakdown(CommonSchema):
    place: int = Field(ge=1)
    percent: Decimal = Field(ge=0, le=1)
    amount: Decimal = Field(ge=0)


class CompetitionFeesView(CommonSchema):
    entry_fee: Decimal = Field(ge=0)
    platform_fee_pct: Decimal = Field(ge=0, le=1)
    platform_fee_amount: Decimal = Field(ge=0)
    host_fee_pct: Decimal = Field(ge=0, le=1)
    host_fee_amount: Decimal = Field(ge=0)
    prize_pool: Decimal = Field(ge=0)


class JoinEligibilityView(CommonSchema):
    eligible: bool
    reason: str | None = None
    requires_invite: bool = False


class DynamicPrizePoolView(CommonSchema):
    enabled: bool = False
    base_funding: Decimal = Field(default=Decimal("0.0000"), ge=0)
    activity_boost: Decimal = Field(default=Decimal("0.0000"), ge=0)
    jackpot_rollover: Decimal = Field(default=Decimal("0.0000"), ge=0)
    total_pool: Decimal = Field(default=Decimal("0.0000"), ge=0)
    active_users_5min: int = Field(default=0, ge=0)
    trade_volume_5min: Decimal = Field(default=Decimal("0.0000"), ge=0)


class CompetitionSummaryView(CommonSchema):
    id: str
    name: str
    format: CompetitionFormat
    visibility: CompetitionVisibility
    status: CompetitionStatus
    creator_id: str
    creator_name: str | None = None
    participant_count: int = Field(ge=0)
    capacity: int = Field(ge=2)
    currency: str
    entry_fee: Decimal = Field(ge=0)
    platform_fee_pct: Decimal = Field(ge=0, le=1)
    host_fee_pct: Decimal = Field(ge=0, le=1)
    platform_fee_amount: Decimal = Field(ge=0)
    host_fee_amount: Decimal = Field(ge=0)
    prize_pool: Decimal = Field(ge=0)
    payout_structure: tuple[PayoutBreakdown, ...]
    rules_summary: str
    join_eligibility: JoinEligibilityView
    dynamic_prize_pool: DynamicPrizePoolView | None = None
    beginner_friendly: bool | None = None
    created_at: datetime
    updated_at: datetime


class CompetitionListResponse(CommonSchema):
    total: int = Field(ge=0)
    items: tuple[CompetitionSummaryView, ...]


class CompetitionInviteView(CommonSchema):
    invite_code: str
    issued_by: str
    created_at: datetime
    expires_at: datetime | None = None
    max_uses: int = Field(ge=1)
    uses: int = Field(ge=0)
    note: str | None = None


class CompetitionInvitesResponse(CommonSchema):
    competition_id: str
    invites: tuple[CompetitionInviteView, ...]


class CompetitionFinancialSummaryView(CommonSchema):
    competition_id: str
    participant_count: int = Field(ge=0)
    entry_fee: Decimal = Field(ge=0)
    gross_pool: Decimal = Field(ge=0)
    platform_fee_pct: Decimal = Field(ge=0, le=1)
    platform_fee_amount: Decimal = Field(ge=0)
    host_fee_pct: Decimal = Field(ge=0, le=1)
    host_fee_amount: Decimal = Field(ge=0)
    prize_pool: Decimal = Field(ge=0)
    payout_structure: tuple[PayoutBreakdown, ...]
    dynamic_prize_pool: DynamicPrizePoolView | None = None
    currency: str


class CompetitionRewardView(CommonSchema):
    reward_id: str
    subject_id: str
    resolved_user_id: str | None = None
    display_name: str | None = None
    placement: int | None = None
    amount: Decimal = Field(ge=0)
    currency: str
    status: str
    ledger_transaction_id: str | None = None
    badge_code: str | None = None
    title_awarded: str | None = None
    ranking_points_delta: int = 0


class CompetitionRewardsResponse(CommonSchema):
    competition_id: str
    rewards: tuple[CompetitionRewardView, ...]


class CompetitionHistoryEntryView(CommonSchema):
    competition_id: str
    competition_name: str
    placement: int | None = None
    played: int = Field(ge=0)
    wins: int = Field(ge=0)
    draws: int = Field(ge=0)
    losses: int = Field(ge=0)
    points: int = Field(ge=0)
    earnings: Decimal = Field(ge=0)
    currency: str
    reward_status: str
    ledger_transaction_id: str | None = None
    badge_code: str | None = None
    title_awarded: str | None = None
    ranking_points_delta: int = 0
    completed_at: datetime | None = None


class CompetitionProgressionView(CommonSchema):
    subject_id: str
    resolved_user_id: str | None = None
    display_name: str | None = None
    current_title: str
    ranking_points: int = Field(ge=0)
    total_wins: int = Field(ge=0)
    total_championships: int = Field(ge=0)
    total_podiums: int = Field(ge=0)
    total_competitions: int = Field(ge=0)
    total_earnings: Decimal = Field(ge=0)
    best_placement: int | None = Field(default=None, ge=1)
    badges: tuple[str, ...] = ()
    titles: tuple[str, ...] = ()
    history: tuple[CompetitionHistoryEntryView, ...] = ()
