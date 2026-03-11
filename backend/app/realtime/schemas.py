from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RealtimeStatusView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_events: int
    channels: dict[str, int]
    last_event_name: str | None
    last_event_at: datetime | None
