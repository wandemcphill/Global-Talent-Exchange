from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BettingProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "betting_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_betting_profiles_user_id"),)

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    region_code: Mapped[str] = mapped_column(String(32), nullable=False, default="GLOBAL", server_default="GLOBAL", index=True)
    compliance_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="regulated", server_default="regulated")
    is_opted_in: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="0")
    is_enabled: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="1")
    available_bet_balance: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    locked_bet_balance: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    max_bet_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("50.0000"),
        server_default="50.0000",
    )
    daily_loss_cap: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("250.0000"),
        server_default="250.0000",
    )
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    self_excluded_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_bet_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BetTicket(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "bet_tickets"
    __table_args__ = (
        Index("ix_bet_tickets_match_id_status", "match_id", "status"),
        Index("ix_bet_tickets_user_id_created_at", "user_id", "created_at"),
    )

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    match_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    event_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("global_events.id", ondelete="SET NULL"), nullable=True, index=True)
    bet_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    selection_key: Mapped[str] = mapped_column(String(160), nullable=False)
    selection_label: Mapped[str] = mapped_column(String(200), nullable=False)
    region_code: Mapped[str] = mapped_column(String(32), nullable=False, default="GLOBAL", server_default="GLOBAL")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="placed", server_default="placed", index=True)
    stake_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    odds_decimal: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=Decimal("1.0000"),
        server_default="1.0000",
    )
    implied_probability: Mapped[Decimal] = mapped_column(
        Numeric(8, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    potential_payout_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    market_demand_factor: Mapped[Decimal] = mapped_column(
        Numeric(8, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    risk_adjustment_factor: Mapped[Decimal] = mapped_column(
        Numeric(8, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    settled_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    placed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BetAuditLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "bet_audit_logs"
    __table_args__ = (Index("ix_bet_audit_logs_user_id_created_at", "user_id", "created_at"),)

    bet_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("bet_tickets.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    before_available_balance: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    after_available_balance: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    before_locked_balance: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    after_locked_balance: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BetIntegrityAlert(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "bet_integrity_alerts"
    __table_args__ = (Index("ix_bet_integrity_alerts_match_id_status", "match_id", "status"),)

    match_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    bet_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("bet_tickets.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    issue_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(24), nullable=False, default="low", server_default="low")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open", server_default="open", index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["BetAuditLog", "BetIntegrityAlert", "BetTicket", "BettingProfile"]
