from __future__ import annotations

from enum import StrEnum


class ClubFinanceEntryType(StrEnum):
    SPONSORSHIP_CREDIT = "sponsorship_credit"
    COMPETITION_REWARD_CREDIT = "competition_reward_credit"
    CATALOG_PURCHASE_DEBIT = "catalog_purchase_debit"
    ACADEMY_PROGRAM_DEBIT = "academy_program_debit"
    SCOUTING_ASSIGNMENT_DEBIT = "scouting_assignment_debit"
    MANUAL_ADMIN_ADJUSTMENT = "manual_admin_adjustment"
    REFUND = "refund"
    RESERVE_HOLD = "reserve_hold"


__all__ = ["ClubFinanceEntryType"]
