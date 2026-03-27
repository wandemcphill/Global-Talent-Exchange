from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification_center import NotificationPreference, NotificationSubscription
from app.models.user import User


@dataclass(frozen=True, slots=True)
class DeliveryAttempt:
    success: bool
    provider_message_id: str | None = None
    failure_reason: str | None = None


class PushDeliveryGateway:
    def send(self, session: Session, *, user: User, payload: dict[str, object]) -> DeliveryAttempt:
        preference = session.scalar(
            select(NotificationPreference).where(NotificationPreference.user_id == user.id)
        )
        if preference is not None and not preference.allow_competition:
            return DeliveryAttempt(success=False, failure_reason="push_opted_out")
        subscription = session.scalar(
            select(NotificationSubscription).where(
                NotificationSubscription.user_id == user.id,
                NotificationSubscription.subscription_type == "fcm",
                NotificationSubscription.active.is_(True),
            )
        )
        token = None if subscription is None else str((subscription.metadata_json or {}).get("device_token") or "").strip()
        if not token:
            return DeliveryAttempt(success=False, failure_reason="missing_fcm_token")
        return DeliveryAttempt(success=True, provider_message_id=f"fcm:{uuid4().hex}")


class SmsDeliveryGateway:
    def send(self, _session: Session, *, user: User, payload: dict[str, object]) -> DeliveryAttempt:
        if not (user.phone_number or "").strip():
            return DeliveryAttempt(success=False, failure_reason="missing_phone_number")
        provider = "termii" if str(payload.get("preferred_sms_provider") or "").strip().lower() == "termii" else "twilio"
        return DeliveryAttempt(success=True, provider_message_id=f"{provider}:{uuid4().hex}")


__all__ = [
    "DeliveryAttempt",
    "PushDeliveryGateway",
    "SmsDeliveryGateway",
]
