from __future__ import annotations

from decimal import Decimal

from pydantic import Field, field_validator

from app.common.schemas.base import CommonSchema

_HANDLE_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789._-")


class CreatorProfileCreateRequest(CommonSchema):
    handle: str = Field(min_length=3, max_length=32)
    display_name: str = Field(min_length=2, max_length=120)
    tier: str = Field(default="emerging", min_length=2, max_length=32)
    status: str = Field(default="active", min_length=2, max_length=32)
    default_competition_id: str | None = Field(default=None, min_length=1, max_length=36)
    revenue_share_percent: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("100"))

    @field_validator("handle")
    @classmethod
    def validate_handle(cls, value: str) -> str:
        candidate = value.strip().lower()
        if any(character not in _HANDLE_CHARS for character in candidate):
            raise ValueError("Creator handles may only include lowercase letters, numbers, dots, hyphens, and underscores.")
        return candidate


class CreatorProfileUpdateRequest(CommonSchema):
    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    tier: str | None = Field(default=None, min_length=2, max_length=32)
    status: str | None = Field(default=None, min_length=2, max_length=32)
    default_competition_id: str | None = Field(default=None, min_length=1, max_length=36)
    revenue_share_percent: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("100"))
