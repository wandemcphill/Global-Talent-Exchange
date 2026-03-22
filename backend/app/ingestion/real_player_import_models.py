from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RealPlayerImportStagingRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "real_player_import_staging"
    __table_args__ = (
        Index("ix_real_player_import_staging_provider_state", "provider_name", "import_state"),
        Index("ix_real_player_import_staging_last_seen_at", "last_seen_at"),
        Index("ix_real_player_import_staging_provider_club_id", "provider_club_id"),
        Index("ix_real_player_import_staging_last_import_run_id", "last_import_run_id"),
        Index(
            "ix_real_player_import_staging_provider_player_id",
            "provider_name",
            "provider_player_id",
            unique=True,
        ),
    )

    provider_name: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_player_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_club_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_club_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    provider_competition_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_competition_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    provider_season_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    short_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    display_position: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nationality_name: Mapped[str | None] = mapped_column(String(96), nullable=True)
    nationality_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    provider_last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    import_state: Mapped[str] = mapped_column(String(32), nullable=False, default="staged", server_default="staged")
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
    latest_payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["RealPlayerImportStagingRecord"]
