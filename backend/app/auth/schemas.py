from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.models.user import KycStatus, UserRole
from backend.app.users.schemas import UserPublic

PROTECTED_PROFILE_FIELDS = frozenset(
    {
        "created_at",
        "email",
        "id",
        "is_active",
        "kyc_status",
        "last_login_at",
        "full_name",
        "phone_number",
        "age_confirmed_at",
        "password",
        "password_hash",
        "role",
        "updated_at",
        "username",
    }
)


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    phone_number: str | None = Field(default=None, min_length=6, max_length=32)
    is_over_18: bool = Field(default=True)
    region_code: str = Field(min_length=2, max_length=8)
    username: str | None = Field(default=None, min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        candidate = value.strip().lower()
        if "@" not in candidate or candidate.startswith("@") or candidate.endswith("@"):
            raise ValueError("A valid email address is required.")
        if "." not in candidate.split("@", maxsplit=1)[1]:
            raise ValueError("A valid email address is required.")
        return candidate

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip().lower()
        if not candidate:
            return None
        return candidate

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip()
        return candidate or None

    @field_validator("phone_number")
    @classmethod
    def normalize_phone_number(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip()
        return candidate or None

    @field_validator("region_code")
    @classmethod
    def normalize_region_code(cls, value: str) -> str:
        candidate = value.strip().upper()
        if not candidate:
            raise ValueError("Region code is required.")
        return candidate



class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()




class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_new_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_new_password_match(self) -> "ChangePasswordRequest":
        if self.new_password != self.confirm_new_password:
            raise ValueError("New password confirmation does not match.")
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from the current password.")
        return self


class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic
    permissions: list[str] = Field(default_factory=list)
    landing_route: str = "/"


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    username: str
    full_name: str | None
    phone_number: str | None
    age_confirmed_at: datetime | None
    display_name: str | None
    avatar_url: str | None
    favourite_club: str | None
    nationality: str | None
    region_code: str | None = None
    preferred_position: str | None
    role: UserRole
    kyc_status: KycStatus
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class CurrentUserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=2048)
    favourite_club: str | None = Field(default=None, max_length=160)
    nationality: str | None = Field(default=None, max_length=120)
    preferred_position: str | None = Field(default=None, max_length=120)

    @model_validator(mode="before")
    @classmethod
    def reject_protected_fields(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value

        attempted_fields = sorted(PROTECTED_PROFILE_FIELDS.intersection(value))
        if attempted_fields:
            raise ValueError(f"Protected fields cannot be updated: {', '.join(attempted_fields)}.")
        return value

    @field_validator("display_name", "favourite_club", "nationality", "preferred_position")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip()
        return candidate or None

    @field_validator("avatar_url")
    @classmethod
    def normalize_avatar_url(cls, value: str | None) -> str | None:
        if value is None:
            return None

        candidate = value.strip()
        if not candidate:
            return None

        parsed_url = urlparse(candidate)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError("avatar_url must be a valid http or https URL.")
        return candidate
