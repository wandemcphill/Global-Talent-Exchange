from __future__ import annotations

from enum import StrEnum


class ReferralEventType(StrEnum):
    SIGNUP_COMPLETED = "signup_completed"
    VERIFICATION_COMPLETED = "verification_completed"
    WALLET_FUNDED = "wallet_funded"
    FIRST_COMPETITION_JOINED = "first_competition_joined"
    FIRST_PAID_COMPETITION_JOINED = "first_paid_competition_joined"
    FIRST_CREATOR_COMPETITION_JOINED = "first_creator_competition_joined"
    RETAINED_DAY_7 = "retained_day_7"
    RETAINED_DAY_30 = "retained_day_30"
    FIRST_TRADE = "first_trade"
