from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class EconomyGovernorPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "economy_governor_policies"
    __table_args__ = (UniqueConstraint("policy_key", name="uq_economy_governor_policy_key"),)

    policy_key: Mapped[str] = mapped_column(String(32), nullable=False, default="default", server_default="default")
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="auto", server_default="auto")
    tournament_entry_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=Decimal("1.0000"),
        server_default="1.0000",
    )
    match_view_cost_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=Decimal("1.0000"),
        server_default="1.0000",
    )
    reward_payout_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=Decimal("1.0000"),
        server_default="1.0000",
    )
    free_prize_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=Decimal("1.0000"),
        server_default="1.0000",
    )
    agent_activity_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=Decimal("1.0000"),
        server_default="1.0000",
    )
    price_change_limit: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=Decimal("0.2500"),
        server_default="0.2500",
    )
    conversion_bonus_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    burn_bonus_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_metrics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    last_actions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    last_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    updated_by_user: Mapped["User | None"] = relationship("User")


__all__ = ["EconomyGovernorPolicy"]
