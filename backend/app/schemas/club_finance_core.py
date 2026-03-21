from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.common.enums.club_finance_account_type import ClubFinanceAccountType
from app.common.enums.club_finance_entry_type import ClubFinanceEntryType
from app.common.schemas.base import CommonSchema


class ClubFinanceAccountView(CommonSchema):
    id: str
    club_id: str
    account_type: ClubFinanceAccountType
    currency: str
    balance_minor: int
    allow_negative: bool = False
    is_active: bool = True


class ClubFinanceLedgerEntryView(CommonSchema):
    id: str
    transaction_id: str
    club_id: str
    account_type: ClubFinanceAccountType
    entry_type: ClubFinanceEntryType
    amount_minor: int
    currency: str
    description: str | None = None
    reference_id: str | None = None
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClubBudgetSnapshotView(CommonSchema):
    club_id: str
    total_budget_minor: int
    academy_allocation_minor: int
    scouting_allocation_minor: int
    sponsorship_commitment_minor: int
    available_budget_minor: int
    captured_at: datetime


class ClubCashflowSummaryView(CommonSchema):
    club_id: str
    currency: str
    total_income_minor: int
    total_expense_minor: int
    net_cashflow_minor: int
    sponsorship_income_minor: int
    competition_income_minor: int
    academy_spend_minor: int
    scouting_spend_minor: int
    as_of: datetime


__all__ = [
    "ClubBudgetSnapshotView",
    "ClubCashflowSummaryView",
    "ClubFinanceAccountView",
    "ClubFinanceLedgerEntryView",
]
