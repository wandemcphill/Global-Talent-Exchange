from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompetitionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    code: str | None
    country_name: str | None
    season_count: int
    club_count: int
    updated_at: datetime
