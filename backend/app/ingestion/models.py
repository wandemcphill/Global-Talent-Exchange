from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow

if TYPE_CHECKING:
    from typing import Sequence


MAJOR_COMPETITIONS = {
    "world cup",
    "uefa champions league",
    "uefa club championship",
    "afcon",
    "copa america",
    "euros",
    "club world cup",
}


@dataclass(frozen=True, slots=True)
class CompetitionContext:
    competition_id: str
    name: str
    stage: str
    season: str | None = None
    country: str | None = None

    @property
    def is_major(self) -> bool:
        return self.name.lower() in MAJOR_COMPETITIONS


@dataclass(frozen=True, slots=True)
class NormalizedMatchEvent:
    source: str
    source_event_id: str
    match_id: str
    player_id: str
    player_name: str
    team_id: str
    team_name: str
    opponent_id: str
    opponent_name: str
    competition: CompetitionContext
    occurred_at: datetime
    minutes: int
    rating: float
    goals: int = 0
    assists: int = 0
    saves: int = 0
    clean_sheet: bool = False
    started: bool = False
    won_match: bool = False
    won_final: bool = False
    big_moment: bool = False
    tags: tuple[str, ...] = ()

    @property
    def dedupe_key(self) -> tuple[str, str, str, str]:
        return (self.source, self.source_event_id, self.match_id, self.player_id)


@dataclass(frozen=True, slots=True)
class NormalizedTransferEvent:
    source: str
    source_event_id: str
    player_id: str
    player_name: str
    occurred_at: datetime
    from_club: str
    to_club: str
    from_competition: str | None = None
    to_competition: str | None = None
    reported_fee_eur: float | None = None
    status: str = "rumour"


@dataclass(frozen=True, slots=True)
class NormalizedAwardEvent:
    source: str
    source_event_id: str
    player_id: str
    player_name: str
    occurred_at: datetime
    award_code: str
    award_name: str
    rank: int | None = None
    category: str | None = None


@dataclass(frozen=True, slots=True)
class PlayerEventWindow:
    player_id: str
    player_name: str
    events: tuple[NormalizedMatchEvent, ...]
    total_minutes: int
    total_goals: int
    total_assists: int
    average_rating: float
    big_moment_count: int


class SyncRunStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"


class Country(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_countries"
    __table_args__ = (
        UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_countries_provider_external_id"),
        Index("ix_ingestion_countries_alpha2_code", "alpha2_code"),
        Index("ix_ingestion_countries_alpha3_code", "alpha3_code"),
    )

    source_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    alpha2_code: Mapped[str | None] = mapped_column(String(4), nullable=True)
    alpha3_code: Mapped[str | None] = mapped_column(String(4), nullable=True)
    flag_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    competitions: Mapped[list["Competition"]] = relationship(back_populates="country")
    clubs: Mapped[list["Club"]] = relationship(back_populates="country")
    players: Mapped[list["Player"]] = relationship(back_populates="country")


class Competition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_competitions"
    __table_args__ = (
        UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_competitions_provider_external_id"),
        Index("ix_ingestion_competitions_slug", "slug"),
        Index("ix_ingestion_competitions_code", "code"),
    )

    source_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    country_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_countries.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False)
    code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    competition_type: Mapped[str] = mapped_column(String(32), nullable=False, default="league", server_default="league")
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    emblem_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_major: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    current_season_external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    country: Mapped[Country | None] = relationship(back_populates="competitions")
    seasons: Mapped[list["Season"]] = relationship(back_populates="competition")
    matches: Mapped[list["Match"]] = relationship(back_populates="competition")
    standings: Mapped[list["TeamStanding"]] = relationship(back_populates="competition")


