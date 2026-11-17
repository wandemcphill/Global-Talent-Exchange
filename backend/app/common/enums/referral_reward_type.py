from __future__ import annotations

from enum import StrEnum


class ReferralRewardType(StrEnum):
    WALLET_CREDIT = "wallet_credit"
    POINTS = "points"
    BADGE = "badge"
    STARTER_PACK = "starter_pack"
    CREATOR_REVSHARE = "creator_revshare"
    FEE_DISCOUNT = "fee_discount"
    FIRST_DEPOSIT_BONUS = "first_deposit_bonus"
    FIRST_DEPOSIT_COMMISSION = "first_deposit_commission"
