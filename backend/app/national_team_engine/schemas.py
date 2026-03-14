from __future__ import annotations

from datetime import datetime
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


class NationalTeamUserHistoryResponse(BaseModel):
    managed_entries: list[NationalTeamEntryResponse]
    squad_memberships: list[NationalTeamSquadMemberResponse]
