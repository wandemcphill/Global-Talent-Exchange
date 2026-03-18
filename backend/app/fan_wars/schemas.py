from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from backend.app.common.schemas.base import CommonSchema

FanWarProfileType = Literal["club", "country", "creator"]
FanWarBoardType = Literal["global", "club", "country", "creator"]
FanWarPeriodType = Literal["weekly", "monthly", "seasonal"]
FanWarSourceType = Literal[
    "watch_match",
    "gift",
    "prediction",
    "tournament_participation",
    "creator_support",
    "club_support",
]


class FanWarProfileUpsertRequest(CommonSchema):
    profile_type: FanWarProfileType
    display_name: str | None = Field(default=None, min_length=2, max_length=160)
    club_id: str | None = Field(default=None, min_length=1, max_length=36)
    creator_profile_id: str | None = Field(default=None, min_length=1, max_length=36)
    country_code: str | None = Field(default=None, min_length=2, max_length=8)
    country_name: str | None = Field(default=None, min_length=2, max_length=120)
    tagline: str | None = Field(default=None, min_length=2, max_length=255)
    scoring_config_json: dict[str, object] = Field(default_factory=dict)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class FanWarPointRecordRequest(CommonSchema):
    actor_user_id: str | None = Field(default=None, min_length=1, max_length=36)
    source_type: FanWarSourceType
    source_ref: str | None = Field(default=None, min_length=1, max_length=120)
    competition_id: str | None = Field(default=None, min_length=1, max_length=36)
    match_id: str | None = Field(default=None, min_length=1, max_length=36)
    club_id: str | None = Field(default=None, min_length=1, max_length=36)
    creator_profile_id: str | None = Field(default=None, min_length=1, max_length=36)
    country_code: str | None = Field(default=None, min_length=2, max_length=8)
    country_name: str | None = Field(default=None, min_length=2, max_length=120)
    profile_ids: tuple[str, ...] = ()
    target_categories: tuple[FanWarProfileType, ...] = ()
    spend_amount_minor: int = Field(default=0, ge=0)
    engagement_units: int = Field(default=1, ge=1, le=10000)
    quality_multiplier_bps: int = Field(default=10000, ge=0, le=50000)
    dedupe_key: str | None = Field(default=None, min_length=1, max_length=160)
    nations_cup_entry_id: str | None = Field(default=None, min_length=1, max_length=36)
    awarded_at: datetime | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)


class CreatorCountryAssignmentRequest(CommonSchema):
    creator_profile_id: str = Field(min_length=1, max_length=36)
    represented_country_code: str = Field(min_length=2, max_length=8)
    represented_country_name: str | None = Field(default=None, min_length=2, max_length=120)
    eligible_country_codes: tuple[str, ...] = ()
    assignment_rule: str = Field(default="admin_approved", min_length=3, max_length=48)
    allow_admin_override: bool = False
    effective_from: date | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)


class PresentationBannerView(CommonSchema):
    title: str
    subtitle: str | None = None
    accent_label: str | None = None
    highlighted_profile_id: str | None = None
    trailing_profile_id: str | None = None
    points_delta: int | None = None


class FanWarProfileView(CommonSchema):
    id: str
    profile_type: FanWarProfileType
    display_name: str
    slug: str
    club_id: str | None = None
    creator_profile_id: str | None = None
    country_code: str | None = None
    country_name: str | None = None
    tagline: str | None = None
    prestige_points: int
    rival_profile_ids: tuple[str, ...] = ()
    scoring_config_json: dict[str, object] = Field(default_factory=dict)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class FanWarPointView(CommonSchema):
    id: str
    profile_id: str
    source_type: FanWarSourceType
    source_ref: str | None = None
    competition_id: str | None = None
    match_id: str | None = None
    nations_cup_entry_id: str | None = None
    base_points: int
    bonus_points: int
    weighted_points: int
    engagement_units: int
    spend_amount_minor: int
    quality_multiplier_bps: int
    awarded_at: datetime
    metadata_json: dict[str, object] = Field(default_factory=dict)


