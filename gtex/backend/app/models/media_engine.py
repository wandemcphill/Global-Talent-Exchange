from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MatchView(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'match_views'
    __table_args__ = (UniqueConstraint('user_id', 'match_key', 'view_date_key', name='uq_match_views_user_match_day'),)

    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    match_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    competition_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    view_date_key: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    watch_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default='0')
    premium_unlocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default='0')
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class PremiumVideoPurchase(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'premium_video_purchases'
    __table_args__ = (UniqueConstraint('user_id', 'match_key', name='uq_premium_video_purchases_user_match'),)

    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    match_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    competition_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    price_coin: Mapped[Decimal] = mapped_column(Numeric(18,4), nullable=False, default=Decimal('0.0000'), server_default='0')
    price_fancoin_equivalent: Mapped[Decimal] = mapped_column(Numeric(18,4), nullable=False, default=Decimal('0.0000'), server_default='0')
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class MatchRevenueSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'match_revenue_snapshots'
    __table_args__ = (UniqueConstraint('match_key', name='uq_match_revenue_snapshots_match_key'),)

    match_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    competition_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    home_club_id: Mapped[str | None] = mapped_column(ForeignKey('club_profiles.id', ondelete='SET NULL'), nullable=True, index=True)
    away_club_id: Mapped[str | None] = mapped_column(ForeignKey('club_profiles.id', ondelete='SET NULL'), nullable=True, index=True)
    total_views: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default='0')
    premium_purchases: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default='0')
    total_revenue_coin: Mapped[Decimal] = mapped_column(Numeric(18,4), nullable=False, default=Decimal('0.0000'), server_default='0')
    home_club_share_coin: Mapped[Decimal] = mapped_column(Numeric(18,4), nullable=False, default=Decimal('0.0000'), server_default='0')
    away_club_share_coin: Mapped[Decimal] = mapped_column(Numeric(18,4), nullable=False, default=Decimal('0.0000'), server_default='0')
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ['MatchView', 'PremiumVideoPurchase', 'MatchRevenueSnapshot']
