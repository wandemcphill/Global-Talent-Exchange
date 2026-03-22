from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RealPlayerProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "real_player_profiles"
    __table_args__ = (
        UniqueConstraint("source_link_id", name="uq_real_player_profiles_source_link_id"),
        Index("ix_real_player_profiles_player_id", "gtex_player_id"),
        Index("ix_real_player_profiles_source_name_key", "source_name", "source_player_key"),
        Index("ix_real_player_profiles_refreshed_at", "source_last_refreshed_at"),
    )

    gtex_player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_link_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("real_player_source_links.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_name: Mapped[str] = mapped_column(String(64), nullable=False)
    source_player_key: Mapped[str] = mapped_column(String(128), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(160), nullable=False)
    known_aliases_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    nationality: Mapped[str | None] = mapped_column(String(96), nullable=True)
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    dominant_foot: Mapped[str | None] = mapped_column(String(16), nullable=True)
    primary_position: Mapped[str | None] = mapped_column(String(64), nullable=True)
    secondary_positions_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_club_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    current_league_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    competition_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    appearances: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minutes_played: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assists: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clean_sheets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    injury_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_market_reference_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_reference_currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    source_last_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    normalization_profile_version: Mapped[str] = mapped_column(String(32), nullable=False, default="real_player_v1", server_default="real_player_v1")
    normalized_signals_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ingestion_batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ingestion_source_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pricing_snapshot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    player = relationship("Player")
    source_link: Mapped["RealPlayerSourceLink"] = relationship("RealPlayerSourceLink", back_populates="profile")


__all__ = ["RealPlayerProfile"]
