from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class RealityMode(StrEnum):
    PURE_REGEN = "pure_regen"
    HYBRID = "hybrid"
    REAL_ONLY = "real_only"


class RealDataSyncStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RealDataProvider(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "real_data_providers"
    __table_args__ = (
        UniqueConstraint("name", name="uq_real_data_providers_name"),
        Index("ix_real_data_providers_is_active", "is_active"),
        Index("ix_real_data_providers_last_sync_at", "last_sync_at"),
    )

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    api_endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    refresh_interval: Mapped[int] = mapped_column(Integer, nullable=False, default=3600, server_default="3600")
    normalization_profile_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="real_player_v1",
        server_default="real_player_v1",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class RealCompetition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "real_world_competitions"
    __table_args__ = (
        UniqueConstraint("provider_id", "external_key", name="uq_real_world_competitions_provider_key"),
        Index("ix_real_world_competitions_provider_id", "provider_id"),
        Index("ix_real_world_competitions_name", "name"),
    )

    provider_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("real_data_providers.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_key: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    country_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    competition_type: Mapped[str] = mapped_column(String(32), nullable=False, default="league", server_default="league")
    gtex_competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_competitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class RealClub(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "real_world_clubs"
    __table_args__ = (
        UniqueConstraint("provider_id", "external_key", name="uq_real_world_clubs_provider_key"),
        Index("ix_real_world_clubs_provider_id", "provider_id"),
        Index("ix_real_world_clubs_name", "name"),
        Index("ix_real_world_clubs_competition_id", "competition_id"),
    )

    provider_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("real_data_providers.id", ondelete="CASCADE"),
        nullable=False,
    )
    competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("real_world_competitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    external_key: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    country_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    gtex_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_clubs.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class RealPlayer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "real_players"
    __table_args__ = (
        UniqueConstraint("provider_id", "external_key", name="uq_real_players_provider_key"),
        Index("ix_real_players_provider_id", "provider_id"),
        Index("ix_real_players_gtex_player_id", "gtex_player_id"),
        Index("ix_real_players_position", "position"),
        Index("ix_real_players_real_world_rating", "real_world_rating"),
        Index("ix_real_players_last_updated", "last_updated"),
    )

    provider_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("real_data_providers.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_key: Mapped[str] = mapped_column(String(128), nullable=False)
    gtex_player_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="SET NULL"),
        nullable=True,
    )
    real_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("real_world_clubs.id", ondelete="SET NULL"),
        nullable=True,
    )
    real_competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("real_world_competitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    nationality: Mapped[str | None] = mapped_column(String(120), nullable=True)
    position: Mapped[str | None] = mapped_column(String(64), nullable=True)
    player_origin: Mapped[str] = mapped_column(String(24), nullable=False, default="real_player", server_default="real_player")
    real_world_rating: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, server_default="50.0")
    normalized_rating: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, server_default="50.0")
    attributes_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    injury_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    soft_injury_impact: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class RealityModeSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reality_mode_settings"
    __table_args__ = (
        UniqueConstraint("owner_user_id", name="uq_reality_mode_settings_owner_user_id"),
    )

    owner_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    mode: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=RealityMode.HYBRID.value,
        server_default=RealityMode.HYBRID.value,
    )
    enable_real_world_events: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    enable_soft_injuries: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    enable_transfer_mirror: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class RealDataSyncJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "real_data_sync_jobs"
    __table_args__ = (
        Index("ix_real_data_sync_jobs_provider_id", "provider_id"),
        Index("ix_real_data_sync_jobs_status", "status"),
        Index("ix_real_data_sync_jobs_started_at", "started_at"),
    )

    provider_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("real_data_providers.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=RealDataSyncStatus.PENDING.value,
        server_default=RealDataSyncStatus.PENDING.value,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    entities_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    entities_upserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    entities_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "RealClub",
    "RealCompetition",
    "RealDataProvider",
    "RealDataSyncJob",
    "RealDataSyncStatus",
    "RealPlayer",
    "RealityMode",
    "RealityModeSetting",
]
