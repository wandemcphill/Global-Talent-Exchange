from __future__ import annotations

from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, Enum as SqlEnum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SupporterTokenStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"


class ClubStadium(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "club_stadiums"
    __table_args__ = (UniqueConstraint("club_id", name="uq_club_stadiums_club_id"),)

    club_id: Mapped[str] = mapped_column(ForeignKey("club_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=5000, server_default="5000")
    theme_key: Mapped[str] = mapped_column(String(64), nullable=False, default="default", server_default="default")
    gift_retention_bonus_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    revenue_multiplier_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=10000, server_default="10000")
    prestige_bonus_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class ClubFacility(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "club_facilities"
    __table_args__ = (UniqueConstraint("club_id", name="uq_club_facilities_club_id"),)

    club_id: Mapped[str] = mapped_column(ForeignKey("club_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    training_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    academy_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    medical_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    branding_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    upkeep_cost_fancoin: Mapped[Decimal] = mapped_column(Numeric(18,4), nullable=False, default=Decimal("0.0000"), server_default="0")


class ClubSupporterToken(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "club_supporter_tokens"
    __table_args__ = (UniqueConstraint("club_id", name="uq_club_supporter_tokens_club_id"),)

    club_id: Mapped[str] = mapped_column(ForeignKey("club_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    token_name: Mapped[str] = mapped_column(String(120), nullable=False)
    token_symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    circulating_supply: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    holder_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    influence_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[SupporterTokenStatus] = mapped_column(SqlEnum(SupporterTokenStatus, name="supportertokenstatus"), nullable=False, default=SupporterTokenStatus.ACTIVE)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(nullable=False, default=dict)


class ClubSupporterHolding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "club_supporter_holdings"
    __table_args__ = (UniqueConstraint("club_id", "user_id", name="uq_club_supporter_holdings_club_user"),)

    club_id: Mapped[str] = mapped_column(ForeignKey("club_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    influence_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_founding_supporter: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    metadata_json: Mapped[dict[str, object]] = mapped_column(nullable=False, default=dict)


__all__ = ["ClubStadium", "ClubFacility", "ClubSupporterToken", "ClubSupporterHolding", "SupporterTokenStatus"]
