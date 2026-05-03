from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CompetitionTemplateView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    template_key: str
    title: str
    description: str
    competition_type: str
    team_type: str
    age_grade: str
    cup_or_league: str
    participants: int
    viewing_mode: str
    gift_rules: dict[str, object] = Field(default_factory=dict)
    seeding_method: str
    is_user_hostable: bool
    entry_fee_fancoin: Decimal
    reward_pool_fancoin: Decimal
    platform_fee_bps: int
    metadata_json: dict[str, object] = Field(default_factory=dict)
    active: bool


class HostedCompetitionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    template_id: str
    host_user_id: str
    title: str
    slug: str
    description: str
    status: str
    visibility: str
    starts_at: datetime | None = None
    lock_at: datetime | None = None
    max_participants: int
    entry_fee_fancoin: Decimal
    reward_pool_fancoin: Decimal
    platform_fee_amount: Decimal
    metadata_json: dict[str, object] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class HostedCompetitionParticipantView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    competition_id: str
    user_id: str
    joined_at: datetime
    entry_fee_fancoin: Decimal
    payout_eligible: bool
    metadata_json: dict[str, object] = Field(default_factory=dict)


class HostedCompetitionInviteView(BaseModel):
    competition_id: str
    invite_id: str
    invited_by_user_id: str
    recipient_user_id: str | None = None
    recipient_email: str | None = None
    status: str
    message: str = ""
    created_at: datetime
    responded_at: datetime | None = None


class HostedCompetitionStandingView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    competition_id: str
    user_id: str
    final_rank: int | None = None
    points: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    payout_amount: Decimal
    metadata_json: dict[str, object] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class HostedCompetitionSettlementView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    competition_id: str
    recipient_user_id: str | None = None
    settlement_type: str
    status: str
    gross_amount: Decimal
    platform_fee_amount: Decimal
    net_amount: Decimal
    ledger_transaction_id: str | None = None
    note: str
    settled_by_user_id: str | None = None
    created_at: datetime
    updated_at: datetime


class HostedCompetitionFinanceView(BaseModel):
    currency: str
    participant_count: int
    entry_fee_fancoin: Decimal
    gross_collected: Decimal
    projected_reward_pool: Decimal
    projected_platform_fee: Decimal
    escrow_balance: Decimal
    settled_prizes: Decimal
    settled_platform_fee: Decimal
    status: str


class HostedCompetitionCreateRequest(BaseModel):
    template_key: str
    title: str
    description: str = ""
    slug: str | None = None
    visibility: str = "public"
    starts_at: datetime | None = None
    lock_at: datetime | None = None
    max_participants: int | None = None
    entry_fee_fancoin: Decimal | None = None
    reward_pool_fancoin: Decimal | None = None
    join_passcode: str | None = Field(default=None, max_length=64)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class AdminHostedCompetitionCreateRequest(HostedCompetitionCreateRequest):
    gtex_hosted: bool = True
    host_user_id: str | None = None


class HostedCompetitionJoinRequest(BaseModel):
    passcode: str | None = Field(default=None, max_length=64)


class HostedCompetitionPlacementRequest(BaseModel):
    user_id: str
    rank: int = Field(ge=1)
    payout_percent: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0.0000"), le=Decimal("100.0000"))


class HostedCompetitionFinalizeRequest(BaseModel):
    placements: list[HostedCompetitionPlacementRequest]
    note: str = ""


class HostedCompetitionInviteCreateRequest(BaseModel):
    recipient_user_ids: list[str] = Field(default_factory=list)
    recipient_emails: list[str] = Field(default_factory=list)
    message: str = Field(default="", max_length=500)


class HostedCompetitionInviteAcceptRequest(BaseModel):
    invite_id: str | None = None


class HostedCompetitionCreateResponse(BaseModel):
    competition: HostedCompetitionView
    template: CompetitionTemplateView
    host_participation_created: bool
    dashboard_summary: str


class HostedCompetitionJoinResponse(BaseModel):
    competition: HostedCompetitionView
    participant: HostedCompetitionParticipantView
    current_participants: int
    dashboard_summary: str


class HostedCompetitionLaunchResponse(BaseModel):
    competition: HostedCompetitionView
    standings: list[HostedCompetitionStandingView]
    dashboard_summary: str


class HostedCompetitionFinalizeResponse(BaseModel):
    competition: HostedCompetitionView
    standings: list[HostedCompetitionStandingView]
    settlements: list[HostedCompetitionSettlementView]
    finance: HostedCompetitionFinanceView
    dashboard_summary: str


class HostedCompetitionInviteCreateResponse(BaseModel):
    competition: HostedCompetitionView
    invites: list[HostedCompetitionInviteView]
    dashboard_summary: str


class HostedCompetitionInviteAcceptResponse(BaseModel):
    competition: HostedCompetitionView
    participant: HostedCompetitionParticipantView
    invite: HostedCompetitionInviteView
    current_participants: int
    dashboard_summary: str


class HostedCompetitionDetailResponse(BaseModel):
    competition: HostedCompetitionView
    template: CompetitionTemplateView
    participants: list[HostedCompetitionParticipantView]
    current_participants: int
    join_open: bool
    invites: list[HostedCompetitionInviteView] = Field(default_factory=list)


class HostedCompetitionListResponse(BaseModel):
    competitions: list[HostedCompetitionView]
