from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PlayerSummaryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    player_name: str
    current_club_id: str | None
    current_club_name: str | None
    current_competition_id: str | None
    current_competition_name: str | None
    last_snapshot_id: str | None
    last_snapshot_at: datetime
    current_value_credits: float
    previous_value_credits: float
    movement_pct: float
    average_rating: float | None
    market_interest_score: int
    summary_json: dict
    updated_at: datetime
