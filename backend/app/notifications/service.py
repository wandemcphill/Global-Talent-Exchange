from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.events import DomainEvent
from backend.app.models.notification_center import NotificationPreference, NotificationSubscription, PlatformAnnouncement
from backend.app.models.notification_record import NotificationRecord
from backend.app.models.user import User


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
            return [self._build_notification(payload.get("user_id"), "wallet", event.name.replace(".", " "), payload, created_at)] if isinstance(payload.get("user_id"), str) else []
        if event.name.startswith("market."):
            notifications: list[Notification] = []
            for key in ("seller_user_id", "buyer_user_id", "user_id"):
                user_id = payload.get(key)
                if isinstance(user_id, str):
                    notifications.append(self._build_notification(user_id, "market", event.name.replace(".", " "), payload, created_at))
            return notifications
        if event.name.startswith("competition.") or event.name.startswith("hosted_competition."):
            user_id = payload.get("user_id")
            topic = "competition"
            return [self._build_notification(user_id if isinstance(user_id, str) else None, topic, event.name.replace(".", " "), payload, created_at)]
        return []

    @staticmethod
    def _build_notification(user_id: str | None, topic: str, message: str, payload: dict[str, Any], created_at: datetime) -> Notification:
        return Notification(
            notification_id=f"ntf_{uuid4().hex[:12]}",
            user_id=user_id,
            topic=topic,
            template_key=None,
            resource_id=str(payload.get("resource_id")) if payload.get("resource_id") is not None else None,
            fixture_id=str(payload.get("fixture_id")) if payload.get("fixture_id") is not None else None,
            competition_id=str(payload.get("competition_id")) if payload.get("competition_id") is not None else None,
            message=message,
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
