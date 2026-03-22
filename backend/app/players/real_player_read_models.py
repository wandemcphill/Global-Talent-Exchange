from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class RealPlayerUniverseListItem:
    player_id: str
    player_name: str
    identity_rail: str
    canonical_display_name: str | None
    real_player_tier: str | None
    nationality: str | None
    nationality_code: str | None
    position: str | None
    secondary_positions: tuple[str, ...]
    age: int | None
    current_club_name: str | None
    current_league_name: str | None
    competition_level: str | None
    current_value_credits: float | None
    previous_value_credits: float | None
    movement_pct: float | None
    market_interest_score: int | None
    average_rating: float | None
    current_market_reference_value: float | None
    market_reference_currency: str | None
    source_name: str
    source_last_refreshed_at: datetime | None
    is_verified_real_player: bool
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class RealPlayerUniverseListResult:
    items: tuple[RealPlayerUniverseListItem, ...]
    limit: int
    offset: int
    total: int


@dataclass(frozen=True, slots=True)
class RealPlayerUniverseDetail:
    player_id: str
    player_name: str
    identity_rail: str
    canonical_display_name: str | None
    first_name: str | None
    last_name: str | None
    short_name: str | None
    nationality: str | None
    nationality_code: str | None
    position: str | None
    normalized_position: str | None
    primary_position: str | None
    secondary_positions: tuple[str, ...]
    age: int | None
    date_of_birth: date | None
    dominant_foot: str | None
    height_cm: int | None
    weight_kg: int | None
    current_club_name: str | None
    current_league_name: str | None
    competition_level: str | None
    current_value_credits: float | None
    previous_value_credits: float | None
    movement_pct: float | None
    market_interest_score: int | None
    average_rating: float | None
    current_market_reference_value: float | None
    market_reference_currency: str | None
    appearances: int | None
    minutes_played: int | None
    goals: int | None
    assists: int | None
    clean_sheets: int | None
    injury_status: str | None
    real_player_tier: str | None
    identity_confidence_score: float | None
    source_name: str
    source_player_key: str
    source_last_refreshed_at: datetime | None
    is_verified_real_player: bool
    verification_state: str
    known_aliases: tuple[str, ...]
    normalized_signals: dict[str, Any]
    ingestion_batch_id: str | None
    ingestion_source_version: str | None
    pricing_snapshot_id: str | None
    normalization_profile_version: str | None
    metadata_json: dict[str, Any]
    summary_json: dict[str, Any]
    updated_at: datetime
