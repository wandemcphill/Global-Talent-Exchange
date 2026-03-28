from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class PlayerShareMarket(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_share_markets"
    __table_args__ = (UniqueConstraint("player_id", name="uq_player_share_markets_player_id"),)

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    total_shares: Mapped[int] = mapped_column(Integer, nullable=False, default=1000, server_default="1000")
    circulating_shares: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    share_price_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    revenue_distributed_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PlayerShareHolding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_share_holdings"
    __table_args__ = (UniqueConstraint("user_id", "player_id", name="uq_player_share_holdings_user_player"),)

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    share_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    average_cost_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    dividends_earned_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped["User"] = relationship("User")


class PlayerShareEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "player_share_events"

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    share_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    price_per_share_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    gross_amount_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped["User | None"] = relationship("User", foreign_keys=[user_id])
    actor_user: Mapped["User | None"] = relationship("User", foreign_keys=[actor_user_id])


__all__ = ["PlayerShareEvent", "PlayerShareHolding", "PlayerShareMarket"]
