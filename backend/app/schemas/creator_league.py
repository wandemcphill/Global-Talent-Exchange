from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from backend.app.common.enums.match_status import MatchStatus
from backend.app.common.schemas.base import CommonSchema


class CreatorLeagueTierCreateRequest(CommonSchema):
    name: str | None = Field(default=None, min_length=3, max_length=80)
    club_count: int = Field(default=20, ge=2, le=64)
    promotion_spots: int = Field(default=3, ge=0, le=20)
    relegation_spots: int = Field(default=0, ge=0, le=20)


class CreatorLeagueTierUpdateRequest(CommonSchema):
    name: str | None = Field(default=None, min_length=3, max_length=80)
    club_count: int | None = Field(default=None, ge=2, le=64)
    promotion_spots: int | None = Field(default=None, ge=0, le=20)
    relegation_spots: int | None = Field(default=None, ge=0, le=20)
    active: bool | None = None


class CreatorLeagueConfigUpdateRequest(CommonSchema):
    enabled: bool | None = None
    seasons_paused: bool | None = None
    league_format: str | None = Field(default=None, min_length=3, max_length=64)
    default_club_count: int | None = Field(default=None, ge=2, le=64)
    division_count: int | None = Field(default=None, ge=1, le=20)
    match_frequency_days: int | None = Field(default=None, ge=1, le=30)
    season_duration_days: int | None = Field(default=None, ge=1, le=730)
    broadcast_purchases_enabled: bool | None = None
    season_pass_sales_enabled: bool | None = None
    match_gifting_enabled: bool | None = None
    settlement_review_enabled: bool | None = None
    settlement_review_total_revenue_coin: Decimal | None = Field(default=None, ge=0)
    settlement_review_creator_share_coin: Decimal | None = Field(default=None, ge=0)
    settlement_review_platform_share_coin: Decimal | None = Field(default=None, ge=0)
    settlement_review_shareholder_distribution_coin: Decimal | None = Field(default=None, ge=0)


class CreatorLeagueSeasonTierAssignmentRequest(CommonSchema):
    tier_id: str = Field(min_length=1, max_length=36)
    club_ids: tuple[str, ...]


class CreatorLeagueSeasonCreateRequest(CommonSchema):
    start_date: date
    name: str | None = Field(default=None, min_length=3, max_length=120)
    activate: bool = True
    created_by_user_id: str | None = Field(default=None, min_length=1, max_length=36)
    assignments: tuple[CreatorLeagueSeasonTierAssignmentRequest, ...]


class CreatorLeagueMovementRuleView(CommonSchema):
    tier_id: str
    tier_name: str
    direction: Literal["promotion", "relegation"]
    target_tier_id: str
    target_tier_name: str
    spots: int


class CreatorLeagueTierView(CommonSchema):
    id: str
    name: str
    slug: str
    display_order: int
    club_count: int
    promotion_spots: int
    relegation_spots: int
    active: bool


class CreatorLeagueSeasonTierView(CommonSchema):
    id: str
    tier_id: str
    competition_id: str
    competition_name: str
    tier_name: str
    tier_order: int
    club_ids: tuple[str, ...]
    round_count: int
    fixture_count: int
    status: str
    banner_title: str | None = None
    banner_subtitle: str | None = None


class CreatorLeagueSeasonView(CommonSchema):
    id: str
    season_number: int
    name: str
    status: str
    start_date: date
    end_date: date
    match_frequency_days: int
    season_duration_days: int
    launched_at: datetime | None = None
    paused_at: datetime | None = None
    completed_at: datetime | None = None
    tiers: tuple[CreatorLeagueSeasonTierView, ...] = ()


class CreatorLeagueConfigView(CommonSchema):
    id: str
    league_key: str
    enabled: bool
    seasons_paused: bool
    league_format: str
    default_club_count: int
    division_count: int
    match_frequency_days: int
    season_duration_days: int
    broadcast_purchases_enabled: bool
    season_pass_sales_enabled: bool
    match_gifting_enabled: bool
    settlement_review_enabled: bool
    settlement_review_total_revenue_coin: Decimal
    settlement_review_creator_share_coin: Decimal
    settlement_review_platform_share_coin: Decimal
    settlement_review_shareholder_distribution_coin: Decimal
    tiers: tuple[CreatorLeagueTierView, ...]
    movement_rules: tuple[CreatorLeagueMovementRuleView, ...]
    current_season: CreatorLeagueSeasonView | None = None


