from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RealPlayerSourceLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "real_player_source_links"
    __table_args__ = (
        UniqueConstraint("source_name", "source_player_key", name="uq_real_player_source_links_source_key"),
        Index("ix_real_player_source_links_player_id", "gtex_player_id"),
        Index("ix_real_player_source_links_canonical_name", "canonical_name"),
        Index("ix_real_player_source_links_verified_state", "verification_state"),
    )

    gtex_player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_name: Mapped[str] = mapped_column(String(64), nullable=False)
    source_player_key: Mapped[str] = mapped_column(String(128), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(160), nullable=False)
    known_aliases_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    nationality: Mapped[str | None] = mapped_column(String(96), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    primary_position: Mapped[str | None] = mapped_column(String(64), nullable=True)
    secondary_positions_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    current_real_world_club: Mapped[str | None] = mapped_column(String(160), nullable=True)
    identity_confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    is_verified_real_player: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    verification_state: Mapped[str] = mapped_column(String(32), nullable=False, default="verified", server_default="verified")

    player = relationship("Player")
    profile: Mapped["RealPlayerProfile | None"] = relationship(
        "RealPlayerProfile",
        back_populates="source_link",
        uselist=False,
        cascade="all, delete-orphan",
    )


__all__ = ["RealPlayerSourceLink"]
