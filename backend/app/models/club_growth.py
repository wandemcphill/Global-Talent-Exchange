from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ClubStaffProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_staff_profiles"
    __table_args__ = (
        UniqueConstraint("market_key", name="uq_club_staff_profiles_market_key"),
    )

    market_key: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    staff_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    rarity: Mapped[str] = mapped_column(String(32), nullable=False, default="standard", server_default="standard")
    skills_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    salary_minor: Mapped[int] = mapped_column(default=0, nullable=False, server_default="0")
    commission_bps: Mapped[int] = mapped_column(default=0, nullable=False, server_default="0")
    rating: Mapped[int] = mapped_column(default=50, nullable=False, server_default="50")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ClubStaffContract(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_staff_contracts"

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    staff_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_staff_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="offered", server_default="offered")
    salary_minor: Mapped[int] = mapped_column(default=0, nullable=False, server_default="0")
    commission_bps: Mapped[int] = mapped_column(default=0, nullable=False, server_default="0")
    duration_days: Mapped[int] = mapped_column(default=90, nullable=False, server_default="90")
    role_scope: Mapped[str] = mapped_column(String(64), nullable=False, default="club", server_default="club")
    exclusive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    terminated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    staff_profile = relationship("ClubStaffProfile")


class ClubStaffAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_staff_assignments"
    __table_args__ = (
        UniqueConstraint("club_id", "role_key", name="uq_club_staff_assignments_club_role"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    staff_contract_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_staff_contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_key: Mapped[str] = mapped_column(String(64), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    staff_contract = relationship("ClubStaffContract")


class ClubStaffPerformanceLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "club_staff_performance_logs"

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    staff_contract_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_staff_contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    rating_delta: Mapped[int] = mapped_column(default=0, nullable=False, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class AcademyProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "academy_profiles"
    __table_args__ = (UniqueConstraint("club_id", name="uq_academy_profiles_club_id"),)

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level: Mapped[int] = mapped_column(default=1, nullable=False, server_default="1")
    investment_minor: Mapped[int] = mapped_column(default=0, nullable=False, server_default="0")
    generation_cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class AcademyProspect(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "academy_prospects"

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academy_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("academy_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    nationality: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    position: Mapped[str] = mapped_column(String(8), nullable=False)
    age: Mapped[int] = mapped_column(default=16, nullable=False, server_default="16")
    personality_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    current_ability: Mapped[int] = mapped_column(default=35, nullable=False, server_default="35")
    potential: Mapped[int] = mapped_column(default=70, nullable=False, server_default="70")
    portrait_asset_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="discovered", server_default="discovered")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    academy_profile = relationship("AcademyProfile")


class AcademyTrainingPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "academy_training_plans"

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    focus: Mapped[str] = mapped_column(String(64), nullable=False, default="balanced", server_default="balanced")
    intensity: Mapped[str] = mapped_column(String(32), nullable=False, default="normal", server_default="normal")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class AcademyRegenContractOffer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "academy_regen_contract_offers"

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prospect_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("academy_prospects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="offered", server_default="offered")
    wage_minor: Mapped[int] = mapped_column(default=0, nullable=False, server_default="0")
    duration_months: Mapped[int] = mapped_column(default=24, nullable=False, server_default="24")
    response_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    prospect = relationship("AcademyProspect")


class AcademyPromotionHistory(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "academy_promotion_history"

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prospect_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("academy_prospects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    senior_player_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class AcademyGenerationRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "academy_generation_runs"

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_seed: Mapped[str] = mapped_column(String(128), nullable=False)
    prospects_created: Mapped[int] = mapped_column(default=0, nullable=False, server_default="0")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed", server_default="completed")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ClubGrowthAuditEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "club_growth_audit_events"

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(96), nullable=False)
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
