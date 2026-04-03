from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class BackgroundTaskView(BaseModel):
    job_id: str
    name: str
    status: str
    queued_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    result: dict[str, Any] | None = None


__all__ = ["BackgroundTaskView"]
