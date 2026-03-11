from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from backend.app.core.events import DomainEvent


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class Notification:
    notification_id: str
    user_id: str | None
    topic: str
    message: str
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
        notifications: list[Notification] = []
        if event.name.startswith("wallet."):
            user_id = payload.get("user_id")
            if isinstance(user_id, str):
                notifications.append(
                    Notification(
                        notification_id=f"ntf_{uuid4().hex[:12]}",
                        user_id=user_id,
                        topic="wallet",
                        message=event.name.replace(".", " "),
                        created_at=created_at,
                    )
                )
        elif event.name.startswith("market."):
            for key in ("seller_user_id", "buyer_user_id", "user_id"):
                user_id = payload.get(key)
                if isinstance(user_id, str):
                    notifications.append(
                        Notification(
                            notification_id=f"ntf_{uuid4().hex[:12]}",
                            user_id=user_id,
                            topic="market",
                            message=event.name.replace(".", " "),
                            created_at=created_at,
                        )
                    )
        elif event.name.startswith("value.") or event.name.startswith("jobs."):
            notifications.append(
                Notification(
                    notification_id=f"ntf_{uuid4().hex[:12]}",
                    user_id=None,
                    topic=event.name.split(".", maxsplit=1)[0],
                    message=event.name.replace(".", " "),
                    created_at=created_at,
                )
            )
        return notifications
