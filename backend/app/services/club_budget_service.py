from __future__ import annotations

from functools import lru_cache

from backend.app.schemas.club_finance_core import ClubBudgetSnapshotView
from backend.app.services.club_finance_service import ClubFinanceService, get_club_finance_service


class ClubBudgetService:
    def __init__(self, *, finance_service: ClubFinanceService | None = None) -> None:
        self.finance_service = finance_service or get_club_finance_service()

    def get_budget(self, club_id: str) -> ClubBudgetSnapshotView:
        return self.finance_service.get_budget_snapshot(club_id)


@lru_cache
def get_club_budget_service() -> ClubBudgetService:
    return ClubBudgetService(finance_service=get_club_finance_service())


__all__ = ["ClubBudgetService", "get_club_budget_service"]
