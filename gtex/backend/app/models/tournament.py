from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class TournamentGameType(StrEnum):
    PREDICTION = "prediction"
    SIMULATION = "simulation"
    DEBATE = "debate"


class TournamentStatus(StrEnum):
    REGISTRATION = "registration"
    ACTIVE = "active"
    COMPLETED = "completed"


class TournamentPlayerStatus(StrEnum):
    REGISTERED = "registered"
    ACTIVE = "active"
    ELIMINATED = "eliminated"
    WINNER = "winner"


class TournamentRoundStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"


class TournamentMatchStatus(StrEnum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"


class Tournament(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tournaments"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    game_type: Mapped[str] = mapped_column(String(24), nullable=False)
    entry_fee: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_players: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=TournamentStatus.REGISTRATION.value,
        server_default=TournamentStatus.REGISTRATION.value,
        index=True,
    )
    rounds: Mapped[int] = mapped_column(Integer, nullable=False)
    current_round: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    prize_pool: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    round_timeout_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60, server_default="60")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    winner_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class TournamentPlayer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tournament_players"
    __table_args__ = (
        UniqueConstraint("tournament_id", "user_id", name="uq_tournament_players_tournament_user"),
        UniqueConstraint("tournament_id", "bracket_slot", name="uq_tournament_players_tournament_slot"),
    )

    tournament_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bracket_slot: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=TournamentPlayerStatus.REGISTERED.value,
        server_default=TournamentPlayerStatus.REGISTERED.value,
        index=True,
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    entry_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)


class TournamentRound(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tournament_rounds"
    __table_args__ = (
        UniqueConstraint("tournament_id", "round_number", name="uq_tournament_rounds_tournament_round"),
    )

    tournament_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=TournamentRoundStatus.ACTIVE.value,
        server_default=TournamentRoundStatus.ACTIVE.value,
        index=True,
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    timeout_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TournamentMatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tournament_matches"
    __table_args__ = (
        UniqueConstraint("tournament_id", "round_number", "slot_index", name="uq_tournament_matches_round_slot"),
    )

    tournament_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    round_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tournament_rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    slot_index: Mapped[int] = mapped_column(Integer, nullable=False)
    player_one_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    player_two_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    winner_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    player_one_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player_two_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=TournamentMatchStatus.SCHEDULED.value,
        server_default=TournamentMatchStatus.SCHEDULED.value,
        index=True,
    )
    resolution: Mapped[str | None] = mapped_column(String(24), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "Tournament",
    "TournamentGameType",
    "TournamentMatch",
    "TournamentMatchStatus",
    "TournamentPlayer",
    "TournamentPlayerStatus",
    "TournamentRound",
    "TournamentRoundStatus",
    "TournamentStatus",
]
