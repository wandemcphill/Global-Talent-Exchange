from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PlayerAgencyState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_agency_states"
    __table_args__ = (
        UniqueConstraint("player_id", name="uq_player_agency_states_player_id"),
        UniqueConstraint("regen_profile_id", name="uq_player_agency_states_regen_profile_id"),
        Index("ix_player_agency_states_current_club_id", "current_club_id"),
        Index("ix_player_agency_states_transfer_request_status", "transfer_request_status"),
        Index("ix_player_agency_states_career_stage", "career_stage"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    regen_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=True,
    )
    current_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    morale: Mapped[float] = mapped_column(nullable=False, default=50.0, server_default="50.0")
    happiness: Mapped[float] = mapped_column(nullable=False, default=50.0, server_default="50.0")
    transfer_appetite: Mapped[float] = mapped_column(nullable=False, default=0.0, server_default="0.0")
    contract_stance: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="balanced",
        server_default="balanced",
    )
    wage_satisfaction: Mapped[float] = mapped_column(nullable=False, default=50.0, server_default="50.0")
    playing_time_satisfaction: Mapped[float] = mapped_column(nullable=False, default=50.0, server_default="50.0")
    development_satisfaction: Mapped[float] = mapped_column(nullable=False, default=50.0, server_default="50.0")
    club_project_belief: Mapped[float] = mapped_column(nullable=False, default=50.0, server_default="50.0")
    grievance_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    promise_memory_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    unmet_expectations_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    recent_offer_cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    transfer_request_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="no_action",
        server_default="no_action",
    )
    preferred_role_band: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="rotation",
        server_default="rotation",
    )
    career_stage: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="prospect",
        server_default="prospect",
    )
    career_target_band: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="development-first",
        server_default="development-first",
    )
    salary_expectation_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    last_major_decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_contract_decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_transfer_decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_transfer_denial_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_transfer_request_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
