"""GTEX regen endorsement deals — platform-owned IP sponsorship on stars."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RegenEndorsementStatus(StrEnum):
    OFFERED = "offered"
    ACTIVE = "active"
    DECLINED = "declined"
    EXPIRED = "expired"
    COMPLETED = "completed"


class RegenEndorsementDeal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_endorsement_deals"

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sponsor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    brand_label: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[RegenEndorsementStatus] = mapped_column(
        Enum(RegenEndorsementStatus, name="regen_endorsement_status", native_enum=False),
        nullable=False,
        default=RegenEndorsementStatus.OFFERED,
        server_default=RegenEndorsementStatus.OFFERED.value,
        index=True,
    )
    term_months: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    deal_value_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    owner_share_ratio: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("0.6000"), server_default="0.6000"
    )
    platform_share_ratio: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("0.4000"), server_default="0.4000"
    )
    badge_label: Mapped[str] = mapped_column(String(80), nullable=False, default="Endorsed", server_default="Endorsed")
    creative_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    offered_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["RegenEndorsementDeal", "RegenEndorsementStatus"]
