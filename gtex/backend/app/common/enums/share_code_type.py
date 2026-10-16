from __future__ import annotations

from enum import StrEnum


class ShareCodeType(StrEnum):
    USER_REFERRAL = "user_referral"
    CREATOR_SHARE = "creator_share"
    COMPETITION_INVITE = "competition_invite"
    PROMO_CODE = "promo_code"
