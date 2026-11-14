from __future__ import annotations

from pydantic import BaseModel, Field


class ClubMatchPlanView(BaseModel):
    club_id: str
    formation: str
    starter_player_ids: list[str] = Field(default_factory=list)
    bench_player_ids: list[str] = Field(default_factory=list)
    is_non_binding_preference: bool = True
    authority_model: str = "first_team_manager_authoritative"
    manager_note: str = (
        "Saved as a non-binding owner preference. The First-Team Manager determines the final matchday XI and formation."
    )


class SaveMatchPlanRequest(BaseModel):
    formation: str = Field(description="e.g. 4-3-3, 4-4-2, 4-2-3-1 (outfield lines sum to 10)")
    starter_player_ids: list[str] = Field(default_factory=list)
    bench_player_ids: list[str] = Field(default_factory=list)
