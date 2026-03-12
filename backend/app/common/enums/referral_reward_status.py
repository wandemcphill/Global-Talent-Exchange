from __future__ import annotations

from enum import StrEnum


class ReferralRewardStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    BLOCKED = "blocked"
    REVERSED = "reversed"
    PAID = "paid"
