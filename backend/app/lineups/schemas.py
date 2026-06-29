from __future__ import annotations

from pydantic import BaseModel, Field


class ClubMatchPlanView(BaseModel):
    club_id: str
    formation: str
    starter_player_ids: list[str] = Field(default_factory=list)
    bench_player_ids: list[str] = Field(default_factory=list)


class SaveMatchPlanRequest(BaseModel):
    formation: str = Field(description="e.g. 4-3-3, 4-4-2, 4-2-3-1 (outfield lines sum to 10)")
    starter_player_ids: list[str] = Field(default_factory=list)
    bench_player_ids: list[str] = Field(default_factory=list)
