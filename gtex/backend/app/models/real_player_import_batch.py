from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class RealPlayerImportBatchStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RealPlayerImportRowStatus(StrEnum):
    PENDING = "pending"
    MATCHED = "matched"
    IMPORTED = "imported"
    SKIPPED = "skipped"
    FAILED = "failed"


class RealPlayerImportBatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "real_player_import_batches"
    __table_args__ = (
        UniqueConstraint("batch_key", name="uq_rp_import_batches_key"),
        UniqueConstraint("provider_name", "provider_job_key", name="uq_rp_import_batches_provider_job"),
        Index("ix_real_player_import_batches_provider", "provider_name"),
        Index("ix_real_player_import_batches_status", "status"),
        Index("ix_real_player_import_batches_requested_at", "requested_at"),
        Index("ix_real_player_import_batches_requested_by", "requested_by_user_id"),
    )

    batch_key: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_job_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RealPlayerImportBatchStatus.QUEUED.value,
        server_default=RealPlayerImportBatchStatus.QUEUED.value,
    )
    requested_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    normalized_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    matched_existing_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_player_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    updated_player_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    skipped_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    failed_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    authoritative_snapshot_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    summary_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    rows: Mapped[list["RealPlayerImportRow"]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
    )


class RealPlayerImportRow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "real_player_import_rows"
    __table_args__ = (
        UniqueConstraint("batch_id", "row_number", name="uq_rp_import_rows_batch_row"),
        UniqueConstraint("batch_id", "source_name", "source_player_key", name="uq_rp_import_rows_batch_source"),
        Index("ix_real_player_import_rows_batch_status", "batch_id", "status"),
        Index("ix_real_player_import_rows_source_key", "source_name", "source_player_key"),
        Index("ix_real_player_import_rows_player_id", "gtex_player_id"),
        Index("ix_real_player_import_rows_snapshot", "authoritative_snapshot_id"),
        Index("ix_real_player_import_rows_exact_identity_key", "exact_identity_key"),
        Index("ix_real_player_import_rows_birthyear_club_key", "name_birthyear_club_key"),
        Index("ix_real_player_import_rows_birthyear_nat_key", "name_birthyear_nationality_key"),
        Index("ix_real_player_import_rows_review_status", "review_status"),
    )

    batch_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("real_player_import_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_name: Mapped[str] = mapped_column(String(64), nullable=False)
    source_player_key: Mapped[str] = mapped_column(String(128), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RealPlayerImportRowStatus.PENDING.value,
        server_default=RealPlayerImportRowStatus.PENDING.value,
    )
    match_action: Mapped[str | None] = mapped_column(String(32), nullable=True)
    import_action: Mapped[str | None] = mapped_column(String(32), nullable=True)
    identity_confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    gtex_player_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_link_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    real_player_profile_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    authoritative_snapshot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    player_import_item_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("player_import_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    normalized_full_name: Mapped[str | None] = mapped_column(String(192), nullable=True)
    normalized_display_name: Mapped[str | None] = mapped_column(String(192), nullable=True)
    name_token_signature: Mapped[str | None] = mapped_column(String(255), nullable=True)
    exact_identity_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name_birthyear_club_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name_birthyear_nationality_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    normalized_nationality: Mapped[str | None] = mapped_column(String(96), nullable=True)
    nationality_code: Mapped[str | None] = mapped_column(String(12), nullable=True)
    primary_position_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    secondary_position_keys_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    position_family: Mapped[str | None] = mapped_column(String(32), nullable=True)
    dominant_foot: Mapped[str | None] = mapped_column(String(16), nullable=True)
    height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    club_reference_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    league_reference_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    normalized_payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    import_metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    validation_errors_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    candidate_players_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="resolved", server_default="resolved")
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    audit_findings_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)

    batch: Mapped[RealPlayerImportBatch] = relationship(back_populates="rows")


__all__ = [
    "RealPlayerImportBatch",
    "RealPlayerImportBatchStatus",
    "RealPlayerImportRow",
    "RealPlayerImportRowStatus",
]
