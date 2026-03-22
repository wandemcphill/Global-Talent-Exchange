from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.admin_engine.service import AdminEngineService
from app.models.base import utcnow
from app.models.creator_monetization import CreatorRevenueSettlement
from app.models.risk_ops import AuditLog
from app.models.user import User
from app.risk_ops_engine.service import RiskOpsService
from app.services.creator_league_service import CreatorLeagueError, CreatorLeagueService
from app.services.creator_share_market_service import CreatorClubShareMarketService
from app.services.creator_stadium_service import CreatorStadiumService


@dataclass(slots=True)
class CreatorLeagueFinanceService:
    session: Session

    def get_report(
        self,
        *,
        season_id: str | None = None,
        settlement_limit: int = 10,
        audit_limit: int = 20,
    ) -> dict[str, object]:
        league_service = CreatorLeagueService(self.session)
        config_view = league_service.get_overview()
        resolved_season_id = season_id or (config_view.current_season.id if config_view.current_season is not None else None)
        share_control = CreatorClubShareMarketService(self.session).serialize_control(
            CreatorClubShareMarketService(self.session).get_admin_control()
        )
        stadium_control = CreatorStadiumService(self.session).get_admin_control()
        gift_controls = AdminEngineService(self.session).get_active_stability_controls().creator_match_gift
        settlements_requiring_review = tuple(
            self.list_settlements(
                season_id=resolved_season_id,
                review_status="review_required",
                limit=settlement_limit,
            )
        )
        return {
            "config": config_view,
            "share_market_control": share_control,
            "stadium_control": {
                "id": stadium_control.id,
                "control_key": stadium_control.control_key,
                "max_matchday_ticket_price_coin": stadium_control.max_matchday_ticket_price_coin,
                "max_season_pass_price_coin": stadium_control.max_season_pass_price_coin,
                "max_vip_ticket_price_coin": stadium_control.max_vip_ticket_price_coin,
                "max_stadium_level": stadium_control.max_stadium_level,
                "vip_seat_ratio_bps": stadium_control.vip_seat_ratio_bps,
                "max_in_stadium_ad_slots": stadium_control.max_in_stadium_ad_slots,
                "max_sponsor_banner_slots": stadium_control.max_sponsor_banner_slots,
                "ad_placement_enabled": stadium_control.ad_placement_enabled,
                "ticket_sales_enabled": stadium_control.ticket_sales_enabled,
                "max_placement_price_coin": stadium_control.max_placement_price_coin,
                "metadata_json": stadium_control.metadata_json or {},
                "created_at": stadium_control.created_at,
                "updated_at": stadium_control.updated_at,
            },
            "creator_match_gift_controls": {
                "max_amount": gift_controls.max_amount,
                "daily_sender_limit": gift_controls.daily_sender_limit,
                "daily_recipient_limit": gift_controls.daily_recipient_limit,
                "daily_pair_limit": gift_controls.daily_pair_limit,
                "cooldown_seconds": gift_controls.cooldown_seconds,
                "burst_window_seconds": gift_controls.burst_window_seconds,
                "burst_max_count": gift_controls.burst_max_count,
                "review_threshold_bps": gift_controls.review_threshold_bps,
            },
            "current_season_summary": self._build_summary(resolved_season_id),
            "settlements_requiring_review": settlements_requiring_review,
            "recent_audit_events": tuple(self._recent_audits(limit=audit_limit)),
        }

    def list_settlements(
        self,
        *,
        season_id: str | None = None,
        review_status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, object]]:
        statement = select(CreatorRevenueSettlement)
        if season_id is not None:
            statement = statement.where(CreatorRevenueSettlement.season_id == season_id)
        if review_status is not None:
            statement = statement.where(CreatorRevenueSettlement.review_status == review_status)
        statement = statement.order_by(
            CreatorRevenueSettlement.settled_at.desc(),
            CreatorRevenueSettlement.updated_at.desc(),
        ).limit(limit)
        return [self._serialize_settlement(item) for item in self.session.scalars(statement).all()]

    def approve_settlement(
        self,
        *,
        settlement_id: str,
        actor: User,
        review_note: str | None = None,
    ) -> dict[str, object]:
        settlement = self.session.get(CreatorRevenueSettlement, settlement_id)
        if settlement is None:
            raise CreatorLeagueError("Creator League settlement was not found.", reason="settlement_not_found")
        if settlement.review_status != "review_required":
            raise CreatorLeagueError(
                "Creator League settlement does not currently require review.",
                reason="settlement_review_not_required",
            )

        settlement.review_status = "approved"
        settlement.reviewed_by_user_id = actor.id
        settlement.reviewed_at = utcnow()
        settlement.review_note = (review_note or "").strip() or None
        RiskOpsService(self.session).log_audit(
            actor_user_id=actor.id,
            action_key="creator_revenue_settlement.review.approved",
            resource_type="creator_revenue_settlement",
            resource_id=settlement.id,
            detail="Creator League settlement review approved by admin.",
            metadata_json={
                "match_id": settlement.match_id,
                "season_id": settlement.season_id,
                "review_reason_codes": settlement.review_reason_codes_json or [],
                "review_note": settlement.review_note,
            },
        )
        self.session.flush()
        self.session.commit()
        return self._serialize_settlement(settlement)

    def _build_summary(self, season_id: str | None) -> dict[str, object] | None:
        if season_id is None:
            return None
        settlements = list(
            self.session.scalars(
                select(CreatorRevenueSettlement)
                .where(CreatorRevenueSettlement.season_id == season_id)
                .order_by(CreatorRevenueSettlement.settled_at.desc(), CreatorRevenueSettlement.updated_at.desc())
            ).all()
        )
        approved_count = sum(1 for item in settlements if item.review_status == "approved")
        review_required_count = sum(1 for item in settlements if item.review_status == "review_required")
        return {
            "season_id": season_id,
            "settlement_count": len(settlements),
            "approved_settlement_count": approved_count,
            "review_required_settlement_count": review_required_count,
            "total_revenue_coin": self._sum_decimal(item.total_revenue_coin for item in settlements),
            "total_creator_share_coin": self._sum_decimal(item.total_creator_share_coin for item in settlements),
            "total_platform_share_coin": self._sum_decimal(item.total_platform_share_coin for item in settlements),
            "total_shareholder_distribution_coin": self._sum_decimal(
                item.shareholder_total_distribution_coin for item in settlements
            ),
            "total_ticket_sales_gross_coin": self._sum_decimal(item.ticket_sales_gross_coin for item in settlements),
            "total_video_viewer_revenue_coin": self._sum_decimal(item.video_viewer_revenue_coin for item in settlements),
            "total_gift_revenue_gross_coin": self._sum_decimal(item.gift_revenue_gross_coin for item in settlements),
            "total_stadium_placement_revenue_coin": self._sum_decimal(
                Decimal(str(item.in_stadium_ads_revenue_coin)) + Decimal(str(item.sponsor_banner_revenue_coin))
                for item in settlements
            ),
        }

    def _recent_audits(self, *, limit: int) -> list[dict[str, object]]:
        statement = (
            select(AuditLog)
            .where(
                or_(
                    AuditLog.action_key.like("creator_league.financial.%"),
                    AuditLog.action_key.like("creator_share_market.%"),
                    AuditLog.action_key.like("creator_stadium.%"),
                    AuditLog.action_key.like("creator_revenue_settlement.%"),
                )
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return [
            {
                "id": item.id,
                "actor_user_id": item.actor_user_id,
                "action_key": item.action_key,
                "resource_type": item.resource_type,
                "resource_id": item.resource_id,
                "outcome": item.outcome,
                "detail": item.detail,
                "metadata_json": item.metadata_json or {},
                "created_at": item.created_at,
            }
            for item in self.session.scalars(statement).all()
        ]

    @staticmethod
    def _serialize_settlement(settlement: CreatorRevenueSettlement) -> dict[str, object]:
        return {
            "id": settlement.id,
            "season_id": settlement.season_id,
            "competition_id": settlement.competition_id,
            "match_id": settlement.match_id,
            "home_club_id": settlement.home_club_id,
            "away_club_id": settlement.away_club_id,
            "total_revenue_coin": settlement.total_revenue_coin,
            "total_creator_share_coin": settlement.total_creator_share_coin,
            "total_platform_share_coin": settlement.total_platform_share_coin,
            "shareholder_total_distribution_coin": settlement.shareholder_total_distribution_coin,
            "review_status": settlement.review_status,
            "review_reason_codes_json": tuple(settlement.review_reason_codes_json or ()),
            "policy_snapshot_json": settlement.policy_snapshot_json or {},
            "reviewed_by_user_id": settlement.reviewed_by_user_id,
            "reviewed_at": settlement.reviewed_at,
            "review_note": settlement.review_note,
            "settled_at": settlement.settled_at,
            "metadata_json": settlement.metadata_json or {},
        }

    @staticmethod
    def _sum_decimal(values) -> Decimal:
        total = Decimal("0.0000")
        for value in values:
            total += Decimal(str(value or 0))
        return total.quantize(Decimal("0.0001"))


__all__ = ["CreatorLeagueFinanceService"]
