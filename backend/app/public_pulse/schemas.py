from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LiveWorldPulseView(BaseModel):
    clubs_on_gtex: int = Field(ge=0)
    users_online: int = Field(ge=0)
    players_online: int = Field(ge=0)
    users_online_window_seconds: int = Field(ge=60)
    generated_at: datetime
    labels: dict[str, str] = Field(default_factory=dict)
