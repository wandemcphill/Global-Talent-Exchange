from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.creator_monetization import CreatorBroadcastPurchase, CreatorMatchGiftEvent
from app.models.media_engine import MatchView
from app.models.user import User
from app.services.creator_broadcast_service import CreatorBroadcastError, CreatorBroadcastService, CreatorMatchContext

AMOUNT_QUANTUM = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class CreatorTopGifterMetric:
    user_id: str
    username: str
    display_name: str | None
    total_gift_coin: Decimal
    gift_count: int


@dataclass(frozen=True, slots=True)
class CreatorAnalyticsDashboard:
    context: CreatorMatchContext
    club_id: str | None
    total_viewers: int
    video_viewers: int
    gift_totals_coin: Decimal
    top_gifters: tuple[CreatorTopGifterMetric, ...]
    fan_engagement_pct: Decimal
    engaged_fans: int
    total_watch_seconds: int


class CreatorAnalyticsService:
    def __init__(self, session: Session, broadcast_service: CreatorBroadcastService | None = None) -> None:
        self.session = session
        self.broadcast_service = broadcast_service or CreatorBroadcastService(session)

    def build_match_dashboard(
        self,
        *,
        actor: User,
        match_id: str,
        club_id: str | None = None,
    ) -> CreatorAnalyticsDashboard:
        context = self.broadcast_service.get_match_context(match_id)
        scoped_club_id = self._resolve_authorized_club(actor=actor, context=context, requested_club_id=club_id)

        purchases = list(
            self.session.scalars(
                select(CreatorBroadcastPurchase).where(CreatorBroadcastPurchase.match_id == context.match.id)
            ).all()
        )
        views = list(
            self.session.scalars(
                select(MatchView).where(MatchView.match_key == context.match.id)
            ).all()
        )
        gifts_query = select(CreatorMatchGiftEvent).where(CreatorMatchGiftEvent.match_id == context.match.id)
        if scoped_club_id is not None:
            gifts_query = gifts_query.where(CreatorMatchGiftEvent.club_id == scoped_club_id)
        gifts = list(self.session.scalars(gifts_query).all())

        total_viewer_ids = {purchase.user_id for purchase in purchases}
        total_viewer_ids.update(view.user_id for view in views)
        video_viewer_ids = {view.user_id for view in views}
        engaged_ids = {
            view.user_id
            for view in views
            if int(view.watch_seconds) >= 300
        }
        engaged_ids.update(gift.sender_user_id for gift in gifts)
        total_watch_seconds = sum(int(view.watch_seconds) for view in views)
        total_viewers = len(total_viewer_ids)
        engaged_fans = len(engaged_ids)
        fan_engagement = Decimal("0.0000")
        if total_viewers > 0:
            fan_engagement = self._normalize_amount((Decimal(engaged_fans) / Decimal(total_viewers)) * Decimal("100.0000"))

        gifter_totals: dict[str, dict[str, Decimal | int]] = defaultdict(
            lambda: {"amount": Decimal("0.0000"), "count": 0}
        )
        for item in gifts:
            bucket = gifter_totals[item.sender_user_id]
            bucket["amount"] = self._normalize_amount(Decimal(bucket["amount"]) + Decimal(str(item.gross_amount_coin)))
            bucket["count"] = int(bucket["count"]) + 1
        top_gifters: list[CreatorTopGifterMetric] = []
        if gifter_totals:
            users = {
                user.id: user
                for user in self.session.scalars(
                    select(User).where(User.id.in_(tuple(gifter_totals.keys())))
                ).all()
            }
            for user_id, totals in sorted(
                gifter_totals.items(),
                key=lambda item: (Decimal(item[1]["amount"]), int(item[1]["count"])),
                reverse=True,
            )[:5]:
                user = users.get(user_id)
                top_gifters.append(
                    CreatorTopGifterMetric(
                        user_id=user_id,
                        username=user.username if user is not None else user_id,
                        display_name=user.display_name if user is not None else None,
                        total_gift_coin=self._normalize_amount(totals["amount"]),
                        gift_count=int(totals["count"]),
                    )
                )

        return CreatorAnalyticsDashboard(
            context=context,
            club_id=scoped_club_id,
            total_viewers=total_viewers,
            video_viewers=len(video_viewer_ids),
            gift_totals_coin=self._normalize_amount(
                sum((Decimal(str(item.gross_amount_coin)) for item in gifts), Decimal("0.0000"))
            ),
            top_gifters=tuple(top_gifters),
            fan_engagement_pct=fan_engagement,
            engaged_fans=engaged_fans,
            total_watch_seconds=total_watch_seconds,
        )

    def _resolve_authorized_club(
        self,
        *,
        actor: User,
        context: CreatorMatchContext,
        requested_club_id: str | None,
    ) -> str | None:
        if actor.role.value in {"admin", "super_admin"}:
            if requested_club_id is not None and requested_club_id not in {
                context.match.home_club_id,
                context.match.away_club_id,
            }:
                raise CreatorBroadcastError(
                    "Requested club is not part of this Creator League match.",
                    reason="analytics_club_not_in_match",
                )
            return requested_club_id

        actor_club_ids = {
            beneficiary.club_id
            for beneficiary in (context.home_beneficiary, context.away_beneficiary)
            if beneficiary is not None and beneficiary.creator_user_id == actor.id
        }
        if not actor_club_ids:
            raise CreatorBroadcastError(
                "Only the participating creator or an admin can view creator match analytics.",
                reason="analytics_access_denied",
            )
        if requested_club_id is not None:
            if requested_club_id not in actor_club_ids:
                raise CreatorBroadcastError(
                    "Creators can only view analytics for their own creator club.",
                    reason="analytics_creator_scope_denied",
                )
            return requested_club_id
        return next(iter(actor_club_ids))

    @staticmethod
    def _normalize_amount(value: Decimal | str | int | float) -> Decimal:
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)


__all__ = [
    "CreatorAnalyticsDashboard",
    "CreatorAnalyticsService",
    "CreatorTopGifterMetric",
]
