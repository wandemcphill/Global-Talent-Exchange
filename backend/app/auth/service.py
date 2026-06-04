from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import logging
from time import perf_counter
import re
import secrets
from uuid import uuid4

from sqlalchemy import column, delete, func, select, table, update
from sqlalchemy.orm import Session

from app.access_control.service import AccessControlService, MembershipAccessContext
from app.admin_godmode.service import AdminGodModeService, SUPER_ADMIN_EXTRA_PERMISSIONS
from app.auth.schemas import (
    AccountRecoveryQuestionResetRequest,
    ChangePasswordRequest,
    CurrentUserResponse,
    CurrentUserUpdateRequest,
    DeviceTrustRequest,
    OrganizationFrictionlessSignupRequest,
    PlayerFrictionlessSignupRequest,
    RecoveryQuestionInput,
)
from app.auth.security import (
    ACCESS_TOKEN_TTL_SECONDS,
    REFRESH_TOKEN_TTL_SECONDS,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    hash_sensitive_secret,
    verify_password,
    verify_sensitive_secret,
)
from app.models.access_control import Organization, OrganizationMembership, OrganizationRole, OrganizationType
from app.models.auth_email_token import AuthEmailToken, AuthEmailTokenPurpose
from app.models.auth_session import AuthSession
from app.models.auth_trust import LoginAttempt, RecoveryQuestion, SecurityEvent, TrustedDevice
from app.models.base import generate_uuid, utcnow
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.user import PublicAccountType, User, UserRole
from app.policies.service import PolicyService
from app.services.club_dynasty_service import ClubDynastyService
from app.services.club_reputation_service import ClubReputationService
from app.services.club_trophy_service import ClubTrophyService
from app.services.email import EmailSendResult, EmailService
from app.users.schemas import UserPublic
from app.wallets.funding_service import WalletFundingService
from app.wallets.service import WalletService

logger = logging.getLogger(__name__)
AuthTimingRecorder = Callable[[str, float], None]

USERNAME_PATTERN = re.compile(r"^[a-z0-9_.-]{3,64}$")
PROFILE_ADMIN_ROUTE = "/profile/admin"
PROFILE_GOD_MODE_ROUTE = "/profile/admin/god-mode"
GOD_MODE_LANDING_PERMISSIONS = frozenset({"view_audit_log", "review_audit_log"})
PROFILE_MUTABLE_FIELDS = (
    "display_name",
    "avatar_url",
    "favourite_club",
    "nationality",
    "preferred_position",
)
SECURITY_FAILURE_LIMIT = 5
SECURITY_FAILURE_WINDOW = timedelta(minutes=15)
SUSPICIOUS_TRAVEL_WINDOW = timedelta(minutes=15)
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


class InvalidRefreshTokenError(AuthError):
    pass


class InvalidSessionError(AuthError):
    pass


class SecurityCooldownError(AuthError):
    pass


@dataclass(frozen=True, slots=True)
class IssuedAuthSession:
    access_token: str
    refresh_token: str
    session_id: str
    expires_in: int
    refresh_expires_in: int
    trusted_device_token: str | None = None
    trusted_device_id: str | None = None
    device_trusted: bool = False
    biometric_enabled: bool = False


@dataclass(frozen=True, slots=True)
class SessionBootstrapState:
    user: CurrentUserResponse
    club: ClubProfile | None
    permissions: list[str]


