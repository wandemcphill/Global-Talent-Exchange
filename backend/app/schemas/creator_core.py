from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import Field, model_validator

from app.common.enums.creator_profile_status import CreatorProfileStatus
from app.common.schemas.base import CommonSchema

_ONE_HUNDRED = Decimal("100")


class CreatorProfileCore(CommonSchema):
    creator_profile_id: str | None = Field(default=None, min_length=1, max_length=36)
    user_id: str = Field(min_length=1, max_length=36)
    handle: str = Field(min_length=3, max_length=64)
    display_name: str = Field(min_length=1, max_length=120)
    tier: str = Field(default="community", min_length=1, max_length=32)
    status: CreatorProfileStatus = CreatorProfileStatus.ACTIVE
    default_share_code: str | None = Field(default=None, min_length=4, max_length=32)
    default_competition_id: str | None = Field(default=None, min_length=1, max_length=36)
    revenue_share_percent: Decimal | None = Field(default=None, ge=0, le=_ONE_HUNDRED)
    payout_config_json: dict[str, Any] | None = None


class CreatorCampaignCore(CommonSchema):
    creator_profile_id: str = Field(min_length=1, max_length=36)
    name: str = Field(min_length=1, max_length=120)
    share_code_id: str | None = Field(default=None, min_length=1, max_length=36)
    linked_competition_id: str | None = Field(default=None, min_length=1, max_length=36)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_dates(self) -> "CreatorCampaignCore":
        if self.starts_at is not None and self.ends_at is not None and self.starts_at > self.ends_at:
            raise ValueError("starts_at cannot be after ends_at")
        return self
