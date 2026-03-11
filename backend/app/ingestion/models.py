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


class VerificationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ImageModerationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class InternalLeagueCode(StrEnum):
    LEAGUE_A = "league_a"
    LEAGUE_B = "league_b"
    LEAGUE_C = "league_c"
    LEAGUE_D = "league_d"
    LEAGUE_E = "league_e"


class InternalLeague(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_internal_leagues"
    __table_args__ = (
        UniqueConstraint("code", name="uq_ingestion_internal_leagues_code"),
        UniqueConstraint("name", name="uq_ingestion_internal_leagues_name"),
        UniqueConstraint("rank", name="uq_ingestion_internal_leagues_rank"),
        Index("ix_ingestion_internal_leagues_name", "name"),
    )

    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    competition_multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default="1.0")
    visibility_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default="1.0")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    competitions: Mapped[list["Competition"]] = relationship(back_populates="internal_league")
    clubs: Mapped[list["Club"]] = relationship(back_populates="internal_league")
    players: Mapped[list["Player"]] = relationship(back_populates="internal_league")


class SupplyTier(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_supply_tiers"
    __table_args__ = (
        UniqueConstraint("code", name="uq_ingestion_supply_tiers_code"),
        UniqueConstraint("name", name="uq_ingestion_supply_tiers_name"),
        UniqueConstraint("rank", name="uq_ingestion_supply_tiers_rank"),
        Index("ix_ingestion_supply_tiers_name", "name"),
    )

    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    min_score: Mapped[float] = mapped_column(Float, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, nullable=False)
    target_share: Mapped[float] = mapped_column(Float, nullable=False)
    circulating_supply: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_pack_supply: Mapped[int] = mapped_column(Integer, nullable=False)
    season_mint_cap: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    players: Mapped[list["Player"]] = relationship(back_populates="supply_tier")


class LiquidityBand(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_liquidity_bands"
    __table_args__ = (
        UniqueConstraint("code", name="uq_ingestion_liquidity_bands_code"),
        UniqueConstraint("name", name="uq_ingestion_liquidity_bands_name"),
        UniqueConstraint("rank", name="uq_ingestion_liquidity_bands_rank"),
        Index("ix_ingestion_liquidity_bands_name", "name"),
    )

    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    min_price_credits: Mapped[int] = mapped_column(Integer, nullable=False)
    max_price_credits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_spread_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    maker_inventory_target: Mapped[int] = mapped_column(Integer, nullable=False)
    instant_sell_fee_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    players: Mapped[list["Player"]] = relationship(back_populates="liquidity_band")


class Country(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_countries"
    __table_args__ = (
        UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_countries_provider_external_id"),
        Index("ix_ingestion_countries_alpha2_code", "alpha2_code"),
        Index("ix_ingestion_countries_alpha3_code", "alpha3_code"),
        Index("ix_ingestion_countries_fifa_code", "fifa_code"),
        Index("ix_ingestion_countries_confederation_code", "confederation_code"),
    )

    source_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    alpha2_code: Mapped[str | None] = mapped_column(String(4), nullable=True)
    alpha3_code: Mapped[str | None] = mapped_column(String(4), nullable=True)
    fifa_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    confederation_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    market_region: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_enabled_for_universe: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
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
        Index("ix_ingestion_competitions_internal_league_id", "internal_league_id"),
    )

    source_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    country_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_countries.id", ondelete="SET NULL"),
        nullable=True,
    )
    internal_league_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_internal_leagues.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False)
    code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    competition_type: Mapped[str] = mapped_column(String(32), nullable=False, default="league", server_default="league")
    format_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    age_bracket: Mapped[str | None] = mapped_column(String(32), nullable=True)
    domestic_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    emblem_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_major: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_tradable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    competition_strength: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_season_external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    country: Mapped[Country | None] = relationship(back_populates="competitions")
    internal_league: Mapped[InternalLeague | None] = relationship(back_populates="competitions")
    seasons: Mapped[list["Season"]] = relationship(back_populates="competition")
    clubs: Mapped[list["Club"]] = relationship(back_populates="current_competition")
    matches: Mapped[list["Match"]] = relationship(back_populates="competition")
    standings: Mapped[list["TeamStanding"]] = relationship(back_populates="competition")
    current_players: Mapped[list["Player"]] = relationship(back_populates="current_competition")


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
    season_status: Mapped[str] = mapped_column(String(32), nullable=False, default="upcoming", server_default="upcoming")
    trading_window_opens_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trading_window_closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data_completeness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
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
        Index("ix_ingestion_clubs_current_competition_id", "current_competition_id"),
        Index("ix_ingestion_clubs_internal_league_id", "internal_league_id"),
    )

    source_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    country_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_countries.id", ondelete="SET NULL"),
        nullable=True,
    )
    current_competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_competitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    internal_league_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_internal_leagues.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    founded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    venue: Mapped[str | None] = mapped_column(String(160), nullable=True)
    crest_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    popularity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_tradable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    country: Mapped[Country | None] = relationship(back_populates="clubs")
    current_competition: Mapped[Competition | None] = relationship(back_populates="clubs")
    internal_league: Mapped[InternalLeague | None] = relationship(back_populates="clubs")
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
        Index("ix_ingestion_players_current_competition_id", "current_competition_id"),
        Index("ix_ingestion_players_internal_league_id", "internal_league_id"),
        Index("ix_ingestion_players_supply_tier_id", "supply_tier_id"),
        Index("ix_ingestion_players_liquidity_band_id", "liquidity_band_id"),
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
    current_competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_competitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    internal_league_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_internal_leagues.id", ondelete="SET NULL"),
        nullable=True,
    )
    supply_tier_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_supply_tiers.id", ondelete="SET NULL"),
        nullable=True,
    )
    liquidity_band_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_liquidity_bands.id", ondelete="SET NULL"),
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
    market_value_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    profile_completeness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_tradable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    country: Mapped[Country | None] = relationship(back_populates="players")
    current_club: Mapped[Club | None] = relationship(back_populates="players")
    current_competition: Mapped[Competition | None] = relationship(back_populates="current_players")
    internal_league: Mapped[InternalLeague | None] = relationship(back_populates="players")
    supply_tier: Mapped[SupplyTier | None] = relationship(back_populates="players")
    liquidity_band: Mapped[LiquidityBand | None] = relationship(back_populates="players")
    player_tenures: Mapped[list["PlayerClubTenure"]] = relationship(back_populates="player")
    match_stats: Mapped[list["PlayerMatchStat"]] = relationship(back_populates="player")
    season_stats: Mapped[list["PlayerSeasonStat"]] = relationship(back_populates="player")
    injury_statuses: Mapped[list["InjuryStatus"]] = relationship(back_populates="player")
    market_signals: Mapped[list["MarketSignal"]] = relationship(back_populates="player")
    verification: Mapped["PlayerVerification | None"] = relationship(
        back_populates="player",
        uselist=False,
        cascade="all, delete-orphan",
    )
    image_metadata: Mapped[list["PlayerImageMetadata"]] = relationship(
        back_populates="player",
        cascade="all, delete-orphan",
    )


class PlayerVerification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_player_verifications"
    __table_args__ = (
        UniqueConstraint("player_id", name="uq_ingestion_player_verifications_player_id"),
        Index("ix_ingestion_player_verifications_status", "status"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=VerificationStatus.PENDING.value,
        server_default=VerificationStatus.PENDING.value,
    )
    verification_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rights_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    player: Mapped[Player] = relationship(back_populates="verification")


class PlayerImageMetadata(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_player_image_metadata"
    __table_args__ = (
        UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_player_images_provider_external_id"),
        UniqueConstraint("player_id", "image_role", name="uq_ingestion_player_images_player_role"),
        Index("ix_ingestion_player_images_player_id", "player_id"),
        Index("ix_ingestion_player_images_moderation_status", "moderation_status"),
    )

    source_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    image_role: Mapped[str] = mapped_column(String(32), nullable=False, default="portrait", server_default="portrait")
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    moderation_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ImageModerationStatus.PENDING.value,
        server_default=ImageModerationStatus.PENDING.value,
    )
    rights_cleared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    last_processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    player: Mapped[Player] = relationship(back_populates="image_metadata")


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
