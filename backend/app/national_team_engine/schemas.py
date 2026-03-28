from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class NationalTeamCompetitionCreateRequest(BaseModel):
    key: str = Field(min_length=3, max_length=64)
    title: str = Field(min_length=3, max_length=160)
    season_label: str = Field(min_length=2, max_length=64)
    region_type: str = Field(default="global", max_length=32)
    age_band: str = Field(default="senior", max_length=16)
    format_type: str = Field(default="cup", max_length=32)
    status: str = Field(default="draft", max_length=32)
    notes: str | None = Field(default=None, max_length=2000)
    linked_competition_id: str | None = Field(default=None, max_length=36)
    entry_opens_at: datetime | None = None
    entry_closes_at: datetime | None = None
    kickoff_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class NationalTeamCompetitionResponse(BaseModel):
    id: str
    key: str
    title: str
    season_label: str
    region_type: str
    age_band: str
    format_type: str
    status: str
    notes: str | None
    active: bool
    linked_competition_id: str | None
    entry_opens_at: datetime | None
    entry_closes_at: datetime | None
    kickoff_at: datetime | None
    completed_at: datetime | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class NationalTeamEntryUpsertRequest(BaseModel):
    country_code: str = Field(min_length=2, max_length=8)
    country_name: str = Field(min_length=2, max_length=120)
    manager_user_id: str | None = Field(default=None, max_length=36)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class NationalTeamEntryResponse(BaseModel):
    id: str
    competition_id: str
    country_code: str
    country_name: str
    manager_user_id: str | None
    squad_size: int
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class NationalTeamSquadMemberUpsert(BaseModel):
    user_id: str = Field(min_length=3, max_length=36)
    player_name: str = Field(min_length=2, max_length=160)
    shirt_number: int | None = Field(default=None, ge=1, le=99)
    role_label: str | None = Field(default=None, max_length=64)
    status: str = Field(default="selected", max_length=32)


class NationalTeamSquadUpsertRequest(BaseModel):
    members: list[NationalTeamSquadMemberUpsert] = Field(default_factory=list)


class NationalTeamSquadMemberResponse(BaseModel):
    id: str
    entry_id: str
    user_id: str
    player_name: str
    shirt_number: int | None
    role_label: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class NationalTeamManagerHistoryResponse(BaseModel):
    id: str
    entry_id: str
    user_id: str | None
    action_type: str
    note: str | None
    created_at: datetime
    updated_at: datetime


class NationalTeamEntryDetailResponse(NationalTeamEntryResponse):
    squad_members: list[NationalTeamSquadMemberResponse]
    manager_history: list[NationalTeamManagerHistoryResponse]
    rental_squad_members: list["NationalTeamRentalSquadMemberResponse"] = Field(default_factory=list)
    rental_contracts: list["RentalContractResponse"] = Field(default_factory=list)
    free_players_remaining: int = 0
    minimum_squad_size: int = 18
    maximum_squad_size: int = 30


class NationalTeamUserHistoryResponse(BaseModel):
    managed_entries: list[NationalTeamEntryResponse]
    squad_memberships: list[NationalTeamSquadMemberResponse]


class NationalTeamRentalPlayerView(BaseModel):
    player_id: str
    player_name: str
    overall_rating: int
    primary_position: str | None = None
    current_club_name: str | None = None
    current_league_name: str | None = None
    nationality: str | None = None
    base_value_coin: Decimal
    loan_price_coin: Decimal
    tier_label: str


class NationalTeamRentalPlayerCollectionResponse(BaseModel):
    total: int
    items: list[NationalTeamRentalPlayerView] = Field(default_factory=list)


class NationalTeamRentalCreateRequest(BaseModel):
    player_id: str = Field(min_length=1, max_length=36)
    shirt_number: int | None = Field(default=None, ge=1, le=99)


class RentalContractResponse(BaseModel):
    id: str
    player_id: str
    user_id: str
    tournament_id: str
    entry_id: str | None
    start_date: datetime
    end_date: datetime
    loan_price_coin: Decimal
    is_free_player: bool
    free_player_tier: str | None = None
    status: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class NationalTeamRentalSquadMemberResponse(BaseModel):
    id: str
    entry_id: str
    rental_contract_id: str
    player_id: str
    player_name: str
    overall_rating: int
    shirt_number: int | None = None
    source_type: str
    status: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class TournamentThemeUpsertRequest(BaseModel):
    video_asset_url: str | None = Field(default=None, max_length=255)
    audio_theme_url: str | None = Field(default=None, max_length=255)
    visual_style: str = Field(default="gtex_default", min_length=2, max_length=64)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class TournamentThemeResponse(BaseModel):
    id: str
    competition_id: str
    video_asset_url: str | None
    audio_theme_url: str | None
    visual_style: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class StadiumAdUpsertRequest(BaseModel):
    asset_url: str = Field(min_length=3, max_length=255)
    placement: str = Field(min_length=3, max_length=32)
    start_date: datetime
    end_date: datetime
    priority: int = Field(default=100, ge=0, le=10_000)
    rotation_interval_seconds: int = Field(default=30, ge=5, le=600)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class StadiumAdResponse(BaseModel):
    id: str
    competition_id: str | None = None
    asset_url: str
    placement: str
    start_date: datetime
    end_date: datetime
    priority: int
    rotation_interval_seconds: int
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class StoryEventResponse(BaseModel):
    id: str
    competition_id: str
    match_id: str | None = None
    type: str
    entities: dict[str, Any] = Field(default_factory=dict)
    narrative_text: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class NationalTeamTournamentGiftRequest(BaseModel):
    recipient_user_id: str = Field(min_length=1, max_length=36)
    gift_key: str = Field(min_length=1, max_length=120)
    quantity: Decimal = Field(gt=0)
    note: str | None = Field(default=None, max_length=500)


class NationalTeamTournamentGiftResponse(BaseModel):
    transaction_id: str
    recipient_user_id: str
    gift_key: str
    quantity: Decimal
    source_scope: str


class NationalTeamRentalStatusResponse(BaseModel):
    entry: NationalTeamEntryDetailResponse
    competition: NationalTeamCompetitionResponse
    active_theme: TournamentThemeResponse | None = None
    active_ads: list[StadiumAdResponse] = Field(default_factory=list)
    story_events: list[StoryEventResponse] = Field(default_factory=list)


class NationalTeamCompetitionPresentationResponse(BaseModel):
    competition: NationalTeamCompetitionResponse
    active_theme: TournamentThemeResponse | None = None
    active_ads: list[StadiumAdResponse] = Field(default_factory=list)
    story_events: list[StoryEventResponse] = Field(default_factory=list)


NationalTeamEntryDetailResponse.model_rebuild()
