from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
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
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="history_recorded",
        server_default="history_recorded",
        index=True,
    )
    global_player_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    global_competition_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    global_match_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    event: Mapped[str] = mapped_column(Text, nullable=False)
    competition: Mapped[str] = mapped_column(Text, nullable=False)
    timeline_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


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
    earnings_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    player_development_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    legacy_boost_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    last_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)


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
    scarcity_tier: Mapped[str] = mapped_column(String(24), nullable=False, default="rare", server_default="rare")
    unique_traits_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    legacy_boost_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    last_evolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class GlobalProjectionCheckpoint(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "global_projection_checkpoints"
    __table_args__ = (
        UniqueConstraint("projection_name", "event_id", name="uq_global_projection_checkpoints_projection_event"),
    )

    projection_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    aggregate_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class NationalTeamCountryRanking(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "national_team_country_rankings"
    __table_args__ = (
        UniqueConstraint("country_code", name="uq_national_team_country_rankings_country_code"),
    )

    country_code: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    country_name: Mapped[str] = mapped_column(String(120), nullable=False)
    elo_rating: Mapped[float] = mapped_column(Float, nullable=False, default=1500.0, server_default="1500.0")
    matches_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    draws: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    titles: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_competition_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "GlobalCompetitionEntry",
    "GlobalPlayerRental",
    "GlobalProjectionCheckpoint",
    "GlobalRegenEvolution",
    "NationalTeamCountryRanking",
    "PlayerHistory",
    "UserDynasty",
]
