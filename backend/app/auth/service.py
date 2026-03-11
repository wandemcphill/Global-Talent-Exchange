from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.security import ACCESS_TOKEN_TTL_SECONDS, create_access_token, hash_password, verify_password
from backend.app.models.base import utcnow
from backend.app.models.user import User, UserRole
from backend.app.wallets.service import WalletService

USERNAME_PATTERN = re.compile(r"^[a-z0-9_.-]{3,64}$")


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
        username: str,
        password: str,
        display_name: str | None = None,
        role: UserRole = UserRole.USER,
    ) -> User:
        normalized_email = self._normalize_email(email)
        normalized_username = self._normalize_username(username)
        self._validate_password(password)

        existing_user = session.scalar(
            select(User).where((User.email == normalized_email) | (User.username == normalized_username))
        )
        if existing_user is not None:
            if existing_user.email == normalized_email:
                raise DuplicateUserError("Email address is already registered.")
            raise DuplicateUserError("Username is already taken.")

        user = User(
            email=normalized_email,
            username=normalized_username,
            display_name=display_name or normalized_username,
            password_hash=hash_password(password),
            role=role,
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

    @staticmethod
    def _validate_password(value: str) -> None:
        if len(value) < 8:
            raise AuthError("Passwords must be at least 8 characters long.")
