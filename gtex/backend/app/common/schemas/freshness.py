from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class FreshnessStatus(str, Enum):
    LIVE = "LIVE"
    RECENT = "RECENT"
    PENDING_RECALCULATION = "PENDING_RECALCULATION"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class FreshnessInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    status: FreshnessStatus = Field(default=FreshnessStatus.UNKNOWN)
    as_of: datetime | None = Field(default=None)
    label: str = Field(default="Unknown")
    pending_reason: str | None = Field(default=None)
    stale_reason: str | None = Field(default=None)
