from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.app.models.user import KycStatus, UserRole


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    username: str
    display_name: str | None
    role: UserRole
    kyc_status: KycStatus
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None
