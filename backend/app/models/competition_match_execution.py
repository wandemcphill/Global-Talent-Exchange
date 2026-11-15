from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class CompetitionMatchExecution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competition_match_executions"
    __table_args__ = (
        Index(
            "ix_competition_match_executions_status_next_step",
            "execution_status",
            "next_step_at",
        ),
    )

    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    execution_status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="scheduled",
        server_default="scheduled",
        index=True,
    )
    execution_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    current_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    target_end_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=90, server_default="90")
    step_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_event_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    clock_phase: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pre_match",
        server_default="pre_match",
    )
    broadcast_category: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="regular",
        server_default="regular",
    )
    assigned_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=600, server_default="600")
    elapsed_broadcast_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    paused_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    halftime_resume_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_step_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    simulation_request_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    checkpoint_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    home_tactics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    away_tactics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    committed_events_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    projected_tail_events_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CompetitionMatchTacticalCommand(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "competition_match_tactical_commands"
    __table_args__ = (
        UniqueConstraint(
            "match_id",
            "idempotency_key",
            name="uq_competition_match_tactical_commands_idempotency",
        ),
    )

    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    execution_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("competition_match_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    expected_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    resulting_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submitted_at_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    effective_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="accepted", server_default="accepted", index=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    command_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    response_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["CompetitionMatchExecution", "CompetitionMatchTacticalCommand"]
