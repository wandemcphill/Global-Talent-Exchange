from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.common.schemas.base import CommonSchema
from app.predictions.models import PredictionOutcome


class PredictionCreateRequest(CommonSchema):
    match_id: str = Field(min_length=1, max_length=36)
    predicted_outcome: PredictionOutcome
    confidence_level: float = Field(ge=0.0, le=1.0)


class PredictionView(CommonSchema):
    id: str
    user_id: str
    match_id: str
    predicted_outcome: PredictionOutcome
    confidence_level: float
    reward_earned: float
    difficulty_multiplier: float
    actual_outcome: PredictionOutcome | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PredictionLeaderboardEntryView(CommonSchema):
    rank: int
    user_id: str
    username: str
    display_name: str | None = None
    total_correct_predictions: int
    total_rewards_earned: float


class PredictionLeaderboardView(CommonSchema):
    entries: list[PredictionLeaderboardEntryView]

