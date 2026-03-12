from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.common.enums.referral_event_type import ReferralEventType
from backend.app.common.enums.referral_source_channel import ReferralSourceChannel
from backend.app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin, utcnow


class ReferralEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "referral_events"

    event_key: Mapped[str] = mapped_column(String(96), nullable=False, unique=True, index=True)
    referral_attribution_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("referral_attributions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    referred_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    referrer_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    creator_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    share_code_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("share_codes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[ReferralEventType] = mapped_column(
        Enum(
            ReferralEventType,
            name="referral_event_type",
            native_enum=False,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
    )
    source_channel: Mapped[ReferralSourceChannel] = mapped_column(
        Enum(
            ReferralSourceChannel,
            name="referral_source_channel",
            native_enum=False,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default="CURRENT_TIMESTAMP",
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    manual_review_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    fraud_suspected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    event_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
