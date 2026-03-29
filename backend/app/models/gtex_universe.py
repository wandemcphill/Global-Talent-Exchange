from __future__ import annotations

from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class CareerPlayerStatus(StrEnum):
    ACTIVE = "active"
    RETIRED = "retired"


class CareerDecisionType(StrEnum):
    TRAINING = "training"
    TRANSFER = "transfer"
    CONTRACT = "contract"
    RETIREMENT = "retirement"


class RealWorldMappingType(StrEnum):
    PLAYER = "player"
    TEAM = "team"


class RealWorldEventStatus(StrEnum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    COMPLETED = "completed"
    MIRRORED = "mirrored"


class ManagerMatchHistory(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "manager_match_history"

    manager_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("manager_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    opponent_manager_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("manager_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_match_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_match_type: Mapped[str] = mapped_column(String(32), nullable=False, default="gtex", server_default="gtex")
    team_side: Mapped[str] = mapped_column(String(8), nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    intensity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    rivalry_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    tactical_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    narrative_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ManagerVsManagerHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "manager_vs_manager_history"
    __table_args__ = (
        UniqueConstraint("manager_a_id", "manager_b_id", name="uq_manager_vs_manager_history_pair"),
    )

    manager_a_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("manager_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    manager_b_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("manager_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    meetings: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    manager_a_wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    manager_b_wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    draws: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    rivalry_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    last_match_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    narrative_tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CareerPlayer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "career_players"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_career_players_user_id"),
        UniqueConstraint("player_id", name="uq_career_players_player_id"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    current_club: Mapped[str | None] = mapped_column(String(160), nullable=True)
    current_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_clubs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    career_stats: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    growth_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.08, server_default="0.08")
    xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    training_focus: Mapped[str] = mapped_column(String(64), nullable=False, default="balanced", server_default="balanced")
    current_form: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default="0.5")
    marketability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default="0.5")
    prestige_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[CareerPlayerStatus] = mapped_column(
        Enum(CareerPlayerStatus, name="career_player_status", native_enum=False),
        nullable=False,
        default=CareerPlayerStatus.ACTIVE,
        server_default=CareerPlayerStatus.ACTIVE.value,
        index=True,
    )
    retired_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    legacy_summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CareerTrainingSession(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "career_training_sessions"

    career_player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("career_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    focus: Mapped[str] = mapped_column(String(64), nullable=False)
    intensity: Mapped[str] = mapped_column(String(16), nullable=False)
    xp_gained: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    form_gain: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    growth_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CareerDecision(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "career_decisions"

    career_player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("career_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    decision_type: Mapped[CareerDecisionType] = mapped_column(
        Enum(CareerDecisionType, name="career_decision_type", native_enum=False),
        nullable=False,
        index=True,
    )
    from_value: Mapped[str | None] = mapped_column(String(160), nullable=True)
    to_value: Mapped[str | None] = mapped_column(String(160), nullable=True)
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    decision_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CareerLegacyRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "career_legacy_records"
    __table_args__ = (
        UniqueConstraint("career_player_id", name="uq_career_legacy_records_career_player_id"),
    )

    career_player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("career_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    legacy_role: Mapped[str] = mapped_column(String(32), nullable=False, default="hall_of_fame", server_default="hall_of_fame")
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class RealWorldEntityMapping(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "real_world_entity_mappings"
    __table_args__ = (
        UniqueConstraint("mapping_type", "real_entity_id", "gtex_entity_id", name="uq_real_world_entity_mappings_triplet"),
    )

    mapping_type: Mapped[RealWorldMappingType] = mapped_column(
        Enum(RealWorldMappingType, name="real_world_mapping_type", native_enum=False),
        nullable=False,
        index=True,
    )
    real_entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    real_entity_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    gtex_entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    gtex_entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default="0.5")
    mapping_source: Mapped[str] = mapped_column(String(64), nullable=False, default="heuristic", server_default="heuristic")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class RealWorldEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "real_world_events"
    __table_args__ = (
        UniqueConstraint("provider_id", "external_key", name="uq_real_world_events_provider_key"),
    )

    provider_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("real_data_providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("real_world_competitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    home_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("real_world_clubs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    away_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("real_world_clubs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    external_key: Mapped[str] = mapped_column(String(128), nullable=False)
    headline: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, default="fixture", server_default="fixture")
    status: Mapped[RealWorldEventStatus] = mapped_column(
        Enum(RealWorldEventStatus, name="real_world_event_status", native_enum=False),
        nullable=False,
        default=RealWorldEventStatus.SCHEDULED,
        server_default=RealWorldEventStatus.SCHEDULED.value,
        index=True,
    )
    scheduled_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    started_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mirror_match_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gtex_matches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    magnitude_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    influence_applied_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    influence_summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "CareerDecision",
    "CareerDecisionType",
    "CareerLegacyRecord",
    "CareerPlayer",
    "CareerPlayerStatus",
    "CareerTrainingSession",
    "ManagerMatchHistory",
    "ManagerVsManagerHistory",
    "RealWorldEntityMapping",
    "RealWorldEvent",
    "RealWorldEventStatus",
    "RealWorldMappingType",
]
