from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UniverseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CareerCreateRequest(BaseModel):
    player_id: str | None = None
    player_name: str | None = Field(default=None, max_length=160)
    position: str | None = Field(default=None, max_length=64)
    current_club: str | None = Field(default=None, max_length=160)
    growth_rate: float = Field(default=0.08, gt=0.0, le=1.0)


class CareerTrainRequest(BaseModel):
    focus: str = Field(default="balanced", min_length=1, max_length=64)
    intensity: str = Field(default="normal", min_length=1, max_length=16)


class CareerTransferRequest(BaseModel):
    current_club: str = Field(min_length=1, max_length=160)
    wage_amount: float = Field(default=0.0, ge=0.0)
    contract_days: int = Field(default=365, ge=30, le=3650)
    notes: str | None = Field(default=None, max_length=255)


class CareerRetireRequest(BaseModel):
    legacy_role: str = Field(default="hall_of_fame", min_length=3, max_length=64)
    legacy_headline: str | None = Field(default=None, max_length=255)


class CareerPlayerView(UniverseSchema):
    id: str
    user_id: str
    player_id: str
    current_club: str | None
    current_club_id: str | None
    career_stats: dict[str, Any]
    growth_rate: float
    xp: int
    level: int
    training_focus: str
    current_form: float
    marketability_score: float
    prestige_score: int
    status: str
    retired_at: datetime | None
    legacy_summary_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class SyncCompetitionInput(BaseModel):
    external_key: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=160)
    country_name: str | None = Field(default=None, max_length=120)
    competition_type: str = Field(default="cup", min_length=1, max_length=32)


class SyncClubInput(BaseModel):
    external_key: str = Field(min_length=1, max_length=128)
    competition_external_key: str | None = Field(default=None, max_length=128)
    name: str = Field(min_length=1, max_length=160)
    country_name: str | None = Field(default=None, max_length=120)
    gtex_team_id: str | None = None
    gtex_team_type: str = Field(default="ai_profile", min_length=1, max_length=32)


class SyncPlayerInput(BaseModel):
    external_key: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=160)
    club_external_key: str | None = Field(default=None, max_length=128)
    competition_external_key: str | None = Field(default=None, max_length=128)
    gtex_player_id: str | None = None
    nationality: str | None = Field(default=None, max_length=120)
    position: str | None = Field(default=None, max_length=64)
    real_world_rating: float = Field(default=50.0, ge=0.0, le=100.0)
    market_value: float | None = Field(default=None, ge=0.0)
    injury_status: str | None = Field(default=None, max_length=64)
    stats_json: dict[str, Any] = Field(default_factory=dict)


class SyncEventInput(BaseModel):
    external_key: str = Field(min_length=1, max_length=128)
    competition_external_key: str | None = Field(default=None, max_length=128)
    home_club_external_key: str | None = Field(default=None, max_length=128)
    away_club_external_key: str | None = Field(default=None, max_length=128)
    headline: str | None = Field(default=None, max_length=255)
    event_type: str = Field(default="fixture", min_length=1, max_length=32)
    status: str = Field(default="scheduled", min_length=1, max_length=24)
    scheduled_at: datetime
    home_score: int | None = Field(default=None, ge=0)
    away_score: int | None = Field(default=None, ge=0)
    featured_player_keys: list[str] = Field(default_factory=list)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)


class SyncUpdateRequest(BaseModel):
    provider_name: str = Field(default="manual-sync", min_length=1, max_length=80)
    provider_endpoint: str = Field(default="manual://sync", min_length=1, max_length=255)
    optional_sync: bool = True
    mirror_into_gtex: bool = True
    career_user_id: str | None = None
    competitions: list[SyncCompetitionInput] = Field(default_factory=list)
    clubs: list[SyncClubInput] = Field(default_factory=list)
    players: list[SyncPlayerInput] = Field(default_factory=list)
    events: list[SyncEventInput] = Field(default_factory=list)


class RealWorldEventView(UniverseSchema):
    id: str
    provider_id: str
    competition_id: str | None
    home_club_id: str | None
    away_club_id: str | None
    external_key: str
    headline: str
    event_type: str
    status: str
    scheduled_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    home_score: int | None
    away_score: int | None
    mirror_match_id: str | None
    magnitude_score: float
    influence_applied_at: datetime | None
    influence_summary_json: dict[str, Any]
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class SyncUpdateResponse(BaseModel):
    provider_id: str
    sync_job_id: str
    competitions_upserted: int
    clubs_upserted: int
    players_upserted: int
    events_upserted: int
    mirrored_match_ids: list[str] = Field(default_factory=list)
    optional_sync: bool
    non_breaking: bool = True


class FanProfileUpdateRequest(BaseModel):
    favorite_club_id: str | None = None
    favorite_player_id: str | None = None
    rival_club_ids: list[str] = Field(default_factory=list)


