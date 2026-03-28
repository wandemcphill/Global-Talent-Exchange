from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OwnershipGroup(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ownership_groups"
    __table_args__ = (
        Index("ix_ownership_groups_owner_user_id", "owner_user_id"),
        UniqueConstraint("owner_user_id", "name", name="uq_ownership_groups_owner_name"),
    )

    owner_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    clubs_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    budget_pool: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    reputation_score: Mapped[float] = mapped_column(nullable=False, default=0.0, server_default="0")
    philosophy: Mapped[str | None] = mapped_column(String(120), nullable=True)
    global_brand_strength: Mapped[float] = mapped_column(nullable=False, default=0.0, server_default="0")
    shared_budget_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class OwnershipGroupClub(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ownership_group_clubs"
    __table_args__ = (
        UniqueConstraint("group_id", "club_id", name="uq_ownership_group_clubs_group_club"),
        UniqueConstraint("club_id", name="uq_ownership_group_clubs_club_id"),
        Index("ix_ownership_group_clubs_group_id", "group_id"),
    )

    group_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ownership_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class OwnershipGroupBudgetMovement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ownership_group_budget_movements"
    __table_args__ = (
        UniqueConstraint("reference_key", name="uq_ownership_group_budget_movements_reference_key"),
        Index("ix_ownership_group_budget_movements_group_id", "group_id"),
    )

    group_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ownership_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    movement_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    reference_key: Mapped[str] = mapped_column(String(160), nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class OwnershipGroupEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ownership_group_events"
    __table_args__ = (
        Index("ix_ownership_group_events_group_id", "group_id"),
        Index("ix_ownership_group_events_event_type", "event_type"),
    )

    group_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ownership_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    headline: Mapped[str] = mapped_column(String(255), nullable=False)
    impact_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "OwnershipGroup",
    "OwnershipGroupBudgetMovement",
    "OwnershipGroupClub",
    "OwnershipGroupEvent",
]
