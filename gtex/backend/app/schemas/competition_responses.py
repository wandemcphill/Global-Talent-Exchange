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
    requires_passcode: bool = False


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
    match_type: str
    type: str
    host_type: str
    competition_type: str = "league"
    creator_id: str
    creator_name: str | None = None
    participant_count: int = Field(ge=0)
    capacity: int = Field(ge=2)
    remaining_slots: int = Field(default=0, ge=0)
    currency: str
    entry_fee: Decimal = Field(ge=0)
    gross_pot: Decimal = Field(default=Decimal("0.0000"), ge=0)
    net_payout_pot: Decimal = Field(default=Decimal("0.0000"), ge=0)
    platform_fee_pct: Decimal = Field(ge=0, le=1)
    host_fee_pct: Decimal = Field(ge=0, le=1)
    platform_fee_amount: Decimal = Field(ge=0)
    host_fee_amount: Decimal = Field(ge=0)
    prize_pool: Decimal = Field(ge=0)
    payout_structure: tuple[PayoutBreakdown, ...]
    rules_summary: str
    join_eligibility: JoinEligibilityView
    dynamic_prize_pool: DynamicPrizePoolView | None = None
    competition_mode: str = "competition"
    prize_mode: str = "entry_funded"
    payout_mode: str = "winner_takes_all"
    is_ranked: bool = True
    registration_deadline: datetime | None = None
    host_funded_prize_total: Decimal = Field(default=Decimal("0.0000"), ge=0)
    host_funding_required: Decimal = Field(default=Decimal("0.0000"), ge=0)
    host_funding_escrowed: Decimal = Field(default=Decimal("0.0000"), ge=0)
    host_platform_fee: Decimal = Field(default=Decimal("0.0000"), ge=0)
    fixed_prizes: dict[str, Decimal] = Field(default_factory=dict)
    eligibility_rules: dict[str, object] = Field(default_factory=dict)
    ranking_policy: dict[str, object] = Field(default_factory=dict)
    featured: bool = False
    manual_approval_required: bool = False
    online_now: bool = False
    beginner_friendly: bool | None = None
    requires_passcode: bool = False
    scheduled_start_at: datetime | None = None
    special_rules: str | None = None
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
    prize_mode: str = "entry_funded"
    is_ranked: bool = True
    remaining_slots: int = Field(default=0, ge=0)
    host_funded_prize_total: Decimal = Field(default=Decimal("0.0000"), ge=0)
    host_funding_required: Decimal = Field(default=Decimal("0.0000"), ge=0)
    host_funding_escrowed: Decimal = Field(default=Decimal("0.0000"), ge=0)


class CompetitionParticipantView(CommonSchema):
    participant_id: str
    competition_id: str
    user_id: str | None = None
    club_id: str
    club_name: str | None = None
    status: str
    entry_fee_amount: Decimal = Field(ge=0)
    entry_fee_currency: str
    escrow_status: str
    wallet_ledger_id: str | None = None
    joined_at: datetime
    refunded_at: datetime | None = None


class CompetitionParticipantsResponse(CommonSchema):
    competition_id: str
    participants: tuple[CompetitionParticipantView, ...]


class CompetitionPotView(CommonSchema):
    competition_id: str
    currency: str
    participant_count: int = Field(ge=0)
    capacity: int = Field(ge=2)
    remaining_slots: int = Field(ge=0)
    entry_fee: Decimal = Field(ge=0)
    gross_pot: Decimal = Field(ge=0)
    platform_fee_pct: Decimal = Field(ge=0, le=1)
    platform_fee_amount: Decimal = Field(ge=0)
    host_fee_pct: Decimal = Field(ge=0, le=1)
    host_fee_amount: Decimal = Field(ge=0)
    net_payout_pot: Decimal = Field(ge=0)
    prize_mode: str
    payout_mode: str
    fixed_prizes: dict[str, Decimal] = Field(default_factory=dict)
    payout_structure: tuple[PayoutBreakdown, ...]


class ClubCompetitionLeaderboardEntry(CommonSchema):
    rank: int = Field(ge=1)
    club_id: str
    club_name: str
    owner_user_id: str | None = None
    ranking_points: int = Field(ge=0)
    wins: int = Field(ge=0)
    draws: int = Field(ge=0)
    losses: int = Field(ge=0)
    trophies: int = Field(default=0, ge=0)
    recent_form: str = ""
    eligibility_tier: str
    gtex_hosted_eligible: bool


class ClubCompetitionLeaderboardResponse(CommonSchema):
    entries: tuple[ClubCompetitionLeaderboardEntry, ...]


class RandomCompetitionQuoteView(CommonSchema):
    competition_id: str
    competition_name: str
    mode: str
    currency: str
    entry_fee: Decimal = Field(ge=0)
    gross_pot: Decimal = Field(ge=0)
    platform_fee_amount: Decimal = Field(ge=0)
    net_payout_pot: Decimal = Field(ge=0)
    ranked: bool
    starts_at: datetime | None = None
    confirmation_required: bool = True


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