class Season(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_seasons"
    __table_args__ = (
        UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_seasons_provider_external_id"),
        UniqueConstraint("competition_id", "label", name="uq_ingestion_seasons_competition_label"),
        Index("ix_ingestion_seasons_competition_id", "competition_id"),
    )

    source_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_competitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    year_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    current_matchday: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    competition: Mapped[Competition] = relationship(back_populates="seasons")
    matches: Mapped[list["Match"]] = relationship(back_populates="season")
    standings: Mapped[list["TeamStanding"]] = relationship(back_populates="season")
    player_tenures: Mapped[list["PlayerClubTenure"]] = relationship(back_populates="season")


class Club(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_clubs"
    __table_args__ = (
        UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_clubs_provider_external_id"),
        Index("ix_ingestion_clubs_slug", "slug"),
        Index("ix_ingestion_clubs_name", "name"),
    )

    source_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    country_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_countries.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    founded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    venue: Mapped[str | None] = mapped_column(String(160), nullable=True)
    crest_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    country: Mapped[Country | None] = relationship(back_populates="clubs")
    players: Mapped[list["Player"]] = relationship(back_populates="current_club")
    home_matches: Mapped[list["Match"]] = relationship(
        back_populates="home_club",
        foreign_keys="Match.home_club_id",
    )
    away_matches: Mapped[list["Match"]] = relationship(
        back_populates="away_club",
        foreign_keys="Match.away_club_id",
    )
    player_tenures: Mapped[list["PlayerClubTenure"]] = relationship(back_populates="club")


class Player(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_players"
    __table_args__ = (
        UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_players_provider_external_id"),
        Index("ix_ingestion_players_full_name", "full_name"),
        Index("ix_ingestion_players_normalized_position", "normalized_position"),
    )

    source_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    country_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_countries.id", ondelete="SET NULL"),
        nullable=True,
    )
    current_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_clubs.id", ondelete="SET NULL"),
        nullable=True,
    )
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    short_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    position: Mapped[str | None] = mapped_column(String(64), nullable=True)
    normalized_position: Mapped[str | None] = mapped_column(String(32), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_foot: Mapped[str | None] = mapped_column(String(16), nullable=True)
    shirt_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    country: Mapped[Country | None] = relationship(back_populates="players")
    current_club: Mapped[Club | None] = relationship(back_populates="players")
    player_tenures: Mapped[list["PlayerClubTenure"]] = relationship(back_populates="player")
    match_stats: Mapped[list["PlayerMatchStat"]] = relationship(back_populates="player")
    season_stats: Mapped[list["PlayerSeasonStat"]] = relationship(back_populates="player")
    injury_statuses: Mapped[list["InjuryStatus"]] = relationship(back_populates="player")
    market_signals: Mapped[list["MarketSignal"]] = relationship(back_populates="player")


class PlayerClubTenure(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_player_club_tenures"
    __table_args__ = (
        UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_tenures_provider_external_id"),
        Index("ix_ingestion_tenures_player_id", "player_id"),
        Index("ix_ingestion_tenures_club_id", "club_id"),
    )

    source_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_clubs.id", ondelete="CASCADE"),
        nullable=False,
    )
    season_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_seasons.id", ondelete="SET NULL"),
        nullable=True,
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    squad_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    player: Mapped[Player] = relationship(back_populates="player_tenures")
    club: Mapped[Club] = relationship(back_populates="player_tenures")
    season: Mapped[Season | None] = relationship(back_populates="player_tenures")


class Match(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_matches"
    __table_args__ = (
        UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_matches_provider_external_id"),
        Index("ix_ingestion_matches_competition_id", "competition_id"),
        Index("ix_ingestion_matches_season_id", "season_id"),
        Index("ix_ingestion_matches_kickoff_at", "kickoff_at"),
    )

    source_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_competitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    season_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_seasons.id", ondelete="SET NULL"),
        nullable=True,
    )
    home_club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_clubs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    away_club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_clubs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    winner_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_clubs.id", ondelete="SET NULL"),
        nullable=True,
    )
    venue: Mapped[str | None] = mapped_column(String(160), nullable=True)
    kickoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled", server_default="scheduled")
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    matchday: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_provider_update_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    competition: Mapped[Competition] = relationship(back_populates="matches")
    season: Mapped[Season | None] = relationship(back_populates="matches")
    home_club: Mapped[Club] = relationship(back_populates="home_matches", foreign_keys=[home_club_id])
    away_club: Mapped[Club] = relationship(back_populates="away_matches", foreign_keys=[away_club_id])
    match_stats: Mapped[list["PlayerMatchStat"]] = relationship(back_populates="match")


class TeamStanding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_team_standings"
    __table_args__ = (
        UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_standings_provider_external_id"),
        UniqueConstraint(
            "competition_id",
            "season_id",
            "club_id",
            "standing_type",
            name="uq_ingestion_standings_competition_season_club_type",
        ),
        Index("ix_ingestion_standings_position", "position"),
    )

    source_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_competitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    season_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_seasons.id", ondelete="SET NULL"),
        nullable=True,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_clubs.id", ondelete="CASCADE"),
        nullable=False,
    )
    standing_type: Mapped[str] = mapped_column(String(32), nullable=False, default="total", server_default="total")
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    played: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    won: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    drawn: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    lost: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    goals_for: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    goals_against: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    goal_difference: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    form: Mapped[str | None] = mapped_column(String(32), nullable=True)

    competition: Mapped[Competition] = relationship(back_populates="standings")
    season: Mapped[Season | None] = relationship(back_populates="standings")


