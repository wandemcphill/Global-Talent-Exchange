from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, Enum as SqlEnum, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class DailyChallengeStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class DailyChallenge(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "daily_challenges"
    __table_args__ = (
        UniqueConstraint("challenge_key", name="uq_daily_challenges_challenge_key"),
    )

    challenge_key: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reward_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal('0.0000'))
    reward_unit: Mapped[str] = mapped_column(String(16), nullable=False, default='credit')
    claim_limit_per_day: Mapped[int] = mapped_column(nullable=False, default=1)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=100)
    status: Mapped[DailyChallengeStatus] = mapped_column(
        SqlEnum(DailyChallengeStatus, name='dailychallengestatus'),
        nullable=False,
        default=DailyChallengeStatus.ACTIVE,
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(nullable=False, default=dict)


class DailyChallengeClaim(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "daily_challenge_claims"
    __table_args__ = (
        UniqueConstraint("user_id", "challenge_id", "claim_date", name="uq_daily_challenge_claims_user_challenge_date"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    challenge_id: Mapped[str] = mapped_column(ForeignKey("daily_challenges.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    reward_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal('0.0000'))
    reward_unit: Mapped[str] = mapped_column(String(16), nullable=False, default='credit')
    reward_settlement_id: Mapped[str | None] = mapped_column(ForeignKey("reward_settlements.id", ondelete="SET NULL"), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(nullable=False, default=dict)
    claimed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
