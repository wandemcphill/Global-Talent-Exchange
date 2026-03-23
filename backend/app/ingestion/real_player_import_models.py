from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class RealPlayerImportRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PARTIAL = "partial"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RealPlayerImportProcessingState(StrEnum):
    PENDING = "pending"
    NORMALIZED = "normalized"
    MAPPED_PARTIAL = "mapped_partial"
    MAPPED_READY = "mapped_ready"
    PUBLISHED = "published"
    REJECTED = "rejected"
    ERROR = "error"


class RealPlayerImportRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "real_player_import_runs"
    __table_args__ = (
        UniqueConstraint("provider_sync_run_id", name="uq_real_player_import_runs_provider_sync_run_id"),
        Index("ix_real_player_import_runs_provider_status", "provider_name", "status"),
        Index("ix_real_player_import_runs_source_reference", "source_type", "source_reference"),
        Index("ix_real_player_import_runs_started_at", "started_at"),
    )

    provider_name: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_sync_run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_provider_sync_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    configured_batch_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_rows_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    processed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    inserted_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    updated_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    duplicate_skipped_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    unresolved_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    publish_ready_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    published_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    failed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RealPlayerImportRunStatus.QUEUED.value,
        server_default=RealPlayerImportRunStatus.QUEUED.value,
    )
    resume_cursor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_successful_batch_marker: Mapped[str | None] = mapped_column(String(128), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)

    staging_records: Mapped[list["RealPlayerImportStagingRecord"]] = relationship(back_populates="import_run")


class RealPlayerImportStagingRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "real_player_import_staging"
    __table_args__ = (
        Index("ix_real_player_import_staging_import_run_id", "import_run_id"),
        Index("ix_real_player_import_staging_import_batch_key", "import_batch_key"),
        Index("ix_real_player_import_staging_provider_state", "provider_name", "import_state"),
        Index("ix_real_player_import_staging_processing_state", "provider_name", "processing_state"),
        Index("ix_real_player_import_staging_last_seen_at", "last_seen_at"),
        Index("ix_real_player_import_staging_provider_club_id", "provider_club_id"),
        Index("ix_real_player_import_staging_last_import_run_id", "last_import_run_id"),
        Index("ix_real_player_import_staging_normalized_name", "normalized_name"),
        Index(
            "ix_real_player_import_staging_provider_player_id",
            "provider_name",
            "provider_player_id",
            unique=True,
        ),
    )

    provider_name: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_player_id: Mapped[str] = mapped_column(String(128), nullable=False)
    import_run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("real_player_import_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    import_batch_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_club_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_club_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    provider_competition_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_competition_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    provider_season_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    normalized_name: Mapped[str | None] = mapped_column(String(192), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    short_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    display_position: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nationality_name: Mapped[str | None] = mapped_column(String(96), nullable=True)
    nationality_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rough_market_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    rough_market_value_currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    provider_last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    import_state: Mapped[str] = mapped_column(String(32), nullable=False, default="staged", server_default="staged")
    processing_state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RealPlayerImportProcessingState.PENDING.value,
        server_default=RealPlayerImportProcessingState.PENDING.value,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_import_cursor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_import_run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_provider_sync_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)

    import_run: Mapped[RealPlayerImportRun | None] = relationship(back_populates="staging_records")


__all__ = [
    "RealPlayerImportProcessingState",
    "RealPlayerImportRun",
    "RealPlayerImportRunStatus",
    "RealPlayerImportStagingRecord",
]