class FanProfileView(UniverseSchema):
    id: str
    user_id: str
    favorite_club: dict[str, Any] = Field(default_factory=dict)
    favorite_player: dict[str, Any] = Field(default_factory=dict)
    fan_tier: str
    loyalty_score: float
    reputation_score: float
    attendance_count: int
    attendance_history: list[dict[str, Any]] = Field(default_factory=list)
    rival_club_ids: list[str] = Field(default_factory=list)
    badges: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    current_tribe: dict[str, Any] | None = None


class FanTribeJoinRequest(BaseModel):
    club_id: str | None = None
    match_id: str | None = None


class FanTribeView(UniverseSchema):
    id: str
    club_id: str
    club_name: str | None = None
    tribe_name: str | None = None
    members: list[str] = Field(default_factory=list)
    rivalry_targets: list[str] = Field(default_factory=list)
    power_score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class FanTicketPurchaseRequest(BaseModel):
    ticket_tier: str = Field(default="matchday", min_length=3, max_length=24)


class FanExperienceTicketView(UniverseSchema):
    id: str
    event_type: str
    event_key: str
    match_id: str | None = None
    ticket_tier: str
    access_level: str
    status: str
    seat_label: str | None = None
    price_coin: Decimal
    discount_bps: int
    priority_stream: bool
    exclusive_commentary_lines: list[str] = Field(default_factory=list)
    loyalty_bonus: float
    reputation_bonus: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class FanReactionCreateRequest(BaseModel):
    reaction_type: str = Field(min_length=3, max_length=24)
    supported_side: str | None = Field(default="home", max_length=8)


class FanReactionSignalView(UniverseSchema):
    id: str
    match_id: str | None = None
    event_key: str
    channel: str
    reaction_type: str
    supported_side: str | None = None
    weight: float
    tier_at_reaction: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MatchChatMessageCreateRequest(BaseModel):
    message: str | None = Field(default=None, max_length=240)
    emoji: str | None = Field(default=None, max_length=32)
    intensity: float = Field(default=1.0, ge=0.2, le=3.0)


class MatchChatMessageView(UniverseSchema):
    id: str
    room_id: str
    match_id: str
    user_id: str
    fan_tribe_id: str | None = None
    fan_tribe_name: str | None = None
    message: str | None = None
    emoji: str | None = None
    intensity: float
    sentiment: str
    spike_score: float
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class MatchChatPostResponseView(UniverseSchema):
    message: MatchChatMessageView
    live_chat: dict[str, Any] = Field(default_factory=dict)
    fan_war: dict[str, Any] = Field(default_factory=dict)


class MatchFanExperienceView(UniverseSchema):
    event_key: str
    match_id: str
    event_title: str
    is_final: bool
    capacity: int
    vip_capacity: int
    tickets_sold: int
    vip_tickets_sold: int
    tickets_remaining: int
    ticket_price_coin: Decimal
    vip_ticket_price_coin: Decimal
    ticket_access_phase: str
    exclusive_commentary_lines: list[str] = Field(default_factory=list)
    sell_out_hype: dict[str, Any] = Field(default_factory=dict)
    current_user: dict[str, Any] | None = None
    discount_bps: int
    reaction_summary: dict[str, Any] = Field(default_factory=dict)
    atmosphere: dict[str, Any] = Field(default_factory=dict)
    social_warfare: dict[str, Any] = Field(default_factory=dict)


class MatchSocialWarfareView(UniverseSchema):
    match_id: str
    current_user_tribe: dict[str, Any] | None = None
    fan_tribes: list[dict[str, Any]] = Field(default_factory=list)
    fan_war: dict[str, Any] = Field(default_factory=dict)
    live_chat: dict[str, Any] = Field(default_factory=dict)
    narrative_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    market_shocks: list[dict[str, Any]] = Field(default_factory=list)
    mega_event: dict[str, Any] | None = None
    legacy: dict[str, Any] = Field(default_factory=dict)


class LegacyBoardView(UniverseSchema):
    generated_at: datetime
    greatest_matches: list[dict[str, Any]] = Field(default_factory=list)
    top_players: list[dict[str, Any]] = Field(default_factory=list)
    club_dynasties: list[dict[str, Any]] = Field(default_factory=list)


class CeremonyTicketPurchaseRequest(BaseModel):
    ticket_tier: str = Field(default="general", min_length=3, max_length=24)


class CeremonyVoteRequest(BaseModel):
    award_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    season_id: str | None = None


class RegenHypeBoardView(UniverseSchema):
    wonderkids: list[dict[str, Any]] = Field(default_factory=list)
    rising_stars: list[dict[str, Any]] = Field(default_factory=list)
    national_heroes: list[dict[str, Any]] = Field(default_factory=list)
    award_nominee_headlines: list[dict[str, Any]] = Field(default_factory=list)
    news_article_ids: list[str] = Field(default_factory=list)


class FullExperienceSimulationRequest(BaseModel):
    match_id: str = Field(min_length=1)
    season_id: str | None = None


class FullExperienceSimulationView(UniverseSchema):
    fan_profile: dict[str, Any]
    ticket: dict[str, Any]
    reaction: dict[str, Any]
    match: dict[str, Any]
    ceremony: dict[str, Any] | None = None
    regen_hype: dict[str, Any]
    timeline: list[str] = Field(default_factory=list)
