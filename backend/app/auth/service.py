from __future__ import annotations

import re

from sqlalchemy import column, select, table, update
from sqlalchemy.orm import Session

from backend.app.auth.schemas import ChangePasswordRequest, CurrentUserResponse, CurrentUserUpdateRequest
from backend.app.admin_godmode.service import AdminGodModeService
from backend.app.auth.security import ACCESS_TOKEN_TTL_SECONDS, create_access_token, hash_password, verify_password
from backend.app.models.base import generate_uuid, utcnow
from backend.app.models.user import User, UserRole
from backend.app.wallets.service import WalletService

USERNAME_PATTERN = re.compile(r"^[a-z0-9_.-]{3,64}$")
PROFILE_MUTABLE_FIELDS = (
    "display_name",
    "avatar_url",
    "favourite_club",
    "nationality",
    "preferred_position",
)
# `table()`/`column()` keep profile access inside the auth domain without mutating the ORM model owned elsewhere.
USER_PROFILE_TABLE = table(
    "users",
    column("id"),
    *[column(field_name) for field_name in PROFILE_MUTABLE_FIELDS],
)


class AuthError(ValueError):
    pass


class DuplicateUserError(AuthError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class AuthService:
    def __init__(self, wallet_service: WalletService | None = None) -> None:
        self.wallet_service = wallet_service or WalletService()

    def register_user(
        self,
        session: Session,
        *,
        email: str,
        full_name: str | None = None,
        phone_number: str | None = None,
        is_over_18: bool = True,
        username: str | None = None,
        password: str,
        display_name: str | None = None,
        role: UserRole = UserRole.USER,
    ) -> User:
        normalized_email = self._normalize_email(email)
        if not is_over_18:
            raise AuthError("You must be at least 18 years old to sign up.")
        normalized_username = self._normalize_username(username) if username else None
        self._validate_password(password)

        resolved_full_name = (full_name or display_name or normalized_username or normalized_email.split("@", 1)[0]).strip()
        if not resolved_full_name:
            raise AuthError("Full name is required.")
        resolved_phone_number = (phone_number or "0000000000").strip()
        if not resolved_phone_number:
            resolved_phone_number = "0000000000"

        existing_user = session.scalar(select(User).where(User.email == normalized_email))
        if existing_user is not None:
            raise DuplicateUserError("Email address is already registered.")

        if normalized_username is None:
            normalized_username = self._generate_unique_username(session, resolved_full_name, normalized_email)
        else:
            existing_username = session.scalar(select(User).where(User.username == normalized_username))
            if existing_username is not None:
                raise DuplicateUserError("Username is already taken.")

        user = User(
            email=normalized_email,
            username=normalized_username,
            full_name=resolved_full_name,
            phone_number=resolved_phone_number,
            display_name=display_name or resolved_full_name or normalized_username,
            password_hash=hash_password(password),
            role=role,
            age_confirmed_at=utcnow(),
        )
        session.add(user)
        session.flush()
        self.wallet_service.ensure_default_accounts(session, user)
        session.flush()
        return user

    def authenticate_user(self, session: Session, *, email: str, password: str) -> User:
        normalized_email = self._normalize_email(email)
        user = session.scalar(select(User).where(User.email == normalized_email))
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password.")
        if not user.is_active:
            raise InvalidCredentialsError("User account is inactive.")

        user.last_login_at = utcnow()
        session.flush()
        return user

    def issue_access_token(self, user: User) -> tuple[str, int]:
        token = create_access_token(
            user.id,
            claims={
                "email": user.email,
                "role": user.role.value,
            },
        )
        return token, ACCESS_TOKEN_TTL_SECONDS

    def resolve_user_permissions(self, app, user: User) -> list[str]:
        if user.role == UserRole.USER:
            return []
        try:
            state = AdminGodModeService(wallet_service=self.wallet_service)._load_state(app)
            profile = AdminGodModeService(wallet_service=self.wallet_service).resolve_profile(user, state)
            return profile.permissions
        except Exception:
            if user.role == UserRole.SUPER_ADMIN:
                return [
                    "manage_admin_roles",
                    "manage_commissions",
                    "manage_payment_rails",
                    "manage_withdrawals",
                    "manage_treasury_withdrawals",
                    "manage_liquidity_desk",
                    "view_audit_log",
                    "pause_payments",
                    "view_integrity_controls",
                    "manage_manager_catalog",
                    "manage_competitions",
                    "manage_manager_supply",
                ]
            return []

    @staticmethod
    def resolve_landing_route(user: User) -> str:
        if user.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            return "/admin/god-mode"
        return "/"

    def get_current_user_profile(self, session: Session, user: User) -> CurrentUserResponse:
        profile_fields = self._get_profile_fields(session, user.id)
        return CurrentUserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            phone_number=user.phone_number,
            age_confirmed_at=user.age_confirmed_at,
            display_name=profile_fields["display_name"],
            avatar_url=profile_fields["avatar_url"],
            favourite_club=profile_fields["favourite_club"],
            nationality=profile_fields["nationality"],
            preferred_position=profile_fields["preferred_position"],
            role=user.role,
            kyc_status=user.kyc_status,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )

    def update_current_user_profile(
        self,
        session: Session,
        *,
        user: User,
        payload: CurrentUserUpdateRequest,
    ) -> CurrentUserResponse:
        updates = payload.model_dump(exclude_unset=True)
        if updates:
            session.execute(
                update(USER_PROFILE_TABLE)
                .where(USER_PROFILE_TABLE.c.id == user.id)
                .values(**updates)
            )
            session.flush()
            session.refresh(user)

        return self.get_current_user_profile(session, user)

    def change_password(
        self,
        session: Session,
        *,
        user: User,
        payload: ChangePasswordRequest,
    ) -> User:
        self._validate_password(payload.new_password)
        if not verify_password(payload.current_password, user.password_hash):
            raise InvalidCredentialsError("Current password is incorrect.")
        user.password_hash = hash_password(payload.new_password)
        session.flush()
        return user

    def ensure_admin_user(
        self,
        session: Session,
        *,
        email: str,
        password: str,
        username: str = "gtex.admin",
        display_name: str = "GTEX Admin",
        role: UserRole = UserRole.SUPER_ADMIN,
    ) -> User:
        normalized_email = self._normalize_email(email)
        normalized_username = self._normalize_username(username)
        self._validate_password(password)

        existing_user = session.scalar(select(User).where(User.email == normalized_email))
        if existing_user is None:
            return self.register_user(
                session,
                email=normalized_email,
                full_name=display_name,
                phone_number="0000000000",
                is_over_18=True,
                username=normalized_username,
                password=password,
                display_name=display_name,
                role=role,
            )

        if existing_user.role != role:
            existing_user.role = role
            existing_user.password_hash = hash_password(password)
        if not existing_user.is_active:
            existing_user.is_active = True
        if not existing_user.display_name:
            existing_user.display_name = display_name
        if not existing_user.full_name:
            existing_user.full_name = display_name
        session.flush()
        return existing_user

    def _get_profile_fields(self, session: Session, user_id: str) -> dict[str, str | None]:
        profile_row = (
            session.execute(
                select(
                    USER_PROFILE_TABLE.c.display_name,
                    USER_PROFILE_TABLE.c.avatar_url,
                    USER_PROFILE_TABLE.c.favourite_club,
                    USER_PROFILE_TABLE.c.nationality,
                    USER_PROFILE_TABLE.c.preferred_position,
                ).where(USER_PROFILE_TABLE.c.id == user_id)
            )
            .mappings()
            .one()
        )
        return {field_name: profile_row[field_name] for field_name in PROFILE_MUTABLE_FIELDS}

    @staticmethod
    def _normalize_email(value: str) -> str:
        candidate = value.strip().lower()
        if "@" not in candidate or candidate.startswith("@") or candidate.endswith("@"):
            raise AuthError("A valid email address is required.")
        local_part, domain = candidate.split("@", maxsplit=1)
        if not local_part or "." not in domain:
            raise AuthError("A valid email address is required.")
        return candidate

    @staticmethod
    def _normalize_username(value: str) -> str:
        candidate = value.strip().lower()
        if not USERNAME_PATTERN.fullmatch(candidate):
            raise AuthError("Username may only contain letters, numbers, dots, hyphens, and underscores.")
        return candidate

    def _generate_unique_username(self, session: Session, full_name: str, email: str) -> str:
        base = full_name.strip().lower()
        if not base:
            base = email.split("@", maxsplit=1)[0].strip().lower()
        slug = re.sub(r"[^a-z0-9_.-]+", ".", base).strip(".-_")
        if len(slug) < 3:
            slug = f"user-{generate_uuid()[:8]}"
        slug = slug[:56]
        candidate = slug
        suffix = 1
        while session.scalar(select(User).where(User.username == candidate)) is not None:
            candidate = f"{slug}-{suffix}"
            suffix += 1
            if len(candidate) > 64:
                candidate = f"{slug[:56]}-{generate_uuid()[:6]}"
        return candidate

    @staticmethod
    def _validate_password(value: str) -> None:
        if len(value) < 8:
            raise AuthError("Passwords must be at least 8 characters long.")
