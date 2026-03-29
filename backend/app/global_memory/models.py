from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class PlayerHistory(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "player_history"

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event: Mapped[str] = mapped_column(Text, nullable=False)
    competition: Mapped[str] = mapped_column(Text, nullable=False)


class UserDynasty(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_dynasty"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_dynasty_user_id"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    total_titles: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    youth_titles: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    senior_titles: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class GlobalCompetitionEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "global_competition_entries"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "competition_id",
            "player_id",
            name="uq_global_competition_entries_user_competition_player",
        ),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="entered", server_default="entered")
    performance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    title_awarded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class GlobalPlayerRental(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "global_player_rentals"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "competition_id",
            "player_id",
            name="uq_global_player_rentals_user_competition_player",
        ),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rental_fee_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    performance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class GlobalRegenEvolution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "global_regen_evolution"
    __table_args__ = (
        UniqueConstraint("player_id", name="uq_global_regen_evolution_player_id"),
        UniqueConstraint("regen_profile_id", name="uq_global_regen_evolution_regen_profile_id"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    regen_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    regen_type: Mapped[str] = mapped_column(String(32), nullable=False, default="academy", server_default="academy")
    performance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    performance_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=80.0, server_default="80.0")
    title_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    current_gsi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_tradable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_unique: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    hall_of_fame: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    last_evolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)

