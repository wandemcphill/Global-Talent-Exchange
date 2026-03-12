from __future__ import annotations

from typing import Any

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id: str
    user_id: str | None
    topic: str
    template_key: str | None = None
    resource_id: str | None = None
    fixture_id: str | None = None
    competition_id: str | None = None
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
