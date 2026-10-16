from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, Field

from app.common.schemas.base import CommonSchema


class ShareCodeView(CommonSchema):
    model_config = ConfigDict(from_attributes=True)

    share_code_id: str
    code: str
    share_code_type: str
    owner_user_id: str | None = None
    owner_creator_id: str | None = None
    linked_competition_id: str | None = None
    active: bool
    max_uses: int
    current_uses: int
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    vanity_code: str | None = None
    created_at: datetime
    updated_at: datetime


class AttributionView(CommonSchema):
    model_config = ConfigDict(from_attributes=True)

    attribution_id: str
    referred_user_id: str
    referrer_user_id: str | None = None
    creator_profile_id: str | None = None
    share_code: str
    source_channel: str
    attribution_status: str
    campaign_name: str | None = None
    linked_competition_id: str | None = None
    first_touched_at: datetime
    milestones: list[str] = Field(default_factory=list)


class ShareCodeRedeemResponse(CommonSchema):
    share_code: ShareCodeView
    attribution: AttributionView
    pending_rewards: int


class ReferralRewardView(CommonSchema):
    model_config = ConfigDict(from_attributes=True)

    reward_id: str
    attribution_id: str
    beneficiary_user_id: str | None = None
    beneficiary_creator_id: str | None = None
    reward_type: str
    status: str
    trigger_milestone: str
    amount: Decimal | None = None
    unit: str | None = None
    label: str
    hold_until: datetime | None = None
    review_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class ReferralInviteView(CommonSchema):
    model_config = ConfigDict(from_attributes=True)

    share_code: str
    referred_user_id: str
    source_channel: str
    linked_competition_id: str | None = None
    campaign_name: str | None = None
    attribution_status: str
    milestones: list[str] = Field(default_factory=list)
    first_touched_at: datetime


class ReferralSummaryView(CommonSchema):
    model_config = ConfigDict(from_attributes=True)

    generated_share_codes: int = 0
    total_invites: int = 0
    total_signups: int = 0
    qualified_users: int = 0
    active_participants: int = 0
    pending_rewards: int = 0
    approved_rewards: int = 0
    paid_rewards: int = 0
    blocked_rewards: int = 0
    default_share_code: str | None = None
