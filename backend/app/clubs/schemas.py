from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClubView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    short_name: str | None
    country_name: str | None
    player_count: int
    updated_at: datetime
