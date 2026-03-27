from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.access_control.schemas import OrganizationMembershipView
from app.models.access_control import OrganizationType
from app.models.user import KycStatus, UserRole


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    username: str
    full_name: str | None
    phone_number: str | None
    display_name: str | None
    role: UserRole
    kyc_status: KycStatus
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None
    active_organization_id: str | None = None
    active_organization_name: str | None = None
    active_organization_type: OrganizationType | None = None
    memberships: tuple[OrganizationMembershipView, ...] = ()
