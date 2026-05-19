from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.access_control.schemas import OrganizationMembershipView
from app.models.access_control import OrganizationType
from app.models.club_profile import ClubType
from app.models.user import KycStatus, PublicAccountType, UserRole
from app.policies.schemas import UserComplianceStatus
from app.schemas.club_identity_core import ClubProfileCore
from app.users.schemas import UserPublic
from app.wallets.schemas import WalletAdaptiveOverviewView

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
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=320)
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    phone_number: str | None = Field(default=None, min_length=6, max_length=32)
    is_over_18: bool = Field(default=True)
    region_code: str | None = Field(default=None, min_length=2, max_length=8)
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

    @field_validator("region_code", mode="before")
    @classmethod
    def normalize_region_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip().upper()
        if not candidate:
            return None
        return candidate


class ComplianceSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    government_id_attachment_id: str = Field(min_length=1, max_length=255)
    selfie_attachment_id: str = Field(min_length=1, max_length=255)
    country_confirmation: str = Field(min_length=2, max_length=120)
    proof_of_address_attachment_id: str | None = Field(default=None, max_length=255)

    @field_validator(
        "government_id_attachment_id",
        "selfie_attachment_id",
        "country_confirmation",
        "proof_of_address_attachment_id",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip()
        return candidate or None


class UserClubSignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=2, max_length=160)
    username: str = Field(min_length=3, max_length=64)
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    country: str = Field(min_length=2, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    club_name: str = Field(min_length=2, max_length=120)
    club_short_tag: str = Field(min_length=2, max_length=40)
    club_country: str = Field(min_length=2, max_length=120)
    club_state: str | None = Field(default=None, max_length=120)
    club_locality: str | None = Field(default=None, max_length=120)
    club_type: ClubType
    crest_asset_ref: str | None = Field(default=None, max_length=255)
    primary_color: str = Field(default="#0F766E", max_length=16)
    secondary_color: str = Field(default="#F8FAFC", max_length=16)
    football_identity: str = Field(default="club_owner", max_length=32)
    position: str | None = Field(default=None, max_length=40)
    dominant_foot: str | None = Field(default=None, max_length=16)
    height_cm: int | None = Field(default=None, ge=120, le=230)
    jersey_number: int | None = Field(default=None, ge=1, le=99)
    preferred_role: str | None = Field(default=None, max_length=80)
    compliance: ComplianceSubmissionRequest

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return RegisterRequest.validate_email(value)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        resolved = RegisterRequest.normalize_username(value)
        if resolved is None:
            raise ValueError("Username is required.")
        return resolved

    @field_validator(
        "full_name",
        "country",
        "state",
        "city",
        "club_name",
        "club_short_tag",
        "club_country",
        "club_state",
        "club_locality",
        "crest_asset_ref",
        "primary_color",
        "secondary_color",
        "football_identity",
        "position",
        "dominant_foot",
        "preferred_role",
    )
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip()
        return candidate or None

    @model_validator(mode="after")
    def validate_player_fields(self) -> "UserClubSignupRequest":
        identity = self.football_identity.strip().lower().replace(" ", "_")
        if identity not in {"club_owner", "player", "both"}:
            raise ValueError("football_identity must be club_owner, player, or both.")
        self.football_identity = identity
        if identity in {"player", "both"} and not self.position:
            raise ValueError("position is required when football_identity includes player.")
        return self


class CreatorSignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    creator_name: str = Field(min_length=2, max_length=120)
    username: str = Field(min_length=3, max_length=64)
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    country: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=80)
    main_club_supported: str | None = Field(default=None, max_length=120)
    primary_language: str = Field(min_length=2, max_length=80)
    avatar_asset_ref: str | None = Field(default=None, max_length=255)
    banner_asset_ref: str | None = Field(default=None, max_length=255)
    monetization: list[str] = Field(default_factory=list, max_length=4)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return RegisterRequest.validate_email(value)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        resolved = RegisterRequest.normalize_username(value)
        if resolved is None:
            raise ValueError("Username is required.")
        return resolved


class TraderSignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=2, max_length=160)
    trading_alias: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    phone_number: str = Field(min_length=6, max_length=32)
    country: str = Field(min_length=2, max_length=120)
    preferred_currency: str = Field(min_length=2, max_length=12)
    trading_experience: str = Field(min_length=2, max_length=32)
    interests: list[str] = Field(default_factory=list, max_length=4)
    wallet_label: str = Field(default="GTEX Trading Wallet", max_length=120)
    totp_secret: str = Field(min_length=16, max_length=128)
    recovery_phrase_hash: str = Field(min_length=16, max_length=255)
    security_pin_hash: str = Field(min_length=16, max_length=255)
    totp_code: str = Field(min_length=6, max_length=12)
    compliance: ComplianceSubmissionRequest

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return RegisterRequest.validate_email(value)

    @field_validator("trading_experience")
    @classmethod
    def validate_experience(cls, value: str) -> str:
        candidate = value.strip().lower()
        if candidate not in {"beginner", "intermediate", "professional"}:
            raise ValueError("trading_experience must be beginner, intermediate, or professional.")
        return candidate

    @model_validator(mode="after")
    def require_trader_proof_of_address(self) -> "TraderSignupRequest":
        if not self.compliance.proof_of_address_attachment_id:
            raise ValueError("proof_of_address_attachment_id is required for coin trader signup.")
        return self


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class RefreshTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=24, max_length=4096)

    @field_validator("refresh_token")
    @classmethod
    def normalize_refresh_token(cls, value: str) -> str:
        candidate = value.strip()
        if not candidate:
            raise ValueError("refresh_token is required.")
        return candidate


class ActionStatusResponse(BaseModel):
    detail: str


class ConfirmEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=8, max_length=256)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip()


class AccountRecoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=320)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class AccountRecoveryResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=8, max_length=256)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_new_password: str = Field(min_length=8, max_length=128)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_new_password_match(self) -> "AccountRecoveryResetRequest":
        if self.new_password != self.confirm_new_password:
            raise ValueError("New password confirmation does not match.")
        return self


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    refresh_token: str
    session_id: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int
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
    account_type: PublicAccountType = PublicAccountType.USER
    kyc_status: KycStatus
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None
    active_organization_id: str | None = None
    active_organization_name: str | None = None
    active_organization_type: OrganizationType | None = None
    memberships: tuple[OrganizationMembershipView, ...] = ()
    permissions: list[str] = Field(default_factory=list)


class SessionBootstrapResponse(BaseModel):
    user: CurrentUserResponse
    club: ClubProfileCore | None = None
    wallet: WalletAdaptiveOverviewView
    compliance: UserComplianceStatus
    permissions: list[str] = Field(default_factory=list)


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
