from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from fastapi import FastAPI
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.awards.service import AwardsCultureService
from app.live_ops.models import SeasonPass, SeasonPassTier
from app.live_ops.service import LiveOpsService
from app.match_engine.schemas import MatchCrowdStateView
from app.models.calendar_engine import GlobalEvent
from app.models.club_infra import ClubStadium
from app.models.competition_match import CompetitionMatch
from app.models.gtex_economy import GtexContributionSourceType
from app.models.notification_record import NotificationRecord
from app.models.ticketing import StadiumEvent, StadiumTicket, TicketReaction, TicketWaitlist
from app.models.user import User, UserRole
from app.notifications.service import NotificationEventMatrixService
from app.ticketing.schemas import (
    AttendeeExperienceView,
    StadiumDemandView,
    StadiumEconomyView,
    StadiumEventView,
    TicketBuyResponse,
    TicketEventResponse,
    TicketReactionResponse,
    TicketReactionType,
    TicketResellResponse,
    TicketSeatTier,
    TicketStatus,
    TicketTierInventoryView,
    TicketView,
    TicketWaitlistStatus,
    TicketWaitlistView,
)
from app.wallets.service import InsufficientBalanceError, LedgerSourceTag, LedgerUnit, WalletService


MONEY_QUANTUM = Decimal("0.0001")
PRIMARY_PLATFORM_RATE = Decimal("0.1800")
PRIMARY_CLUB_RATE = Decimal("0.6700")
PRIMARY_JACKPOT_RATE = Decimal("0.1500")
RESALE_SELLER_RATE = Decimal("0.8500")
RESALE_PLATFORM_RATE = Decimal("0.1000")
RESALE_JACKPOT_RATE = Decimal("0.0500")
ACTIVE_TICKET_STATUSES = {"available", "sold", "used"}
TIER_ORDER = ("regular", "premium", "vip")
TIER_PREFIX = {"regular": "REG", "premium": "PRE", "vip": "VIP"}
TIER_INFLUENCE = {"regular": Decimal("1.0000"), "premium": Decimal("1.1500"), "vip": Decimal("1.3500")}
TIER_LATENCY = {"regular": 220, "premium": 160, "vip": 110}
TIER_CAMERAS = {
    "regular": ["stadium_pan", "goal_line"],
    "premium": ["bench_cam", "stadium_pan", "goal_line"],
    "vip": ["tunnel_cam", "bench_cam", "skyline_drone", "goal_line"],
}
TIER_WEIGHTS = {
    "league": {"regular": 0.72, "premium": 0.22, "vip": 0.06},
    "final": {"regular": 0.55, "premium": 0.30, "vip": 0.15},
    "derby": {"regular": 0.60, "premium": 0.25, "vip": 0.15},
    "ai_mega_match": {"regular": 0.78, "premium": 0.17, "vip": 0.05},
    "ceremony": {"regular": 0.00, "premium": 0.40, "vip": 0.60},
}
BASE_PRICES = {
    "league": {"regular": Decimal("12.0000"), "premium": Decimal("28.0000"), "vip": Decimal("80.0000")},
    "final": {"regular": Decimal("24.0000"), "premium": Decimal("52.0000"), "vip": Decimal("140.0000")},
    "derby": {"regular": Decimal("18.0000"), "premium": Decimal("40.0000"), "vip": Decimal("108.0000")},
    "ai_mega_match": {"regular": Decimal("10.0000"), "premium": Decimal("22.0000"), "vip": Decimal("60.0000")},
    "ceremony": {"regular": Decimal("0.0000"), "premium": Decimal("90.0000"), "vip": Decimal("180.0000")},
}
TICKET_REWARD_LOYALTY = {"regular": 40, "premium": 70, "vip": 120}
TICKET_REWARD_XP = {"regular": 18, "premium": 34, "vip": 60}
EVENT_REWARD_BONUS = {"league": 10, "derby": 20, "final": 32, "ai_mega_match": 16, "ceremony": 38}
COMPLETED_MATCH_STATUSES = {"completed", "complete", "finished", "final"}
LIVE_MATCH_STATUSES = {"live", "in_progress", "playing", "ongoing"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _money(value: Decimal | float | int | str | None) -> Decimal:
    return Decimal(str(value or "0")).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _bounded_ratio(value: Decimal | float | int | str | None) -> Decimal:
    return max(Decimal("0.0000"), min(Decimal("1.0000"), _money(value)))


def _clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _as_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class TicketingError(ValueError):
    pass


class TicketingNotFoundError(TicketingError):
    pass


class TicketingConflictError(TicketingError):
    pass


class TicketingValidationError(TicketingError):
    pass


class TicketingService:
    def __init__(self, session: Session, *, app: FastAPI | None = None, wallet_service: WalletService | None = None) -> None:
        self.session = session
        self.app = app
        self.wallet_service = wallet_service or WalletService(
            event_publisher=getattr(getattr(app, "state", None), "event_publisher", None),
            cache_backend=getattr(getattr(app, "state", None), "cache_backend", None),
        )

    def get_event(self, *, match_id: str, user: User | None = None) -> TicketEventResponse:
        event = self._get_or_create_event(match_id)
        self._refresh_event_market_state(event)
        self._settle_rewards_if_due(event)
        my_ticket = self._find_user_ticket(event.id, user.id) if user is not None else None
        waitlist = self._find_waitlist(event.match_id, user.id) if user is not None else None
        attendee_access = self._build_attendee_experience(my_ticket, event) if self._can_use_attendee_mode(my_ticket) else None
        return TicketEventResponse(
            event=self._build_event_view(event, user=user),
            my_ticket=self._build_ticket_view(my_ticket) if my_ticket is not None else None,
            attendee_access=attendee_access,
            waitlist=self._build_waitlist_view(waitlist) if waitlist is not None else None,
            available_resale_tickets=[self._build_ticket_view(ticket) for ticket in self._list_resale_tickets(event.id)],
        )

    def buy_ticket(
        self,
        *,
        user: User,
        match_id: str,
        seat_tier: TicketSeatTier | str | None = None,
        resale_ticket_id: str | None = None,
    ) -> TicketBuyResponse:
        event = self._get_or_create_event(match_id)
        if self._find_user_ticket(event.id, user.id) is not None:
            raise TicketingConflictError("User already owns a ticket for this event.")
        if resale_ticket_id is not None:
            ticket = self._buy_resale_ticket(event=event, buyer=user, resale_ticket_id=resale_ticket_id)
        else:
            if seat_tier is None:
                raise TicketingValidationError("seat_tier is required when buying from primary inventory.")
            ticket = self._buy_primary_ticket(event=event, buyer=user, seat_tier=str(seat_tier))
        self._refresh_event_market_state(event)
        self._publish_matrix_notification(
            event_key="ticket_purchased",
            target_user_ids=[user.id],
            resource_id=ticket.id,
            message=f"Your {event.title} ticket is confirmed.",
            metadata={
                "event_id": event.id,
                "match_id": event.match_id,
                "ticket_id": ticket.id,
                "seat_tier": ticket.seat_tier,
                "seat_code": ticket.seat_code,
                "sale_type": "resale" if resale_ticket_id is not None else "primary",
                "route": "/app/play",
            },
        )
        wallet_summary = self.wallet_service.get_wallet_summary(self.session, user, currency=LedgerUnit.CREDIT)
        return TicketBuyResponse(
            event=self._build_event_view(event, user=user),
            ticket=self._build_ticket_view(ticket),
            attendee_access=self._build_attendee_experience(ticket, event),
            wallet_balance=wallet_summary.available_balance,
        )

    def resell_ticket(self, *, user: User, ticket_id: str, price: Decimal) -> TicketResellResponse:
        ticket = self.session.get(StadiumTicket, ticket_id)
        if ticket is None:
            raise TicketingNotFoundError("Ticket was not found.")
        if ticket.user_id != user.id:
            raise TicketingConflictError("Only the ticket owner can list it for resale.")
        event = self.session.get(StadiumEvent, ticket.event_id)
        if event is None:
            raise TicketingNotFoundError("Ticket event was not found.")
        self._assert_resale_window(event)
        if ticket.status == TicketStatus.USED.value:
            raise TicketingConflictError("Used tickets cannot be resold.")
        minimum, maximum = self._resale_bounds(ticket=ticket, event=event)
        listing_price = _money(price)
        if listing_price < minimum or listing_price > maximum:
            raise TicketingValidationError(f"Resale price must stay between {minimum} and {maximum} credits for this ticket.")
        was_listed = ticket.status == TicketStatus.AVAILABLE.value
        ticket.status = TicketStatus.AVAILABLE.value
        ticket.resale_listing_price = listing_price
        ticket.listed_at = _utcnow()
        ticket.seller_user_id = user.id
        ticket.metadata_json = {**dict(ticket.metadata_json or {}), "last_resale_listing_price": str(listing_price)}
        if not was_listed:
            event.resale_ticket_count += 1
        self._refresh_event_market_state(event)
        notified = self._notify_waitlist(event=event, seat_tier=ticket.seat_tier, price=listing_price)
        return TicketResellResponse(
            event=self._build_event_view(event, user=user),
            ticket=self._build_ticket_view(ticket),
            notified_waitlist_count=notified,
        )

    def join_waitlist(self, *, user: User, match_id: str, seat_tier: TicketSeatTier | str | None = None) -> TicketWaitlistView:
        event = self._get_or_create_event(match_id)
        if self._find_user_ticket(event.id, user.id) is not None:
            raise TicketingConflictError("Ticket owners cannot join the waitlist for the same event.")
        resolved_tier = str(seat_tier) if seat_tier is not None else None
        if resolved_tier is not None and resolved_tier not in TIER_ORDER:
            raise TicketingValidationError("Unknown seat tier.")
        entry = self._find_waitlist(event.match_id, user.id)
        if entry is None:
            entry = TicketWaitlist(
                match_id=event.match_id,
                user_id=user.id,
                seat_tier=resolved_tier,
                status=TicketWaitlistStatus.QUEUED.value,
                requested_at=_utcnow(),
                metadata_json={},
            )
            self.session.add(entry)
            self.session.flush()
        else:
            entry.seat_tier = resolved_tier
            entry.status = TicketWaitlistStatus.QUEUED.value
            entry.requested_at = _utcnow()
            entry.notified_at = None
        return self._build_waitlist_view(entry)

    def record_attendance_reaction(
        self,
        *,
        user: User,
        match_id: str,
        reaction_type: TicketReactionType | str,
        intensity: float = 1.0,
        source: str = "api",
    ) -> TicketReactionResponse:
        event = self._get_or_create_event(match_id)
        ticket = self._require_attendee_ticket(event=event, user_id=user.id, consume=True)
        resolved_reaction = self._normalize_reaction_type(reaction_type)
        influence_multiplier = TIER_INFLUENCE[ticket.seat_tier]
        crowd_delta = _money(min(Decimal("0.0800"), Decimal("0.0150") * _money(intensity) * influence_multiplier))
        reaction = TicketReaction(
            ticket_id=ticket.id,
            match_id=event.match_id,
            user_id=user.id,
            reaction_type=resolved_reaction.value,
            crowd_delta=crowd_delta,
            influence_multiplier=influence_multiplier,
            metadata_json={"source": source, "seat_tier": ticket.seat_tier},
        )
        self.session.add(reaction)
        self._apply_reaction_heat(event=event, reaction_type=resolved_reaction.value, crowd_delta=crowd_delta)
        return TicketReactionResponse(
            match_id=match_id,
            reaction_type=resolved_reaction,
            crowd_delta=crowd_delta,
            influence_multiplier=influence_multiplier,
            attendee_access=self._build_attendee_experience(ticket, event),
        )

    def record_attendance_reaction_by_user_id(
        self,
        *,
        user_id: str,
        match_id: str,
        reaction_type: TicketReactionType | str,
        intensity: float = 1.0,
        source: str = "runtime",
    ) -> TicketReactionResponse | None:
        user = self.session.get(User, user_id)
        if user is None:
            return None
        return self.record_attendance_reaction(
            user=user,
            match_id=match_id,
            reaction_type=reaction_type,
            intensity=intensity,
            source=source,
        )

    def resolve_attendee_access(self, *, match_id: str, user_id: str, consume: bool = False) -> dict[str, Any] | None:
        event = self._find_event(match_id)
        if event is None:
            return None
        ticket = self._find_user_ticket(event.id, user_id)
        if not self._can_use_attendee_mode(ticket):
            return None
        if consume:
            self._mark_ticket_used(ticket, event)
        self._refresh_event_market_state(event)
        self._settle_rewards_if_due(event)
        attendee_access = self._build_attendee_experience(ticket, event)
        return {
            "access_source": "ticket_attendee",
            "premium_features": {
                "attendee_mode": True,
                "priority_stream": True,
                "enhanced_crowd_audio": True,
                "exclusive_camera_angles": True,
            },
            "channel_context": {
                "stadium_badge": attendee_access.badge,
                "seat_tier": attendee_access.seat_tier.value,
                "seat_code": attendee_access.seat_code,
                "venue_name": event.venue_name,
                "camera_angles": attendee_access.exclusive_camera_angles,
                "attendee_access": attendee_access.model_dump(mode="json"),
            },
            "sync_strategy": "priority_low_latency",
            "watch_party_enabled": True,
            "reactions_enabled": True,
        }

    def build_crowd_overlay(self, *, match_id: str, base_crowd: MatchCrowdStateView | None) -> MatchCrowdStateView | None:
        event = self._find_event(match_id)
        if event is None:
            return base_crowd
        metadata = dict(event.metadata_json or {})
        overlay_score = min(float(metadata.get("crowd_overlay_score") or 0.0), 0.18)
        boo_ratio = _clamp_float(float(metadata.get("boo_ratio") or 0.0), 0.0, 1.0)
        payload = (
            base_crowd.model_dump(mode="json")
            if base_crowd is not None
            else MatchCrowdStateView(profile=self._crowd_profile_for_event(event.event_type)).model_dump(mode="json")
        )
        payload["profile"] = payload.get("profile") or self._crowd_profile_for_event(event.event_type)
        payload["stadium_name"] = event.venue_name
        payload["stadium_theme"] = "ceremony_gold" if event.event_type == "ceremony" else "ticketed_live"
        payload["crowd_intensity"] = _clamp_float(float(payload.get("crowd_intensity") or 0.5) + overlay_score, 0.0, 1.0)
        payload["chant_level"] = _clamp_float(float(payload.get("chant_level") or 0.5) + (overlay_score * 0.65), 0.0, 1.0)
        payload["hostility"] = _clamp_float(float(payload.get("hostility") or 0.0) + (overlay_score * boo_ratio), 0.0, 1.0)
        payload["spike"] = overlay_score >= 0.05
        payload["crowd_mood"] = "electric" if overlay_score >= 0.08 else payload.get("crowd_mood") or "tense"
        dominant_side = str(payload.get("dominant_side") or "home")
        if dominant_side == "away":
            payload["away_intensity"] = _clamp_float(float(payload.get("away_intensity") or 0.5) + (overlay_score * 0.45), 0.0, 1.0)
            payload["home_intensity"] = _clamp_float(float(payload.get("home_intensity") or 0.5) + (overlay_score * 0.18), 0.0, 1.0)
        else:
            payload["home_intensity"] = _clamp_float(float(payload.get("home_intensity") or 0.5) + (overlay_score * 0.45), 0.0, 1.0)
            payload["away_intensity"] = _clamp_float(float(payload.get("away_intensity") or 0.5) + (overlay_score * 0.18), 0.0, 1.0)
        return MatchCrowdStateView.model_validate(payload)

    def _buy_primary_ticket(self, *, event: StadiumEvent, buyer: User, seat_tier: str) -> StadiumTicket:
        resolved_tier = seat_tier.lower()
        if resolved_tier not in TIER_ORDER:
            raise TicketingValidationError("Unknown seat tier.")
        self._assert_primary_sale_window(event, buyer)
        inventory = self._tier_inventory(event)
        if inventory[resolved_tier]["primary_available"] <= 0:
            raise TicketingConflictError("Requested seat tier is sold out.")
        price = self._price_for_event(event, resolved_tier)
        seat_code = self._next_seat_code(event=event, seat_tier=resolved_tier)
        now = _utcnow()
        try:
            self.wallet_service.settle_available_funds(
                self.session,
                user=buyer,
                amount=price,
                reference=f"ticket-buy:{event.id}:{buyer.id}:{seat_code}",
                description=f"Bought {resolved_tier} ticket for {event.title}",
                external_reference=f"ticket:{event.id}:{seat_code}",
                unit=LedgerUnit.CREDIT,
                source_tag=LedgerSourceTag.VIDEO_VIEW_SPEND,
            )
        except InsufficientBalanceError as exc:
            raise TicketingConflictError(str(exc)) from exc
        ticket = StadiumTicket(
            event_id=event.id,
            user_id=buyer.id,
            match_id=event.match_id,
            seat_tier=resolved_tier,
            seat_code=seat_code,
            price=price,
            original_price=price,
            status=TicketStatus.SOLD.value,
            sold_at=now,
            metadata_json={"sale_type": "primary", "event_type": event.event_type},
        )
        self.session.add(ticket)
        self.session.flush()
        event.gross_revenue = _money(event.gross_revenue + price)
        event.platform_cut_total = _money(event.platform_cut_total + (price * PRIMARY_PLATFORM_RATE))
        event.club_share_total = _money(event.club_share_total + (price * PRIMARY_CLUB_RATE))
        jackpot_amount = _money(price * PRIMARY_JACKPOT_RATE)
        event.jackpot_pool_total = _money(event.jackpot_pool_total + jackpot_amount)
        self._record_jackpot_contribution(
            participant_user_id=buyer.id,
            source_id=ticket.id,
            entry_fee=price,
            contribution_amount=jackpot_amount,
            metadata={"match_id": event.match_id, "sale_type": "primary"},
        )
        self._mark_waitlist_fulfilled(event.match_id, buyer.id)
        return ticket

    def _buy_resale_ticket(self, *, event: StadiumEvent, buyer: User, resale_ticket_id: str) -> StadiumTicket:
        self._assert_resale_window(event)
        ticket = self.session.get(StadiumTicket, resale_ticket_id)
        if ticket is None or ticket.event_id != event.id:
            raise TicketingNotFoundError("Resale ticket was not found for this event.")
        if ticket.status != TicketStatus.AVAILABLE.value or ticket.resale_listing_price is None:
            raise TicketingConflictError("Ticket is not currently available on the resale market.")
        if ticket.user_id == buyer.id:
            raise TicketingConflictError("Cannot purchase your own resale listing.")
        seller = self.session.get(User, ticket.user_id)
        if seller is None:
            raise TicketingConflictError("Resale seller could not be resolved.")
        price = _money(ticket.resale_listing_price)
        try:
            self.wallet_service.settle_available_funds(
                self.session,
                user=buyer,
                amount=price,
                reference=f"ticket-resale-buy:{ticket.id}:{buyer.id}",
                description=f"Bought resale ticket for {event.title}",
                external_reference=f"ticket-resale:{ticket.id}",
                unit=LedgerUnit.CREDIT,
                source_tag=LedgerSourceTag.VIDEO_VIEW_SPEND,
            )
        except InsufficientBalanceError as exc:
            raise TicketingConflictError(str(exc)) from exc
        seller_proceeds = _money(price * RESALE_SELLER_RATE)
        self.wallet_service.credit_trade_proceeds(
            self.session,
            user=seller,
            amount=seller_proceeds,
            reference=f"ticket-resale-sell:{ticket.id}:{seller.id}",
            description=f"Sold resale ticket for {event.title}",
            external_reference=f"ticket-resale:{ticket.id}",
            unit=LedgerUnit.CREDIT,
            source_tag=LedgerSourceTag.MATCH_VIEW_REVENUE,
        )
        ticket.metadata_json = {
            **dict(ticket.metadata_json or {}),
            "sale_type": "resale",
            "previous_owner_id": seller.id,
            "last_resale_price": str(price),
        }
        ticket.seller_user_id = seller.id
        ticket.user_id = buyer.id
        ticket.status = TicketStatus.SOLD.value
        ticket.price = price
        ticket.resale_listing_price = None
        ticket.sold_at = _utcnow()
        ticket.listed_at = None
        event.gross_revenue = _money(event.gross_revenue + price)
        event.resale_volume = _money(event.resale_volume + price)
        event.platform_cut_total = _money(event.platform_cut_total + (price * RESALE_PLATFORM_RATE))
        jackpot_amount = _money(price * RESALE_JACKPOT_RATE)
        event.jackpot_pool_total = _money(event.jackpot_pool_total + jackpot_amount)
        self._record_jackpot_contribution(
            participant_user_id=buyer.id,
            source_id=ticket.id,
            entry_fee=price,
            contribution_amount=jackpot_amount,
            metadata={"match_id": event.match_id, "sale_type": "resale"},
        )
        self._mark_waitlist_fulfilled(event.match_id, buyer.id)
        return ticket

    def _assert_primary_sale_window(self, event: StadiumEvent, buyer: User) -> None:
        self._assert_sales_open(event, buyer)
        if event.tickets_sold >= event.capacity:
            raise TicketingConflictError("This event is sold out.")

    def _assert_resale_window(self, event: StadiumEvent) -> None:
        now = _utcnow()
        sales_close_at = _as_utc_datetime(event.sales_close_at)
        if sales_close_at is not None and now > sales_close_at:
            raise TicketingConflictError("Ticket resale has closed for this event.")
        live_status = self._resolve_live_status(event)
        if live_status == "completed":
            raise TicketingConflictError("Completed events no longer support resale.")
        if live_status == "live":
            raise TicketingConflictError("Live events cannot be resold.")

    def _assert_sales_open(self, event: StadiumEvent, buyer: User) -> None:
        now = _utcnow()
        live_status = self._resolve_live_status(event)
        if live_status == "completed":
            raise TicketingConflictError("Ticket sales are closed for completed events.")
        if live_status == "live":
            raise TicketingConflictError("Ticket sales are closed once the event is live.")
        sales_close_at = _as_utc_datetime(event.sales_close_at)
        if sales_close_at is not None and now > sales_close_at:
            raise TicketingConflictError("Ticket sales are closed for this event.")
        public_sales_starts_at = _as_utc_datetime(event.public_sales_starts_at)
        early_access_starts_at = _as_utc_datetime(event.early_access_starts_at)
        if public_sales_starts_at is not None and now < public_sales_starts_at:
            if early_access_starts_at is not None and now >= early_access_starts_at and self._has_early_access(buyer):
                return
            raise TicketingConflictError("Ticket sales are currently limited to the early-access window.")

    def _get_or_create_event(self, match_id: str) -> StadiumEvent:
        event = self._find_event(match_id)
        if event is not None:
            return event
        if match_id.startswith("ceremony:"):
            event = self._build_ceremony_event(match_id)
        else:
            match = self.session.get(CompetitionMatch, match_id)
            event = self._build_match_event(match) if match is not None else self._build_ai_event(match_id)
        self.session.add(event)
        self.session.flush()
        return event

    def _find_event(self, match_id: str) -> StadiumEvent | None:
        return self.session.scalar(select(StadiumEvent).where(StadiumEvent.match_id == match_id))

    def _build_match_event(self, match: CompetitionMatch) -> StadiumEvent:
        event_type = self._event_type_for_match(match)
        stadium = self.session.scalar(select(ClubStadium).where(ClubStadium.club_id == match.home_club_id))
        global_event = self.session.scalar(
            select(GlobalEvent).where(GlobalEvent.match_id == match.id).order_by(GlobalEvent.priority.desc(), GlobalEvent.start_time.asc())
        )
        base_capacity = stadium.capacity if stadium is not None else 40000
        capacity = self._resolve_capacity(base_capacity=base_capacity, event_type=event_type)
        home_name, away_name = self._resolve_match_names(match)
        title = global_event.event_name if global_event is not None else f"{home_name} vs {away_name}"
        venue_name = stadium.name if stadium is not None else "GTEX Matchday Arena"
        importance_score, rivalry_score, popularity_score = self._hype_scores_for_match(match=match, event_type=event_type)
        now = _utcnow()
        return StadiumEvent(
            stadium_id=stadium.id if stadium is not None else f"virtual:{match.id}",
            match_id=match.id,
            calendar_event_id=global_event.calendar_event_id if global_event is not None else None,
            source_match_id=match.id,
            title=title,
            venue_name=venue_name,
            home_club_id=match.home_club_id,
            away_club_id=match.away_club_id,
            event_type=event_type,
            event_status="on_sale",
            capacity=capacity,
            tier_distribution_json=self._resolve_tier_distribution(capacity=capacity, event_type=event_type),
            base_price_json={tier: str(price) for tier, price in self._base_prices_for_event(event_type).items()},
            early_access_starts_at=now - timedelta(hours=2),
            public_sales_starts_at=now - timedelta(hours=1),
            sales_close_at=(match.scheduled_at or now + timedelta(hours=4)) + timedelta(hours=1),
            importance_score=importance_score,
            rivalry_score=rivalry_score,
            player_popularity_score=popularity_score,
            demand_multiplier=Decimal("1.0000"),
            metadata_json={
                "experience": self._experience_payload(event_type=event_type, venue_name=venue_name, title=title),
                "global_event_id": global_event.id if global_event is not None else None,
                "home_name": home_name,
                "away_name": away_name,
                "crowd_overlay_score": 0.0,
                "boo_ratio": 0.0,
            },
        )

    def _build_ai_event(self, match_id: str) -> StadiumEvent:
        now = _utcnow()
        event_type = "ai_mega_match"
        capacity = self._resolve_capacity(base_capacity=70000, event_type=event_type)
        title = f"AI Mega Match {match_id[-6:].upper()}"
        return StadiumEvent(
            stadium_id=f"virtual:{match_id}",
            match_id=match_id,
            source_match_id=None,
            title=title,
            venue_name="GTEX Hyper Stadium",
            home_club_id=None,
            away_club_id=None,
            event_type=event_type,
            event_status="on_sale",
            capacity=capacity,
            tier_distribution_json=self._resolve_tier_distribution(capacity=capacity, event_type=event_type),
            base_price_json={tier: str(price) for tier, price in self._base_prices_for_event(event_type).items()},
            early_access_starts_at=now - timedelta(hours=2),
            public_sales_starts_at=now - timedelta(hours=1),
            sales_close_at=now + timedelta(days=2),
            importance_score=Decimal("0.7600"),
            rivalry_score=Decimal("0.2800"),
            player_popularity_score=Decimal("0.6600"),
            demand_multiplier=Decimal("1.0000"),
            metadata_json={
                "experience": self._experience_payload(event_type=event_type, venue_name="GTEX Hyper Stadium", title=title),
                "crowd_overlay_score": 0.0,
                "boo_ratio": 0.0,
            },
        )

    def _build_ceremony_event(self, match_id: str) -> StadiumEvent:
        season_id = match_id.split(":", 1)[1] if ":" in match_id else None
        ceremony = AwardsCultureService(self.session).get_ceremony(season_id=season_id)
        title = str(ceremony.get("title") if ceremony is not None else "GTEX Awards Night")
        now = _utcnow()
        event_type = "ceremony"
        capacity = self._resolve_capacity(base_capacity=7200, event_type=event_type)
        return StadiumEvent(
            stadium_id=f"ceremony:{season_id or 'global'}",
            match_id=match_id,
            source_match_id=None,
            title=title,
            venue_name="GTEX Honors Hall",
            home_club_id=None,
            away_club_id=None,
            event_type=event_type,
            event_status="on_sale",
            capacity=capacity,
            tier_distribution_json=self._resolve_tier_distribution(capacity=capacity, event_type=event_type),
            base_price_json={tier: str(price) for tier, price in self._base_prices_for_event(event_type).items()},
            early_access_starts_at=now - timedelta(hours=3),
            public_sales_starts_at=now - timedelta(hours=1),
            sales_close_at=now + timedelta(days=3),
            importance_score=Decimal("1.0000"),
            rivalry_score=Decimal("0.6000"),
            player_popularity_score=Decimal("0.9200"),
            demand_multiplier=Decimal("1.0000"),
            metadata_json={
                "experience": self._experience_payload(
                    event_type=event_type,
                    venue_name="GTEX Honors Hall",
                    title=title,
                    ceremony=ceremony,
                ),
                "ceremony": ceremony or {},
                "season_id": ceremony.get("season_id") if ceremony is not None else season_id,
                "crowd_overlay_score": 0.0,
                "boo_ratio": 0.0,
            },
        )

    def _refresh_event_market_state(self, event: StadiumEvent) -> None:
        tickets = self._event_tickets(event.id)
        event.tickets_sold = len(tickets)
        event.tickets_used = sum(1 for ticket in tickets if ticket.status == TicketStatus.USED.value)
        event.resale_ticket_count = sum(1 for ticket in tickets if ticket.status == TicketStatus.AVAILABLE.value)
        sell_through = _money(Decimal(event.tickets_sold) / Decimal(max(event.capacity, 1)))
        base_demand = (
            Decimal("1.0000")
            + (_bounded_ratio(event.importance_score) * Decimal("0.4500"))
            + (_bounded_ratio(event.rivalry_score) * Decimal("0.2800"))
            + (_bounded_ratio(event.player_popularity_score) * Decimal("0.2200"))
            + (sell_through * Decimal("0.6500"))
        )
        event.demand_multiplier = _money(min(base_demand, Decimal("3.5000")))
        event.event_status = self._resolve_event_status(event)

    def _resolve_event_status(self, event: StadiumEvent) -> str:
        live_status = self._resolve_live_status(event)
        if live_status == "completed":
            return "completed"
        if live_status == "live":
            return "live"
        now = _utcnow()
        if event.tickets_sold >= event.capacity:
            return "sold_out"
        sales_close_at = _as_utc_datetime(event.sales_close_at)
        if sales_close_at is not None and now > sales_close_at:
            return "closed"
        early_access_starts_at = _as_utc_datetime(event.early_access_starts_at)
        public_sales_starts_at = _as_utc_datetime(event.public_sales_starts_at)
        if early_access_starts_at is not None and public_sales_starts_at is not None and early_access_starts_at <= now < public_sales_starts_at:
            return "early_access"
        return "on_sale"

    def _resolve_live_status(self, event: StadiumEvent) -> str:
        if event.source_match_id is None:
            return "completed" if bool((event.metadata_json or {}).get("completed")) else "scheduled"
        match = self.session.get(CompetitionMatch, event.source_match_id)
        if match is None:
            return "scheduled"
        status = str(match.status or "").strip().lower()
        if match.completed_at is not None or status in COMPLETED_MATCH_STATUSES:
            return "completed"
        if status in LIVE_MATCH_STATUSES:
            return "live"
        return "scheduled"

    def _settle_rewards_if_due(self, event: StadiumEvent) -> None:
        if self._resolve_live_status(event) != "completed":
            return
        live_ops = LiveOpsService(self.session)
        tickets = list(
            self.session.scalars(
                select(StadiumTicket).where(
                    StadiumTicket.event_id == event.id,
                    StadiumTicket.status == TicketStatus.USED.value,
                    StadiumTicket.rewarded_at.is_(None),
                )
            ).all()
        )
        for ticket in tickets:
            loyalty_points = TICKET_REWARD_LOYALTY[ticket.seat_tier] + EVENT_REWARD_BONUS.get(event.event_type, 10)
            xp_amount = TICKET_REWARD_XP[ticket.seat_tier] + (EVENT_REWARD_BONUS.get(event.event_type, 10) // 2)
            season_id = (event.metadata_json or {}).get("season_id")
            grant = live_ops.award_xp(
                user_id=ticket.user_id,
                source_type="ticket_attendance",
                amount=xp_amount,
                reference_key=f"ticket-attendance:{event.id}:{ticket.id}",
                metadata={"event_id": event.id, "match_id": event.match_id, "seat_tier": ticket.seat_tier},
                season_id=season_id if isinstance(season_id, str) else None,
            )
            ticket.loyalty_points_awarded = loyalty_points
            ticket.xp_awarded = grant.amount
            ticket.rewarded_at = _utcnow()
            if ticket.seat_tier == TicketSeatTier.VIP.value or event.event_type in {"final", "ceremony"}:
                ticket.exclusive_drop_code = ticket.exclusive_drop_code or f"DROP-{event.id[:6].upper()}-{ticket.id[:6].upper()}"
                self.session.add(
                    NotificationRecord(
                        user_id=ticket.user_id,
                        topic="ticket_drop_unlocked",
                        template_key="TICKET_DROP_UNLOCKED",
                        resource_type="stadium_ticket",
                        resource_id=ticket.id,
                        message=f"{event.title} unlocked an exclusive stadium drop."[:255],
                        metadata_json={"event_id": event.id, "match_id": event.match_id, "ticket_id": ticket.id, "drop_code": ticket.exclusive_drop_code},
                    )
                )
            ticket.metadata_json = {
                **dict(ticket.metadata_json or {}),
                "rewarded": True,
                "loyalty_points": loyalty_points,
                "xp_awarded": grant.amount,
            }
            event.loyalty_points_distributed += loyalty_points

    def _mark_ticket_used(self, ticket: StadiumTicket, event: StadiumEvent) -> None:
        if ticket.status != TicketStatus.SOLD.value:
            return
        ticket.status = TicketStatus.USED.value
        ticket.used_at = _utcnow()
        event.tickets_used += 1

    def _require_attendee_ticket(self, *, event: StadiumEvent, user_id: str, consume: bool) -> StadiumTicket:
        ticket = self._find_user_ticket(event.id, user_id)
        if ticket is None or not self._can_use_attendee_mode(ticket):
            raise TicketingConflictError("A valid event ticket is required to access attendee mode.")
        if consume:
            self._mark_ticket_used(ticket, event)
        return ticket

    def _can_use_attendee_mode(self, ticket: StadiumTicket | None) -> bool:
        return ticket is not None and ticket.status in {TicketStatus.SOLD.value, TicketStatus.USED.value}

    def _build_event_view(self, event: StadiumEvent, *, user: User | None) -> StadiumEventView:
        inventory = self._tier_inventory(event)
        now = _utcnow()
        early_access_starts_at = _as_utc_datetime(event.early_access_starts_at)
        public_sales_starts_at = _as_utc_datetime(event.public_sales_starts_at)
        sales_close_at = _as_utc_datetime(event.sales_close_at)
        early_access_active = bool(early_access_starts_at is not None and public_sales_starts_at is not None and early_access_starts_at <= now < public_sales_starts_at)
        sell_through = _money(Decimal(event.tickets_sold) / Decimal(max(event.capacity, 1)))
        return StadiumEventView(
            event_id=event.id,
            stadium_id=event.stadium_id,
            match_id=event.match_id,
            title=event.title,
            venue_name=event.venue_name,
            event_type=event.event_type,
            event_status=event.event_status,
            capacity=event.capacity,
            tickets_sold=event.tickets_sold,
            tickets_used=event.tickets_used,
            resale_ticket_count=event.resale_ticket_count,
            tier_distribution={tier: int((event.tier_distribution_json or {}).get(tier) or 0) for tier in TIER_ORDER},
            base_price_by_tier=self._event_base_prices(event),
            tier_inventory=[
                TicketTierInventoryView(
                    tier=TicketSeatTier(tier),
                    capacity=inventory[tier]["capacity"],
                    issued=inventory[tier]["issued"],
                    primary_available=inventory[tier]["primary_available"],
                    resale_available=inventory[tier]["resale_available"],
                    current_price=self._price_for_event(event, tier),
                )
                for tier in TIER_ORDER
            ],
            early_access_starts_at=early_access_starts_at,
            public_sales_starts_at=public_sales_starts_at,
            sales_close_at=sales_close_at,
            early_access_enabled=event.early_access_starts_at is not None,
            early_access_active=early_access_active,
            user_has_early_access=self._has_early_access(user) if user is not None else False,
            demand=StadiumDemandView(
                importance_score=_money(event.importance_score),
                rivalry_score=_money(event.rivalry_score),
                player_popularity_score=_money(event.player_popularity_score),
                sell_through=sell_through,
                demand_multiplier=_money(event.demand_multiplier),
            ),
            economy=StadiumEconomyView(
                gross_revenue=_money(event.gross_revenue),
                resale_volume=_money(event.resale_volume),
                platform_cut_total=_money(event.platform_cut_total),
                club_share_total=_money(event.club_share_total),
                jackpot_pool_total=_money(event.jackpot_pool_total),
                loyalty_points_distributed=event.loyalty_points_distributed,
            ),
            experience=dict((event.metadata_json or {}).get("experience") or {}),
        )

    def _build_ticket_view(self, ticket: StadiumTicket) -> TicketView:
        return TicketView(
            ticket_id=ticket.id,
            user_id=ticket.user_id,
            match_id=ticket.match_id,
            seat_tier=TicketSeatTier(ticket.seat_tier),
            seat_code=ticket.seat_code,
            price=_money(ticket.price),
            original_price=_money(ticket.original_price),
            status=TicketStatus(ticket.status),
            resale_listing_price=_money(ticket.resale_listing_price) if ticket.resale_listing_price is not None else None,
            listed_at=ticket.listed_at,
            sold_at=ticket.sold_at,
            used_at=ticket.used_at,
            loyalty_points_awarded=ticket.loyalty_points_awarded,
            xp_awarded=ticket.xp_awarded,
            exclusive_drop_code=ticket.exclusive_drop_code,
            metadata=dict(ticket.metadata_json or {}),
        )

    def _build_waitlist_view(self, waitlist: TicketWaitlist) -> TicketWaitlistView:
        return TicketWaitlistView(
            waitlist_id=waitlist.id,
            match_id=waitlist.match_id,
            seat_tier=TicketSeatTier(waitlist.seat_tier) if waitlist.seat_tier else None,
            status=TicketWaitlistStatus(waitlist.status),
            position=self._waitlist_position(waitlist),
            requested_at=waitlist.requested_at,
            notified_at=waitlist.notified_at,
        )

    def _build_attendee_experience(self, ticket: StadiumTicket, event: StadiumEvent) -> AttendeeExperienceView:
        return AttendeeExperienceView(
            badge="You are in the stadium",
            seat_tier=TicketSeatTier(ticket.seat_tier),
            seat_code=ticket.seat_code,
            priority_stream=True,
            enhanced_crowd_audio=True,
            exclusive_camera_angles=list(TIER_CAMERAS[ticket.seat_tier]),
            influence_multiplier=TIER_INFLUENCE[ticket.seat_tier],
            low_latency_target_ms=TIER_LATENCY[ticket.seat_tier],
            fairness_guardrail="Crowd reactions change presentation only. Match simulation stays fair.",
            metadata={"venue_name": event.venue_name, "event_type": event.event_type, "seat_tier": ticket.seat_tier},
        )

    def _event_tickets(self, event_id: str) -> list[StadiumTicket]:
        return list(self.session.scalars(select(StadiumTicket).where(StadiumTicket.event_id == event_id).order_by(StadiumTicket.created_at.asc())).all())

    def _list_resale_tickets(self, event_id: str) -> list[StadiumTicket]:
        return list(
            self.session.scalars(
                select(StadiumTicket)
                .where(StadiumTicket.event_id == event_id, StadiumTicket.status == TicketStatus.AVAILABLE.value)
                .order_by(StadiumTicket.resale_listing_price.asc(), StadiumTicket.listed_at.asc())
            ).all()
        )

    def _find_user_ticket(self, event_id: str, user_id: str) -> StadiumTicket | None:
        return self.session.scalar(
            select(StadiumTicket)
            .where(StadiumTicket.event_id == event_id, StadiumTicket.user_id == user_id, StadiumTicket.status.in_(tuple(ACTIVE_TICKET_STATUSES)))
            .order_by(StadiumTicket.created_at.desc())
        )

    def _find_waitlist(self, match_id: str, user_id: str) -> TicketWaitlist | None:
        return self.session.scalar(select(TicketWaitlist).where(TicketWaitlist.match_id == match_id, TicketWaitlist.user_id == user_id))

    def _waitlist_position(self, waitlist: TicketWaitlist) -> int:
        entries = list(
            self.session.scalars(
                select(TicketWaitlist)
                .where(TicketWaitlist.match_id == waitlist.match_id, TicketWaitlist.status.in_(("queued", "notified")))
                .order_by(TicketWaitlist.requested_at.asc(), TicketWaitlist.id.asc())
            ).all()
        )
        for index, entry in enumerate(entries, start=1):
            if entry.id == waitlist.id:
                return index
        return max(len(entries), 1)

    def _tier_inventory(self, event: StadiumEvent) -> dict[str, dict[str, int]]:
        issued_by_tier = {tier: 0 for tier in TIER_ORDER}
        resale_by_tier = {tier: 0 for tier in TIER_ORDER}
        for ticket in self._event_tickets(event.id):
            issued_by_tier[ticket.seat_tier] = issued_by_tier.get(ticket.seat_tier, 0) + 1
            if ticket.status == TicketStatus.AVAILABLE.value:
                resale_by_tier[ticket.seat_tier] = resale_by_tier.get(ticket.seat_tier, 0) + 1
        distribution = {tier: int((event.tier_distribution_json or {}).get(tier) or 0) for tier in TIER_ORDER}
        return {
            tier: {
                "capacity": distribution.get(tier, 0),
                "issued": issued_by_tier.get(tier, 0),
                "primary_available": max(distribution.get(tier, 0) - issued_by_tier.get(tier, 0), 0),
                "resale_available": resale_by_tier.get(tier, 0),
            }
            for tier in TIER_ORDER
        }

    def _event_base_prices(self, event: StadiumEvent) -> dict[str, Decimal]:
        payload = dict(event.base_price_json or {})
        fallback = self._base_prices_for_event(event.event_type)
        return {tier: _money(payload.get(tier) or fallback[tier]) for tier in TIER_ORDER}

    def _price_for_event(self, event: StadiumEvent, seat_tier: str) -> Decimal:
        base = self._event_base_prices(event)[seat_tier]
        sell_through = Decimal(event.tickets_sold) / Decimal(max(event.capacity, 1))
        demand_component = max(Decimal("0.0000"), (_money(event.demand_multiplier) - Decimal("1.0000")) * (base * Decimal("0.4500")) + (_money(sell_through) * Decimal("8.0000")))
        importance_component = (_bounded_ratio(event.importance_score) * (base * Decimal("0.3000"))) + (_bounded_ratio(event.rivalry_score) * Decimal("4.0000")) + (_bounded_ratio(event.player_popularity_score) * Decimal("3.0000"))
        return _money(base + demand_component + importance_component)

    def _base_prices_for_event(self, event_type: str) -> dict[str, Decimal]:
        return dict(BASE_PRICES.get(event_type, BASE_PRICES["league"]))

    def _resolve_capacity(self, *, base_capacity: int, event_type: str) -> int:
        safe_base = max(int(base_capacity or 0), 2)
        if event_type == "final":
            return max(2, int(round(safe_base * 0.65)))
        if event_type == "ceremony":
            return max(2, int(round(safe_base * 0.28)))
        if event_type == "ai_mega_match":
            return max(safe_base, int(round(safe_base * 1.20)))
        if event_type == "derby":
            return max(2, int(round(safe_base * 0.88)))
        return safe_base

    def _resolve_tier_distribution(self, *, capacity: int, event_type: str) -> dict[str, int]:
        weights = dict(TIER_WEIGHTS.get(event_type, TIER_WEIGHTS["league"]))
        counts = {tier: int(capacity * weight) for tier, weight in weights.items()}
        remainder = max(capacity - sum(counts.values()), 0)
        ranking = sorted(weights, key=lambda tier: (capacity * weights[tier]) - counts[tier], reverse=True)
        for index in range(remainder):
            counts[ranking[index % len(ranking)]] += 1
        active_tiers = [tier for tier, weight in weights.items() if weight > 0]
        if capacity >= len(active_tiers):
            for tier in active_tiers:
                if counts[tier] > 0:
                    continue
                donor = max(active_tiers, key=lambda candidate: counts[candidate])
                if counts[donor] > 1:
                    counts[donor] -= 1
                    counts[tier] += 1
        return {tier: int(counts.get(tier, 0)) for tier in TIER_ORDER}

    def _event_type_for_match(self, match: CompetitionMatch) -> str:
        metadata = dict(match.metadata_json or {})
        stage = str(match.stage or "").strip().lower()
        if stage in {"final", "grand_final", "cup_final"} or ("final" in stage and "semi" not in stage and "quarter" not in stage):
            return "final"
        if bool(metadata.get("is_derby")) or float(metadata.get("rivalry_score") or metadata.get("rivalry_intensity") or 0.0) >= 0.75:
            return "derby"
        if bool(metadata.get("generated_match")) or str(metadata.get("competition_family") or "").strip().lower() == "ai":
            return "ai_mega_match"
        return "league"

    def _hype_scores_for_match(self, *, match: CompetitionMatch, event_type: str) -> tuple[Decimal, Decimal, Decimal]:
        metadata = dict(match.metadata_json or {})
        importance = Decimal("0.5200")
        if event_type == "final":
            importance = Decimal("1.0000")
        elif event_type == "derby":
            importance = Decimal("0.8600")
        elif event_type == "ai_mega_match":
            importance = Decimal("0.7600")
        rivalry = _bounded_ratio(metadata.get("rivalry_score") or metadata.get("rivalry_intensity") or (0.84 if event_type == "derby" else 0.24))
        popularity = _bounded_ratio(metadata.get("player_popularity_score") or metadata.get("star_power") or (0.86 if event_type == "final" else 0.58))
        return _bounded_ratio(importance), rivalry, popularity

    def _resolve_match_names(self, match: CompetitionMatch) -> tuple[str, str]:
        metadata = dict(match.metadata_json or {})
        preview = metadata.get("preview_request") if isinstance(metadata.get("preview_request"), dict) else {}
        home = self._extract_name(preview.get("home_team"), fallback=metadata.get("home_name") or match.home_club_id)
        away = self._extract_name(preview.get("away_team"), fallback=metadata.get("away_name") or match.away_club_id)
        return home, away

    def _extract_name(self, payload: object, *, fallback: object) -> str:
        if isinstance(payload, dict):
            for key in ("name", "team_name", "display_name", "short_name"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        text = str(fallback or "").strip()
        return text if text else "GTEX Club"

    def _experience_payload(self, *, event_type: str, venue_name: str, title: str, ceremony: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {
            "venue_name": venue_name,
            "title": title,
            "stadium_badge": "You are in the stadium",
            "exclusive_camera_angles": list(TIER_CAMERAS["vip"]),
            "countdown_seconds": 90,
            "entry_sequence": ["gate_scan", "stadium_lights", "anthem_swell"],
            "player_arrivals": True,
        }
        if event_type == "ceremony":
            payload.update(
                {
                    "countdown_seconds": int((ceremony or {}).get("countdown_seconds") or 120),
                    "entry_sequence": ["red_carpet", "spotlight_walk", "main_stage_reveal"],
                    "red_carpet": True,
                    "early_reveal": True,
                    "vip_only_lounges": True,
                    "segments": list((ceremony or {}).get("segments") or []),
                }
            )
        elif event_type == "final":
            payload.update({"entry_sequence": ["anthem_lights", "trophy_walk", "kickoff_tunnel"], "finals_energy": True})
        elif event_type == "ai_mega_match":
            payload.update({"entry_sequence": ["grid_launch", "skybox_intro", "hyper_kickoff"], "ai_showcase": True})
        elif event_type == "derby":
            payload.update({"entry_sequence": ["flare_tunnel", "chant_duel", "derby_roar"], "rivalry_mode": True})
        return payload

    def _resale_bounds(self, *, ticket: StadiumTicket, event: StadiumEvent) -> tuple[Decimal, Decimal]:
        reference_price = max(_money(ticket.original_price), self._price_for_event(event, ticket.seat_tier))
        return _money(max(reference_price * Decimal("0.8000"), Decimal("1.0000"))), _money(reference_price * Decimal("2.5000"))

    def _next_seat_code(self, *, event: StadiumEvent, seat_tier: str) -> str:
        next_position = 1 + sum(1 for ticket in self._event_tickets(event.id) if ticket.seat_tier == seat_tier)
        return f"{TIER_PREFIX[seat_tier]}-{next_position:04d}"

    def _has_early_access(self, user: User | None) -> bool:
        if user is None:
            return False
        if user.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            return True
        season_pass = self.session.scalar(
            select(SeasonPass).where(SeasonPass.user_id == user.id).order_by(SeasonPass.tier.desc(), SeasonPass.level.desc(), SeasonPass.updated_at.desc())
        )
        if season_pass is None:
            return False
        return season_pass.tier == SeasonPassTier.PREMIUM or season_pass.level >= 15

    def _normalize_reaction_type(self, reaction_type: TicketReactionType | str) -> TicketReactionType:
        raw = str(reaction_type).strip().lower()
        if raw in {"boo", "downvote"}:
            return TicketReactionType.BOO
        if raw in {"cheer", "clap", "fire", "goal", "wave"}:
            return TicketReactionType.CHEER
        return TicketReactionType.REACT

    def _apply_reaction_heat(self, *, event: StadiumEvent, reaction_type: str, crowd_delta: Decimal) -> None:
        metadata = dict(event.metadata_json or {})
        current_heat = _clamp_float(float(metadata.get("crowd_overlay_score") or 0.0), 0.0, 1.0)
        overlay_score = min(0.18, (current_heat * 0.82) + (float(crowd_delta) * 1.45))
        reaction_count = int(metadata.get("reaction_count") or 0) + 1
        boo_count = int(metadata.get("boo_count") or 0) + (1 if reaction_type == TicketReactionType.BOO.value else 0)
        metadata["reaction_count"] = reaction_count
        metadata["boo_count"] = boo_count
        metadata["boo_ratio"] = 0.0 if reaction_count == 0 else round(boo_count / reaction_count, 4)
        metadata["crowd_overlay_score"] = round(overlay_score, 4)
        metadata["last_reaction_at"] = _utcnow().isoformat()
        event.metadata_json = metadata

    def _mark_waitlist_fulfilled(self, match_id: str, user_id: str) -> None:
        entry = self._find_waitlist(match_id, user_id)
        if entry is None:
            return
        entry.status = TicketWaitlistStatus.FULFILLED.value
        if entry.notified_at is None:
            entry.notified_at = _utcnow()

    def _notify_waitlist(self, *, event: StadiumEvent, seat_tier: str, price: Decimal) -> int:
        entries = list(
            self.session.scalars(
                select(TicketWaitlist)
                .where(TicketWaitlist.match_id == event.match_id, TicketWaitlist.status == TicketWaitlistStatus.QUEUED.value)
                .order_by(TicketWaitlist.requested_at.asc(), TicketWaitlist.id.asc())
            ).all()
        )
        notified = 0
        for entry in entries:
            if entry.seat_tier is not None and entry.seat_tier != seat_tier:
                continue
            entry.status = TicketWaitlistStatus.NOTIFIED.value
            entry.notified_at = _utcnow()
            self.session.add(
                NotificationRecord(
                    user_id=entry.user_id,
                    topic="ticket_resale_available",
                    template_key="TICKET_RESALE_AVAILABLE",
                    resource_type="stadium_event",
                    resource_id=event.id,
                    message=f"{event.title} has a {seat_tier} resale ticket available."[:255],
                    metadata_json={"event_id": event.id, "match_id": event.match_id, "seat_tier": seat_tier, "price": str(price)},
                )
            )
            notified += 1
        return notified

    def _publish_matrix_notification(
        self,
        *,
        event_key: str,
        target_user_ids: list[str | None],
        resource_id: str,
        message: str,
        metadata: dict[str, object],
    ) -> None:
        if not self._notification_tables_available():
            return
        normalized_targets = [user_id for user_id in target_user_ids if user_id]
        if not normalized_targets:
            return
        NotificationEventMatrixService(self.session).publish_event(
            event_key=event_key,
            target_user_ids=normalized_targets,
            resource_id=resource_id,
            message=message,
            metadata_json=metadata,
        )

    def _notification_tables_available(self) -> bool:
        inspector = inspect(self.session.connection())
        return all(
            inspector.has_table(table_name)
            for table_name in ("notification_records", "notification_preferences", "users")
        )

    def _record_jackpot_contribution(self, *, participant_user_id: str | None, source_id: str | None, entry_fee: Decimal, contribution_amount: Decimal, metadata: dict[str, Any]) -> None:
        if self.app is None or contribution_amount <= Decimal("0.0000"):
            return
        runtime = getattr(getattr(self.app, "state", None), "gtex_runtime", None)
        if runtime is None:
            return
        runtime.jackpot.record_contribution(
            self.session,
            participant_user_id=participant_user_id,
            source_type=GtexContributionSourceType.PLATFORM_ACTIVITY,
            source_id=source_id,
            entry_fee=entry_fee,
            contribution_amount=contribution_amount,
            metadata=dict(metadata),
        )

    def _crowd_profile_for_event(self, event_type: str) -> str:
        if event_type == "ceremony":
            return "gala"
        if event_type == "derby":
            return "fever"
        if event_type == "final":
            return "finale"
        if event_type == "ai_mega_match":
            return "festival"
        return "standard"


__all__ = [
    "TicketingConflictError",
    "TicketingError",
    "TicketingNotFoundError",
    "TicketingService",
    "TicketingValidationError",
]
