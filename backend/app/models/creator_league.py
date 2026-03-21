from __future__ import annotations

from datetime import date, datetime
from typing import Any

from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CreatorLeagueConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_league_configs"
    __table_args__ = (
        UniqueConstraint("league_key", name="uq_creator_league_configs_league_key"),
    )

    league_key: Mapped[str] = mapped_column(String(64), nullable=False, default="creator_league", server_default="creator_league")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    seasons_paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    league_format: Mapped[str] = mapped_column(String(64), nullable=False, default="double_round_robin", server_default="double_round_robin")
    default_club_count: Mapped[int] = mapped_column(Integer, nullable=False, default=20, server_default="20")
    match_frequency_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7, server_default="7")
    season_duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=266, server_default="266")
    broadcast_purchases_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    season_pass_sales_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    match_gifting_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    settlement_review_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    settlement_review_total_revenue_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("250.0000"),
        server_default="250.0000",
    )
    settlement_review_creator_share_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("150.0000"),
        server_default="150.0000",
    )
    settlement_review_platform_share_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("150.0000"),
        server_default="150.0000",
    )
    settlement_review_shareholder_distribution_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("75.0000"),
        server_default="75.0000",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorLeagueTier(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_league_tiers"
    __table_args__ = (
        UniqueConstraint("config_id", "display_order", name="uq_creator_league_tiers_config_order"),
        UniqueConstraint("config_id", "slug", name="uq_creator_league_tiers_config_slug"),
    )

    config_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_league_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    slug: Mapped[str] = mapped_column(String(96), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    club_count: Mapped[int] = mapped_column(Integer, nullable=False, default=20, server_default="20")
    promotion_spots: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    relegation_spots: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorLeagueSeason(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_league_seasons"
    __table_args__ = (
        UniqueConstraint("config_id", "season_number", name="uq_creator_league_seasons_config_number"),
    )

    config_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_league_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft", server_default="draft", index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    match_frequency_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7, server_default="7")
    season_duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=266, server_default="266")
    launched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorLeagueSeasonTier(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_league_season_tiers"
    __table_args__ = (
        UniqueConstraint("season_id", "tier_order", name="uq_creator_league_season_tiers_season_order"),
        UniqueConstraint("competition_id", name="uq_creator_league_season_tiers_competition_id"),
    )

    season_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_league_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tier_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    competition_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    competition_name: Mapped[str] = mapped_column(String(160), nullable=False)
    tier_name: Mapped[str] = mapped_column(String(80), nullable=False)
    tier_order: Mapped[int] = mapped_column(Integer, nullable=False)
    club_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    round_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    fixture_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft", server_default="draft", index=True)
    banner_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    banner_subtitle: Mapped[str | None] = mapped_column(String(160), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "CreatorLeagueConfig",
    "CreatorLeagueSeason",
    "CreatorLeagueSeasonTier",
    "CreatorLeagueTier",
]
