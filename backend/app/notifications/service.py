from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.events import DomainEvent
from app.models.notification_center import NotificationPreference, NotificationSubscription, PlatformAnnouncement
from app.models.notification_record import NotificationRecord
from app.models.user import User
from app.notifications.schemas import NotificationEventMatrixItemView, NotificationTestEventRequest


NOTIFICATION_EVENT_MATRIX: tuple[dict[str, Any], ...] = (
    {
        "event_key": "transfer_listing_created",
        "topic": "transfer_market",
        "template_key": "transfer.listing.created",
        "title": "Player listed",
        "default_message": "A player has been listed on the transfer market.",
        "audience": "club_owner",
        "deep_link_route": "/app/market",
        "preference_key": "allow_market",
    },
    {
        "event_key": "offer_received",
        "topic": "transfer_market",
        "template_key": "transfer.offer.received",
        "title": "Offer received",
        "default_message": "Your club received a transfer offer.",
        "audience": "club_owner",
        "deep_link_route": "/app/market",
        "preference_key": "allow_market",
    },
    {
        "event_key": "offer_accepted",
        "topic": "transfer_market",
        "template_key": "transfer.offer.accepted",
        "title": "Offer accepted",
        "default_message": "A transfer offer has been accepted.",
        "audience": "buyer_seller",
        "deep_link_route": "/app/market",
        "preference_key": "allow_market",
    },
    {
        "event_key": "loan_expiring",
        "topic": "transfer_market",
        "template_key": "loan.expiring",
        "title": "Loan expiring",
        "default_message": "A player loan is approaching expiry.",
        "audience": "club_owner",
        "deep_link_route": "/app/market",
        "preference_key": "allow_market",
    },
    {
        "event_key": "swap_proposed",
        "topic": "transfer_market",
        "template_key": "swap.proposed",
        "title": "Swap proposed",
        "default_message": "A swap proposal is waiting for review.",
        "audience": "club_owner",
        "deep_link_route": "/app/market",
        "preference_key": "allow_market",
    },
    {
        "event_key": "coin_trader_order_accepted",
        "topic": "coin_trader",
        "template_key": "coin_trader.order.accepted",
        "title": "Coin trader order accepted",
        "default_message": "A coin trader accepted an order.",
        "audience": "buyer_seller",
        "deep_link_route": "/app/coin-traders",
        "preference_key": "allow_market",
    },
    {
        "event_key": "escrow_locked",
        "topic": "wallet",
        "template_key": "escrow.locked",
        "title": "Escrow locked",
        "default_message": "Funds or assets have been locked in escrow.",
        "audience": "buyer_seller",
        "deep_link_route": "/app/wallet",
        "preference_key": "allow_wallet",
    },
    {
        "event_key": "payment_window_expiring",
        "topic": "wallet",
        "template_key": "payment.window.expiring",
        "title": "Payment window expiring",
        "default_message": "A payment window is close to expiry.",
        "audience": "user",
        "deep_link_route": "/app/wallet",
        "preference_key": "allow_wallet",
    },
    {
        "event_key": "payment_confirmed",
        "topic": "wallet",
        "template_key": "payment.confirmed",
        "title": "Payment confirmed",
        "default_message": "A payment has been confirmed.",
        "audience": "user",
        "deep_link_route": "/app/wallet",
        "preference_key": "allow_wallet",
    },
    {
        "event_key": "coins_released",
        "topic": "wallet",
        "template_key": "coins.released",
        "title": "Coins released",
        "default_message": "Coins have been released from escrow.",
        "audience": "user",
        "deep_link_route": "/app/wallet",
        "preference_key": "allow_wallet",
    },
    {
        "event_key": "dispute_opened",
        "topic": "dispute",
        "template_key": "dispute.opened",
        "title": "Dispute opened",
        "default_message": "A dispute has been opened and needs attention.",
        "audience": "user_admin",
        "deep_link_route": "/notifications",
        "preference_key": "allow_market",
    },
    {
        "event_key": "kyc_approved",
        "topic": "kyc",
        "template_key": "kyc.approved",
        "title": "KYC approved",
        "default_message": "KYC verification has been approved.",
        "audience": "user",
        "deep_link_route": "/app/wallet",
        "preference_key": "allow_wallet",
    },
    {
        "event_key": "kyc_rejected",
        "topic": "kyc",
        "template_key": "kyc.rejected",
        "title": "KYC rejected",
        "default_message": "KYC verification needs another review.",
        "audience": "user",
        "deep_link_route": "/app/wallet",
        "preference_key": "allow_wallet",
    },
    {
        "event_key": "academy_regen_generated",
        "topic": "club",
        "template_key": "academy.regen.generated",
        "title": "Academy prospect generated",
        "default_message": "A new academy prospect is ready for review.",
        "audience": "club_owner",
        "deep_link_route": "/app/club",
        "preference_key": "allow_competition",
    },
    {
        "event_key": "sponsorship_paid",
        "topic": "sponsorship",
        "template_key": "sponsorship.paid",
        "title": "Sponsorship paid",
        "default_message": "A sponsorship payout has settled.",
        "audience": "club_owner",
        "deep_link_route": "/app/club",
        "preference_key": "allow_wallet",
    },
    {
        "event_key": "fan_gift_received",
        "topic": "social",
        "template_key": "fan.gift.received",
        "title": "Fan gift received",
        "default_message": "A fan sent a gift.",
        "audience": "creator_club_player",
        "deep_link_route": "/app/community",
        "preference_key": "allow_social",
    },
    {
        "event_key": "award_nomination",
        "topic": "competition",
        "template_key": "award.nomination",
        "title": "Award nomination",
        "default_message": "A player, club, or creator received an award nomination.",
        "audience": "user",
        "deep_link_route": "/app/play",
        "preference_key": "allow_competition",
    },
    {
        "event_key": "national_rental_expiring",
        "topic": "competition",
        "template_key": "national.rental.expiring",
        "title": "National rental expiring",
        "default_message": "A national-team rental is approaching expiry.",
        "audience": "manager",
        "deep_link_route": "/national-team",
        "preference_key": "allow_competition",
    },
    {
        "event_key": "ticket_purchased",
        "topic": "ticketing",
        "template_key": "ticket.purchased",
        "title": "Ticket purchased",
        "default_message": "A match ticket purchase was confirmed.",
        "audience": "fan",
        "deep_link_route": "/app/play",
        "preference_key": "allow_competition",
    },
    {
        "event_key": "card_offer_received",
        "topic": "player_cards",
        "template_key": "card.offer.received",
        "title": "Card offer received",
        "default_message": "A collectible card offer is waiting.",
        "audience": "user",
        "deep_link_route": "/player-cards",
        "preference_key": "allow_market",
    },
    {
        "event_key": "staff_contract_expiring",
        "topic": "club",
        "template_key": "staff.contract.expiring",
        "title": "Staff contract expiring",
        "default_message": "A club staff contract is close to expiry.",
        "audience": "club_owner",
        "deep_link_route": "/app/club",
        "preference_key": "allow_competition",
    },
    {
        "event_key": "club_readiness_complete",
        "topic": "club",
        "template_key": "club.readiness.complete",
        "title": "Club readiness complete",
        "default_message": "Your club is ready for competition entry.",
        "audience": "club_owner",
        "deep_link_route": "/app/club",
        "preference_key": "allow_competition",
    },
    {
        "event_key": "squad_registration_locked",
        "topic": "club",
        "template_key": "squad.registration.locked",
        "title": "Squad registration locked",
        "default_message": "A squad registration has been locked for competition entry.",
        "audience": "club_owner",
        "deep_link_route": "/app/club",
        "preference_key": "allow_competition",
    },
    {
        "event_key": "staff_hired",
        "topic": "club",
        "template_key": "staff.hired",
        "title": "Staff hired",
        "default_message": "A staff contract has been accepted.",
        "audience": "club_owner",
        "deep_link_route": "/app/club",
        "preference_key": "allow_competition",
    },
    {
        "event_key": "academy_contract_offered",
        "topic": "club",
        "template_key": "academy.contract.offered",
        "title": "Academy contract offered",
        "default_message": "An academy prospect has received a contract offer.",
        "audience": "club_owner",
        "deep_link_route": "/app/club",
        "preference_key": "allow_competition",
    },
    {
        "event_key": "academy_prospect_promoted",
        "topic": "club",
        "template_key": "academy.prospect.promoted",
        "title": "Academy prospect promoted",
        "default_message": "An academy prospect has been promoted to the senior squad.",
        "audience": "club_owner",
        "deep_link_route": "/world/regens",
        "preference_key": "allow_competition",
    },
    {
        "event_key": "sponsorship_application_received",
        "topic": "sponsorship",
        "template_key": "sponsorship.application.received",
        "title": "Sponsorship application received",
        "default_message": "A sponsorship application is waiting for review.",
        "audience": "sponsor_admin",
        "deep_link_route": "/app/club",
        "preference_key": "allow_market",
    },
    {
        "event_key": "sponsor_asset_needs_review",
        "topic": "sponsorship",
        "template_key": "sponsor.asset.review",
        "title": "Sponsor asset needs review",
        "default_message": "A sponsor brand asset requires moderation.",
        "audience": "admin",
        "deep_link_route": "/admin/moderation",
        "preference_key": "allow_market",
    },
    {
        "event_key": "federation_vote_opened",
        "topic": "competition",
        "template_key": "federation.vote.opened",
        "title": "Federation vote opened",
        "default_message": "A federation governance vote is open.",
        "audience": "federation_member",
        "deep_link_route": "/app/play",
        "preference_key": "allow_competition",
    },
    {
        "event_key": "federation_sanction_created",
        "topic": "competition",
        "template_key": "federation.sanction.created",
        "title": "Federation sanction created",
        "default_message": "A federation sanction has been created.",
        "audience": "club_owner_admin",
        "deep_link_route": "/app/play",
        "preference_key": "allow_competition",
    },
    {
        "event_key": "federation_sanction_resolved",
        "topic": "competition",
        "template_key": "federation.sanction.resolved",
        "title": "Federation sanction resolved",
        "default_message": "A federation sanction has been resolved.",
        "audience": "club_owner_admin",
        "deep_link_route": "/app/play",
        "preference_key": "allow_competition",
    },
    {
        "event_key": "prediction_settled",
        "topic": "social",
        "template_key": "prediction.settled",
        "title": "Prediction settled",
        "default_message": "A fan prediction has been settled.",
        "audience": "fan",
        "deep_link_route": "/app/community",
        "preference_key": "allow_social",
    },
    {
        "event_key": "fan_war_reward",
        "topic": "social",
        "template_key": "fan_war.reward",
        "title": "Fan war reward",
        "default_message": "A fan war reward has been issued.",
        "audience": "fan",
        "deep_link_route": "/app/community",
        "preference_key": "allow_social",
    },
    {
        "event_key": "clip_approved",
        "topic": "broadcast",
        "template_key": "clip.approved",
        "title": "Clip approved",
        "default_message": "A clip has been approved for distribution.",
        "audience": "creator_admin",
        "deep_link_route": "/news",
        "preference_key": "allow_broadcasts",
    },
    {
        "event_key": "clip_blocked",
        "topic": "broadcast",
        "template_key": "clip.blocked",
        "title": "Clip blocked",
        "default_message": "A clip was blocked by moderation or rights checks.",
        "audience": "creator_admin",
        "deep_link_route": "/news",
        "preference_key": "allow_broadcasts",
    },
    {
        "event_key": "broadcast_package_purchased",
        "topic": "broadcast",
        "template_key": "broadcast.package.purchased",
        "title": "Broadcast package purchased",
        "default_message": "A broadcast package purchase was confirmed.",
        "audience": "user",
        "deep_link_route": "/broadcast/live",
        "preference_key": "allow_broadcasts",
    },
    {
        "event_key": "creator_clip_revenue_paid",
        "topic": "broadcast",
        "template_key": "creator.clip.revenue.paid",
        "title": "Clip revenue paid",
        "default_message": "Creator clip revenue has been paid.",
        "audience": "creator",
        "deep_link_route": "/news",
        "preference_key": "allow_wallet",
    },
    {
        "event_key": "ticket_resale_sold",
        "topic": "ticketing",
        "template_key": "ticket.resale.sold",
        "title": "Ticket resale sold",
        "default_message": "A resale ticket has sold.",
        "audience": "fan",
        "deep_link_route": "/app/play",
        "preference_key": "allow_competition",
    },
    {
        "event_key": "ticket_attendance_reward",
        "topic": "ticketing",
        "template_key": "ticket.attendance.reward",
        "title": "Attendance reward issued",
        "default_message": "A ticket attendance reward has been issued.",
        "audience": "fan",
        "deep_link_route": "/app/play",
        "preference_key": "allow_competition",
    },
    {
        "event_key": "card_pack_opened",
        "topic": "player_cards",
        "template_key": "card.pack.opened",
        "title": "Card pack opened",
        "default_message": "A player card pack has been opened.",
        "audience": "user",
        "deep_link_route": "/player-cards",
        "preference_key": "allow_market",
    },
    {
        "event_key": "card_listing_sold",
        "topic": "player_cards",
        "template_key": "card.listing.sold",
        "title": "Card listing sold",
        "default_message": "A player card listing has sold.",
        "audience": "buyer_seller",
        "deep_link_route": "/player-cards",
        "preference_key": "allow_market",
    },
    {
        "event_key": "feature_flag_changed",
        "topic": "admin",
        "template_key": "feature.flag.changed",
        "title": "Feature flag changed",
        "default_message": "A feature flag changed in launch control.",
        "audience": "admin",
        "deep_link_route": "/admin/launch-control",
        "preference_key": "allow_broadcasts",
    },
    {
        "event_key": "kill_switch_enabled",
        "topic": "admin",
        "template_key": "kill_switch.enabled",
        "title": "Kill switch enabled",
        "default_message": "A launch-control kill switch has been enabled.",
        "audience": "admin",
        "deep_link_route": "/admin/launch-control",
        "preference_key": "allow_broadcasts",
    },
    {
        "event_key": "beta_access_granted",
        "topic": "admin",
        "template_key": "beta_access.granted",
        "title": "Beta access granted",
        "default_message": "A beta access grant changed in launch control.",
        "audience": "admin_user",
        "deep_link_route": "/admin/launch-control",
        "preference_key": "allow_broadcasts",
    },
    {
        "event_key": "beta_access_revoked",
        "topic": "admin",
        "template_key": "beta_access.revoked",
        "title": "Beta access revoked",
        "default_message": "A beta access grant was revoked in launch control.",
        "audience": "admin_user",
        "deep_link_route": "/admin/launch-control",
        "preference_key": "allow_broadcasts",
    },
    {
        "event_key": "operations_readiness_blocked",
        "topic": "admin",
        "template_key": "operations.readiness.blocked",
        "title": "Operations readiness blocked",
        "default_message": "An operations readiness queue is blocked.",
        "audience": "admin",
        "deep_link_route": "/admin/ops",
        "preference_key": "allow_broadcasts",
    },
)

