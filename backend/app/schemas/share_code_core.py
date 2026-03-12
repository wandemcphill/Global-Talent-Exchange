from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from backend.app.common.enums.share_code_type import ShareCodeType
from backend.app.common.schemas.base import CommonSchema


class ShareCodeCore(CommonSchema):
    code: str = Field(min_length=4, max_length=32)
    code_type: ShareCodeType
    owner_user_id: str | None = Field(default=None, min_length=1, max_length=36)
    owner_creator_id: str | None = Field(default=None, min_length=1, max_length=36)
    linked_competition_id: str | None = Field(default=None, min_length=1, max_length=36)
    vanity_code: str | None = Field(default=None, min_length=4, max_length=32)
    is_active: bool = True
    max_uses: int | None = Field(default=None, ge=1)
    current_uses: int = Field(default=0, ge=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_usage_window(self) -> "ShareCodeCore":
        if self.max_uses is not None and self.current_uses > self.max_uses:
            raise ValueError("current_uses cannot exceed max_uses")
        if self.starts_at is not None and self.ends_at is not None and self.starts_at > self.ends_at:
            raise ValueError("starts_at cannot be after ends_at")
        return self


class ShareCodeGenerationRequest(CommonSchema):
    code_type: ShareCodeType
    owner_user_id: str | None = Field(default=None, min_length=1, max_length=36)
    owner_creator_id: str | None = Field(default=None, min_length=1, max_length=36)
    linked_competition_id: str | None = Field(default=None, min_length=1, max_length=36)
    owner_handle: str | None = Field(default=None, min_length=1, max_length=64)
    vanity_code: str | None = Field(default=None, min_length=4, max_length=32)
    max_uses: int | None = Field(default=None, ge=1)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
