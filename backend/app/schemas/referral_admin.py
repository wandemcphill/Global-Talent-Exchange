from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import ConfigDict, Field, field_validator

from app.common.enums.creator_profile_status import CreatorProfileStatus
from app.common.enums.referral_reward_status import ReferralRewardStatus
from app.common.schemas.base import CommonSchema


class AdminShareCodeUpdateRequest(CommonSchema):
    is_active: bool | None = None
    moderation_note: str | None = Field(default=None, max_length=255)


class AdminCreatorProfileUpdateRequest(CommonSchema):
    status: CreatorProfileStatus
    moderation_note: str | None = Field(default=None, max_length=255)
    freeze_pending_rewards: bool = True


class AdminRewardReviewRequest(CommonSchema):
    status: ReferralRewardStatus
    review_reason: str | None = Field(default=None, max_length=255)


class AdminShareCodeView(CommonSchema):
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


class AdminCreatorProfileView(CommonSchema):
    model_config = ConfigDict(from_attributes=True)

    creator_id: str
    user_id: str
    handle: str
    display_name: str
    tier: str
    status: str
    default_share_code_id: str | None = None
    default_share_code: str | None = None
    default_competition_id: str | None = None
    revenue_share_percent: Decimal | None = None
    created_at: datetime
    updated_at: datetime


class AdminAttributionView(CommonSchema):
    model_config = ConfigDict(from_attributes=True)

    attribution_id: str
    referred_user_id: str
    referrer_user_id: str | None = None
    creator_profile_id: str | None = None
    share_code_id: str
    share_code: str
    source_channel: str
    attribution_status: str
    campaign_name: str | None = None
    linked_competition_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    first_touched_at: datetime
    milestones: list[str] = Field(default_factory=list)


class AdminRewardView(CommonSchema):
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


class AdminRewardLedgerView(CommonSchema):
    model_config = ConfigDict(from_attributes=True)

    ledger_entry_id: str
    reward_id: str
    entry_key: str
    entry_type: str
    amount: Decimal | None = None
    unit: str | None = None
    status_after: str
    reference_id: str | None = None
    payload_json: dict[str, str] = Field(default_factory=dict)
    created_at: datetime


ReviewAction = Literal["approve", "block"]


class ReferralFlagView(CommonSchema):
    model_config = ConfigDict(from_attributes=True)

    flag_id: str
    flag_type: str
    severity: str
    entity_type: str
    entity_id: str
    title: str
    description: str
    recommended_action: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    flagged_at: datetime


class ShareCodeModerationRequest(CommonSchema):
    reason: str = Field(min_length=3, max_length=255)
    disable_code: bool = True


class CreatorRewardFreezeRequest(CommonSchema):
    freeze: bool = True
    reason: str = Field(min_length=3, max_length=255)


class RewardReviewRequest(CommonSchema):
    action: ReviewAction
    reason: str | None = Field(default=None, max_length=255)
    reference: str | None = Field(default=None, max_length=64)


class RewardReviewDecisionView(CommonSchema):
    reward_id: str
    action: ReviewAction
    status_after: str
    reason: str | None = None
    reference: str | None = None
    performed_by_admin_id: str
    performed_at: datetime


class ShareCodeUsageSummaryView(CommonSchema):
    code_id: str
    code: str
    share_code_type: str
    owner_user_id: str | None = None
    owner_creator_id: str | None = None
    linked_competition_id: str | None = None
    active: bool
    max_uses: int
    current_uses: int
    usage_share: Decimal = Decimal("0")
    attributed_signups: int = 0
    qualified_referrals: int = 0
    creator_competition_joins: int = 0
    retained_users: int = 0
    reward_cost: Decimal = Decimal("0")
    blocked_rewards: int = 0
    approval_frozen: bool = False
    flagged: bool = False
    flags: list[ReferralFlagView] = Field(default_factory=list)


