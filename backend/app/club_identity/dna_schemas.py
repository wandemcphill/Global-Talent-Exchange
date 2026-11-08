from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ClubDNAPolicyView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    club_id: str
    primary_philosophy: str
    secondary_philosophies: list[str] = Field(default_factory=list)
    nationality_mode: str
    target_nationalities: list[str] = Field(default_factory=list)
    allow_dual_nationality: bool = True
    age_mode: str
    preferred_max_age: int | None = None
    allow_age_exceptions: bool = True
    transfer_strategy: str
    financial_philosophy: str
    club_vision_narrative: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClubDNAPolicyPatch(BaseModel):
    model_config = ConfigDict(extra="ignore")

    primary_philosophy: str | None = None
    secondary_philosophies: list[str] | None = None
    nationality_mode: str | None = None
    target_nationalities: list[str] | None = None
    allow_dual_nationality: bool | None = None
    age_mode: str | None = None
    preferred_max_age: int | None = None
    allow_age_exceptions: bool | None = None
    transfer_strategy: str | None = None
    financial_philosophy: str | None = None
    club_vision_narrative: str | None = None
    metadata: dict[str, Any] | None = None


class ClubGovernanceExceptionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    club_id: str
    policy_type: str
    player_id: str
    player_name: str
    player_nationality: str | None = None
    player_age: int | None = None
    reason: str
    approved_by_user_id: str
    status: str
    approved_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClubGovernanceExceptionCreateRequest(BaseModel):
    player_id: str
    player_name: str
    policy_type: str = "age"
    player_nationality: str | None = None
    player_age: int | None = None
    reason: str = Field(min_length=5, max_length=1000)
