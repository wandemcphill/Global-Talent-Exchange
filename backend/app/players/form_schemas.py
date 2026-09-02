from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlayerPerformanceView(BaseModel):
    """One persisted competition performance."""

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    match_id: str
    competition_id: str
    club_id: str | None = None
    occurred_at: datetime
    rating: float
    started: bool
    minutes_played: int
    goals: int
    assists: int
    saves: int
    key_passes: int
    tackles_won: int
    interceptions: int
    yellow_cards: int
    red_card: bool
    eligible_for_valuation: bool
    ineligibility_reason: str | None = None


class MatchdayValuationSignalView(BaseModel):
    """The bounded valuation influence this player's form currently carries.

    ``applied`` is the field the UI must respect: when it is false, form exists but
    is explicitly not moving this player's value, and the interface must not imply
    otherwise.
    """

    model_config = ConfigDict(extra="ignore")

    applied: bool
    adjustment_pct: float
    reason_code: str
    confidence: float
    capped: bool
    matches_counted: int
    competitions_counted: int
    minimum_matches_required: int
    effective_max_adjustment_pct: float


class PlayerFormView(BaseModel):
    """A footballer's recent GTEX competition form and its valuation consequence."""

    model_config = ConfigDict(extra="ignore")

    player_id: str
    has_sample: bool = Field(
        description="False when this player has no eligible GTEX competition football yet."
    )
    matches_counted: int
    competitions_counted: int
    average_rating: float | None = None
    trend: str
    trend_delta: float
    total_minutes: int
    total_goals: int
    total_assists: int
    excluded_by_competition_cap: int = Field(
        default=0,
        description=(
            "Performances dropped from the window because a single competition may "
            "not dominate it. Present so the anti-farming rule is visible, not hidden."
        ),
    )
    signal: MatchdayValuationSignalView | None = None
    performances: list[PlayerPerformanceView] = Field(default_factory=list)


__all__ = [
    "MatchdayValuationSignalView",
    "PlayerFormView",
    "PlayerPerformanceView",
]
