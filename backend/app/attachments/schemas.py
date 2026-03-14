from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttachmentView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
