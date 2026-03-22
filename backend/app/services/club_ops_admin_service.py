from __future__ import annotations

from functools import lru_cache

from app.schemas.club_ops_admin import ClubOpsSummaryView, SponsorModerationQueueItemView
from app.services.club_finance_service import ClubFinanceService, ClubOpsStore, get_club_finance_service, get_club_ops_store
from app.services.club_ops_analytics_service import ClubOpsAnalyticsService, get_club_ops_analytics_service


class ClubOpsAdminService:
    def __init__(
        self,
        *,
        store: ClubOpsStore | None = None,
        finance_service: ClubFinanceService | None = None,
        analytics_service: ClubOpsAnalyticsService | None = None,
    ) -> None:
        self.store = store or get_club_ops_store()
        self.finance_service = finance_service or get_club_finance_service()
        self.analytics_service = analytics_service or get_club_ops_analytics_service()

    def ops_summary(self) -> ClubOpsSummaryView:
        sponsorship_analytics = self.analytics_service.sponsorship_analytics()
        academy_analytics = self.analytics_service.academy_analytics()
        scouting_analytics = self.analytics_service.scouting_analytics()
        moderation_queue = self._moderation_queue()
        return ClubOpsSummaryView(
            tracked_club_count=len(self.finance_service.tracked_club_ids()),
            active_contract_count=sponsorship_analytics.active_contract_count,
            pending_sponsor_moderation_count=sponsorship_analytics.pending_moderation_count,
            academy_enrollment_count=academy_analytics.enrollment_count,
            active_scouting_assignment_count=scouting_analytics.active_assignments,
            youth_prospect_count=scouting_analytics.prospect_count,
            top_academies=academy_analytics.top_academies,
            top_scouting_clubs=scouting_analytics.top_scouting_clubs,
            sponsor_moderation_queue=moderation_queue,
        )

    def _moderation_queue(self) -> tuple[SponsorModerationQueueItemView, ...]:
        with self.store.lock:
            contracts = [
                contract
                for club_contracts in self.store.sponsorship_contracts_by_club.values()
                for contract in club_contracts.values()
                if contract.moderation_required and contract.moderation_status == "pending"
            ]
        return tuple(
            SponsorModerationQueueItemView(
                contract_id=contract.id,
                club_id=contract.club_id,
                sponsor_name=contract.sponsor_name,
                asset_type=contract.asset_type.value,
                moderation_status=contract.moderation_status,
            )
            for contract in contracts
        )


@lru_cache
def get_club_ops_admin_service() -> ClubOpsAdminService:
    return ClubOpsAdminService(
        store=get_club_ops_store(),
        finance_service=get_club_finance_service(),
        analytics_service=get_club_ops_analytics_service(),
    )


__all__ = ["ClubOpsAdminService", "get_club_ops_admin_service"]
