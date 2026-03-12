from __future__ import annotations

from functools import lru_cache

from backend.app.common.enums.academy_player_status import AcademyPlayerStatus
from backend.app.common.enums.player_pathway_stage import PlayerPathwayStage
from backend.app.common.enums.sponsorship_asset_type import SponsorshipAssetType
from backend.app.common.enums.sponsorship_status import SponsorshipStatus
from backend.app.schemas.club_ops_admin import TopClubMetricView
from backend.app.schemas.club_ops_analytics import (
    ClubAcademyAnalyticsView,
    ClubFinanceAnalyticsView,
    ClubScoutingAnalyticsView,
    ClubSponsorshipAnalyticsView,
)
from backend.app.services.club_finance_service import ClubFinanceService, ClubOpsStore, get_club_finance_service, get_club_ops_store


class ClubOpsAnalyticsService:
    def __init__(
        self,
        *,
        store: ClubOpsStore | None = None,
        finance_service: ClubFinanceService | None = None,
    ) -> None:
        self.store = store or get_club_ops_store()
        self.finance_service = finance_service or get_club_finance_service()

    def finance_analytics(self) -> ClubFinanceAnalyticsView:
        club_ids = self.finance_service.tracked_club_ids()
        budgets = {club_id: self.finance_service.get_budget_snapshot(club_id) for club_id in club_ids}
        cashflows = {club_id: self.finance_service.get_cashflow_summary(club_id) for club_id in club_ids}
        return ClubFinanceAnalyticsView(
            tracked_club_count=len(club_ids),
            total_operating_balance_minor=sum(snapshot.total_budget_minor for snapshot in budgets.values()),
            total_sponsorship_revenue_minor=sum(summary.sponsorship_income_minor for summary in cashflows.values()),
            total_academy_spend_minor=sum(summary.academy_spend_minor for summary in cashflows.values()),
            total_scouting_spend_minor=sum(summary.scouting_spend_minor for summary in cashflows.values()),
            top_budget_clubs=self._top_metric(
                ((club_id, snapshot.available_budget_minor) for club_id, snapshot in budgets.items()),
                label_template="available_budget_minor",
            ),
        )

    def sponsorship_analytics(self) -> ClubSponsorshipAnalyticsView:
        with self.store.lock:
            contracts_by_club = {
                club_id: tuple(contracts.values())
                for club_id, contracts in self.store.sponsorship_contracts_by_club.items()
            }
            assets_by_club = {
                club_id: tuple(assets.values())
                for club_id, assets in self.store.sponsorship_assets_by_club.items()
            }
        all_contracts = [contract for contracts in contracts_by_club.values() for contract in contracts]
        all_assets = [asset for assets in assets_by_club.values() for asset in assets]
        revenue_by_club = {
            club_id: sum(contract.settled_amount_minor for contract in contracts)
            for club_id, contracts in contracts_by_club.items()
        }
        return ClubSponsorshipAnalyticsView(
            active_contract_count=sum(1 for contract in all_contracts if contract.status == SponsorshipStatus.ACTIVE),
            total_contract_value_minor=sum(contract.contract_amount_minor for contract in all_contracts),
            total_settled_revenue_minor=sum(contract.settled_amount_minor for contract in all_contracts),
            pending_moderation_count=sum(
                1 for contract in all_contracts if contract.moderation_required and contract.moderation_status == "pending"
            ),
            utilization_by_asset_type={
                asset_type.value: self._asset_utilization(all_assets, asset_type)
                for asset_type in SponsorshipAssetType
            },
            top_revenue_clubs=self._top_metric(revenue_by_club.items(), label_template="settled_revenue_minor"),
        )

    def academy_analytics(self) -> ClubAcademyAnalyticsView:
        with self.store.lock:
            players_by_club = {
                club_id: tuple(players.values())
                for club_id, players in self.store.academy_players_by_club.items()
            }
        all_players = [player for players in players_by_club.values() for player in players]
        academy_scores = {
            club_id: sum(
                3 if player.status == AcademyPlayerStatus.PROMOTED else 2 if player.status == AcademyPlayerStatus.STANDOUT else 1
                for player in players
            )
            for club_id, players in players_by_club.items()
        }
        return ClubAcademyAnalyticsView(
            tracked_club_count=len(players_by_club),
            enrollment_count=len(
                [player for player in all_players if player.status not in {AcademyPlayerStatus.PROMOTED, AcademyPlayerStatus.RELEASED}]
            ),
            developing_count=sum(1 for player in all_players if player.status == AcademyPlayerStatus.DEVELOPING),
            standout_count=sum(1 for player in all_players if player.status == AcademyPlayerStatus.STANDOUT),
            promoted_count=sum(1 for player in all_players if player.status == AcademyPlayerStatus.PROMOTED),
            released_count=sum(1 for player in all_players if player.status == AcademyPlayerStatus.RELEASED),
            top_academies=self._top_metric(academy_scores.items(), label_template="academy_pathway_score"),
        )

    def scouting_analytics(self) -> ClubScoutingAnalyticsView:
        with self.store.lock:
            assignments_by_club = {
                club_id: tuple(assignments.values())
                for club_id, assignments in self.store.scouting_assignments_by_club.items()
            }
            prospects_by_club = {
                club_id: tuple(prospects.values())
                for club_id, prospects in self.store.prospects_by_club.items()
            }
        all_assignments = [assignment for assignments in assignments_by_club.values() for assignment in assignments]
        all_prospects = [prospect for prospects in prospects_by_club.values() for prospect in prospects]
        pathway_funnel = {
            stage.value: sum(1 for prospect in all_prospects if prospect.pathway_stage == stage)
            for stage in PlayerPathwayStage
        }
        discovered = max(1, pathway_funnel[PlayerPathwayStage.DISCOVERED.value])
        scouting_scores = {
            club_id: sum(
                3 if prospect.pathway_stage == PlayerPathwayStage.PROMOTED else 2 if prospect.pathway_stage == PlayerPathwayStage.ACADEMY_SIGNED else 1
                for prospect in prospects
            )
            for club_id, prospects in prospects_by_club.items()
        }
        return ClubScoutingAnalyticsView(
            tracked_club_count=len(prospects_by_club),
            active_assignments=len(all_assignments),
            prospect_count=len(all_prospects),
            academy_signed_count=pathway_funnel[PlayerPathwayStage.ACADEMY_SIGNED.value],
            promoted_count=pathway_funnel[PlayerPathwayStage.PROMOTED.value],
            academy_conversion_rate_bps=round((pathway_funnel[PlayerPathwayStage.ACADEMY_SIGNED.value] / discovered) * 10_000),
            pathway_funnel=pathway_funnel,
            top_scouting_clubs=self._top_metric(scouting_scores.items(), label_template="pipeline_conversion_score"),
        )

    def _top_metric(self, entries, *, label_template: str) -> tuple[TopClubMetricView, ...]:
        top_entries = sorted(entries, key=lambda item: item[1], reverse=True)[:5]
        return tuple(
            TopClubMetricView(
                club_id=club_id,
                label=label_template,
                value=int(value),
            )
            for club_id, value in top_entries
        )

    def _asset_utilization(self, assets, asset_type: SponsorshipAssetType) -> int:
        matching_assets = [asset for asset in assets if asset.asset_type == asset_type]
        if not matching_assets:
            return 0
        occupied = sum(1 for asset in matching_assets if asset.contract_id is not None)
        return round((occupied / len(matching_assets)) * 100)


@lru_cache
def get_club_ops_analytics_service() -> ClubOpsAnalyticsService:
    return ClubOpsAnalyticsService(
        store=get_club_ops_store(),
        finance_service=get_club_finance_service(),
    )


__all__ = ["ClubOpsAnalyticsService", "get_club_ops_analytics_service"]
