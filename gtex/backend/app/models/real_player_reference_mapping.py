from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RealPlayerReferenceMapping(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "real_player_reference_mappings"
    __table_args__ = (
        UniqueConstraint(
            "source_name",
            "entity_type",
            "provider_reference_key",
            name="uq_real_player_reference_mappings_source_entity_reference",
        ),
        Index("ix_real_player_reference_mappings_entity_type", "entity_type"),
        Index("ix_real_player_reference_mappings_status", "mapping_status"),
        Index("ix_real_player_reference_mappings_provider_external_id", "source_name", "entity_type", "provider_external_id"),
        Index("ix_real_player_reference_mappings_country_id", "canonical_country_id"),
        Index("ix_real_player_reference_mappings_competition_id", "canonical_competition_id"),
        Index("ix_real_player_reference_mappings_club_id", "canonical_club_id"),
    )

    source_name: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_external_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    provider_reference_key: Mapped[str] = mapped_column(String(180), nullable=False)
    provider_label: Mapped[str | None] = mapped_column(String(180), nullable=True)
    normalized_label: Mapped[str | None] = mapped_column(String(180), nullable=True)
    canonical_country_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_countries.id", ondelete="SET NULL"),
        nullable=True,
    )
    canonical_competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_competitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    canonical_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_clubs.id", ondelete="SET NULL"),
        nullable=True,
    )
    team_identity_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mapping_status: Mapped[str] = mapped_column(String(32), nullable=False, default="resolved", server_default="resolved")
    resolution_method: Mapped[str] = mapped_column(String(64), nullable=False, default="manual", server_default="manual")
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RealPlayerUnresolvedReference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "real_player_unresolved_references"
    __table_args__ = (
        UniqueConstraint(
            "source_name",
            "entity_type",
            "provider_reference_key",
            name="uq_real_player_unresolved_references_source_entity_reference",
        ),
        Index("ix_real_player_unresolved_references_entity_type", "entity_type"),
        Index("ix_real_player_unresolved_references_status", "status"),
        Index("ix_real_player_unresolved_references_last_seen_at", "last_seen_at"),
        Index("ix_real_player_unresolved_references_reason_code", "reason_code"),
    )

    source_name: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_external_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    provider_reference_key: Mapped[str] = mapped_column(String(180), nullable=False)
    raw_label: Mapped[str | None] = mapped_column(String(180), nullable=True)
    normalized_label: Mapped[str | None] = mapped_column(String(180), nullable=True)
    team_identity_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", server_default="open")
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canonical_country_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_countries.id", ondelete="SET NULL"),
        nullable=True,
    )
    canonical_competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_competitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    canonical_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_clubs.id", ondelete="SET NULL"),
        nullable=True,
    )
    sample_payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "RealPlayerReferenceMapping",
    "RealPlayerUnresolvedReference",
]
