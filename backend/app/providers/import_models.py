from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class RealPlayerSourceItem:
    provider_player_id: str
    full_name: str
    first_name: str | None = None
    last_name: str | None = None
    short_name: str | None = None
    display_position: str | None = None
    nationality_name: str | None = None
    nationality_code: str | None = None
    date_of_birth: date | None = None
    current_club_id: str | None = None
    current_club_name: str | None = None
    current_competition_id: str | None = None
    current_competition_name: str | None = None
    current_season_id: str | None = None
    provider_last_updated_at: datetime | None = None
    metadata_json: dict[str, Any] = field(default_factory=dict)
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RealPlayerSourcePage:
    provider_name: str
    items: tuple[RealPlayerSourceItem, ...]
    next_cursor: str | None
    exhausted: bool
    source_version: str | None = None
