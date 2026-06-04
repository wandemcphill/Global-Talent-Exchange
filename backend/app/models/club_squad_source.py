from __future__ import annotations

from sqlalchemy import Float, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClubSquadPlayerSourceRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_squad_player_sources"
    __table_args__ = (
        UniqueConstraint("club_id", "player_id", name="uq_club_squad_player_sources_club_player"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    morale_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    morale_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    morale_trend: Mapped[str | None] = mapped_column(String(32), nullable=True)
    chemistry_overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    chemistry_position_fit: Mapped[float | None] = mapped_column(Float, nullable=True)
    chemistry_team_fit: Mapped[float | None] = mapped_column(Float, nullable=True)
    chemistry_warnings_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    source_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
