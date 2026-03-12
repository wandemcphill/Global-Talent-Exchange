from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.common.enums.referral_event_type import ReferralEventType
from backend.app.common.enums.referral_reward_status import ReferralRewardStatus
from backend.app.common.enums.referral_reward_type import ReferralRewardType
from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ReferralReward(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "referral_rewards"

    reward_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    referral_attribution_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("referral_attributions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reward_source_event_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("referral_events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    referred_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    beneficiary_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    beneficiary_creator_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    trigger_event_type: Mapped[ReferralEventType] = mapped_column(
        Enum(
            ReferralEventType,
            name="referral_event_type",
            native_enum=False,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
    )
    reward_type: Mapped[ReferralRewardType] = mapped_column(
        Enum(
            ReferralRewardType,
            name="referral_reward_type",
            native_enum=False,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
    )
    status: Mapped[ReferralRewardStatus] = mapped_column(
        Enum(
            ReferralRewardStatus,
            name="referral_reward_status",
            native_enum=False,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
        default=ReferralRewardStatus.PENDING,
    )
    reward_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    reward_unit: Mapped[str | None] = mapped_column(String(24), nullable=True)
    reward_reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hold_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reward_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