class PlayerMatchStat(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_player_match_stats"
    __table_args__ = (
        UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_player_match_stats_provider_external_id"),
        UniqueConstraint("player_id", "match_id", name="uq_ingestion_player_match_stats_player_match"),
        Index("ix_ingestion_player_match_stats_match_id", "match_id"),
    )

    source_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_matches.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_clubs.id", ondelete="SET NULL"),
        nullable=True,
    )
    competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_competitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    season_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_seasons.id", ondelete="SET NULL"),
        nullable=True,
    )
    appearances: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    starts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assists: Mapped[int | None] = mapped_column(Integer, nullable=True)
    saves: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clean_sheet: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_position: Mapped[str | None] = mapped_column(String(64), nullable=True)

    player: Mapped[Player] = relationship(back_populates="match_stats")
    match: Mapped[Match] = relationship(back_populates="match_stats")


class PlayerSeasonStat(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_player_season_stats"
    __table_args__ = (
        UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_player_season_stats_provider_external_id"),
        UniqueConstraint("player_id", "season_id", "competition_id", name="uq_ingestion_player_season_stats_player_scope"),
        Index("ix_ingestion_player_season_stats_season_id", "season_id"),
    )

    source_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_clubs.id", ondelete="SET NULL"),
        nullable=True,
    )
    competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_competitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    season_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_seasons.id", ondelete="SET NULL"),
        nullable=True,
    )
    appearances: Mapped[int | None] = mapped_column(Integer, nullable=True)
    starts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assists: Mapped[int | None] = mapped_column(Integer, nullable=True)
    yellow_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    red_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clean_sheets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    saves: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_rating: Mapped[float | None] = mapped_column(Float, nullable=True)

    player: Mapped[Player] = relationship(back_populates="season_stats")


class InjuryStatus(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_injury_statuses"
    __table_args__ = (
        UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_injuries_provider_external_id"),
    )

    source_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_clubs.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_return_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    player: Mapped[Player] = relationship(back_populates="injury_statuses")


class MarketSignal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_market_signals"
    __table_args__ = (
        UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_market_signals_provider_external_id"),
        Index("ix_ingestion_market_signals_signal_type", "signal_type"),
    )

    source_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    signal_type: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    player: Mapped[Player] = relationship(back_populates="market_signals")


class ProviderSyncRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_provider_sync_runs"
    __table_args__ = (
        Index("ix_ingestion_sync_runs_provider_status", "provider_name", "status"),
        Index("ix_ingestion_sync_runs_started_at", "started_at"),
    )

    provider_name: Mapped[str] = mapped_column(String(64), nullable=False)
    job_name: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=SyncRunStatus.RUNNING.value)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    inserted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    updated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    cursor_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    raw_payloads: Mapped[list["ProviderRawPayload"]] = relationship(back_populates="sync_run")


class ProviderSyncCursor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_provider_sync_cursors"
    __table_args__ = (
        UniqueConstraint("provider_name", "entity_type", "cursor_key", name="uq_ingestion_sync_cursors_provider_entity_key"),
    )

    provider_name: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    cursor_key: Mapped[str] = mapped_column(String(64), nullable=False, default="default", server_default="default")
    cursor_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    checkpoint_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_provider_sync_runs.id", ondelete="SET NULL"),
        nullable=True,
    )


class ProviderRawPayload(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ingestion_provider_raw_payloads"
    __table_args__ = (
        UniqueConstraint("provider_name", "entity_type", "payload_hash", name="uq_ingestion_raw_payload_provider_hash"),
        Index("ix_ingestion_raw_payloads_external_id", "provider_external_id"),
        Index("ix_ingestion_raw_payloads_received_at", "received_at"),
    )

    provider_name: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sync_run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_provider_sync_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    sync_run: Mapped[ProviderSyncRun | None] = relationship(back_populates="raw_payloads")


class IngestionJobLock(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ingestion_job_locks"
    __table_args__ = (
        UniqueConstraint("lock_key", name="uq_ingestion_job_locks_lock_key"),
        Index("ix_ingestion_job_locks_expires_at", "expires_at"),
    )

    lock_key: Mapped[str] = mapped_column(String(128), nullable=False)
    owner_token: Mapped[str] = mapped_column(String(128), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