def _record_timing(recorder: AuthTimingRecorder | None, step: str, started_at: float) -> None:
    if recorder is None:
        return
    recorder(step, round((perf_counter() - started_at) * 1000, 2))


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
        account_type: PublicAccountType = PublicAccountType.USER,
        timing_recorder: AuthTimingRecorder | None = None,
    ) -> User:
        normalize_started_at = perf_counter()
        normalized_email = self._normalize_email(email)
        _record_timing(timing_recorder, "auth.normalize_email_ms", normalize_started_at)
        if not is_over_18:
            raise AuthError("You must be at least 18 years old to sign up.")
        username_started_at = perf_counter()
        normalized_username = self._normalize_username(username) if username else None
        _record_timing(timing_recorder, "auth.normalize_username_ms", username_started_at)
        self._validate_password(password)

        resolved_full_name = (full_name or display_name or normalized_username or normalized_email.split("@", 1)[0]).strip()
        if not resolved_full_name:
            raise AuthError("Full name is required.")
        resolved_phone_number = (phone_number or "0000000000").strip()
        if not resolved_phone_number:
            resolved_phone_number = "0000000000"

        lookup_started_at = perf_counter()
        existing_user = session.scalar(select(User).where(User.email == normalized_email))
        _record_timing(timing_recorder, "db.lookup_user_by_email_ms", lookup_started_at)
        if existing_user is not None:
            raise DuplicateUserError("Email address is already registered.")

        if normalized_username is None:
            username_generation_started_at = perf_counter()
            normalized_username = self._generate_unique_username(session, resolved_full_name, normalized_email)
            _record_timing(timing_recorder, "db.generate_username_ms", username_generation_started_at)
        else:
            username_lookup_started_at = perf_counter()
            existing_username = session.scalar(select(User).where(User.username == normalized_username))
            _record_timing(timing_recorder, "db.lookup_user_by_username_ms", username_lookup_started_at)
            if existing_username is not None:
                raise DuplicateUserError("Username is already taken.")

        password_hash_started_at = perf_counter()
        password_hash = hash_password(password)
        _record_timing(timing_recorder, "auth.hash_password_ms", password_hash_started_at)
        user = User(
            email=normalized_email,
            username=normalized_username,
            full_name=resolved_full_name,
            phone_number=resolved_phone_number,
            display_name=display_name or resolved_full_name or normalized_username,
            password_hash=password_hash,
            role=role,
            account_type=account_type,
            age_confirmed_at=utcnow(),
        )
        session.add(user)
        initial_flush_started_at = perf_counter()
        session.flush()
        _record_timing(timing_recorder, "db.flush_user_ms", initial_flush_started_at)
        wallet_started_at = perf_counter()
        self.wallet_service.ensure_default_accounts(session, user)
        WalletFundingService(wallet_service=self.wallet_service).ensure_wallet(session, user)
        _record_timing(timing_recorder, "db.ensure_default_wallets_ms", wallet_started_at)
        region_started_at = perf_counter()
        PolicyService(session).ensure_user_region_profile(user=user, region_code=region_code)
        _record_timing(timing_recorder, "db.ensure_user_region_profile_ms", region_started_at)
        final_flush_started_at = perf_counter()
        session.flush()
        _record_timing(timing_recorder, "db.flush_registration_side_effects_ms", final_flush_started_at)
        return user

    def register_frictionless_player(
        self,
        session: Session,
        *,
        payload: PlayerFrictionlessSignupRequest,
        timing_recorder: AuthTimingRecorder | None = None,
    ) -> User:
        user = self.register_user(
            session,
            email=payload.email,
            full_name=payload.full_name,
            phone_number=payload.phone_number,
            is_over_18=True,
            region_code=payload.country[:8],
            username=None,
            password=payload.password,
            display_name=payload.full_name,
            role=UserRole.USER,
            account_type=PublicAccountType.USER,
            timing_recorder=timing_recorder,
        )
        user.country = payload.country
        user.nationality = payload.country
        user.preferred_position = payload.preferred_position
        user.date_of_birth = payload.date_of_birth
        self.set_security_pin(session, user=user, pin=payload.pin)
        self.replace_recovery_questions(session, user=user, questions=payload.recovery_questions)
        self.record_security_event(
            session,
            user_id=user.id,
            event_type="frictionless_player_signup",
            severity="info",
            metadata={"country": payload.country, "preferred_position": payload.preferred_position},
        )
        session.flush()
        return user

    def register_frictionless_organization(
        self,
        session: Session,
        *,
        payload: OrganizationFrictionlessSignupRequest,
        timing_recorder: AuthTimingRecorder | None = None,
    ) -> User:
        organization_type = payload.organization_type
        user_role = self._role_for_organization_type(organization_type)
        membership_role = self._membership_role_for_organization_type(organization_type)
        user = self.register_user(
            session,
            email=payload.email,
            full_name=payload.contact_name,
            phone_number=payload.phone_number,
            is_over_18=True,
            region_code=payload.country[:8],
            username=None,
            password=payload.password,
            display_name=payload.contact_name,
            role=user_role,
            account_type=PublicAccountType.USER,
            timing_recorder=timing_recorder,
        )
        user.country = payload.country
        user.nationality = payload.country
        self.set_security_pin(session, user=user, pin=payload.pin)
        self.replace_recovery_questions(session, user=user, questions=payload.recovery_questions)

        organization = Organization(
            name=payload.organization_name,
            organization_type=(
                OrganizationType.CLUB
                if organization_type in {"club", "academy"}
                else OrganizationType.AGENCY
            ),
            metadata_json={
                "source": "frictionless_signup",
                "football_organization_type": organization_type,
                "country": payload.country,
                "contact_name": payload.contact_name,
            },
        )
        session.add(organization)
        session.flush()
        session.add(
            OrganizationMembership(
                user_id=user.id,
                organization_id=organization.id,
                role=membership_role,
                is_primary=True,
                invited_by_user_id=None,
            )
        )
        self.record_security_event(
            session,
            user_id=user.id,
            event_type="frictionless_organization_signup",
            severity="info",
            metadata={
                "organization_id": organization.id,
                "organization_type": organization_type,
                "country": payload.country,
            },
        )
        session.flush()
        return user

    def set_security_pin(self, session: Session, *, user: User, pin: str) -> None:
        resolved_pin = self._normalize_pin(pin)
        user.pin_hash = hash_sensitive_secret(resolved_pin)
        self.record_security_event(
            session,
            user_id=user.id,
            event_type="security_pin_set",
            severity="info",
            metadata={},
        )

    def verify_security_pin(
        self,
        session: Session,
        *,
        user: User,
        pin: str,
        action_type: str = "sensitive_action",
    ) -> None:
        self._assert_security_attempts_available(
            session,
            user_id=user.id,
            event_types=("security_pin_failed",),
            lock_event_type="security_pin_locked",
            action_type=action_type,
        )
        resolved_pin = self._normalize_pin(pin)
        if not user.pin_hash or not verify_sensitive_secret(resolved_pin, user.pin_hash):
            self.record_security_event(
                session,
                user_id=user.id,
                event_type="security_pin_failed",
                severity="warning",
                metadata={"action_type": action_type},
            )
            session.flush()
            raise InvalidCredentialsError("Security PIN is invalid.")
        self.record_security_event(
            session,
            user_id=user.id,
            event_type="security_pin_verified",
            severity="info",
            metadata={"action_type": action_type},
        )
        session.flush()

    def replace_recovery_questions(
        self,
        session: Session,
        *,
        user: User,
        questions: list[RecoveryQuestionInput],
    ) -> list[RecoveryQuestion]:
        if len(questions) != 2:
            raise AuthError("Exactly 2 custom recovery questions are required.")
        normalized_question_texts = [self._normalize_recovery_question(item.question) for item in questions]
        if len(set(normalized_question_texts)) != 2:
            raise AuthError("Recovery questions must be distinct.")
        session.execute(delete(RecoveryQuestion).where(RecoveryQuestion.user_id == user.id))
        records: list[RecoveryQuestion] = []
        for position, item in enumerate(questions, start=1):
            record = RecoveryQuestion(
                user_id=user.id,
                position=position,
                question=item.question.strip(),
                answer_hash=hash_sensitive_secret(self._normalize_recovery_answer(item.answer)),
            )
            session.add(record)
            records.append(record)
        session.flush()
        return records

    def recovery_challenge_for_email(self, session: Session, *, email: str) -> tuple[str, list[RecoveryQuestion]]:
        normalized_email = self._normalize_email(email)
        user = session.scalar(select(User).where(User.email == normalized_email))
        if user is None or not user.is_active:
            return normalized_email, []
        questions = list(
            session.scalars(
                select(RecoveryQuestion)
                .where(RecoveryQuestion.user_id == user.id)
                .order_by(RecoveryQuestion.position.asc())
            )
        )
        self.record_security_event(
            session,
            user_id=user.id,
            event_type="recovery_challenge_requested",
            severity="info",
            metadata={},
        )
        return normalized_email, questions

    def reset_password_with_recovery_questions(
        self,
        session: Session,
        *,
        payload: AccountRecoveryQuestionResetRequest,
    ) -> User:
        self._validate_password(payload.new_password)
        normalized_email = self._normalize_email(payload.email)
        user = session.scalar(select(User).where(User.email == normalized_email))
        if user is None or not user.is_active:
            raise AuthError("The account recovery could not be completed.")
        self.verify_security_pin(session, user=user, pin=payload.pin, action_type="account_recovery")
        self._assert_security_attempts_available(
            session,
            user_id=user.id,
            event_types=("recovery_answers_failed",),
            lock_event_type="account_recovery_locked",
            action_type="account_recovery",
        )
        questions = list(
            session.scalars(
                select(RecoveryQuestion)
                .where(RecoveryQuestion.user_id == user.id)
                .order_by(RecoveryQuestion.position.asc())
            )
        )
        if len(questions) != 2:
            self.record_security_event(
                session,
                user_id=user.id,
                event_type="recovery_answers_failed",
                severity="warning",
                metadata={"reason": "question_mismatch"},
            )
            raise AuthError("Recovery answers are invalid.")
        answer_by_question_id = {answer.question_id: answer.answer for answer in payload.answers}
        generic_answers_by_position: dict[int, str] = {}
        for answer in payload.answers:
            if answer.question_id.startswith("recovery-question-"):
                try:
                    position = int(answer.question_id.rsplit("-", 1)[1])
                except (IndexError, ValueError):
                    position = 0
                generic_answers_by_position[position] = answer.answer
        for question in questions:
            raw_answer = answer_by_question_id.get(question.id)
            if raw_answer is None:
                raw_answer = generic_answers_by_position.get(question.position)
            if raw_answer is None:
                self.record_security_event(
                    session,
                    user_id=user.id,
                    event_type="recovery_answers_failed",
                    severity="warning",
                    metadata={"reason": "question_mismatch"},
                )
                raise AuthError("Recovery answers are invalid.")
            candidate = self._normalize_recovery_answer(raw_answer)
            if not verify_sensitive_secret(candidate, question.answer_hash):
                self.record_security_event(
                    session,
                    user_id=user.id,
                    event_type="recovery_answers_failed",
                    severity="warning",
                    metadata={"question_id": question.id},
                )
                raise AuthError("Recovery answers are invalid.")
        now = utcnow()
        user.password_hash = hash_password(payload.new_password)
        session.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user.id)
            .where(AuthSession.revoked_at.is_(None))
            .values(revoked_at=now, revocation_reason="account_recovery", last_used_at=now)
        )
        if payload.device is not None:
            self.upsert_trusted_device(
                session,
                user=user,
                device=payload.device,
                ip_address=None,
                user_agent=None,
            )
        self.record_security_event(
            session,
            user_id=user.id,
            event_type="password_recovered_with_questions",
            severity="warning",
            metadata={"sessions_revoked": True},
        )
        session.flush()
        return user

    def authenticate_user(
        self,
        session: Session,
        *,
        email: str,
        password: str,
        timing_recorder: AuthTimingRecorder | None = None,
    ) -> User:
        normalize_started_at = perf_counter()
        normalized_email = self._normalize_email(email)
        _record_timing(timing_recorder, "auth.normalize_email_ms", normalize_started_at)
        lookup_started_at = perf_counter()
        user = session.scalar(select(User).where(User.email == normalized_email))
        _record_timing(timing_recorder, "db.lookup_user_by_email_ms", lookup_started_at)
        verify_started_at = perf_counter()
        credentials_valid = user is not None and verify_password(password, user.password_hash)
        _record_timing(timing_recorder, "auth.verify_password_ms", verify_started_at)
        if not credentials_valid:
            raise InvalidCredentialsError("Invalid email or password.")
        if not user.is_active:
            raise InvalidCredentialsError("User account is inactive.")

        user.last_login_at = utcnow()
        flush_started_at = perf_counter()
        session.flush()
        _record_timing(timing_recorder, "db.flush_last_login_ms", flush_started_at)
        return user

    def record_login_attempt(
        self,
        session: Session,
        *,
        email: str,
        success: bool,
        ip_address: str | None = None,
        device_id: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        del user_agent
        session.add(
            LoginAttempt(
                email=self._normalize_email(email),
                ip_address=ip_address,
                device_id=device_id,
                success=success,
            )
        )

    def record_security_event(
        self,
        session: Session,
        *,
        user_id: str | None,
        event_type: str,
        severity: str = "info",
        metadata: dict[str, object] | None = None,
    ) -> SecurityEvent:
        event = SecurityEvent(
            user_id=user_id,
            event_type=event_type,
            severity=severity,
            metadata_json=dict(metadata or {}),
        )
        session.add(event)
        return event

    def _assert_security_attempts_available(
        self,
        session: Session,
        *,
        user_id: str,
        event_types: tuple[str, ...],
        lock_event_type: str,
        action_type: str,
    ) -> None:
        cutoff = utcnow() - SECURITY_FAILURE_WINDOW
        failed_attempts = session.scalar(
            select(func.count())
            .select_from(SecurityEvent)
            .where(SecurityEvent.user_id == user_id)
            .where(SecurityEvent.event_type.in_(event_types))
            .where(SecurityEvent.created_at >= cutoff)
        )
        if int(failed_attempts or 0) < SECURITY_FAILURE_LIMIT:
            return
        self.record_security_event(
            session,
            user_id=user_id,
            event_type=lock_event_type,
            severity="critical",
            metadata={
                "action_type": action_type,
                "window_seconds": int(SECURITY_FAILURE_WINDOW.total_seconds()),
                "failure_limit": SECURITY_FAILURE_LIMIT,
            },
        )
        session.flush()
        raise SecurityCooldownError("Too many failed security attempts. Try again later.")

    def upsert_trusted_device(
        self,
        session: Session,
        *,
        user: User,
        device: DeviceTrustRequest | None = None,
        device_id: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str | None, TrustedDevice | None]:
        resolved_device_id = self._normalize_optional_text(
            (device.device_id if device is not None else None)
            or device_id
            or (device.install_id if device is not None else None)
        )
        if resolved_device_id is None:
            return None, None
        now = utcnow()
        existing_device = session.scalar(
            select(TrustedDevice).where(
                TrustedDevice.user_id == user.id,
                TrustedDevice.device_id == resolved_device_id,
            )
        )
        ip_region = self._normalize_optional_text(device.ip_region if device is not None else None)
        if ip_region is None:
            ip_region = self._region_from_ip_address(ip_address)
        biometric_enabled = bool(device.biometric_enabled) if device is not None else False
        presented_trusted_device_token = self._normalize_optional_text(
            device.trusted_device_token if device is not None else None
        )
        stored_trusted_device_token_hash = (
            existing_device.trusted_device_token_hash if existing_device is not None else None
        )
        trusted_device_token_required = bool(stored_trusted_device_token_hash)
        trusted_device_token_matches = not trusted_device_token_required
        if trusted_device_token_required and presented_trusted_device_token is not None:
            trusted_device_token_matches = (
                self._hash_trusted_device_token(presented_trusted_device_token)
                == stored_trusted_device_token_hash
            )
        trusted_device_token_failed = trusted_device_token_required and not trusted_device_token_matches
        trusted_device = existing_device or TrustedDevice(
            user_id=user.id,
            device_id=resolved_device_id,
        )
        risk_score = self._score_device_risk(
            session,
            user=user,
            device_id=resolved_device_id,
            ip_region=ip_region,
            biometric_enabled=biometric_enabled,
            existing_device=existing_device,
        )
        if trusted_device_token_failed:
            risk_score = max(risk_score, 95)
            biometric_enabled = False
        raw_trusted_device_token = None if trusted_device_token_failed else secrets.token_urlsafe(32)
        trusted_device.install_id = self._normalize_optional_text(device.install_id if device is not None else None)
        trusted_device.os = self._normalize_optional_text(device.os if device is not None else None)
        trusted_device.device_model = self._normalize_optional_text(device.device_model if device is not None else None)
        trusted_device.ip_region = ip_region
        trusted_device.biometric_enabled = biometric_enabled
        trusted_device.risk_score = risk_score
        trusted_device.trusted = risk_score < 80 and not trusted_device_token_failed
        trusted_device.last_seen_at = now
        if raw_trusted_device_token is not None:
            trusted_device.trusted_device_token_hash = self._hash_trusted_device_token(raw_trusted_device_token)
        if existing_device is None:
            session.add(trusted_device)
        token_status = "new_device"
        if existing_device is not None:
            if not trusted_device_token_required:
                token_status = "bootstrap"
            elif presented_trusted_device_token is None:
                token_status = "missing"
            elif trusted_device_token_matches:
                token_status = "matched"
            else:
                token_status = "mismatch"
        self.record_security_event(
            session,
            user_id=user.id,
            event_type="trusted_device_seen" if existing_device is not None else "trusted_device_created",
            severity="warning" if risk_score >= 50 else "info",
            metadata={
                "device_id": resolved_device_id,
                "ip_region": ip_region,
                "risk_score": risk_score,
                "trusted": trusted_device.trusted,
                "biometric_enabled": biometric_enabled,
                "trusted_device_token_status": token_status,
                "user_agent_present": bool(user_agent),
            },
        )
        if trusted_device_token_failed:
            self.record_security_event(
                session,
                user_id=user.id,
                event_type="trusted_device_token_failed",
                severity="critical",
                metadata={
                    "device_id": resolved_device_id,
                    "ip_region": ip_region,
                    "trusted_device_token_status": token_status,
                },
            )
        if risk_score >= 80:
            self.record_security_event(
                session,
                user_id=user.id,
                event_type="suspicious_login_detected",
                severity="critical",
                metadata={
                    "device_id": resolved_device_id,
                    "ip_region": ip_region,
                    "risk_score": risk_score,
                    "trusted": trusted_device.trusted,
                },
            )
        session.flush()
        return raw_trusted_device_token, trusted_device

    def issue_access_token(
        self,
        user: User,
        *,
        session: Session | None = None,
        timing_recorder: AuthTimingRecorder | None = None,
    ) -> tuple[str, int]:
        if session is None:
            token = create_access_token(
                user.id,
                claims={
                    "email": user.email,
                    "role": user.role.value,
                    "sid": str(uuid4()),
                },
            )
            return token, ACCESS_TOKEN_TTL_SECONDS

        issued_session = self.issue_session_tokens(
            user,
            session=session,
            timing_recorder=timing_recorder,
        )
        return issued_session.access_token, issued_session.expires_in

    def issue_access_token_with_session(
        self,
        user: User,
        *,
        session: Session | None = None,
        session_id: str | None = None,
        timing_recorder: AuthTimingRecorder | None = None,
    ) -> tuple[str, int, str]:
        if session is None:
            resolved_session_id = (session_id or str(uuid4())).strip()
            token = create_access_token(
                user.id,
                claims={
                    "email": user.email,
                    "role": user.role.value,
                    "account_type": user.account_type.value,
                    "sid": resolved_session_id,
                },
            )
            return token, ACCESS_TOKEN_TTL_SECONDS, resolved_session_id

        issued_session = self.issue_session_tokens(
            user,
            session=session,
            session_id=session_id,
            timing_recorder=timing_recorder,
        )
        return issued_session.access_token, issued_session.expires_in, issued_session.session_id

    def issue_session_tokens(
        self,
        user: User,
        *,
        session: Session,
        session_id: str | None = None,
        device_id: str | None = None,
        device: DeviceTrustRequest | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
        timing_recorder: AuthTimingRecorder | None = None,
    ) -> IssuedAuthSession:
        effective_role = user.role
        active_org_id: str | None = None
        access_context_started_at = perf_counter()
        access_context = AccessControlService(session).bind_user_access_context(user)
        _record_timing(timing_recorder, "auth.bind_access_context_ms", access_context_started_at)
        effective_role = access_context.effective_role
        active_org_id = access_context.active_organization_id
        session_id_started_at = perf_counter()
        resolved_session_id = (session_id or str(uuid4())).strip()
        _record_timing(timing_recorder, "auth.create_session_id_ms", session_id_started_at)
        now = utcnow()
        token_started_at = perf_counter()
        access_token = create_access_token(
            user.id,
            claims={
                "email": user.email,
                "role": effective_role.value,
                "account_type": user.account_type.value,
                "org_id": active_org_id,
                "sid": resolved_session_id,
                "club_id": active_org_id,
            },
        )
        refresh_token = create_refresh_token(
            user.id,
            claims={
                "sid": resolved_session_id,
            },
        )
        _record_timing(timing_recorder, "auth.create_access_token_ms", token_started_at)
        trusted_device_token: str | None = None
        trusted_device: TrustedDevice | None = None
        trusted_device_started_at = perf_counter()
        trusted_device_token, trusted_device = self.upsert_trusted_device(
            session,
            user=user,
            device=device,
            device_id=device_id,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        _record_timing(timing_recorder, "auth.upsert_trusted_device_ms", trusted_device_started_at)
        persistence_started_at = perf_counter()
        auth_session = session.get(AuthSession, resolved_session_id)
        if auth_session is None:
            auth_session = AuthSession(id=resolved_session_id, user_id=user.id)
            session.add(auth_session)
        auth_session.refresh_token_hash = self._hash_refresh_token(refresh_token)
        auth_session.expires_at = now + timedelta(seconds=REFRESH_TOKEN_TTL_SECONDS)
        auth_session.last_used_at = now
        auth_session.revoked_at = None
        auth_session.revocation_reason = None
        auth_session.device_id = (trusted_device.device_id if trusted_device is not None else device_id) or auth_session.device_id
        auth_session.user_agent = user_agent or auth_session.user_agent
        auth_session.ip_address = ip_address or auth_session.ip_address
        session.flush()
        _record_timing(timing_recorder, "db.persist_auth_session_ms", persistence_started_at)
        return IssuedAuthSession(
            access_token=access_token,
            refresh_token=refresh_token,
            session_id=resolved_session_id,
            expires_in=ACCESS_TOKEN_TTL_SECONDS,
            refresh_expires_in=REFRESH_TOKEN_TTL_SECONDS,
            trusted_device_token=trusted_device_token,
            trusted_device_id=trusted_device.device_id if trusted_device is not None else None,
            device_trusted=bool(trusted_device.trusted) if trusted_device is not None else False,
            biometric_enabled=bool(trusted_device.biometric_enabled) if trusted_device is not None else False,
        )

    def refresh_session_tokens(
        self,
        session: Session,
        *,
        refresh_token: str,
        device_id: str | None = None,
        device: DeviceTrustRequest | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
        timing_recorder: AuthTimingRecorder | None = None,
    ) -> tuple[User, IssuedAuthSession]:
        decode_started_at = perf_counter()
        try:
            payload = decode_refresh_token(refresh_token)
        except ValueError as exc:
            raise InvalidRefreshTokenError("Refresh token is invalid or expired.") from exc
        _record_timing(timing_recorder, "auth.decode_refresh_token_ms", decode_started_at)
        subject = payload.get("sub")
        session_id = payload.get("sid")
        if not isinstance(subject, str) or not subject or not isinstance(session_id, str) or not session_id:
            raise InvalidRefreshTokenError("Refresh token is invalid or expired.")
        lookup_started_at = perf_counter()
        auth_session = session.get(AuthSession, session_id)
        _record_timing(timing_recorder, "db.lookup_auth_session_ms", lookup_started_at)
        if auth_session is None or auth_session.user_id != subject:
            raise InvalidRefreshTokenError("Refresh token is invalid or expired.")
        self._assert_active_auth_session(auth_session, expected_refresh_token=refresh_token)
        user = session.get(User, subject)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError("Refresh token is invalid or expired.")
        issued_session = self.issue_session_tokens(
            user,
            session=session,
            session_id=auth_session.id,
            device_id=device_id or auth_session.device_id,
            device=device,
            user_agent=user_agent or auth_session.user_agent,
            ip_address=ip_address or auth_session.ip_address,
            timing_recorder=timing_recorder,
        )
        return user, issued_session

    def revoke_session(
        self,
        session: Session,
        *,
        session_id: str,
        user_id: str | None = None,
        reason: str = "logout",
    ) -> AuthSession | None:
        auth_session = session.get(AuthSession, session_id)
        if auth_session is None:
            return None
        if user_id is not None and auth_session.user_id != user_id:
            raise InvalidSessionError("Authenticated session does not belong to the current user.")
        if auth_session.revoked_at is None:
            auth_session.revoked_at = utcnow()
        auth_session.revocation_reason = reason
        auth_session.last_used_at = utcnow()
        session.flush()
        return auth_session

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
                            *SUPER_ADMIN_EXTRA_PERMISSIONS,
                        ],
                    )
                )
            return membership_permissions

    @staticmethod
    def resolve_landing_route(
        user: User,
        *,
        permissions: list[str] | tuple[str, ...] = (),
        session: Session | None = None,
    ) -> str:
        effective_role = user.role
        if session is not None:
            effective_role = AccessControlService(session).bind_user_access_context(user).effective_role
        normalized_permissions = {
            permission.strip().lower()
            for permission in permissions
            if permission and permission.strip()
        }
        if effective_role == UserRole.SUPER_ADMIN:
            return PROFILE_GOD_MODE_ROUTE
        if effective_role == UserRole.ADMIN:
            if normalized_permissions & GOD_MODE_LANDING_PERMISSIONS:
                return PROFILE_GOD_MODE_ROUTE
            return PROFILE_ADMIN_ROUTE
        if user.account_type == PublicAccountType.CREATOR:
            return "/app/hub"
        if user.account_type == PublicAccountType.COIN_TRADER:
            return "/trader"
        return "/app/world"

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
            account_type=user.account_type,
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
            account_type=user.account_type,
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

    def build_session_bootstrap_state(
        self,
        session: Session,
        user: User,
        *,
        app=None,
    ) -> SessionBootstrapState:
        club = self.resolve_user_club(session, user)
        if club is not None and club.lifecycle_status != ClubLifecycleStatus.ARCHIVED_GENERATED:
            owner_user_id = user.id if club.owner_user_id == user.id else None
            AccessControlService(session).ensure_club_organization(club, owner_user_id=owner_user_id)
        profile = self.get_current_user_profile(session, user, app=app)
        return SessionBootstrapState(
            user=profile,
            club=club,
            permissions=list(profile.permissions),
        )

    def ensure_user_club_context(self, session: Session, user: User) -> ClubProfile:
        if user.account_type != PublicAccountType.USER:
            raise AuthError("Club context is only available to football user accounts.")
        club = self.resolve_user_club(session, user)
        if club is None:
            raise AuthError("Club context is unavailable until an explicit club is created.")
        owner_user_id = user.id if club.owner_user_id == user.id else None
        AccessControlService(session).ensure_club_organization(club, owner_user_id=owner_user_id)
        session.flush()
        return club

    def resolve_user_club(self, session: Session, user: User) -> ClubProfile | None:
        if user.account_type != PublicAccountType.USER:
            return None
        owned_club = session.scalar(
            select(ClubProfile)
            .where(ClubProfile.owner_user_id == user.id)
            .where(ClubProfile.lifecycle_status != ClubLifecycleStatus.ARCHIVED_GENERATED)
            .order_by(ClubProfile.created_at.asc())
        )
        if owned_club is not None:
            return owned_club
        return session.scalar(
            select(ClubProfile)
            .join(Organization, Organization.club_profile_id == ClubProfile.id)
            .join(OrganizationMembership, OrganizationMembership.organization_id == Organization.id)
            .where(OrganizationMembership.user_id == user.id)
            .where(ClubProfile.lifecycle_status != ClubLifecycleStatus.ARCHIVED_GENERATED)
            .order_by(
                OrganizationMembership.is_primary.desc(),
                OrganizationMembership.created_at.asc(),
                ClubProfile.created_at.asc(),
            )
        )

    def create_explicit_club_profile(
        self,
        session: Session,
        user: User,
        *,
        club_name: str,
        short_name: str,
        club_type: ClubType,
        country_code: str | None,
        region_name: str | None,
        city_name: str | None,
        crest_asset_ref: str | None,
        primary_color: str,
        secondary_color: str,
    ) -> ClubProfile:
        if user.account_type != PublicAccountType.USER:
            raise AuthError("Only football user accounts can create clubs.")
        normalized_name = club_name.strip()
        if not normalized_name:
            raise AuthError("Club name is required.")
        club = ClubProfile(
            owner_user_id=user.id,
            club_name=normalized_name,
            short_name=short_name.strip().upper()[:40] or normalized_name[:4].upper(),
            club_type=club_type,
            lifecycle_status=ClubLifecycleStatus.ACTIVE,
            slug=self._generate_unique_club_slug(session, normalized_name),
            crest_asset_ref=crest_asset_ref,
            primary_color=primary_color.strip() or "#0F766E",
            secondary_color=secondary_color.strip() or "#F8FAFC",
            accent_color="#EA580C",
            country_code=((country_code or "").strip().upper()[:8]) or None,
            region_name=(region_name or "").strip() or None,
            city_name=(city_name or "").strip() or None,
            visibility="public",
        )
        session.add(club)
        session.flush()
        ClubReputationService(session).ensure_profile(club.id)
        ClubDynastyService(session).ensure_progress(club.id)
        ClubTrophyService(session).ensure_cabinet(club.id)
        AccessControlService(session).ensure_club_organization(club, owner_user_id=user.id)
        session.flush()
        return club

    def get_auth_session_record(
        self,
        session: Session,
        *,
        session_id: str,
        user_id: str,
    ) -> AuthSession:
        auth_session = session.get(AuthSession, session_id)
        if auth_session is None or auth_session.user_id != user_id:
            raise InvalidSessionError("Authenticated session is invalid.")
        self._assert_active_auth_session(auth_session)
        return auth_session

    @staticmethod
    def _assert_active_auth_session(
        auth_session: AuthSession,
        *,
        expected_refresh_token: str | None = None,
    ) -> None:
        now = utcnow()
        if auth_session.revoked_at is not None:
            raise InvalidSessionError("Authenticated session has been revoked.")
        if AuthService._as_utc_datetime(auth_session.expires_at) <= now:
            raise InvalidSessionError("Authenticated session has expired.")
        if expected_refresh_token is not None:
            expected_hash = AuthService._hash_refresh_token(expected_refresh_token)
            if auth_session.refresh_token_hash != expected_hash:
                raise InvalidRefreshTokenError("Refresh token is invalid or expired.")

    def _generate_unique_club_slug(self, session: Session, seed: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", seed.strip().lower()).strip("-")
        if not base:
            base = f"club-{generate_uuid()[:8]}"
        base = base[:96]
        candidate = base
        suffix = 1
        while session.scalar(select(ClubProfile).where(ClubProfile.slug == candidate)) is not None:
            candidate = f"{base[:90]}-{suffix}"
            suffix += 1
        return candidate

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

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip()
        return candidate or None

    @staticmethod
    def _normalize_pin(value: str) -> str:
        candidate = value.strip()
        if len(candidate) != 4 or not candidate.isdigit():
            raise AuthError("Security PIN must be exactly 4 digits.")
        return candidate

    @staticmethod
    def _normalize_recovery_question(value: str) -> str:
        candidate = " ".join(value.strip().casefold().replace("?", "").split())
        banned_fragments = {
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
        if not candidate:
            raise AuthError("Recovery question is required.")
        if any(fragment in candidate for fragment in banned_fragments):
            raise AuthError("Use a custom football or personal recovery question, not a generic predefined prompt.")
        return candidate

    @staticmethod
    def _normalize_recovery_answer(value: str) -> str:
        candidate = " ".join(value.strip().casefold().split())
        if not candidate:
            raise AuthError("Recovery answer is required.")
        return candidate

    @staticmethod
    def _role_for_organization_type(organization_type: str) -> UserRole:
        if organization_type in {"club", "academy"}:
            return UserRole.CLUB
        if organization_type in {"agent", "agency"}:
            return UserRole.AGENT
        return UserRole.SCOUT

    @staticmethod
    def _membership_role_for_organization_type(organization_type: str) -> OrganizationRole:
        if organization_type in {"club", "academy"}:
            return OrganizationRole.CLUB
        if organization_type in {"agent", "agency"}:
            return OrganizationRole.AGENT
        return OrganizationRole.SCOUT

    @staticmethod
    def _region_from_ip_address(ip_address: str | None) -> str | None:
        if ip_address is None:
            return None
        candidate = ip_address.strip()
        if not candidate:
            return None
        if candidate.startswith(("10.", "192.168.", "127.", "::1")):
            return "local"
        return candidate.rsplit(".", maxsplit=1)[0][:120]

    def _score_device_risk(
        self,
        session: Session,
        *,
        user: User,
        device_id: str,
        ip_region: str | None,
        biometric_enabled: bool,
        existing_device: TrustedDevice | None,
    ) -> int:
        risk_score = 0 if existing_device is not None else 10
        if not biometric_enabled:
            risk_score += 5
        previous_device = session.scalar(
            select(TrustedDevice)
            .where(TrustedDevice.user_id == user.id)
            .where(TrustedDevice.device_id != device_id)
            .where(TrustedDevice.last_seen_at.is_not(None))
            .order_by(TrustedDevice.last_seen_at.desc())
        )
        if previous_device is not None and ip_region and previous_device.ip_region and previous_device.ip_region != ip_region:
            risk_score += 35
            previous_seen_at = previous_device.last_seen_at
            if previous_seen_at is not None:
                if previous_seen_at.tzinfo is None:
                    previous_seen_at = previous_seen_at.replace(tzinfo=timezone.utc)
                if previous_seen_at >= utcnow() - SUSPICIOUS_TRAVEL_WINDOW:
                    risk_score += 45
        return min(risk_score, 100)

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
    def _hash_refresh_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_trusted_device_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

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
