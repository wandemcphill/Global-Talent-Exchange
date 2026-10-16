from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.common.schemas.base import CommonSchema

ShareCodeType = Literal["user_referral", "creator_share", "competition_invite", "promo_code"]
ReferralSourceChannel = Literal[
    "direct_link",
    "direct_share",
    "creator_profile",
    "community_post",
    "community_invite",
    "competition_lobby",
    "competition_page",
    "promo_campaign",
    "manual_entry",
    "dm",
    "qr",
]
ReferralMilestone = Literal[
    "signup_completed",
    "verification_completed",
    "wallet_funded",
    "first_competition_joined",
    "first_paid_competition_joined",
    "first_creator_competition_joined",
    "retained_day_7",
    "retained_day_30",
    "first_trade",
]

_VANITY_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789")


class ShareCodeCreateRequest(CommonSchema):
    share_code_type: ShareCodeType
    vanity_code: str | None = Field(default=None, min_length=4, max_length=20)
    linked_competition_id: str | None = Field(default=None, min_length=1, max_length=36)
    max_uses: int = Field(default=250, ge=1, le=100_000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    use_as_default: bool = False

    @field_validator("vanity_code")
    @classmethod
    def validate_vanity_code(cls, value: str | None) -> str | None:
        if value is None:
            return value
        candidate = value.strip().lower()
        if any(character not in _VANITY_CHARS for character in candidate):
            raise ValueError("Vanity share codes may only contain lowercase letters and numbers.")
        return candidate


class ShareCodeUpdateRequest(CommonSchema):
    active: bool | None = None
    max_uses: int | None = Field(default=None, ge=1, le=100_000)
    linked_competition_id: str | None = Field(default=None, min_length=1, max_length=36)
    ends_at: datetime | None = None
    metadata: dict[str, str] | None = None
    use_as_default: bool | None = None


class ShareCodeRedeemRequest(CommonSchema):
    source_channel: ReferralSourceChannel = "direct_link"
    campaign_name: str | None = Field(default=None, max_length=120)
    linked_competition_id: str | None = Field(default=None, min_length=1, max_length=36)
    metadata: dict[str, str] = Field(default_factory=dict)


class AttributionCaptureRequest(CommonSchema):
    share_code: str | None = Field(default=None, min_length=4, max_length=32)
    source_channel: ReferralSourceChannel = "direct_link"
    milestone: ReferralMilestone
    campaign_name: str | None = Field(default=None, max_length=120)
    linked_competition_id: str | None = Field(default=None, min_length=1, max_length=36)
    metadata: dict[str, str] = Field(default_factory=dict)
