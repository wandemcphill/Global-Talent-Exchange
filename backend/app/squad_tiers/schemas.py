from __future__ import annotations

from pydantic import BaseModel, Field


class SquadTierMemberView(BaseModel):
    player_id: str
    player_name: str
    position: str | None = None
    secondary_positions: list[str] = Field(default_factory=list)
    age: int | None = None
    tier: str
    source: str
    promotion_readiness: str = "settled"


class SquadTiersView(BaseModel):
    club_id: str
    first_team: list[SquadTierMemberView] = Field(default_factory=list)
    u21: list[SquadTierMemberView] = Field(default_factory=list)
    reserve: list[SquadTierMemberView] = Field(default_factory=list)
    total: int = 0


class AcademyIntakeView(BaseModel):
    club_id: str
    youth: list[SquadTierMemberView] = Field(default_factory=list)
    ready_to_sign_up: list[SquadTierMemberView] = Field(default_factory=list)


class AssignTierRequest(BaseModel):
    tier: str = Field(description="first_team | u21 | reserve")