class CreatorLeagueStandingView(CommonSchema):
    rank: int
    club_id: str
    club_name: str | None = None
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int
    movement_zone: Literal["promotion", "relegation", "safe"]


class CreatorLeagueLiveMatchView(CommonSchema):
    match_id: str
    competition_id: str
    competition_name: str
    season_id: str | None = None
    season_tier_id: str | None = None
    home_club_id: str
    home_club_name: str | None = None
    away_club_id: str
    away_club_name: str | None = None
    scheduled_at: datetime | None = None
    status: MatchStatus
    is_creator_league: bool
    priority_rank: int
    banner_title: str | None = None
    banner_subtitle: str | None = None


class CreatorLeagueLivePriorityView(CommonSchema):
    banner_title: str | None = None
    banner_subtitle: str | None = None
    matches: tuple[CreatorLeagueLiveMatchView, ...] = ()


class CreatorLeagueShareMarketControlSnapshotView(CommonSchema):
    id: str
    control_key: str
    max_shares_per_club: int
    max_shares_per_fan: int
    shareholder_revenue_share_bps: int
    issuance_enabled: bool
    purchase_enabled: bool
    max_primary_purchase_value_coin: Decimal
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class CreatorLeagueStadiumControlSnapshotView(CommonSchema):
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
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class CreatorLeagueGiftControlView(CommonSchema):
    max_amount: Decimal
    daily_sender_limit: Decimal
    daily_recipient_limit: Decimal
    daily_pair_limit: Decimal
    cooldown_seconds: int
    burst_window_seconds: int
    burst_max_count: int
    review_threshold_bps: int


class CreatorLeagueSettlementReviewRequest(CommonSchema):
    review_note: str | None = Field(default=None, max_length=255)


class CreatorLeagueSettlementView(CommonSchema):
    id: str
    season_id: str
    competition_id: str
    match_id: str
    home_club_id: str
    away_club_id: str
    total_revenue_coin: Decimal
    total_creator_share_coin: Decimal
    total_platform_share_coin: Decimal
    shareholder_total_distribution_coin: Decimal
    review_status: str
    review_reason_codes_json: tuple[str, ...] = ()
    policy_snapshot_json: dict[str, object]
    reviewed_by_user_id: str | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None
    settled_at: datetime | None = None
    metadata_json: dict[str, object]


class CreatorLeagueFinancialSummaryView(CommonSchema):
    season_id: str | None = None
    settlement_count: int
    approved_settlement_count: int
    review_required_settlement_count: int
    total_revenue_coin: Decimal
    total_creator_share_coin: Decimal
    total_platform_share_coin: Decimal
    total_shareholder_distribution_coin: Decimal
    total_ticket_sales_gross_coin: Decimal
    total_video_viewer_revenue_coin: Decimal
    total_gift_revenue_gross_coin: Decimal
    total_stadium_placement_revenue_coin: Decimal


class CreatorLeagueAuditEventView(CommonSchema):
    id: str
    actor_user_id: str | None = None
    action_key: str
    resource_type: str
    resource_id: str | None = None
    outcome: str
    detail: str
    metadata_json: dict[str, object]
    created_at: datetime


class CreatorLeagueFinancialReportView(CommonSchema):
    config: CreatorLeagueConfigView
    share_market_control: CreatorLeagueShareMarketControlSnapshotView
    stadium_control: CreatorLeagueStadiumControlSnapshotView
    creator_match_gift_controls: CreatorLeagueGiftControlView
    current_season_summary: CreatorLeagueFinancialSummaryView | None = None
    settlements_requiring_review: tuple[CreatorLeagueSettlementView, ...] = ()
    recent_audit_events: tuple[CreatorLeagueAuditEventView, ...] = ()
