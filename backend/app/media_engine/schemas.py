from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class MatchViewCreateRequest(BaseModel):
    match_key: str = Field(min_length=2)
    competition_key: str | None = None
    watch_seconds: int = Field(default=30, ge=1, le=7200)
    premium_unlocked: bool = False


class PremiumVideoPurchaseRequest(BaseModel):
    match_key: str = Field(min_length=2)
    competition_key: str | None = None


class RevenueSnapshotCreateRequest(BaseModel):
    match_key: str = Field(min_length=2)
    competition_key: str | None = None
    home_club_id: str | None = None
    away_club_id: str | None = None


class MatchViewView(BaseModel):
    id: str
    user_id: str
    match_key: str
    competition_key: str | None
    view_date_key: str
    watch_seconds: int
    premium_unlocked: bool
    metadata_json: dict[str, object]


class PremiumVideoPurchaseView(BaseModel):
    id: str
    user_id: str
    match_key: str
    competition_key: str | None
    price_coin: Decimal
    price_fancoin_equivalent: Decimal
    metadata_json: dict[str, object]


class MatchRevenueSnapshotView(BaseModel):
    id: str
    match_key: str
    competition_key: str | None
    home_club_id: str | None
    away_club_id: str | None
    total_views: int
    premium_purchases: int
    total_revenue_coin: Decimal
    home_club_share_coin: Decimal
    away_club_share_coin: Decimal
    metadata_json: dict[str, object]


class MediaAssetView(BaseModel):
    storage_key: str
    content_type: str
    size_bytes: int
    metadata: dict[str, Any]
    expires_at: datetime | None = None


class MediaDownloadRequest(BaseModel):
    storage_key: str = Field(min_length=3)
    match_key: str | None = None
    download_kind: str = Field(default="highlight")
    premium_required: bool = True
    watermark_label: str | None = None
    watermark_metadata: dict[str, Any] = Field(default_factory=dict)


class MediaDownloadResponse(BaseModel):
    storage_key: str
    download_url: str
    expires_at: datetime
    content_type: str
    filename: str
    metadata: dict[str, Any]


class HighlightShareTemplateView(BaseModel):
    id: str
    code: str
    name: str
    description: str | None
    aspect_ratio: str
    is_active: bool
    overlay_defaults_json: dict[str, Any]
    metadata_json: dict[str, Any]


class HighlightShareExportRequest(BaseModel):
    source_storage_key: str = Field(min_length=3)
    match_key: str = Field(min_length=2)
    competition_key: str | None = None
    template_code: str | None = None
    aspect_ratio: str | None = None
    share_title: str | None = None
    share_caption: str | None = None
    watermark_label: str | None = None
    enable_watermark: bool = True
    include_scoreline_overlay: bool = True
    include_club_name_overlay: bool = True
    include_match_metadata_card: bool = True
    include_sponsor_overlay: bool = True
    scoreline: dict[str, Any] = Field(default_factory=dict)
    club_names: dict[str, Any] = Field(default_factory=dict)
    home_club_id: str | None = None
    away_club_id: str | None = None
    stage_name: str | None = None
    region_code: str | None = None
    rivalry_visibility: int = Field(default=0, ge=0)


class HighlightShareExportView(BaseModel):
    export_id: str
    storage_key: str
    content_type: str
    size_bytes: int
    template_code: str | None
    aspect_ratio: str
    share_title: str | None
    watermark_label: str | None
    metadata: dict[str, Any]
    created_at: datetime


class HighlightShareAmplificationRequest(BaseModel):
    channel: str = Field(default="story_feed", min_length=3, max_length=32)
    subject_type: str | None = Field(default=None, max_length=48)
    subject_id: str | None = Field(default=None, max_length=64)
    title: str | None = Field(default=None, max_length=200)
    caption: str | None = Field(default=None, max_length=4000)
    country_code: str | None = Field(default=None, max_length=8)
    featured: bool = False
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class HighlightShareAmplificationView(BaseModel):
    id: str
    export_id: str
    story_feed_item_id: str | None
    channel: str
    status: str
    subject_type: str | None
    subject_id: str | None
    title: str
    caption: str | None
    metadata_json: dict[str, Any]
    created_at: datetime


class CreatorBroadcastPurchaseRequest(BaseModel):
    duration_minutes: int = Field(ge=10, le=90)


class CreatorSeasonPassCreateRequest(BaseModel):
    season_id: str = Field(min_length=1, max_length=36)
    club_id: str = Field(min_length=1, max_length=36)


