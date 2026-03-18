from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CreatorBroadcastModeConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_broadcast_mode_configs"
    __table_args__ = (
        UniqueConstraint("mode_key", name="uq_creator_broadcast_mode_configs_mode_key"),
    )

    mode_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    min_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    max_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    min_price_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    max_price_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorBroadcastPurchase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_broadcast_purchases"
    __table_args__ = (
        UniqueConstraint("user_id", "match_id", name="uq_creator_broadcast_purchases_user_match"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_league_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mode_key: Mapped[str] = mapped_column(String(32), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    price_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    platform_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    home_creator_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    away_creator_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorSeasonPass(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_season_passes"
    __table_args__ = (
        UniqueConstraint("user_id", "season_id", "club_id", name="uq_creator_season_passes_user_season_club"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creator_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_league_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    access_scope: Mapped[str] = mapped_column(String(48), nullable=False, default="creator_league_only", server_default="creator_league_only")
    price_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    creator_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    platform_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    includes_full_season: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    includes_home_away: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    includes_live_highlights: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorMatchGiftEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_match_gift_events"

    season_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_league_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_creator_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gift_label: Mapped[str] = mapped_column(String(80), nullable=False)
    gross_amount_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    creator_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    platform_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorStadiumControl(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_stadium_controls"
    __table_args__ = (
        UniqueConstraint("control_key", name="uq_creator_stadium_controls_control_key"),
    )

    control_key: Mapped[str] = mapped_column(String(32), nullable=False, default="default", server_default="default")
    max_matchday_ticket_price_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("25.0000"),
        server_default="25.0000",
    )
    max_season_pass_price_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("120.0000"),
        server_default="120.0000",
    )
    max_vip_ticket_price_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("60.0000"),
        server_default="60.0000",
    )
    max_stadium_level: Mapped[int] = mapped_column(Integer, nullable=False, default=5, server_default="5")
    vip_seat_ratio_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=500, server_default="500")
    max_in_stadium_ad_slots: Mapped[int] = mapped_column(Integer, nullable=False, default=6, server_default="6")
    max_sponsor_banner_slots: Mapped[int] = mapped_column(Integer, nullable=False, default=4, server_default="4")
    ad_placement_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    ticket_sales_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    max_placement_price_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("250.0000"),
        server_default="250.0000",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorStadiumProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_stadium_profiles"
    __table_args__ = (
        UniqueConstraint("club_id", name="uq_creator_stadium_profiles_club_id"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creator_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_stadium_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_stadiums.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=5000, server_default="5000")
    premium_seat_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=250, server_default="250")
    visual_upgrade_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    custom_chant_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    custom_visuals_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorStadiumPricing(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_stadium_pricing"
    __table_args__ = (
        UniqueConstraint("season_id", "club_id", name="uq_creator_stadium_pricing_season_club"),
    )

    season_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_league_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creator_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    matchday_ticket_price_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    season_pass_price_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    vip_ticket_price_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    live_video_access_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    stadium_visual_upgrades_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    custom_chants_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    custom_visuals_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorStadiumTicketPurchase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_stadium_ticket_purchases"
    __table_args__ = (
        UniqueConstraint("user_id", "match_id", name="uq_creator_stadium_ticket_purchases_user_match"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creator_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_league_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ticket_type: Mapped[str] = mapped_column(String(24), nullable=False)
    seat_tier: Mapped[str] = mapped_column(String(24), nullable=False, default="general", server_default="general")
    price_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    creator_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    platform_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    includes_live_video_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    includes_premium_seating: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    includes_stadium_visual_upgrades: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    includes_custom_chants: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    includes_custom_visuals: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorStadiumPlacement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_stadium_placements"
    __table_args__ = (
        UniqueConstraint("match_id", "placement_type", "slot_key", name="uq_creator_stadium_placements_match_slot"),
    )

    season_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_league_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creator_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    approved_by_admin_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    placement_type: Mapped[str] = mapped_column(String(24), nullable=False)
    slot_key: Mapped[str] = mapped_column(String(64), nullable=False)
    sponsor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    creative_asset_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    copy_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    price_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    creator_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    platform_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active")
    audit_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorRevenueSettlement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_revenue_settlements"
    __table_args__ = (
        UniqueConstraint("match_id", name="uq_creator_revenue_settlements_match_id"),
    )

    season_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_league_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    home_club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    away_club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ticket_sales_gross_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    ticket_sales_creator_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    ticket_sales_platform_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    stadium_matchday_revenue_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    stadium_matchday_creator_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    stadium_matchday_platform_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    premium_seating_revenue_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    premium_seating_creator_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    premium_seating_platform_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    in_stadium_ads_revenue_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    in_stadium_ads_creator_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    in_stadium_ads_platform_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    sponsor_banner_revenue_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    sponsor_banner_creator_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    sponsor_banner_platform_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    video_viewer_revenue_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    video_viewer_creator_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    video_viewer_platform_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    gift_revenue_gross_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    gift_creator_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    gift_platform_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    shareholder_match_video_distribution_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    shareholder_gift_distribution_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    shareholder_ticket_sales_distribution_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    shareholder_total_distribution_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    total_revenue_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    total_creator_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    total_platform_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    home_creator_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    away_creator_share_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    review_status: Mapped[str] = mapped_column(String(24), nullable=False, default="approved", server_default="approved", index=True)
    review_reason_codes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    policy_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reviewed_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "CreatorBroadcastModeConfig",
    "CreatorBroadcastPurchase",
    "CreatorMatchGiftEvent",
    "CreatorRevenueSettlement",
    "CreatorSeasonPass",
    "CreatorStadiumControl",
    "CreatorStadiumPlacement",
    "CreatorStadiumPricing",
    "CreatorStadiumProfile",
    "CreatorStadiumTicketPurchase",
]
