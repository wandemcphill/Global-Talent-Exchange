from __future__ import annotations

from functools import lru_cache

from app.schemas.club_finance_core import ClubCashflowSummaryView
from app.services.club_finance_service import ClubFinanceService, get_club_finance_service


class ClubCashflowService:
    def __init__(self, *, finance_service: ClubFinanceService | None = None) -> None:
        self.finance_service = finance_service or get_club_finance_service()

    def get_cashflow(self, club_id: str) -> ClubCashflowSummaryView:
        return self.finance_service.get_cashflow_summary(club_id)


@lru_cache
def get_club_cashflow_service() -> ClubCashflowService:
    return ClubCashflowService(finance_service=get_club_finance_service())


__all__ = ["ClubCashflowService", "get_club_cashflow_service"]