class CreatorStadiumConfigUpdateRequest(BaseModel):
    season_id: str = Field(min_length=1, max_length=36)
    matchday_ticket_price_coin: Decimal = Field(gt=0)
    season_pass_price_coin: Decimal = Field(gt=0)
    vip_ticket_price_coin: Decimal = Field(gt=0)
    visual_upgrade_level: int = Field(default=1, ge=1, le=5)
    custom_chant_text: str | None = Field(default=None, max_length=255)
    custom_visuals_json: dict[str, Any] = Field(default_factory=dict)


class CreatorStadiumTicketPurchaseRequest(BaseModel):
    ticket_type: str = Field(pattern="^(matchday|vip)$")


class CreatorStadiumPlacementCreateRequest(BaseModel):
    placement_type: str = Field(pattern="^(in_stadium_ad|sponsor_banner)$")
    slot_key: str = Field(min_length=2, max_length=64)
    sponsor_name: str = Field(min_length=2, max_length=120)
    price_coin: Decimal = Field(gt=0)
    creative_asset_url: str | None = Field(default=None, max_length=255)
    copy_text: str | None = Field(default=None, max_length=255)
    audit_note: str | None = Field(default=None, max_length=255)


class CreatorStadiumControlUpdateRequest(BaseModel):
    max_matchday_ticket_price_coin: Decimal = Field(gt=0)
    max_season_pass_price_coin: Decimal = Field(gt=0)
    max_vip_ticket_price_coin: Decimal = Field(gt=0)
    max_stadium_level: int = Field(ge=1, le=5)
    vip_seat_ratio_bps: int = Field(gt=0, le=10000)
    max_in_stadium_ad_slots: int = Field(ge=0, le=24)
    max_sponsor_banner_slots: int = Field(ge=0, le=24)
    ad_placement_enabled: bool = True
    ticket_sales_enabled: bool = True
    max_placement_price_coin: Decimal = Field(default=Decimal("250.0000"), gt=0)


class CreatorStadiumLevelUpdateRequest(BaseModel):
    level: int = Field(ge=1, le=5)


class CreatorMatchGiftRequest(BaseModel):
    club_id: str = Field(min_length=1, max_length=36)
    amount_coin: Decimal = Field(gt=0)
    gift_label: str = Field(min_length=2, max_length=80)
    note: str | None = Field(default=None, max_length=255)


class CreatorBroadcastModeView(BaseModel):
    mode_key: str
    name: str
    description: str | None
    min_duration_minutes: int
    max_duration_minutes: int
    min_price_coin: Decimal
    max_price_coin: Decimal
    metadata_json: dict[str, Any]


class CreatorMatchAccessView(BaseModel):
    match_id: str
    competition_id: str
    season_id: str
    home_club_id: str
    away_club_id: str
    mode_key: str
    mode_name: str
    duration_minutes: int
    price_coin: Decimal
    has_access: bool
    access_source: str | None = None
    pass_club_id: str | None = None
    stadium_ticket_type: str | None = None
    includes_premium_seating: bool = False
    metadata_json: dict[str, Any]


class CreatorBroadcastPurchaseView(BaseModel):
    id: str
    user_id: str
    season_id: str
    competition_id: str
    match_id: str
    mode_key: str
    duration_minutes: int
    price_coin: Decimal
    platform_share_coin: Decimal
    home_creator_share_coin: Decimal
    away_creator_share_coin: Decimal
    metadata_json: dict[str, Any]


class CreatorSeasonPassView(BaseModel):
    id: str
    user_id: str
    creator_user_id: str
    season_id: str
    club_id: str
    access_scope: str
    price_coin: Decimal
    creator_share_coin: Decimal
    platform_share_coin: Decimal
    includes_full_season: bool
    includes_home_away: bool
    includes_live_highlights: bool
    metadata_json: dict[str, Any]


class CreatorStadiumControlView(BaseModel):
    id: str
    control_key: str
    max_matchday_ticket_price_coin: Decimal
    max_season_pass_price_coin: Decimal
    max_vip_ticket_price_coin: Decimal
    max_stadium_level: int
    vip_seat_ratio_bps: int
    max_in_stadium_ad_slots: int
    max_sponsor_banner_slots: int
    ad_placement_enabled: bool
    ticket_sales_enabled: bool
    max_placement_price_coin: Decimal
    metadata_json: dict[str, Any]


class CreatorStadiumProfileView(BaseModel):
    id: str
    club_id: str
    creator_user_id: str
    club_stadium_id: str | None = None
    level: int
    capacity: int
    premium_seat_capacity: int
    visual_upgrade_level: int
    custom_chant_text: str | None = None
    custom_visuals_json: dict[str, Any]
    metadata_json: dict[str, Any]


class CreatorStadiumPricingView(BaseModel):
    id: str
    season_id: str
    club_id: str
    creator_user_id: str
    matchday_ticket_price_coin: Decimal
    season_pass_price_coin: Decimal
    vip_ticket_price_coin: Decimal
    live_video_access_enabled: bool
    stadium_visual_upgrades_enabled: bool
    custom_chants_enabled: bool
    custom_visuals_enabled: bool
    is_active: bool
    metadata_json: dict[str, Any]


