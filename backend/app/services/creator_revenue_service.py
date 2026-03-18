from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.base import utcnow
from backend.app.models.creator_league import CreatorLeagueConfig
from backend.app.models.creator_monetization import (
    CreatorBroadcastPurchase,
    CreatorMatchGiftEvent,
    CreatorRevenueSettlement,
    CreatorStadiumPlacement,
    CreatorStadiumTicketPurchase,
)
from backend.app.models.creator_share_market import CreatorClubShareDistribution
from backend.app.models.media_engine import MatchView
from backend.app.risk_ops_engine.service import RiskOpsService
from backend.app.services.creator_broadcast_service import CreatorBroadcastService, CreatorMatchContext
from backend.app.services.creator_stadium_service import IN_STADIUM_AD, MATCHDAY_TICKET, SPONSOR_BANNER, VIP_TICKET

AMOUNT_QUANTUM = Decimal("0.0001")
CREATOR_LEAGUE_KEY = "creator_league"
VIEWER_REVENUE_PER_VIEW_COIN = Decimal("0.0500")
VIDEO_VIEWER_CREATOR_SHARE = Decimal("0.6000")


class CreatorRevenueService:
    def __init__(self, session: Session, broadcast_service: CreatorBroadcastService | None = None) -> None:
        self.session = session
        self.broadcast_service = broadcast_service or CreatorBroadcastService(session)

    def build_match_settlement(self, *, match_id: str, actor_user_id: str | None = None) -> CreatorRevenueSettlement:
        context = self.broadcast_service.get_match_context(match_id)
        purchases = list(
            self.session.scalars(
                select(CreatorBroadcastPurchase).where(CreatorBroadcastPurchase.match_id == context.match.id)
            ).all()
        )
        gifts = list(
            self.session.scalars(
                select(CreatorMatchGiftEvent).where(CreatorMatchGiftEvent.match_id == context.match.id)
            ).all()
        )
        stadium_tickets = list(
            self.session.scalars(
                select(CreatorStadiumTicketPurchase).where(CreatorStadiumTicketPurchase.match_id == context.match.id)
            ).all()
        )
        placements = list(
            self.session.scalars(
                select(CreatorStadiumPlacement).where(
                    CreatorStadiumPlacement.match_id == context.match.id,
                    CreatorStadiumPlacement.status == "active",
                )
            ).all()
        )
        video_viewers = int(
            self.session.scalar(
                select(func.count())
                .select_from(MatchView)
                .where(MatchView.match_key == context.match.id)
            )
            or 0
        )

        stadium_ticket_gross = self._sum_decimal(item.price_coin for item in stadium_tickets)
        stadium_ticket_platform = self._sum_decimal(item.platform_share_coin for item in stadium_tickets)
        stadium_ticket_home_creator = self._sum_decimal(
            item.creator_share_coin for item in stadium_tickets if item.club_id == context.match.home_club_id
        )
        stadium_ticket_away_creator = self._sum_decimal(
            item.creator_share_coin for item in stadium_tickets if item.club_id == context.match.away_club_id
        )

        ticket_sales_gross = self._normalize_amount(
            self._sum_decimal(purchase.price_coin for purchase in purchases) + stadium_ticket_gross
        )
        ticket_sales_platform = self._normalize_amount(
            self._sum_decimal(purchase.platform_share_coin for purchase in purchases) + stadium_ticket_platform
        )
        ticket_sales_home_creator = self._normalize_amount(
            self._sum_decimal(purchase.home_creator_share_coin for purchase in purchases) + stadium_ticket_home_creator
        )
        ticket_sales_away_creator = self._normalize_amount(
            self._sum_decimal(purchase.away_creator_share_coin for purchase in purchases) + stadium_ticket_away_creator
        )
        ticket_sales_creator = self._normalize_amount(ticket_sales_home_creator + ticket_sales_away_creator)

        stadium_matchday_revenue = self._sum_decimal(
            item.price_coin for item in stadium_tickets if item.ticket_type == MATCHDAY_TICKET
        )
        stadium_matchday_creator = self._sum_decimal(
            item.creator_share_coin for item in stadium_tickets if item.ticket_type == MATCHDAY_TICKET
        )
        stadium_matchday_platform = self._sum_decimal(
            item.platform_share_coin for item in stadium_tickets if item.ticket_type == MATCHDAY_TICKET
        )
        premium_seating_revenue = self._sum_decimal(
            item.price_coin for item in stadium_tickets if item.ticket_type == VIP_TICKET
        )
        premium_seating_creator = self._sum_decimal(
            item.creator_share_coin for item in stadium_tickets if item.ticket_type == VIP_TICKET
        )
        premium_seating_platform = self._sum_decimal(
            item.platform_share_coin for item in stadium_tickets if item.ticket_type == VIP_TICKET
        )

        viewer_revenue = self._normalize_amount(Decimal(video_viewers) * VIEWER_REVENUE_PER_VIEW_COIN)
        viewer_creator_split = self._split_participant_creator_share(
            context=context,
            creator_total=self._normalize_amount(viewer_revenue * VIDEO_VIEWER_CREATOR_SHARE),
        )
        viewer_home_creator = viewer_creator_split.get(context.match.home_club_id, Decimal("0.0000"))
        viewer_away_creator = viewer_creator_split.get(context.match.away_club_id, Decimal("0.0000"))
        viewer_creator = self._normalize_amount(viewer_home_creator + viewer_away_creator)
        viewer_platform = self._normalize_amount(viewer_revenue - viewer_creator)

        gift_revenue_gross = self._sum_decimal(item.gross_amount_coin for item in gifts)
        gift_platform = self._sum_decimal(item.platform_share_coin for item in gifts)
        gift_home_creator = self._sum_decimal(
            item.creator_share_coin for item in gifts if item.club_id == context.match.home_club_id
        )
        gift_away_creator = self._sum_decimal(
            item.creator_share_coin for item in gifts if item.club_id == context.match.away_club_id
        )
        gift_creator = self._normalize_amount(gift_home_creator + gift_away_creator)

        in_stadium_ads_revenue = self._sum_decimal(
            item.price_coin for item in placements if item.placement_type == IN_STADIUM_AD
        )
        in_stadium_ads_creator = self._sum_decimal(
            item.creator_share_coin for item in placements if item.placement_type == IN_STADIUM_AD
        )
        in_stadium_ads_platform = self._sum_decimal(
            item.platform_share_coin for item in placements if item.placement_type == IN_STADIUM_AD
        )
        sponsor_banner_revenue = self._sum_decimal(
            item.price_coin for item in placements if item.placement_type == SPONSOR_BANNER
        )
        sponsor_banner_creator = self._sum_decimal(
            item.creator_share_coin for item in placements if item.placement_type == SPONSOR_BANNER
        )
        sponsor_banner_platform = self._sum_decimal(
            item.platform_share_coin for item in placements if item.placement_type == SPONSOR_BANNER
        )
        placement_home_creator = self._sum_decimal(
            item.creator_share_coin for item in placements if item.club_id == context.match.home_club_id
        )
        placement_away_creator = self._sum_decimal(
            item.creator_share_coin for item in placements if item.club_id == context.match.away_club_id
        )
        placement_platform = self._normalize_amount(in_stadium_ads_platform + sponsor_banner_platform)

        shareholder_match_video_distribution = self._shareholder_distribution_sum(
            match_id=context.match.id,
            source_type="match_video",
        )
        shareholder_gift_distribution = self._shareholder_distribution_sum(
            match_id=context.match.id,
            source_type="gifts",
        )
        shareholder_ticket_distribution = self._shareholder_distribution_sum(
            match_id=context.match.id,
            source_type="ticket_sales",
        )
        shareholder_total_distribution = self._normalize_amount(
            shareholder_match_video_distribution + shareholder_gift_distribution + shareholder_ticket_distribution
        )

        total_revenue = self._normalize_amount(
            ticket_sales_gross + viewer_revenue + gift_revenue_gross + in_stadium_ads_revenue + sponsor_banner_revenue
        )
        home_creator_total = self._normalize_amount(
            ticket_sales_home_creator + viewer_home_creator + gift_home_creator + placement_home_creator
        )
        away_creator_total = self._normalize_amount(
            ticket_sales_away_creator + viewer_away_creator + gift_away_creator + placement_away_creator
        )
        creator_total = self._normalize_amount(home_creator_total + away_creator_total)
        platform_total = self._normalize_amount(ticket_sales_platform + viewer_platform + gift_platform + placement_platform)

        settlement = self.session.scalar(
            select(CreatorRevenueSettlement).where(CreatorRevenueSettlement.match_id == context.match.id)
        )
        if settlement is None:
            settlement = CreatorRevenueSettlement(
                season_id=context.season.id,
                competition_id=context.competition.id,
                match_id=context.match.id,
                home_club_id=context.match.home_club_id,
                away_club_id=context.match.away_club_id,
            )
            self.session.add(settlement)

        settlement.season_id = context.season.id
        settlement.competition_id = context.competition.id
        settlement.home_club_id = context.match.home_club_id
        settlement.away_club_id = context.match.away_club_id
        settlement.ticket_sales_gross_coin = ticket_sales_gross
        settlement.ticket_sales_creator_share_coin = ticket_sales_creator
        settlement.ticket_sales_platform_share_coin = ticket_sales_platform
        settlement.stadium_matchday_revenue_coin = stadium_matchday_revenue
        settlement.stadium_matchday_creator_share_coin = stadium_matchday_creator
        settlement.stadium_matchday_platform_share_coin = stadium_matchday_platform
        settlement.premium_seating_revenue_coin = premium_seating_revenue
        settlement.premium_seating_creator_share_coin = premium_seating_creator
        settlement.premium_seating_platform_share_coin = premium_seating_platform
        settlement.in_stadium_ads_revenue_coin = in_stadium_ads_revenue
        settlement.in_stadium_ads_creator_share_coin = in_stadium_ads_creator
        settlement.in_stadium_ads_platform_share_coin = in_stadium_ads_platform
        settlement.sponsor_banner_revenue_coin = sponsor_banner_revenue
        settlement.sponsor_banner_creator_share_coin = sponsor_banner_creator
        settlement.sponsor_banner_platform_share_coin = sponsor_banner_platform
        settlement.video_viewer_revenue_coin = viewer_revenue
        settlement.video_viewer_creator_share_coin = viewer_creator
        settlement.video_viewer_platform_share_coin = viewer_platform
        settlement.gift_revenue_gross_coin = gift_revenue_gross
        settlement.gift_creator_share_coin = gift_creator
        settlement.gift_platform_share_coin = gift_platform
        settlement.shareholder_match_video_distribution_coin = shareholder_match_video_distribution
        settlement.shareholder_gift_distribution_coin = shareholder_gift_distribution
        settlement.shareholder_ticket_sales_distribution_coin = shareholder_ticket_distribution
        settlement.shareholder_total_distribution_coin = shareholder_total_distribution
        settlement.total_revenue_coin = total_revenue
        settlement.total_creator_share_coin = creator_total
        settlement.total_platform_share_coin = platform_total
        settlement.home_creator_share_coin = home_creator_total
        settlement.away_creator_share_coin = away_creator_total
        review_status, review_reason_codes, policy_snapshot = self._evaluate_review_status(
            total_revenue_coin=total_revenue,
            total_creator_share_coin=creator_total,
            total_platform_share_coin=platform_total,
            shareholder_total_distribution_coin=shareholder_total_distribution,
        )
        settlement.review_status = review_status
        settlement.review_reason_codes_json = review_reason_codes
        settlement.policy_snapshot_json = policy_snapshot
        if review_status == "review_required":
            settlement.reviewed_by_user_id = None
            settlement.reviewed_at = None
            settlement.review_note = None
        settlement.settled_at = utcnow()
        settlement.metadata_json = {
            "ticket_sales_count": len(purchases) + len(stadium_tickets),
            "stadium_ticket_sales_count": len(stadium_tickets),
            "stadium_matchday_sales_count": sum(1 for item in stadium_tickets if item.ticket_type == MATCHDAY_TICKET),
            "premium_seating_sales_count": sum(1 for item in stadium_tickets if item.ticket_type == VIP_TICKET),
            "video_viewers": video_viewers,
            "viewer_revenue_rate_coin": str(VIEWER_REVENUE_PER_VIEW_COIN),
            "gift_event_count": len(gifts),
            "stadium_placement_count": len(placements),
        }
        RiskOpsService(self.session).log_audit(
            actor_user_id=actor_user_id,
            action_key=f"creator_revenue_settlement.{review_status}",
            resource_type="creator_revenue_settlement",
            resource_id=settlement.id,
            detail=f"Creator League match settlement built with status {review_status}.",
            metadata_json={
                "match_id": context.match.id,
                "season_id": context.season.id,
                "review_reason_codes": review_reason_codes,
                "policy_snapshot": policy_snapshot,
            },
        )
        self.session.flush()
        return settlement

    def _split_participant_creator_share(
        self,
        *,
        context: CreatorMatchContext,
        creator_total: Decimal,
    ) -> dict[str, Decimal]:
        return self.broadcast_service._creator_split(
            creator_total=self._normalize_amount(creator_total),
            home_beneficiary=context.home_beneficiary,
            away_beneficiary=context.away_beneficiary,
        )

    def _shareholder_distribution_sum(self, *, match_id: str, source_type: str) -> Decimal:
        value = self.session.scalar(
            select(func.coalesce(func.sum(CreatorClubShareDistribution.shareholder_pool_coin), 0))
            .where(
                CreatorClubShareDistribution.match_id == match_id,
                CreatorClubShareDistribution.source_type == source_type,
            )
        )
        return self._normalize_amount(value or 0)

    def _evaluate_review_status(
        self,
        *,
        total_revenue_coin: Decimal,
        total_creator_share_coin: Decimal,
        total_platform_share_coin: Decimal,
        shareholder_total_distribution_coin: Decimal,
    ) -> tuple[str, list[str], dict[str, str | bool]]:
        config = self._creator_league_config()
        policy_snapshot = {
            "settlement_review_enabled": True if config is None else bool(config.settlement_review_enabled),
            "settlement_review_total_revenue_coin": str(
                self._policy_decimal(config, "settlement_review_total_revenue_coin", Decimal("250.0000"))
            ),
            "settlement_review_creator_share_coin": str(
                self._policy_decimal(config, "settlement_review_creator_share_coin", Decimal("150.0000"))
            ),
            "settlement_review_platform_share_coin": str(
                self._policy_decimal(config, "settlement_review_platform_share_coin", Decimal("150.0000"))
            ),
            "settlement_review_shareholder_distribution_coin": str(
                self._policy_decimal(config, "settlement_review_shareholder_distribution_coin", Decimal("75.0000"))
            ),
        }
        if not policy_snapshot["settlement_review_enabled"]:
            return "approved", [], policy_snapshot

        review_reason_codes: list[str] = []
        if total_revenue_coin >= self._policy_decimal(config, "settlement_review_total_revenue_coin", Decimal("250.0000")):
            review_reason_codes.append("total_revenue_threshold_exceeded")
        if total_creator_share_coin >= self._policy_decimal(config, "settlement_review_creator_share_coin", Decimal("150.0000")):
            review_reason_codes.append("creator_share_threshold_exceeded")
        if total_platform_share_coin >= self._policy_decimal(config, "settlement_review_platform_share_coin", Decimal("150.0000")):
            review_reason_codes.append("platform_share_threshold_exceeded")
        if shareholder_total_distribution_coin >= self._policy_decimal(
            config,
            "settlement_review_shareholder_distribution_coin",
            Decimal("75.0000"),
        ):
            review_reason_codes.append("shareholder_distribution_threshold_exceeded")
        return ("review_required" if review_reason_codes else "approved"), review_reason_codes, policy_snapshot

    def _creator_league_config(self) -> CreatorLeagueConfig | None:
        return self.session.scalar(
            select(CreatorLeagueConfig).where(CreatorLeagueConfig.league_key == CREATOR_LEAGUE_KEY)
        )

    def _policy_decimal(self, config: CreatorLeagueConfig | None, attr: str, default: Decimal) -> Decimal:
        if config is None:
            return self._normalize_amount(default)
        return self._normalize_amount(getattr(config, attr))

    @staticmethod
    def _sum_decimal(values) -> Decimal:
        return CreatorRevenueService._normalize_amount(sum((Decimal(str(value)) for value in values), Decimal("0.0000")))

    @staticmethod
    def _normalize_amount(value: Decimal | str | int | float) -> Decimal:
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)


__all__ = ["CreatorRevenueService", "VIEWER_REVENUE_PER_VIEW_COIN"]
