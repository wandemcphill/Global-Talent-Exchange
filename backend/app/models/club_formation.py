from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ClubFormation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_formations"
    __table_args__ = (
        Index("ix_club_formations_club_status", "club_id", "status"),
        Index("ix_club_formations_published_at", "published_at"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    scheme: Mapped[str] = mapped_column(String(24), nullable=False, default="4-3-3", server_default="4-3-3")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft", server_default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    slots_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    chemistry_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    warnings_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    validation_blockers_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    source_formation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    updated_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    audit_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)


class ClubFormationAuditEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "club_formation_audit_events"
    __table_args__ = (
        Index("ix_club_formation_audit_events_formation_created", "formation_id", "created_at"),
        Index("ix_club_formation_audit_events_club_created", "club_id", "created_at"),
        Index("ix_club_formation_audit_events_action", "action"),
    )

    formation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_formations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