class CreatorStadiumPlacementView(BaseModel):
    id: str
    season_id: str
    competition_id: str
    match_id: str
    club_id: str
    creator_user_id: str
    approved_by_admin_user_id: str | None = None
    placement_type: str
    slot_key: str
    sponsor_name: str
    creative_asset_url: str | None = None
    copy_text: str | None = None
    price_coin: Decimal
    creator_share_coin: Decimal
    platform_share_coin: Decimal
    status: str
    audit_note: str | None = None
    metadata_json: dict[str, Any]


class CreatorStadiumTicketPurchaseView(BaseModel):
    id: str
    user_id: str
    creator_user_id: str
    season_id: str
    competition_id: str
    match_id: str
    club_id: str
    ticket_type: str
    seat_tier: str
    price_coin: Decimal
    creator_share_coin: Decimal
    platform_share_coin: Decimal
    includes_live_video_access: bool
    includes_premium_seating: bool
    includes_stadium_visual_upgrades: bool
    includes_custom_chants: bool
    includes_custom_visuals: bool
    metadata_json: dict[str, Any]


class CreatorStadiumMonetizationView(BaseModel):
    season_id: str
    club_id: str
    control: CreatorStadiumControlView
    stadium: CreatorStadiumProfileView
    pricing: CreatorStadiumPricingView | None = None


class CreatorMatchStadiumOfferView(BaseModel):
    match_id: str
    competition_id: str
    season_id: str
    club_id: str
    stadium: CreatorStadiumProfileView
    pricing: CreatorStadiumPricingView
    control: CreatorStadiumControlView
    remaining_capacity: int
    remaining_vip_capacity: int
    placements: list[CreatorStadiumPlacementView]
    metadata_json: dict[str, Any]


class CreatorMatchGiftView(BaseModel):
    id: str
    season_id: str
    competition_id: str
    match_id: str
    sender_user_id: str
    recipient_creator_user_id: str
    club_id: str
    gift_label: str
    gross_amount_coin: Decimal
    creator_share_coin: Decimal
    platform_share_coin: Decimal
    note: str | None
    metadata_json: dict[str, Any]


class CreatorRevenueSettlementView(BaseModel):
    id: str
    season_id: str
    competition_id: str
    match_id: str
    home_club_id: str
    away_club_id: str
    ticket_sales_gross_coin: Decimal
    ticket_sales_creator_share_coin: Decimal
    ticket_sales_platform_share_coin: Decimal
    stadium_matchday_revenue_coin: Decimal
    stadium_matchday_creator_share_coin: Decimal
    stadium_matchday_platform_share_coin: Decimal
    premium_seating_revenue_coin: Decimal
    premium_seating_creator_share_coin: Decimal
    premium_seating_platform_share_coin: Decimal
    in_stadium_ads_revenue_coin: Decimal
    in_stadium_ads_creator_share_coin: Decimal
    in_stadium_ads_platform_share_coin: Decimal
    sponsor_banner_revenue_coin: Decimal
    sponsor_banner_creator_share_coin: Decimal
    sponsor_banner_platform_share_coin: Decimal
    video_viewer_revenue_coin: Decimal
    video_viewer_creator_share_coin: Decimal
    video_viewer_platform_share_coin: Decimal
    gift_revenue_gross_coin: Decimal
    gift_creator_share_coin: Decimal
    gift_platform_share_coin: Decimal
    shareholder_match_video_distribution_coin: Decimal
    shareholder_gift_distribution_coin: Decimal
    shareholder_ticket_sales_distribution_coin: Decimal
    shareholder_total_distribution_coin: Decimal
    total_revenue_coin: Decimal
    total_creator_share_coin: Decimal
    total_platform_share_coin: Decimal
    home_creator_share_coin: Decimal
    away_creator_share_coin: Decimal
    review_status: str
    review_reason_codes_json: list[str]
    policy_snapshot_json: dict[str, Any]
    reviewed_by_user_id: str | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None
    settled_at: datetime | None = None
    metadata_json: dict[str, Any]


class CreatorAnalyticsTopGifterView(BaseModel):
    user_id: str
    username: str
    display_name: str | None
    total_gift_coin: Decimal
    gift_count: int


class CreatorAnalyticsDashboardView(BaseModel):
    match_id: str
    competition_id: str
    season_id: str
    club_id: str | None = None
    total_viewers: int
    video_viewers: int
    gift_totals_coin: Decimal
    top_gifters: list[CreatorAnalyticsTopGifterView]
    fan_engagement_pct: Decimal
    engaged_fans: int
    total_watch_seconds: int
    metadata_json: dict[str, Any]
