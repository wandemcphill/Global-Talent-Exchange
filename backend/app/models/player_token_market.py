from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint, event
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.market.player_eligibility_policy import is_share_market_eligible
from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.players.token_market_defaults import resolve_player_share_market_config

if TYPE_CHECKING:
    from app.ingestion.models import Player
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

    player: Mapped["Player"] = relationship("Player", back_populates="share_market")

    @property
    def liquidity_coin(self) -> Decimal:
        raw_value = (self.metadata_json or {}).get("liquidity_coin", "0.0000")
        return Decimal(str(raw_value or "0.0000")).quantize(Decimal("0.0001"))


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

    player: Mapped["Player"] = relationship("Player", back_populates="share_holdings")
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

    player: Mapped["Player"] = relationship("Player", back_populates="share_events")
    user: Mapped["User | None"] = relationship("User", foreign_keys=[user_id])
    actor_user: Mapped["User | None"] = relationship("User", foreign_keys=[actor_user_id])


__all__ = ["PlayerShareEvent", "PlayerShareHolding", "PlayerShareMarket"]


@event.listens_for(Session, "before_flush")
def _auto_initialize_player_share_markets(session: Session, _flush_context, _instances) -> None:
    from app.ingestion.models import Player

    for pending in tuple(session.new):
        if not isinstance(pending, Player):
            continue
        if pending.share_market is not None or not is_share_market_eligible(pending):
            continue

        config = resolve_player_share_market_config(pending)
        pending.share_market = PlayerShareMarket(
            total_shares=config.total_shares,
            share_price_coin=config.share_price_coin,
            status=config.status,
            metadata_json={
                "player_name": pending.canonical_display_name or pending.full_name,
                "is_real_player": bool(pending.is_real_player),
                "real_player_tier": pending.real_player_tier,
                "market_issued": True,
                "auto_initialized": True,
                "liquidity_coin": str(config.liquidity_coin),
                "initial_liquidity_coin": str(config.liquidity_coin),
            },
        )
