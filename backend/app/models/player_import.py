from __future__ import annotations

from enum import Enum

from sqlalchemy import Enum as SqlEnum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PlayerImportJobStatus(str, Enum):
    DRAFT = "draft"
    PROCESSED = "processed"
    PARTIAL = "partial"
    FAILED = "failed"


class PlayerImportItemStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    IMPORTED = "imported"
    SKIPPED = "skipped"


class PlayerImportJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "player_import_jobs"

    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_label: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[PlayerImportJobStatus] = mapped_column(SqlEnum(PlayerImportJobStatus, name="playerimportjobstatus"), nullable=False, default=PlayerImportJobStatus.DRAFT)
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    valid_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    imported_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    failed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(nullable=False, default=dict)


class PlayerImportItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "player_import_items"
    __table_args__ = (UniqueConstraint("job_id", "row_number", name="uq_player_import_items_job_row"),)

    job_id: Mapped[str] = mapped_column(ForeignKey("player_import_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    external_source_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    player_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    normalized_position: Mapped[str | None] = mapped_column(String(32), nullable=True)
    nationality_code: Mapped[str | None] = mapped_column(String(12), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[PlayerImportItemStatus] = mapped_column(SqlEnum(PlayerImportItemStatus, name="playerimportitemstatus"), nullable=False, default=PlayerImportItemStatus.VALID)
    validation_errors_json: Mapped[list[str]] = mapped_column(nullable=False, default=list)
    payload_json: Mapped[dict[str, object]] = mapped_column(nullable=False, default=dict)
    linked_player_id: Mapped[str | None] = mapped_column(ForeignKey("ingestion_players.id", ondelete="SET NULL"), nullable=True, index=True)


__all__ = ["PlayerImportJob", "PlayerImportItem", "PlayerImportJobStatus", "PlayerImportItemStatus"]
