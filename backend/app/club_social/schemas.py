from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.common.schemas.base import CommonSchema
from app.config.club_social import DEFAULT_CHALLENGE_VISIBILITY


class ChallengeCreateRequest(CommonSchema):
    title: str = Field(min_length=4, max_length=160)
    message: str = Field(min_length=8, max_length=4000)
    stakes_text: str | None = Field(default=None, max_length=255)
    target_club_id: str | None = None
    visibility: str = Field(default=DEFAULT_CHALLENGE_VISIBILITY, max_length=24)
    country_code: str | None = Field(default=None, max_length=8)
    region_name: str | None = Field(default=None, max_length=120)
    city_name: str | None = Field(default=None, max_length=120)
    competition_id: str | None = None
    accept_by: datetime | None = None
    scheduled_for: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ChallengeAcceptRequest(CommonSchema):
    responding_club_id: str = Field(min_length=1)
    message: str | None = Field(default=None, max_length=4000)
    scheduled_for: datetime | None = None
    competition_id: str | None = None
    linked_match_id: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ChallengeLinkCreateRequest(CommonSchema):
    channel: str = Field(default="share", min_length=2, max_length=32)
    is_primary: bool = False
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ChallengeShareEventRequest(CommonSchema):
    link_id: str | None = None
    link_code: str | None = None
    event_type: str = Field(min_length=2, max_length=32)
    source_platform: str | None = Field(default=None, max_length=48)
    country_code: str | None = Field(default=None, max_length=8)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class RivalryMatchRecordRequest(CommonSchema):
    home_club_id: str = Field(min_length=1)
    away_club_id: str = Field(min_length=1)
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    winner_club_id: str | None = None
    match_id: str | None = None
    competition_id: str | None = None
    challenge_id: str | None = None
    happened_at: datetime | None = None
    final_flag: bool = False
    challenge_match_flag: bool = False
    high_view_flag: bool | None = None
    high_gift_flag: bool | None = None
    upset_flag: bool | None = None
    view_count: int = Field(default=0, ge=0)
    gift_count: int = Field(default=0, ge=0)
    notable_moments: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ChallengeView(CommonSchema):
    id: str
    issuing_club_id: str
    issuing_club_name: str
    target_club_id: str | None = None
    target_club_name: str | None = None
    accepted_club_id: str | None = None
    accepted_club_name: str | None = None
    competition_id: str | None = None
    linked_match_id: str | None = None
    winner_club_id: str | None = None
    winner_club_name: str | None = None
    title: str
    slug: str
    message: str
    stakes_text: str | None = None
    visibility: str
    country_code: str | None = None
    region_name: str | None = None
    city_name: str | None = None
    status: str
    accept_by: datetime | None = None
    scheduled_for: datetime | None = None
    live_at: datetime | None = None
    published_at: datetime | None = None
    settled_at: datetime | None = None
    countdown_seconds: int | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ChallengeResponseView(CommonSchema):
    id: str
    challenge_id: str
    responding_club_id: str
    responding_club_name: str
    responder_user_id: str | None = None
    response_type: str
    response_status: str
    message: str | None = None
    scheduled_for: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ChallengeLinkView(CommonSchema):
    id: str
    challenge_id: str
    channel: str
    link_code: str
    vanity_path: str
    web_path: str
    deep_link_path: str
    is_primary: bool
    is_active: bool
    click_count: int
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ChallengeShareEventView(CommonSchema):
    id: str
    challenge_id: str
    link_id: str | None = None
    actor_user_id: str | None = None
    event_type: str
    source_platform: str | None = None
    country_code: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ChallengeShareStatsView(CommonSchema):
    challenge_id: str
    total_events: int
    share_count: int
    click_count: int
    open_count: int
    country_breakdown: dict[str, int] = Field(default_factory=dict)


class MatchReactionView(CommonSchema):
    id: str
    match_id: str
    competition_id: str | None = None
    challenge_id: str | None = None
    rivalry_profile_id: str | None = None
    club_id: str | None = None
    reaction_type: str
    reaction_label: str
    intensity_score: int
    minute: int | None = None
    happened_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class MatchReactionFeedView(CommonSchema):
    match_id: str
    reactions: list[MatchReactionView] = Field(default_factory=list)


class RivalrySummaryView(CommonSchema):
    rivalry_id: str
    club_id: str
    club_name: str
    opponent_club_id: str
    opponent_club_name: str
    label: str
    intensity_score: int
    derby_indicator: bool
    giant_killer_flag: bool
    matches_played: int
    wins: int
    losses: int
    draws: int
    goals_for: int
    goals_against: int
    streak_holder_club_id: str | None = None
    streak_length: int
    upset_count: int
    challenge_matches: int
    high_view_matches: int
    high_gift_matches: int
    notable_moments: list[str] = Field(default_factory=list)
    narrative_tags: list[str] = Field(default_factory=list)
    rematch_prompt: str | None = None
    last_match_at: datetime | None = None


class RivalryHistoryView(CommonSchema):
    id: str
    rivalry_id: str
    match_id: str | None = None
    competition_id: str | None = None
    challenge_id: str | None = None
    home_club_id: str
    away_club_id: str
    winner_club_id: str | None = None
    home_score: int
    away_score: int
    upset_flag: bool
    final_flag: bool
    challenge_match_flag: bool
    high_view_flag: bool
    high_gift_flag: bool
    view_count: int
    gift_count: int
    match_weight: int
    notable_moments: list[str] = Field(default_factory=list)
    happened_at: datetime
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class RivalryDetailView(CommonSchema):
    summary: RivalrySummaryView
    history: list[RivalryHistoryView] = Field(default_factory=list)


class ClubIdentityMetricsView(CommonSchema):
    id: str
    club_id: str
    fan_count: int
    reputation_score: int
    media_popularity_score: int
    media_value_minor: int
    club_valuation_minor: int
    rivalry_intensity_score: int
    support_momentum_score: int
    sponsorship_potential_score: int
    discoverability_score: int
    challenge_history_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ChallengeCardView(CommonSchema):
    challenge_id: str
    title: str
    issuing_club_id: str
    issuing_club_name: str
    opponent_club_id: str | None = None
    opponent_club_name: str | None = None
    status: str
    stakes_text: str | None = None
    countdown_seconds: int | None = None
    spectator_hype_score: int
    rivalry_label: str | None = None
    derby_indicator: bool = False
    giant_killer_flag: bool = False
    primary_web_path: str | None = None
    primary_deep_link_path: str | None = None
    share_count: int = 0


class ChallengePageView(CommonSchema):
    challenge: ChallengeView
    card: ChallengeCardView
    responses: list[ChallengeResponseView] = Field(default_factory=list)
    links: list[ChallengeLinkView] = Field(default_factory=list)
    share_stats: ChallengeShareStatsView
    rivalry: RivalrySummaryView | None = None
    recent_reactions: list[MatchReactionView] = Field(default_factory=list)


class ClubChallengesView(CommonSchema):
    club_id: str
    challenges: list[ChallengeCardView] = Field(default_factory=list)


class ClubRivalriesView(CommonSchema):
    club_id: str
    rivalries: list[RivalrySummaryView] = Field(default_factory=list)
