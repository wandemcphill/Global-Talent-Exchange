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
    currency: str
