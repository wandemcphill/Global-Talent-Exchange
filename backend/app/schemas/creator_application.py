from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

from pydantic import Field, field_validator

from app.common.schemas.base import CommonSchema

_HANDLE_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789._-")
_SUPPORTED_PLATFORMS = {"youtube", "twitch", "tiktok"}


class CreatorApplicationSubmitRequest(CommonSchema):
    requested_handle: str = Field(min_length=3, max_length=64)
    display_name: str = Field(min_length=2, max_length=120)
    platform: str = Field(min_length=3, max_length=24)
    follower_count: int = Field(ge=0)
    social_links: list[str] = Field(min_length=1, max_length=5)

    @field_validator("requested_handle")
    @classmethod
    def validate_requested_handle(cls, value: str) -> str:
        candidate = value.strip().lower()
        if any(character not in _HANDLE_CHARS for character in candidate):
            raise ValueError("Creator handles may only include lowercase letters, numbers, dots, hyphens, and underscores.")
        return candidate

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, value: str) -> str:
        candidate = value.strip().lower()
        if candidate not in _SUPPORTED_PLATFORMS:
            raise ValueError("Platform must be one of: youtube, twitch, tiktok.")
        return candidate

    @field_validator("social_links")
    @classmethod
    def validate_social_links(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in value:
            candidate = item.strip()
            parsed = urlparse(candidate)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("Each social link must be a valid http or https URL.")
            normalized.append(candidate)
        return normalized


class CreatorApplicationAdminActionRequest(CommonSchema):
    reason: str | None = Field(default=None, max_length=500)
    review_notes: str | None = Field(default=None, max_length=1000)


class CreatorContactVerificationView(CommonSchema):
    user_id: str
    email_verified_at: datetime | None = None
    phone_verified_at: datetime | None = None


class CreatorProvisioningView(CommonSchema):
    creator_profile_id: str
    club_id: str
    stadium_id: str
    creator_squad_id: str
    creator_regen_id: str
    provision_status: str


class CreatorApplicationView(CommonSchema):
    application_id: str
    user_id: str
    requested_handle: str
    display_name: str
    platform: str
    follower_count: int
    social_links: list[str] = Field(default_factory=list)
    email_verified_at: datetime
    phone_verified_at: datetime
    status: str
    review_notes: str | None = None
    decision_reason: str | None = None
    reviewed_by_user_id: str | None = None
    reviewed_at: datetime | None = None
    verification_requested_at: datetime | None = None
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    provisioning: CreatorProvisioningView | None = None


class CreatorAdminDashboardView(CommonSchema):
    pending_count: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    verification_requested_count: int = 0
    applications: list[CreatorApplicationView] = Field(default_factory=list)


__all__ = [
    "CreatorAdminDashboardView",
    "CreatorApplicationAdminActionRequest",
    "CreatorApplicationSubmitRequest",
    "CreatorApplicationView",
    "CreatorContactVerificationView",
    "CreatorProvisioningView",
]
