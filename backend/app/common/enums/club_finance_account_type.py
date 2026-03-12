from __future__ import annotations

from enum import StrEnum


class ClubFinanceAccountType(StrEnum):
    OPERATING_BALANCE = "operating_balance"
    SPONSORSHIP_INCOME = "sponsorship_income"
    COMPETITION_INCOME = "competition_income"
    COSMETIC_INCOME = "cosmetic_income"
    ACADEMY_SPEND = "academy_spend"
    SCOUTING_SPEND = "scouting_spend"
    BRANDING_SPEND = "branding_spend"
    FACILITIES_SPEND = "facilities_spend"
    TRANSFER_INCOME = "transfer_income"
    TRANSFER_SPEND = "transfer_spend"


__all__ = ["ClubFinanceAccountType"]
