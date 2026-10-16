from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class PlayerAdminView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    full_name: str
    source_provider: str
    is_regen: bool
    is_real_player: bool
    date_of_birth: date | None = None
    current_club_id: str | None = None
    current_club_name: str | None = None
    current_competition_id: str | None = None
    overall: int | None = None
    potential: int | None = None
    club_rating: int | None = None
    is_tradable: bool = True
    current_value_credits: float | None = None
    current_value_naira: float | None = None
    price_tier: str | None = None


class PlayerAdminEditRequest(BaseModel):
    """All fields optional — only the ones provided are changed."""

    model_config = ConfigDict(extra="forbid")

    overall: int | None = Field(default=None, ge=1, le=99)
    potential: int | None = Field(default=None, ge=1, le=99)
    club_rating: int | None = Field(default=None, ge=1, le=99)
    # Direct price override (credits). When set, skips the banded recompute for this
    # edit and pins the displayed/traded price to this value.
    market_value_credits: float | None = Field(default=None, ge=0)
    # Move the player to another club (canonical ingestion_clubs.id). Empty string
    # clears the club (free agent).
    current_club_id: str | None = None
    is_tradable: bool | None = None
    # Convenience: retire = mark untradable + free agent.
    retire: bool | None = None
    reason: str | None = Field(default=None, max_length=500)


class PlayerAdminEditResult(BaseModel):
    player: PlayerAdminView
    changed_fields: list[str]
    repriced: bool
