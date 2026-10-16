from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow

SQUAD_TIERS: tuple[str, ...] = ("first_team", "u21", "reserve")
SQUAD_TIER_SOURCES: tuple[str, ...] = ("academy", "transfer", "son", "mint", "manual")
SQUAD_TIER_STATUSES: tuple[str, ...] = ("active", "released", "promoted_out")


class ClubSquadTierMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Which tier (first_team / u21 / reserve) an owned player sits in at a club.

    A layer on top of the club<->player relationship; complementary to the
    academy youth feeder (see SQUAD_TIER_PIPELINE_DESIGN.md).
    """

    __tablename__ = "club_squad_tier_memberships"
    __table_args__ = (
        UniqueConstraint(
            "club_id", "player_id", "status", name="uq_squad_tier_club_player_status"
        ),
        Index("ix_squad_tier_club_tier_status", "club_id", "tier", "status"),
        Index("ix_squad_tier_status_evaluated", "status", "last_evaluated_at"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("club_profiles.id", ondelete="CASCADE"), nullable=False
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    tier: Mapped[str] = mapped_column(
        String(16), nullable=False, default="reserve", server_default="reserve"
    )
    source: Mapped[str] = mapped_column(
        String(16), nullable=False, default="manual", server_default="manual"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active"
    )
    joined_club_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    joined_tier_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    last_evaluated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )


__all__ = [
    "ClubSquadTierMembership",
    "SQUAD_TIERS",
    "SQUAD_TIER_SOURCES",
    "SQUAD_TIER_STATUSES",
]
