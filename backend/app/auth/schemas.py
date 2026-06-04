from __future__ import annotations

from datetime import date, datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.access_control.schemas import OrganizationMembershipView
from app.models.access_control import OrganizationType
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

GENERIC_RECOVERY_QUESTION_FRAGMENTS = frozenset(
    {
        "favorite color",
        "favourite colour",
        "favorite food",
        "favourite food",
        "mother's maiden",
        "mothers maiden",
        "maiden name",
        "pet's name",
        "pet name",
        "first car",
        "birth city",
        "city were you born",
        "name of your school",
    }
)


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip()
    return candidate or None


def _validate_recovery_question_text(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValueError("Recovery question is required.")
    normalized = " ".join(candidate.casefold().replace("?", "").split())
    if any(fragment in normalized for fragment in GENERIC_RECOVERY_QUESTION_FRAGMENTS):
        raise ValueError("Use a custom football or personal recovery question, not a generic predefined prompt.")
    return candidate


def _validate_four_digit_pin(value: str) -> str:
    candidate = value.strip()
    if len(candidate) != 4 or not candidate.isdigit():
        raise ValueError("Security PIN must be exactly 4 digits.")
    return candidate


def _validate_exactly_two_recovery_questions(questions: list["RecoveryQuestionInput"]) -> None:
    if len(questions) != 2:
        raise ValueError("Exactly 2 custom recovery questions are required.")
    normalized_questions = {_validate_recovery_question_text(question.question).casefold() for question in questions}
    if len(normalized_questions) != 2:
        raise ValueError("Recovery questions must be distinct.")


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


class RecoveryQuestionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=8, max_length=255)
    answer: str = Field(min_length=2, max_length=255)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        return _validate_recovery_question_text(value)

    @field_validator("answer")
    @classmethod
    def normalize_answer(cls, value: str) -> str:
        candidate = value.strip()
        if not candidate:
            raise ValueError("Recovery answer is required.")
        return candidate


class RecoveryAnswerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1, max_length=64)
    answer: str = Field(min_length=1, max_length=255)

    @field_validator("question_id", "answer")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        candidate = value.strip()
        if not candidate:
            raise ValueError("Recovery answer is required.")
        return candidate


class DeviceTrustRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str | None = Field(default=None, min_length=4, max_length=120)
    install_id: str | None = Field(default=None, min_length=4, max_length=120)
    os: str | None = Field(default=None, max_length=80)
    device_model: str | None = Field(default=None, max_length=160)
    ip_region: str | None = Field(default=None, max_length=120)
    trusted_device_token: str | None = Field(default=None, min_length=16, max_length=256)
    biometric_enabled: bool = False

    @field_validator("device_id", "install_id", "os", "device_model", "ip_region", "trusted_device_token")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)


class PlayerFrictionlessSignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    phone_number: str | None = Field(default=None, min_length=6, max_length=32)
    country: str = Field(min_length=2, max_length=120)
    preferred_position: str = Field(min_length=2, max_length=120)
    date_of_birth: date
    pin: str = Field(min_length=4, max_length=4)
    recovery_questions: list[RecoveryQuestionInput] = Field(min_length=2, max_length=2)
    device: DeviceTrustRequest | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return RegisterRequest.validate_email(value)

    @field_validator("full_name", "phone_number", "country", "preferred_position")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, value: str) -> str:
        return _validate_four_digit_pin(value)

    @model_validator(mode="after")
    def validate_recovery_questions(self) -> "PlayerFrictionlessSignupRequest":
        _validate_exactly_two_recovery_questions(self.recovery_questions)
        return self


class OrganizationFrictionlessSignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_name: str = Field(min_length=2, max_length=160)
    contact_name: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    phone_number: str | None = Field(default=None, min_length=6, max_length=32)
    organization_type: str = Field(min_length=2, max_length=40)
    country: str = Field(min_length=2, max_length=120)
    pin: str = Field(min_length=4, max_length=4)
    recovery_questions: list[RecoveryQuestionInput] = Field(min_length=2, max_length=2)
    device: DeviceTrustRequest | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return RegisterRequest.validate_email(value)

    @field_validator("organization_name", "contact_name", "phone_number", "country")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    @field_validator("organization_type")
    @classmethod
    def normalize_organization_type(cls, value: str) -> str:
        candidate = value.strip().lower().replace(" ", "_")
        allowed = {"club", "academy", "scout", "agent", "agency", "coach", "analyst", "recruiter"}
        if candidate not in allowed:
            raise ValueError("organization_type must be club, academy, scout, agent, agency, coach, analyst, or recruiter.")
        return candidate

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, value: str) -> str:
        return _validate_four_digit_pin(value)

    @model_validator(mode="after")
    def validate_recovery_questions(self) -> "OrganizationFrictionlessSignupRequest":
        _validate_exactly_two_recovery_questions(self.recovery_questions)
        return self


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    device: DeviceTrustRequest | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class RefreshTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=24, max_length=4096)
    device: DeviceTrustRequest | None = None

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


class RecoveryChallengeQuestion(BaseModel):
    id: str
    question: str


class AccountRecoveryChallengeResponse(BaseModel):
    email: str
    questions: list[RecoveryChallengeQuestion] = Field(default_factory=list)


class AccountRecoveryQuestionResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=320)
    answers: list[RecoveryAnswerInput] = Field(min_length=2, max_length=2)
    pin: str = Field(min_length=4, max_length=4)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_new_password: str = Field(min_length=8, max_length=128)
    device: DeviceTrustRequest | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, value: str) -> str:
        return _validate_four_digit_pin(value)

    @model_validator(mode="after")
    def validate_reset_payload(self) -> "AccountRecoveryQuestionResetRequest":
        if self.new_password != self.confirm_new_password:
            raise ValueError("New password confirmation does not match.")
        if len({answer.question_id for answer in self.answers}) != 2:
            raise ValueError("Recovery answers must reference two distinct questions.")
        return self


class PinVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pin: str = Field(min_length=4, max_length=4)
    action_type: str = Field(min_length=2, max_length=80)

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, value: str) -> str:
        return _validate_four_digit_pin(value)

    @field_validator("action_type")
    @classmethod
    def normalize_action_type(cls, value: str) -> str:
        candidate = value.strip().lower().replace(" ", "_")
        if not candidate:
            raise ValueError("action_type is required.")
        return candidate


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
    trusted_device_token: str | None = None
    trusted_device_id: str | None = None
    device_trusted: bool = False
    biometric_enabled: bool = False


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