QUALIFICATION_TEMPLATE_MESSAGES: dict[str, tuple[str, str]] = {
    "qualified": ("qualified", "You qualified from {competition_name}."),
    "playoff": ("reached_playoff", "You reached the playoff stage in {competition_name}."),
    "champions_league": (
        "qualified_champions_league",
        "You qualified for the Champions League from {competition_name}.",
    ),
    "world_super_cup": (
        "qualified_world_super_cup",
        "You qualified for the World Super Cup from {competition_name}.",
    ),
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _fixture_label(payload: dict[str, Any]) -> str:
    home = str(payload.get("home_club_name") or "Home club").strip()
    away = str(payload.get("away_club_name") or "Away club").strip()
    return f"{home} vs {away}"


def _competition_name(payload: dict[str, Any]) -> str:
    return str(payload.get("competition_name") or "your competition").strip()


@dataclass(frozen=True, slots=True)
class Notification:
    notification_id: str
    user_id: str | None
    topic: str
    template_key: str | None
    resource_id: str | None
    fixture_id: str | None
    competition_id: str | None
    message: str
    metadata: dict[str, Any]
    created_at: datetime


@dataclass(slots=True)
class NotificationCenter:
    _notifications: list[Notification] = field(default_factory=list)
    _lock: RLock = field(default_factory=RLock)

    def handle_event(self, event: DomainEvent) -> None:
        for notification in self._translate(event):
            with self._lock:
                self._notifications.append(notification)

    def list_for_user(self, user_id: str, limit: int = 20) -> list[Notification]:
        with self._lock:
            items = [item for item in self._notifications if item.user_id in {None, user_id}]
            return list(reversed(items[-limit:]))

    def _translate(self, event: DomainEvent) -> list[Notification]:
        payload = event.payload
        created_at = event.occurred_at
        if event.name.startswith("wallet."):
            user_id = payload.get("user_id") or payload.get("owner_user_id")
            return [self._build_notification(user_id, "wallet", event.name.replace(".", " "), payload, created_at)] if isinstance(user_id, str) else []
        if event.name == "JACKPOT_TRIGGERED":
            notifications: list[Notification] = []
            for winner in payload.get("winners") or []:
                if not isinstance(winner, dict):
                    continue
                user_id = winner.get("user_id")
                if isinstance(user_id, str):
                    notifications.append(
                        self._build_notification(
                            user_id,
                            "jackpot",
                            "jackpot dropped",
                            payload,
                            created_at,
                        )
                    )
            return notifications
        if event.name.startswith("market."):
            notifications: list[Notification] = []
            for key in ("seller_user_id", "buyer_user_id", "user_id"):
                user_id = payload.get(key)
                if isinstance(user_id, str):
                    notifications.append(self._build_notification(user_id, "market", event.name.replace(".", " "), payload, created_at))
            return notifications
        if event.name.startswith("competition."):
            return self._translate_competition_event(event)
        if event.name.startswith("hosted_competition."):
            user_id = payload.get("user_id")
            topic = "competition"
            return [self._build_notification(user_id if isinstance(user_id, str) else None, topic, event.name.replace(".", " "), payload, created_at)]
        if event.name.startswith("transfer_market."):
            notifications: list[Notification] = []
            for key in ("user_id", "seller_user_id", "buyer_user_id", "previous_bidder_user_id", "highest_bidder_user_id"):
                user_id = payload.get(key)
                if isinstance(user_id, str):
                    notifications.append(self._build_notification(user_id, "transfer_market", event.name.replace(".", " "), payload, created_at))
            return notifications
        return []

    def _translate_competition_event(self, event: DomainEvent) -> list[Notification]:
        payload = event.payload
        user_id = payload.get("user_id")
        target_user_id = user_id if isinstance(user_id, str) else None
        notification_payload = dict(payload)
        template_key, message = self._competition_template(event.name, payload)
        if template_key is not None:
            notification_payload["template_key"] = template_key
        if message is not None:
            notification_payload["message"] = message
        return [
            self._build_notification(
                target_user_id,
                "competition",
                event.name.replace(".", " "),
                notification_payload,
                event.occurred_at,
            )
        ]

    @staticmethod
    def _competition_template(event_name: str, payload: dict[str, Any]) -> tuple[str | None, str | None]:
        if event_name == "competition.match.starting":
            minutes = payload.get("minutes_until_start")
            if minutes == 10:
                return "match_starts_10m", f"{_fixture_label(payload)} starts in 10 minutes."
            if minutes == 1:
                return "match_starts_1m", f"{_fixture_label(payload)} starts in 1 minute."
        if event_name == "competition.match.live":
            return "match_live_now", f"{_fixture_label(payload)} is live now."
        if event_name == "competition.match.result":
            result = str(payload.get("result") or "").strip().lower()
            home_goals = payload.get("home_goals")
            away_goals = payload.get("away_goals")
            if result == "won":
                return "you_won", f"You won {_fixture_label(payload)} {home_goals}-{away_goals}."
            if result == "lost":
                return "you_lost", f"You lost {_fixture_label(payload)} {home_goals}-{away_goals}."
        if event_name == "competition.qualification.updated":
            status = str(payload.get("qualification_status") or "").strip().lower()
            template = QUALIFICATION_TEMPLATE_MESSAGES.get(status)
            if template is not None:
                template_key, message_template = template
                return template_key, message_template.format(
                    competition_name=_competition_name(payload),
                )
        if event_name == "competition.fast_cup.starting":
            return "fast_cup_starts_soon", "The next fast cup starts in 15 minutes."
        return None, None

    @staticmethod
    def _build_notification(user_id: str | None, topic: str, message: str, payload: dict[str, Any], created_at: datetime) -> Notification:
        template_key = payload.get("template_key")
        resolved_message = payload.get("message")
        return Notification(
            notification_id=f"ntf_{uuid4().hex[:12]}",
            user_id=user_id,
            topic=topic,
            template_key=str(template_key) if template_key is not None else None,
            resource_id=str(payload.get("resource_id")) if payload.get("resource_id") is not None else None,
            fixture_id=str(payload.get("fixture_id")) if payload.get("fixture_id") is not None else None,
            competition_id=str(payload.get("competition_id")) if payload.get("competition_id") is not None else None,
            message=str(resolved_message) if isinstance(resolved_message, str) and resolved_message.strip() else message,
            metadata={k: v for k, v in payload.items() if isinstance(k, str)},
            created_at=created_at,
        )


class NotificationServiceError(ValueError):
    pass


@dataclass(slots=True)
class NotificationSettingsService:
    session: Session

    def get_or_create_preferences(self, *, actor: User) -> NotificationPreference:
        pref = self.session.scalar(select(NotificationPreference).where(NotificationPreference.user_id == actor.id))
        if pref is None:
            pref = NotificationPreference(user_id=actor.id)
            self.session.add(pref)
            self.session.flush()
        return pref

    def update_preferences(self, *, actor: User, payload) -> NotificationPreference:
        pref = self.get_or_create_preferences(actor=actor)
        for key, value in payload.model_dump().items():
            setattr(pref, key, value)
        self.session.flush()
        return pref

    def list_subscriptions(self, *, actor: User) -> list[NotificationSubscription]:
        stmt = select(NotificationSubscription).where(NotificationSubscription.user_id == actor.id).order_by(NotificationSubscription.updated_at.desc())
        return list(self.session.scalars(stmt).all())

    def upsert_subscription(self, *, actor: User, payload) -> NotificationSubscription:
        item = self.session.scalar(select(NotificationSubscription).where(NotificationSubscription.user_id == actor.id, NotificationSubscription.subscription_key == payload.subscription_key))
        if item is None:
            item = NotificationSubscription(user_id=actor.id, subscription_key=payload.subscription_key)
            self.session.add(item)
        item.subscription_type = payload.subscription_type
        item.label = payload.label
        item.active = payload.active
        item.metadata_json = payload.metadata_json
        self.session.flush()
        return item

    def remove_subscription(self, *, actor: User, subscription_id: str) -> None:
        item = self.session.get(NotificationSubscription, subscription_id)
        if item is None or item.user_id != actor.id:
            raise NotificationServiceError("Notification subscription was not found.")
        self.session.delete(item)
        self.session.flush()

    def list_announcements(self, *, active_only: bool = True) -> list[PlatformAnnouncement]:
        stmt = select(PlatformAnnouncement)
        if active_only:
            stmt = stmt.where(PlatformAnnouncement.active.is_(True))
        stmt = stmt.order_by(PlatformAnnouncement.created_at.desc())
        return list(self.session.scalars(stmt).all())

    def publish_announcement(self, *, actor: User, payload) -> PlatformAnnouncement:
        item = self.session.scalar(select(PlatformAnnouncement).where(PlatformAnnouncement.announcement_key == payload.announcement_key))
        if item is None:
            item = PlatformAnnouncement(announcement_key=payload.announcement_key, published_by_user_id=actor.id)
            self.session.add(item)
        item.title = payload.title
        item.body = payload.body
        item.audience = payload.audience
        item.severity = payload.severity
        item.active = payload.active
        item.deliver_as_notification = payload.deliver_as_notification
        item.metadata_json = payload.metadata_json
        self.session.flush()
        if item.deliver_as_notification and item.active:
            self._fan_out_announcement(item)
        return item

    def _fan_out_announcement(self, item: PlatformAnnouncement) -> None:
        users = list(self.session.scalars(select(User)).all())
        for user in users:
            pref = self.session.scalar(select(NotificationPreference).where(NotificationPreference.user_id == user.id))
            if pref is not None and not pref.allow_broadcasts:
                continue
            self.session.add(
                NotificationRecord(
                    user_id=user.id,
                    topic="announcement",
                    template_key=item.announcement_key,
                    resource_type="announcement",
                    resource_id=item.id,
                    message=item.title,
                    metadata_json={"severity": item.severity, "body": item.body, **(item.metadata_json or {})},
                )
            )
        self.session.flush()


@dataclass(slots=True)
class NotificationEventMatrixService:
    session: Session

    def list_matrix(self) -> list[NotificationEventMatrixItemView]:
        return [NotificationEventMatrixItemView(**item) for item in NOTIFICATION_EVENT_MATRIX]

    def get_matrix_item(self, event_key: str) -> NotificationEventMatrixItemView:
        normalized = event_key.strip().lower()
        for item in self.list_matrix():
            if item.event_key == normalized:
                return item
        raise NotificationServiceError("notification_event_not_found")

    def publish_test_event(self, *, actor: User, payload: NotificationTestEventRequest) -> tuple[NotificationRecord, NotificationEventMatrixItemView]:
        item = self.get_matrix_item(payload.event_key)
        target = self.session.get(User, payload.target_user_id)
        if target is None:
            raise NotificationServiceError("target_user_not_found")
        message = payload.message.strip() if payload.message is not None else ""
        metadata = {
            "title": item.title,
            "event_key": item.event_key,
            "deep_link_route": item.deep_link_route,
            "audience": item.audience,
            "tested_by_admin_user_id": actor.id,
            **payload.metadata_json,
        }
        record = NotificationRecord(
            user_id=target.id,
            topic=item.topic,
            template_key=item.template_key,
            resource_type=item.event_key,
            resource_id=payload.resource_id,
            message=message or item.default_message,
            metadata_json=metadata,
        )
        self.session.add(record)
        self.session.flush()
        return record, item

    def publish_event(
        self,
        *,
        event_key: str,
        target_user_ids: list[str] | tuple[str, ...],
        resource_id: str | None = None,
        message: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> list[NotificationRecord]:
        item = self.get_matrix_item(event_key)
        records: list[NotificationRecord] = []
        seen: set[str] = set()
        for user_id in target_user_ids:
            normalized_user_id = user_id.strip()
            if not normalized_user_id or normalized_user_id in seen:
                continue
            seen.add(normalized_user_id)
            target = self.session.get(User, normalized_user_id)
            if target is None or not self._allows_matrix_item(target, item):
                continue
            record = NotificationRecord(
                user_id=target.id,
                topic=item.topic,
                template_key=item.template_key,
                resource_type=item.event_key,
                resource_id=resource_id,
                message=message.strip() if message and message.strip() else item.default_message,
                metadata_json={
                    "title": item.title,
                    "event_key": item.event_key,
                    "deep_link_route": item.deep_link_route,
                    "audience": item.audience,
                    **(metadata_json or {}),
                },
            )
            self.session.add(record)
            records.append(record)
        self.session.flush()
        return records

    def _allows_matrix_item(self, user: User, item: NotificationEventMatrixItemView) -> bool:
        preference_key = (item.preference_key or "").strip()
        if not preference_key:
            return True
        pref = self.session.scalar(select(NotificationPreference).where(NotificationPreference.user_id == user.id))
        if pref is None:
            return True
        return bool(getattr(pref, preference_key, True))