class AttributionChainEntryView(CommonSchema):
    attribution_id: str
    referred_user_id: str
    referrer_user_id: str | None = None
    creator_profile_id: str | None = None
    share_code_id: str
    share_code: str
    source_channel: str
    attribution_status: str
    campaign_name: str | None = None
    linked_competition_id: str | None = None
    first_touched_at: datetime
    milestones: list[str] = Field(default_factory=list)
    reward_ids: list[str] = Field(default_factory=list)
    reward_statuses: list[str] = Field(default_factory=list)


class PendingRewardView(CommonSchema):
    reward_id: str
    attribution_id: str
    beneficiary_user_id: str | None = None
    beneficiary_creator_id: str | None = None
    beneficiary_name: str | None = None
    beneficiary_email: str | None = None
    payout_method: str | None = None
    payout_destination_reference: str | None = None
    share_code: str | None = None
    deposit_reference: str | None = None
    deposit_amount_fiat: Decimal | None = None
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
    approval_frozen: bool = False


class CreatorAdminSummaryView(CommonSchema):
    creator_id: str
    user_id: str
    handle: str
    display_name: str
    tier: str
    status: str
    default_share_code: str | None = None
    default_competition_id: str | None = None
    share_code_count: int = 0
    attributed_signups: int = 0
    qualified_participants: int = 0
    creator_competition_joins: int = 0
    retained_users: int = 0
    reward_cost: Decimal = Decimal("0")
    pending_rewards: int = 0
    blocked_rewards: int = 0
    approval_frozen: bool = False
    top_share_codes: list[ShareCodeUsageSummaryView] = Field(default_factory=list)
    flags: list[ReferralFlagView] = Field(default_factory=list)


class ReferralAdminDashboardView(CommonSchema):
    total_share_codes: int = 0
    active_share_codes: int = 0
    pending_rewards: int = 0
    blocked_share_codes: int = 0
    frozen_creators: int = 0
    total_flags: int = 0
    high_severity_flags: int = 0
    recent_flags: list[ReferralFlagView] = Field(default_factory=list)


class ReferralPartnerCreateRequest(CommonSchema):
    display_name: str = Field(min_length=2, max_length=120)
    contact_email: str | None = Field(default=None, max_length=320)
    social_handle: str | None = Field(default=None, max_length=120)
    campaign_name: str | None = Field(default=None, max_length=120)
    payout_method: Literal["bank_transfer", "mobile_money", "crypto", "wallet", "manual", "other"] = "bank_transfer"
    payout_destination_reference: str | None = Field(default=None, max_length=128)
    vanity_code: str | None = Field(default=None, min_length=4, max_length=32)
    max_uses: int = Field(default=100000, ge=1, le=1000000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=255)


class ReferralPartnerView(CommonSchema):
    partner_id: str
    display_name: str
    contact_email: str | None = None
    social_handle: str | None = None
    campaign_name: str | None = None
    payout_method: str
    payout_destination_reference: str | None = None
    notes: str | None = None
    is_active: bool
    share_code_id: str | None = None
    share_code: str | None = None
    referral_path: str | None = None
    current_uses: int = 0
    max_uses: int = 0
    attributed_signups: int = 0
    pending_commission: Decimal = Decimal("0.0000")
    approved_commission: Decimal = Decimal("0.0000")
    paid_commission: Decimal = Decimal("0.0000")
    created_at: datetime


class ReferralPartnerStatusRequest(CommonSchema):
    is_active: bool
    reason: str = Field(min_length=3, max_length=255)


class ReferralPayoutBatchRequest(CommonSchema):
    reward_ids: list[str] = Field(min_length=1, max_length=100)
    payment_reference: str = Field(min_length=3, max_length=128)

    @field_validator("reward_ids")
    @classmethod
    def validate_reward_ids(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if not cleaned or len(cleaned) != len(set(cleaned)):
            raise ValueError("Reward IDs must be unique and non-empty.")
        return cleaned


class ReferralPayoutBatchView(CommonSchema):
    payment_reference: str
    reward_count: int
    total_amount: Decimal
    currency: str
    reward_ids: list[str]
    paid_at: datetime
