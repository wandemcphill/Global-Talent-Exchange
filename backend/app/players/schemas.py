from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.regen_universe import RegenPlayerPrestigeSummaryView


class RealPlayerSummaryIdentityView(BaseModel):
    model_config = ConfigDict(extra="ignore")

    is_real_player: bool = True
    is_verified_real_player: bool | None = None
    real_player_tier: str | None = None
    canonical_display_name: str | None = None
    identity_confidence_score: float | None = None
    source_name: str | None = None
    source_player_key: str | None = None
    source_last_refreshed_at: datetime | None = None
    real_world_club_name: str | None = None
    real_world_league_name: str | None = None
    current_market_reference_value: float | None = None
    market_reference_currency: str | None = None
    normalization_profile_version: str | None = None
    pricing_snapshot_id: str | None = None
    valuation_lineage_id: str | None = None


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
    identity_rail: Literal["player_universe", "real_player_universe", "regen_universe"] = "player_universe"
    is_real_player: bool = False
    real_player_universe: RealPlayerSummaryIdentityView | None = None
    regen_universe: RegenPlayerPrestigeSummaryView | None = None
    updated_at: datetime
