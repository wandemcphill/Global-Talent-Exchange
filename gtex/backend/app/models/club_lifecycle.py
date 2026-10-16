from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ClubLifecycleState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_lifecycle_states"
    __table_args__ = (UniqueConstraint("club_id", name="uq_club_lifecycle_states_club_id"),)

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="created", server_default="created")
    previous_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    readiness_score: Mapped[int] = mapped_column(default=0, nullable=False, server_default="0")
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    advanced_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    advanced_by_user = relationship("User")


class ClubReadinessStatus(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_readiness_statuses"
    __table_args__ = (UniqueConstraint("club_id", name="uq_club_readiness_statuses_club_id"),)

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    readiness_score: Mapped[int] = mapped_column(default=0, nullable=False, server_default="0")
    checklist_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    blockers_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    recommended_state: Mapped[str] = mapped_column(String(32), nullable=False, default="created", server_default="created")
    competition_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")


class ClubSquadRegistration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_squad_registrations"
    __table_args__ = (
        UniqueConstraint("club_id", "season_label", name="uq_club_squad_registrations_club_season"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_label: Mapped[str] = mapped_column(String(32), nullable=False, default="launch", server_default="launch")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft")
    player_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    position_summary_json: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False, default=dict)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    locked_by_user = relationship("User")


class ClubRegistrationSlot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_registration_slots"
    __table_args__ = (
        UniqueConstraint("registration_id", "player_id", name="uq_club_registration_slots_registration_player"),
    )

    registration_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_squad_registrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position_group: Mapped[str] = mapped_column(String(32), nullable=False)
    slot_status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft")


class ClubEligibilityFlag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_eligibility_flags"
    __table_args__ = (
        UniqueConstraint("club_id", "flag_key", name="uq_club_eligibility_flags_club_key"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    flag_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="clear", server_default="clear")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ClubOperatingStatus(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_operating_statuses"
    __table_args__ = (UniqueConstraint("club_id", name="uq_club_operating_statuses_club_id"),)

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    operating_state: Mapped[str] = mapped_column(String(32), nullable=False, default="setup", server_default="setup")
    dashboard_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ClubLifecycleAuditEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "club_lifecycle_audit_events"

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    next_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    actor_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    actor = relationship("User")
