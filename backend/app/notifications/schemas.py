from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id: str
    user_id: str | None
    topic: str
    message: str
    created_at: datetime
