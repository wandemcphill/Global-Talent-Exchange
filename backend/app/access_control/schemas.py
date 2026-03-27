from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.access_control import OrganizationRole, OrganizationType


class OrganizationSummaryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    organization_type: OrganizationType
    club_profile_id: str | None = None


class OrganizationMembershipView(BaseModel):
    id: str
    organization_id: str
    organization_name: str
    organization_type: OrganizationType
    role: OrganizationRole
    is_primary: bool
    permissions: list[str] = Field(default_factory=list)


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    organization_type: OrganizationType

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        candidate = value.strip()
        if not candidate:
            raise ValueError("Organization name is required.")
        return candidate


class OrganizationCreateResponse(BaseModel):
    organization: OrganizationSummaryView
    membership: OrganizationMembershipView


class OrganizationInviteRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    role: OrganizationRole

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        candidate = value.strip().lower()
        if "@" not in candidate or candidate.startswith("@") or candidate.endswith("@"):
            raise ValueError("A valid email address is required.")
        return candidate


class OrganizationInviteAcceptRequest(BaseModel):
    invite_code: str = Field(min_length=8, max_length=96)

    @field_validator("invite_code")
    @classmethod
    def normalize_invite_code(cls, value: str) -> str:
        return value.strip()


class OrganizationInviteView(BaseModel):
    id: str
    organization_id: str
    organization_name: str
    organization_type: OrganizationType
    email: str
    role: OrganizationRole
    invite_code: str
    expires_at: datetime
    accepted_at: datetime | None = None


class AccessAuditLogView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_user_id: str | None = None
    organization_id: str | None = None
    target_user_id: str | None = None
    player_id: str | None = None
    action: str
    metadata_json: dict[str, object] = Field(default_factory=dict)
    created_at: datetime
