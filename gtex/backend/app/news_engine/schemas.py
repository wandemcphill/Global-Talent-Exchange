from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class NewsStoryView(BaseModel):
    id: str
    headline: str
    body: str
    type: str
    priority: int = Field(ge=1, le=10)
    club: str | None = None
    player_id: str | None = None
    player_name: str | None = None
    is_regen: bool = False
    journalist: str
    created_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DailyNewsResponse(BaseModel):
    breaking: list[NewsStoryView] = Field(default_factory=list)
    top_stories: list[NewsStoryView] = Field(default_factory=list)
    rumors: list[NewsStoryView] = Field(default_factory=list)


__all__ = ["DailyNewsResponse", "NewsStoryView"]
