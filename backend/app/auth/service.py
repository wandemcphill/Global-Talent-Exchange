from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import logging
import re
import secrets
from uuid import uuid4

from sqlalchemy import column, select, table, update
from sqlalchemy.orm import Session

from app.access_control.service import AccessControlService, MembershipAccessContext
from app.admin_godmode.service import AdminGodModeService
from app.auth.schemas import ChangePasswordRequest, CurrentUserResponse, CurrentUserUpdateRequest
from app.auth.security import ACCESS_TOKEN_TTL_SECONDS, create_access_token, hash_password, verify_password
from app.models.auth_email_token import AuthEmailToken, AuthEmailTokenPurpose
from app.models.base import generate_uuid, utcnow
from app.models.user import User, UserRole
from app.policies.service import PolicyService
from app.services.email import EmailSendResult, EmailService
from app.users.schemas import UserPublic
from app.wallets.service import WalletService

logger = logging.getLogger(__name__)

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
    def __init__(
        self,
        wallet_service: WalletService | None = None,
        email_service: EmailService | None = None,
    ) -> None:
        self.wallet_service = wallet_service or WalletService()
        self.email_service = email_service or EmailService.disabled()

    def register_user(
        self,
        session: Session,
        *,
        email: str,
        full_name: str | None = None,
        phone_number: str | None = None,
        is_over_18: bool = True,
        region_code: str | None = None,
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
        PolicyService(session).ensure_user_region_profile(user=user, region_code=region_code)
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

    def issue_access_token(self, user: User, *, session: Session | None = None) -> tuple[str, int]:
        token, expires_in, _session_id = self.issue_access_token_with_session(user, session=session)
        return token, expires_in

    def issue_access_token_with_session(
        self,
        user: User,
        *,
        session: Session | None = None,
        session_id: str | None = None,
    ) -> tuple[str, int, str]:
        effective_role = user.role
        active_org_id: str | None = None
        if session is not None:
            access_context = AccessControlService(session).bind_user_access_context(user)
            effective_role = access_context.effective_role
            active_org_id = access_context.active_organization_id
        resolved_session_id = (session_id or str(uuid4())).strip()
        token = create_access_token(
            user.id,
            claims={
                "email": user.email,
                "role": effective_role.value,
                "org_id": active_org_id,
                "sid": resolved_session_id,
            },
        )
        return token, ACCESS_TOKEN_TTL_SECONDS, resolved_session_id

    def resolve_user_permissions(self, app, user: User, *, session: Session | None = None) -> list[str]:
        if session is not None:
            access_context = AccessControlService(session).bind_user_access_context(user)
            membership_permissions = list(access_context.permissions)
        else:
            membership_permissions = []
        if user.role == UserRole.USER and not membership_permissions:
            return []
        try:
            state = AdminGodModeService(wallet_service=self.wallet_service)._load_state(app)
            profile = AdminGodModeService(wallet_service=self.wallet_service).resolve_profile(user, state)
            return list(self._dedupe_permissions(membership_permissions, profile.permissions))
        except Exception:
            if user.role == UserRole.SUPER_ADMIN:
                return list(
                    self._dedupe_permissions(
                        membership_permissions,
                        [
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
                        ],
                    )
                )
            return membership_permissions

    @staticmethod
    def resolve_landing_route(user: User, *, session: Session | None = None) -> str:
        effective_role = user.role
        if session is not None:
            effective_role = AccessControlService(session).bind_user_access_context(user).effective_role
        if effective_role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            return "/admin/god-mode"
        return "/"

    def build_user_public(self, session: Session, user: User) -> UserPublic:
        access_context = AccessControlService(session).bind_user_access_context(user)
        return UserPublic(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            phone_number=user.phone_number,
            display_name=user.display_name,
            role=access_context.effective_role,
            kyc_status=user.kyc_status,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            active_organization_id=access_context.active_organization_id,
            active_organization_name=access_context.active_organization_name,
            active_organization_type=access_context.active_organization_type,
            memberships=tuple(self._membership_views(access_context.memberships)),
        )

    def get_current_user_profile(self, session: Session, user: User, *, app=None) -> CurrentUserResponse:
        profile_fields = self._get_profile_fields(session, user.id)
        region_code = PolicyService(session).resolve_country_code_for_user(user=user)
        access_context = AccessControlService(session).bind_user_access_context(user)
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
            region_code=region_code,
            preferred_position=profile_fields["preferred_position"],
            role=access_context.effective_role,
            kyc_status=user.kyc_status,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            active_organization_id=access_context.active_organization_id,
            active_organization_name=access_context.active_organization_name,
            active_organization_type=access_context.active_organization_type,
            memberships=tuple(self._membership_views(access_context.memberships)),
            permissions=self.resolve_user_permissions(app, user, session=session),
        )

    @staticmethod
    def _dedupe_permissions(*permission_sets: list[str] | tuple[str, ...]) -> tuple[str, ...]:
        seen: list[str] = []
        for permission_set in permission_sets:
            for permission in permission_set:
                if permission not in seen:
                    seen.append(permission)
        return tuple(seen)

    @staticmethod
    def _membership_views(memberships: tuple[MembershipAccessContext, ...]):
        from app.access_control.schemas import OrganizationMembershipView

        for membership in memberships:
            yield OrganizationMembershipView(
                id=membership.membership_id,
                organization_id=membership.organization_id,
                organization_name=membership.organization_name,
                organization_type=membership.organization_type,
                role=membership.role,
                is_primary=membership.is_primary,
                permissions=list(membership.permissions),
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

    def prepare_signup_confirmation(self, session: Session, *, user: User) -> str:
        return self._issue_email_token(
            session,
            user=user,
            purpose=AuthEmailTokenPurpose.SIGNUP_CONFIRMATION,
            ttl_minutes=self.email_service.signup_confirmation_ttl_minutes,
        )

    def send_signup_confirmation_email(self, *, user: User, confirmation_code: str) -> EmailSendResult:
        return self._send_email_result(
            self.email_service.send_signup_confirmation_email(
                user.email,
                confirmation_code,
                recipient_name=user.display_name or user.full_name or user.username,
                confirmation_link=self.email_service.build_signup_confirmation_link(confirmation_code),
            ),
            flow="signup_confirmation",
            recipient=user.email,
        )

    def confirm_email_address(self, session: Session, *, code: str) -> User:
        token = self._consume_email_token(
            session,
            purpose=AuthEmailTokenPurpose.SIGNUP_CONFIRMATION,
            code=code,
            error_message="Confirmation code is invalid or has expired.",
        )
        user = session.get(User, token.user_id)
        if user is None:
            raise AuthError("The email confirmation could not be completed.")
        now = utcnow()
        user.email_verified_at = user.email_verified_at or now
        self._invalidate_active_email_tokens(session, user=user, purpose=AuthEmailTokenPurpose.SIGNUP_CONFIRMATION, now=now)
        token.used_at = now
        session.flush()
        return user

    def prepare_account_recovery(self, session: Session, *, email: str) -> tuple[User | None, str | None]:
        normalized_email = self._normalize_email(email)
        user = session.scalar(select(User).where(User.email == normalized_email))
        if user is None or not user.is_active:
            return None, None
        recovery_code = self._issue_email_token(
            session,
            user=user,
            purpose=AuthEmailTokenPurpose.ACCOUNT_RECOVERY,
            ttl_minutes=self.email_service.account_recovery_ttl_minutes,
        )
        return user, recovery_code

    def send_account_recovery_email(self, *, user: User, recovery_code: str) -> EmailSendResult:
        return self._send_email_result(
            self.email_service.send_account_recovery_email(
                user.email,
                recovery_code,
                recipient_name=user.display_name or user.full_name or user.username,
                recovery_link=self.email_service.build_account_recovery_link(recovery_code),
            ),
            flow="account_recovery",
            recipient=user.email,
        )

    def reset_password_with_recovery(
        self,
        session: Session,
        *,
        code: str,
        new_password: str,
    ) -> User:
        self._validate_password(new_password)
        token = self._consume_email_token(
            session,
            purpose=AuthEmailTokenPurpose.ACCOUNT_RECOVERY,
            code=code,
            error_message="Recovery code is invalid or has expired.",
        )
        user = session.get(User, token.user_id)
        if user is None or not user.is_active:
            raise AuthError("The account recovery could not be completed.")
        now = utcnow()
        user.password_hash = hash_password(new_password)
        self._invalidate_active_email_tokens(session, user=user, purpose=AuthEmailTokenPurpose.ACCOUNT_RECOVERY, now=now)
        token.used_at = now
        session.flush()
        return user

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

    def _issue_email_token(
        self,
        session: Session,
        *,
        user: User,
        purpose: AuthEmailTokenPurpose,
        ttl_minutes: int,
    ) -> str:
        now = utcnow()
        self._invalidate_active_email_tokens(session, user=user, purpose=purpose, now=now)
        raw_code = secrets.token_urlsafe(24)
        token = AuthEmailToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=self._hash_email_token(raw_code),
            expires_at=now + timedelta(minutes=max(ttl_minutes, 1)),
            metadata_json={},
        )
        session.add(token)
        session.flush()
        return raw_code

    def _consume_email_token(
        self,
        session: Session,
        *,
        purpose: AuthEmailTokenPurpose,
        code: str,
        error_message: str,
    ) -> AuthEmailToken:
        token = session.scalar(
            select(AuthEmailToken).where(
                AuthEmailToken.purpose == purpose,
                AuthEmailToken.token_hash == self._hash_email_token(code),
            )
        )
        if token is None:
            raise AuthError(error_message)
        if token.used_at is not None:
            raise AuthError(error_message)
        if self._as_utc_datetime(token.expires_at) <= utcnow():
            raise AuthError(error_message)
        return token

    def _invalidate_active_email_tokens(
        self,
        session: Session,
        *,
        user: User,
        purpose: AuthEmailTokenPurpose,
        now,
    ) -> None:
        session.execute(
            update(AuthEmailToken)
            .where(
                AuthEmailToken.user_id == user.id,
                AuthEmailToken.purpose == purpose,
                AuthEmailToken.used_at.is_(None),
            )
            .values(used_at=now)
        )

    @staticmethod
    def _hash_email_token(code: str) -> str:
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    @staticmethod
    def _as_utc_datetime(value: datetime) -> datetime:
        # SQLite returns naive datetimes even when timezone=True is declared.
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _send_email_result(
        self,
        result: EmailSendResult,
        *,
        flow: str,
        recipient: str,
    ) -> EmailSendResult:
        if not result.success and result.error != "email_disabled":
            logger.warning(
                "auth.email.delivery_failed flow=%s provider=%s recipient=%s error=%s",
                flow,
                result.provider,
                recipient,
                result.error,
            )
        return result