class CreatorCountryAssignmentView(CommonSchema):
    id: str
    creator_profile_id: str
    creator_user_id: str
    club_id: str | None = None
    represented_country_code: str
    represented_country_name: str
    eligible_country_codes: tuple[str, ...] = ()
    assignment_rule: str
    allow_admin_override: bool
    assigned_by_user_id: str | None = None
    effective_from: date
    effective_to: date | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)


class FanWarSourceBreakdownView(CommonSchema):
    source_type: FanWarSourceType
    points: int
    event_count: int


class FanWarSummaryView(CommonSchema):
    total_points: int
    event_count: int
    unique_supporters: int
    momentum_points: int
    source_breakdown: tuple[FanWarSourceBreakdownView, ...] = ()
    recent_points: tuple[FanWarPointView, ...] = ()


class FanWarLeaderboardEntryView(CommonSchema):
    rank: int
    profile_id: str
    profile_type: FanWarProfileType
    display_name: str
    club_id: str | None = None
    creator_profile_id: str | None = None
    country_code: str | None = None
    country_name: str | None = None
    points_total: int
    event_count: int
    unique_supporters: int
    movement: int


class FanWarLeaderboardView(CommonSchema):
    board_type: FanWarBoardType
    period_type: FanWarPeriodType
    window_start: date
    window_end: date
    banner: PresentationBannerView | None = None
    entries: tuple[FanWarLeaderboardEntryView, ...] = ()


class RivalryLeaderboardEntryView(CommonSchema):
    profile_type: FanWarProfileType
    left_profile_id: str
    left_display_name: str
    left_points: int
    right_profile_id: str
    right_display_name: str
    right_points: int
    leader_profile_id: str | None = None
    points_gap: int


class RivalryLeaderboardView(CommonSchema):
    board_type: FanWarBoardType
    period_type: FanWarPeriodType
    banner: PresentationBannerView | None = None
    entries: tuple[RivalryLeaderboardEntryView, ...] = ()


class FanWarDashboardView(CommonSchema):
    profile: FanWarProfileView
    period_type: FanWarPeriodType
    window_start: date
    window_end: date
    global_rank: int | None = None
    category_rank: int | None = None
    banner: PresentationBannerView | None = None
    summary: FanWarSummaryView
    rivalry_entries: tuple[RivalryLeaderboardEntryView, ...] = ()


class NationsCupCreateRequest(CommonSchema):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    season_label: str | None = Field(default=None, min_length=2, max_length=64)
    start_date: date
    group_count: int = Field(default=8, ge=1, le=16)
    group_size: int = Field(default=4, ge=2, le=8)
    group_advance_count: int = Field(default=2, ge=1, le=4)
    creator_profile_ids: tuple[str, ...] = ()
    activate: bool = True
    created_by_user_id: str | None = Field(default=None, min_length=1, max_length=36)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class NationsCupEntryView(CommonSchema):
    id: str
    competition_id: str
    creator_profile_id: str
    creator_user_id: str
    club_id: str
    club_name: str | None = None
    creator_display_name: str | None = None
    country_code: str
    country_name: str
    seed: int
    group_key: str | None = None
    status: str
    advanced_to_knockout: bool
    fan_energy_score: int
    country_prestige_points: int
    creator_prestige_points: int
    fanbase_prestige_points: int
    played: int
    wins: int
    draws: int
    losses: int
    goal_diff: int
    competition_points: int
    group_rank: int | None = None
    record_summary_json: dict[str, object] = Field(default_factory=dict)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class NationsCupGroupView(CommonSchema):
    group_key: str
    standings: tuple[NationsCupEntryView, ...] = ()


class NationsCupRecordView(CommonSchema):
    label: str
    value: str
    entry_id: str | None = None


class NationsCupOverviewView(CommonSchema):
    competition_id: str
    title: str
    season_label: str
    status: str
    stage: str
    start_date: date
    format_description: str
    banner: PresentationBannerView | None = None
    groups: tuple[NationsCupGroupView, ...] = ()
    entries: tuple[NationsCupEntryView, ...] = ()
    records: tuple[NationsCupRecordView, ...] = ()
    total_fan_energy: int
