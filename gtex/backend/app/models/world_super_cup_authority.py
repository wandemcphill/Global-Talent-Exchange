from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class WorldSuperCupTournament(TimestampMixin, Base):
    __tablename__ = "world_super_cup_tournaments"
    __table_args__ = (
        Index("ix_world_super_cup_tournaments_status_starts", "status", "starts_at"),
        Index("ix_world_super_cup_tournaments_competition_id", "competition_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    competition_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tournament_name: Mapped[str] = mapped_column(String(160), nullable=False)
    season_label: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled", server_default="scheduled")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reference_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    seasons_considered_json: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    champion_club_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    runner_up_club_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ceremony_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class WorldSuperCupCountdown(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "world_super_cup_countdowns"
    __table_args__ = (
        UniqueConstraint("tournament_id", name="uq_world_super_cup_countdowns_tournament"),
        Index("ix_world_super_cup_countdowns_starts_at", "starts_at"),
    )

    tournament_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("world_super_cup_tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tournament_name: Mapped[str] = mapped_column(String(160), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reference_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    minutes_until_start: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    pause_policy_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class WorldSuperCupCoefficient(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "world_super_cup_coefficients"
    __table_args__ = (
        UniqueConstraint("tournament_id", "club_id", name="uq_world_super_cup_coefficients_tournament_club"),
        Index("ix_world_super_cup_coefficients_tournament_rank", "tournament_id", "ranking"),
    )

    tournament_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("world_super_cup_tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ranking: Mapped[int] = mapped_column(Integer, nullable=False)
    club_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    club_name: Mapped[str] = mapped_column(String(160), nullable=False)
    region: Mapped[str] = mapped_column(String(64), nullable=False)
    total_points: Mapped[int] = mapped_column(Integer, nullable=False)
    recent_season_points: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_season_points: Mapped[int] = mapped_column(Integer, nullable=False)
    winner_seasons_json: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    runner_up_seasons_json: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)


class WorldSuperCupQualifiedClub(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "world_super_cup_qualified_clubs"
    __table_args__ = (
        UniqueConstraint(
            "tournament_id",
            "qualification_stage",
            "club_id",
            name="uq_world_super_cup_qualified_clubs_stage_club",
        ),
        Index("ix_world_super_cup_qualified_clubs_tournament_stage_order", "tournament_id", "qualification_stage", "display_order"),
    )

    tournament_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("world_super_cup_tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    qualification_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    club_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    club_name: Mapped[str] = mapped_column(String(160), nullable=False)
    region: Mapped[str] = mapped_column(String(64), nullable=False)
    qualification_path: Mapped[str] = mapped_column(String(64), nullable=False)
    coefficient_points: Mapped[int] = mapped_column(Integer, nullable=False)
    regional_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_seed: Mapped[int] = mapped_column(Integer, nullable=False)


class WorldSuperCupGroup(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "world_super_cup_groups"
    __table_args__ = (
        UniqueConstraint("tournament_id", "group_name", name="uq_world_super_cup_groups_tournament_group"),
        Index("ix_world_super_cup_groups_tournament_order", "tournament_id", "display_order"),
    )

    tournament_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("world_super_cup_tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    group_name: Mapped[str] = mapped_column(String(12), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    club_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class WorldSuperCupFixture(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "world_super_cup_fixtures"
    __table_args__ = (
        UniqueConstraint("tournament_id", "fixture_id", name="uq_world_super_cup_fixtures_tournament_fixture"),
        Index("ix_world_super_cup_fixtures_tournament_stage", "tournament_id", "stage", "sequence"),
        Index("ix_world_super_cup_fixtures_status_kickoff", "status", "kickoff_at"),
    )

    tournament_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("world_super_cup_tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fixture_id: Mapped[str] = mapped_column(String(80), nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    round_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    group_name: Mapped[str | None] = mapped_column(String(12), nullable=True)
    matchday: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    home_club_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    away_club_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    kickoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    venue: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled", server_default="scheduled")
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    winner_club_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    decided_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    requires_winner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class WorldSuperCupStanding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "world_super_cup_standings"
    __table_args__ = (
        UniqueConstraint("tournament_id", "group_name", "club_id", name="uq_world_super_cup_standings_group_club"),
        Index("ix_world_super_cup_standings_tournament_group_position", "tournament_id", "group_name", "position"),
    )

    tournament_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("world_super_cup_tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    group_name: Mapped[str] = mapped_column(String(12), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    club_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    played: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    draws: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    goals_for: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    goals_against: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    goal_difference: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class WorldSuperCupSettlement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "world_super_cup_settlements"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_world_super_cup_settlements_idempotency_key"),
        Index("ix_world_super_cup_settlements_tournament_fixture", "tournament_id", "fixture_id"),
    )

    tournament_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("world_super_cup_tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fixture_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    home_score: Mapped[int] = mapped_column(Integer, nullable=False)
    away_score: Mapped[int] = mapped_column(Integer, nullable=False)
    winner_club_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "WorldSuperCupCoefficient",
    "WorldSuperCupCountdown",
    "WorldSuperCupFixture",
    "WorldSuperCupGroup",
    "WorldSuperCupQualifiedClub",
    "WorldSuperCupSettlement",
    "WorldSuperCupStanding",
    "WorldSuperCupTournament",
]
