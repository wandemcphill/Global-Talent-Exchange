from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field, model_validator

from backend.app.common.enums.referral_event_type import ReferralEventType
from backend.app.common.enums.referral_reward_status import ReferralRewardStatus
from backend.app.common.enums.referral_reward_type import ReferralRewardType
from backend.app.common.enums.referral_source_channel import ReferralSourceChannel
from backend.app.common.schemas.base import CommonSchema

AttributionStatus = Literal["pending", "qualified", "blocked", "superseded"]
RewardBeneficiary = Literal["referred_user", "referrer_user", "creator_profile"]


class ReferralAttributionCore(CommonSchema):
    referred_user_id: str = Field(min_length=1, max_length=36)
    referrer_user_id: str | None = Field(default=None, min_length=1, max_length=36)
    creator_profile_id: str | None = Field(default=None, min_length=1, max_length=36)
    share_code_id: str | None = Field(default=None, min_length=1, max_length=36)
    source_channel: ReferralSourceChannel
    first_touch_at: datetime
    attribution_status: AttributionStatus = "pending"
    campaign_name: str | None = Field(default=None, max_length=120)
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_referral_source(self) -> "ReferralAttributionCore":
        if not any([self.referrer_user_id, self.creator_profile_id, self.share_code_id]):
            raise ValueError("At least one referrer, creator profile, or share code is required.")
        return self


class ReferralEventCore(CommonSchema):
    event_key: str = Field(min_length=1, max_length=96)
    event_type: ReferralEventType
    referred_user_id: str = Field(min_length=1, max_length=36)
    attribution_id: str | None = Field(default=None, min_length=1, max_length=36)
    referrer_user_id: str | None = Field(default=None, min_length=1, max_length=36)
    creator_profile_id: str | None = Field(default=None, min_length=1, max_length=36)
    share_code_id: str | None = Field(default=None, min_length=1, max_length=36)
    source_channel: ReferralSourceChannel
    occurred_at: datetime
    verified: bool = True
    manual_review_requested: bool = False
    fraud_suspected: bool = False
    event_payload: dict[str, Any] = Field(default_factory=dict)


class ReferralRewardPolicy(CommonSchema):
    event_type: ReferralEventType
    reward_type: ReferralRewardType
    beneficiary: RewardBeneficiary
    amount: Decimal | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, min_length=1, max_length=24)
    reference_code: str | None = Field(default=None, min_length=1, max_length=64)
    hold_days: int = Field(default=0, ge=0, le=365)
    require_verified_event: bool = True
    allow_signup_reward: bool = False
    require_manual_review: bool = False
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_reward_shape(self) -> "ReferralRewardPolicy":
        if self.reward_type in {
            ReferralRewardType.WALLET_CREDIT,
            ReferralRewardType.POINTS,
            ReferralRewardType.CREATOR_REVSHARE,
            ReferralRewardType.FEE_DISCOUNT,
        }:
            if self.amount is None or self.unit is None:
                raise ValueError("amount and unit are required for numeric referral rewards")
        if self.reward_type in {ReferralRewardType.BADGE, ReferralRewardType.STARTER_PACK} and self.reference_code is None:
            raise ValueError("reference_code is required for badge and starter pack rewards")
        return self


class ReferralValidationResult(CommonSchema):
    is_valid: bool
    attribution_status: AttributionStatus
    resolved_referrer_user_id: str | None = Field(default=None, min_length=1, max_length=36)
    resolved_creator_profile_id: str | None = Field(default=None, min_length=1, max_length=36)
    reason_codes: tuple[str, ...] = ()


class ReferralRewardComputation(CommonSchema):
    reward_key: str = Field(min_length=1, max_length=128)
    reward_type: ReferralRewardType
    status: ReferralRewardStatus
    beneficiary_user_id: str | None = Field(default=None, min_length=1, max_length=36)
    beneficiary_creator_id: str | None = Field(default=None, min_length=1, max_length=36)
    amount: Decimal | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, min_length=1, max_length=24)
    reference_code: str | None = Field(default=None, min_length=1, max_length=64)
    hold_until: datetime | None = None
    review_reason: str | None = Field(default=None, max_length=255)
    reward_payload: dict[str, Any] = Field(default_factory=dict)


class ReferralRewardLedgerEntryCore(CommonSchema):
    entry_key: str = Field(min_length=1, max_length=128)
    reward_key: str = Field(min_length=1, max_length=128)
    entry_type: str = Field(min_length=1, max_length=32)
    amount: Decimal | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, min_length=1, max_length=24)
    status_after: ReferralRewardStatus
    payload_json: dict[str, Any] = Field(default_factory=dict)


class ReferralRewardEvaluation(CommonSchema):
    attribution_status: AttributionStatus
    blocked_reason_codes: tuple[str, ...] = ()
    rewards: tuple[ReferralRewardComputation, ...] = ()
    ledger_entries: tuple[ReferralRewardLedgerEntryCore, ...] = ()
