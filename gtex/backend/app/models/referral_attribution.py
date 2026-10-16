from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums.referral_source_channel import ReferralSourceChannel
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class ReferralAttribution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "referral_attributions"
    __table_args__ = (
        UniqueConstraint("referred_user_id", name="uq_referral_attributions_referred_user_id"),
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
    source_channel: Mapped[ReferralSourceChannel] = mapped_column(
        Enum(
            ReferralSourceChannel,
            name="referral_source_channel",
            native_enum=False,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
    )
    first_touch_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default="CURRENT_TIMESTAMP",
    )
    attribution_status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    campaign_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    linked_competition_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
