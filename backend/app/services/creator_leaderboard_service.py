from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping

from backend.app.schemas.referral_analytics import CreatorLeaderboardEntryView, CreatorLeaderboardResponse
from backend.app.services.referral_analytics_service import ReferralAnalyticsService
from backend.app.services.referral_orchestrator import ReferralOrchestrator, utcnow
from backend.app.services.referral_risk_service import ReferralRiskService

_FOUR_PLACES = Decimal("0.0001")


class CreatorLeaderboardService:
    def __init__(self, orchestrator: ReferralOrchestrator) -> None:
        self.orchestrator = orchestrator
        self.analytics = ReferralAnalyticsService(orchestrator)
        self.risk = ReferralRiskService(orchestrator)

    def build(
        self,
        *,
        net_revenue_contribution: Mapping[str, Decimal] | None = None,
    ) -> CreatorLeaderboardResponse:
        creator_metrics = self.analytics.creator_metrics()
        risk_flags = self.risk.scan()
        penalties_by_creator: dict[str, Decimal] = {}

        for flag in risk_flags:
            if flag.entity_type == "creator_profile":
                penalties_by_creator[flag.entity_id] = penalties_by_creator.get(flag.entity_id, Decimal("0")) + self._penalty(flag.severity)

        share_code_owner: dict[str, str] = {}
        for metric in self.analytics.share_code_metrics().values():
            if metric.owner_creator_id is not None:
                share_code_owner[metric.share_code_id] = metric.owner_creator_id

        for flag in risk_flags:
            if flag.entity_type != "share_code":
                continue
            owner_creator_id = share_code_owner.get(flag.entity_id)
            if owner_creator_id is None:
                continue
            penalties_by_creator[owner_creator_id] = penalties_by_creator.get(owner_creator_id, Decimal("0")) + self._penalty(flag.severity)

        entries: list[CreatorLeaderboardEntryView] = []
        revenue_hooks = net_revenue_contribution or {}
        for creator_id, metric in creator_metrics.items():
            revenue = revenue_hooks.get(creator_id, Decimal("0"))
            penalty = penalties_by_creator.get(creator_id, Decimal("0"))
            base_score = (
                (Decimal(metric.attributed_signups) * Decimal("1.0"))
                + (Decimal(metric.qualified_participants) * Decimal("2.0"))
                + (Decimal(metric.creator_competition_joins) * Decimal("2.5"))
                + (Decimal(metric.retained_users) * Decimal("3.0"))
                + (revenue * Decimal("0.1"))
            )
            score = (base_score - penalty).quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP)
            entries.append(
                CreatorLeaderboardEntryView(
                    rank=0,
                    creator_id=creator_id,
                    creator_handle=metric.handle,
                    handle=metric.handle,
                    creator_display_name=metric.display_name,
                    display_name=metric.display_name,
                    tier=metric.tier,
                    attributed_signups=metric.attributed_signups,
                    qualified_participants=metric.qualified_participants,
                    creator_competition_joins=metric.creator_competition_joins,
                    retained_users=metric.retained_users,
                    net_revenue_contribution=revenue.quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP),
                    fraud_adjusted_score=score,
                    score=score,
                    risk_penalty=penalty.quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP),
                    headline=self._headline(metric.attributed_signups, metric.qualified_participants, metric.retained_users),
                    total_signups=metric.attributed_signups,
                    qualified_joins=metric.qualified_participants,
                    active_participants=metric.creator_competition_joins,
                )
            )

        entries.sort(
            key=lambda item: (
                item.fraud_adjusted_score,
                item.retained_users,
                item.qualified_participants,
                item.attributed_signups,
            ),
            reverse=True,
        )
        ranked = [item.model_copy(update={"rank": index}) for index, item in enumerate(entries, start=1)]
        return CreatorLeaderboardResponse(
            generated_at=utcnow(),
            metric="fraud_adjusted_score",
            items=ranked,
        )

    @staticmethod
    def _penalty(severity: str) -> Decimal:
        return {
            "high": Decimal("6.0"),
            "medium": Decimal("3.0"),
            "low": Decimal("1.0"),
        }.get(severity, Decimal("2.0"))

    @staticmethod
    def _headline(attributed_signups: int, qualified_participants: int, retained_users: int) -> str:
        if retained_users >= qualified_participants and retained_users > 0:
            return "Strongest retained community growth"
        if qualified_participants >= attributed_signups and qualified_participants > 0:
            return "Highest qualified participation"
        if attributed_signups > 0:
            return "Top community builder"
        return "Early creator momentum"
