from __future__ import annotations

import logging
from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.analytics.service import AnalyticsService
from app.auth.dependencies import get_current_user, get_session
from app.auth.schemas import (
    AccountRecoveryChallengeResponse,
    AccountRecoveryQuestionResetRequest,
    AccountRecoveryRequest,
    AccountRecoveryResetRequest,
    ActionStatusResponse,
    ChangePasswordRequest,
    ConfirmEmailRequest,
    CurrentUserResponse,
    CurrentUserUpdateRequest,
    DeviceTrustRequest,
    LoginRequest,
    OrganizationFrictionlessSignupRequest,
    PinVerificationRequest,
    PlayerFrictionlessSignupRequest,
    RefreshTokenRequest,
    RecoveryChallengeQuestion,
    SessionBootstrapResponse,
    TokenResponse,
)
from app.auth.service import (
    AuthError,
    AuthService,
    DuplicateUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidSessionError,
    IssuedAuthSession,
    SecurityCooldownError,
)
from app.core.request_security import extract_client_ip
from app.models.user import KycStatus, User
from app.policies.schemas import PolicyRequirementSummary, UserComplianceStatus
from app.policies.service import PolicyService
from app.schemas.club_identity_core import ClubProfileCore
from app.wallets.funding_service import WalletFundingService
from app.wallets.schemas import WalletAdaptiveOverviewView
from app.wallets.service import WalletService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])
api_v2_router = APIRouter(prefix="/api/v2/auth")

_GENERIC_RECOVERY_CHALLENGE_QUESTIONS = (
    "Custom recovery question 1",
    "Custom recovery question 2",
)


class _AuthRouteTelemetry:
    def __init__(self, flow: str) -> None:
        self.flow = flow
        self.started_at = perf_counter()
        self.steps: dict[str, float] = {}

    def capture(self, step: str, duration_ms: float) -> None:
        self.steps[step] = round(duration_ms, 2)

    def mark(self, step: str, started_at: float) -> None:
        self.capture(step, (perf_counter() - started_at) * 1000)

    def log_entry(self, *, method: str, path: str, modules_hydrated: bool | None) -> None:
        logger.info(
            "auth.request.route_entry flow=%s method=%s path=%s modules_hydrated=%s",
            self.flow,
            method,
            path,
            modules_hydrated,
        )

    def log_success(self, *, status_code: int, user_id: str | None) -> None:
        logger.info(
            "auth.request.completed flow=%s status_code=%s user_id=%s duration_ms=%.2f steps=%s",
            self.flow,
            status_code,
            user_id,
            (perf_counter() - self.started_at) * 1000,
            self.steps,
        )

    def log_failure(self, *, status_code: int, user_id: str | None, error: str) -> None:
        logger.warning(
            "auth.request.failed flow=%s status_code=%s user_id=%s duration_ms=%.2f error=%s steps=%s",
            self.flow,
            status_code,
            user_id,
            (perf_counter() - self.started_at) * 1000,
            error,
            self.steps,
        )


def _build_auth_service(request: Request | None) -> AuthService:
    wallet_service = None
    email_service = None
    if request is not None:
        wallet_service = WalletService(
            event_publisher=getattr(request.app.state, "event_publisher", None),
            cache_backend=getattr(request.app.state, "cache_backend", None),
        )
    if request is not None and hasattr(request.app.state, "email_service"):
        email_service = request.app.state.email_service
    return AuthService(wallet_service=wallet_service, email_service=email_service)


def _log_email_dispatch_exception(*, flow: str, recipient: str | None, exc: Exception) -> None:
    logger.warning(
        "auth.email.dispatch_exception flow=%s recipient=%s error_type=%s error=%s",
        flow,
        recipient or "unknown",
        exc.__class__.__name__,
        str(exc),
    )


def _rollback_with_telemetry(session: Session, telemetry: _AuthRouteTelemetry) -> None:
    rollback_started_at = perf_counter()
    session.rollback()
    telemetry.mark("db.rollback_ms", rollback_started_at)


def _build_token_response(
    *,
    service: AuthService,
    session: Session,
    request: Request | None,
    telemetry: _AuthRouteTelemetry,
    user: User,
    issued_session: IssuedAuthSession,
) -> TokenResponse:
    user_public_started_at = perf_counter()
    user_public = service.build_user_public(session, user)
    telemetry.mark("service.build_user_public_ms", user_public_started_at)
    permissions_started_at = perf_counter()
    permissions = service.resolve_user_permissions(request.app, user, session=session) if request is not None else []
    telemetry.mark("service.resolve_permissions_ms", permissions_started_at)
    landing_route_started_at = perf_counter()
    landing_route = service.resolve_landing_route(
        user,
        permissions=permissions,
        session=session,
    )
    telemetry.mark("service.resolve_landing_route_ms", landing_route_started_at)
    return TokenResponse(
        access_token=issued_session.access_token,
        refresh_token=issued_session.refresh_token,
        session_id=issued_session.session_id,
        expires_in=issued_session.expires_in,
        refresh_expires_in=issued_session.refresh_expires_in,
        user=user_public,
        permissions=permissions,
        landing_route=landing_route,
        trusted_device_token=issued_session.trusted_device_token,
        trusted_device_id=issued_session.trusted_device_id,
        device_trusted=issued_session.device_trusted,
        biometric_enabled=issued_session.biometric_enabled,
    )


def _build_recovery_challenge_questions(questions: list[object]) -> list[RecoveryChallengeQuestion]:
    return [
        RecoveryChallengeQuestion(id=f"recovery-question-{index}", question=label)
        for index, label in enumerate(_GENERIC_RECOVERY_CHALLENGE_QUESTIONS, start=1)
    ]


def _request_client_context(request: Request | None, *, device_id: str | None = None) -> dict[str, str | None]:
    user_agent = None
    ip_address = None
    if request is not None:
        user_agent = request.headers.get("user-agent")
        ip_address = extract_client_ip(request)
    return {
        "device_id": device_id,
        "user_agent": user_agent,
        "ip_address": ip_address,
    }


def _payload_device_id(payload_device) -> str | None:
    if payload_device is None:
        return None
    return payload_device.device_id or payload_device.install_id


def _device_with_trusted_token(
    payload_device: DeviceTrustRequest | None,
    trusted_device_token: str | None,
) -> DeviceTrustRequest | None:
    token = (trusted_device_token or "").strip()
    if token and len(token) < 16:
        token = ""
    if not token or (payload_device is not None and payload_device.trusted_device_token):
        return payload_device
    if payload_device is None:
        return DeviceTrustRequest(trusted_device_token=token)
    return payload_device.model_copy(update={"trusted_device_token": token})


def _record_login_attempt(
    request: Request | None,
    *,
    email: str,
    success: bool,
    user_id: str | None,
    device_id: str | None,
    failure_reason: str | None = None,
) -> None:
    if request is None:
        return
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        return
    from app.risk.security_monitoring_service import SecurityMonitoringService

    client_context = _request_client_context(request, device_id=device_id)
    try:
        SecurityMonitoringService(session_factory=session_factory).record_login_attempt(
            email=email,
            success=success,
            user_id=user_id,
            ip_address=client_context["ip_address"],
            user_agent=client_context["user_agent"],
            device_id=client_context["device_id"],
            path=str(request.url.path),
            failure_reason=failure_reason,
        )
    except Exception as exc:
        logger.warning(
            "auth.login.audit_failed email=%s success=%s error_type=%s error=%s",
            email,
            success,
            exc.__class__.__name__,
            str(exc),
        )


def _build_compliance_status(session: Session, user: User) -> UserComplianceStatus:
    policy_service = PolicyService(session)
    country_policy = policy_service.get_country_policy_for_user(user=user)
    missing = policy_service.list_missing_acceptances(user_id=user.id)
    wallet = WalletFundingService().ensure_wallet(session, user)
    is_verified = str(wallet.compliance_status or "").strip().lower() == "verified"
    return UserComplianceStatus(
        country_code=country_policy.country_code,
        country_policy_bucket=country_policy.bucket_type,
        deposits_enabled=country_policy.deposits_enabled,
        market_trading_enabled=country_policy.market_trading_enabled,
        platform_reward_withdrawals_enabled=country_policy.platform_reward_withdrawals_enabled,
        compliance_status=wallet.compliance_status,
        required_policy_acceptances_missing=len(missing),
        missing_policy_acceptances=[
            PolicyRequirementSummary(
                document_key=version.document.document_key,
                title=version.document.title,
                version_label=version.version_label,
                is_mandatory=version.document.is_mandatory,
                effective_at=version.effective_at,
            )
            for version in missing
        ],
        can_deposit=country_policy.deposits_enabled,
        can_withdraw_platform_rewards=country_policy.platform_reward_withdrawals_enabled,
        can_trade_market=country_policy.market_trading_enabled and is_verified,
    )


def _build_wallet_bootstrap(service: AuthService, session: Session, user: User) -> WalletAdaptiveOverviewView:
    wallet_payload = service.wallet_service.get_adaptive_overview(session, user)
    wallet_payload["competition_reward_balance"] = service.wallet_service.competition_reward_balance(session, user)
    wallet_payload["competition_reward_withdrawable_balance"] = (
        service.wallet_service.competition_reward_withdrawable_balance(
            session,
            user,
        )
    )
    return WalletAdaptiveOverviewView(**wallet_payload)


def _build_session_bootstrap_response(
    *,
    service: AuthService,
    session: Session,
    request: Request,
    user: User,
) -> SessionBootstrapResponse:
    bootstrap = service.build_session_bootstrap_state(session, user, app=request.app)
    wallet = _build_wallet_bootstrap(service, session, user)
    compliance = _build_compliance_status(session, user)
    return SessionBootstrapResponse(
        user=bootstrap.user,
        club=None if bootstrap.club is None else ClubProfileCore.model_validate(bootstrap.club),
        wallet=wallet,
        compliance=compliance,
        permissions=bootstrap.permissions,
    )


@api_v2_router.post("/signup/player", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup_player_frictionless(
    payload: PlayerFrictionlessSignupRequest,
    session: Session = Depends(get_session),
    request: Request = None,
) -> TokenResponse:
    service = _build_auth_service(request)
    telemetry = _AuthRouteTelemetry("signup_player_frictionless")
    user: User | None = None
    issued_session: IssuedAuthSession | None = None
    try:
        user = service.register_frictionless_player(
            session,
            payload=payload,
            timing_recorder=telemetry.capture,
        )
        issued_session = service.issue_session_tokens(
            user,
            session=session,
            device=payload.device,
            **_request_client_context(request, device_id=_payload_device_id(payload.device)),
            timing_recorder=telemetry.capture,
        )
        session.commit()
        session.refresh(user)
    except DuplicateUserError as exc:
        _rollback_with_telemetry(session, telemetry)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthError as exc:
        _rollback_with_telemetry(session, telemetry)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _build_token_response(
        service=service,
        session=session,
        request=request,
        telemetry=telemetry,
        user=user,
        issued_session=issued_session,
    )


@api_v2_router.post("/signup/organization", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup_organization_frictionless(
    payload: OrganizationFrictionlessSignupRequest,
    session: Session = Depends(get_session),
    request: Request = None,
) -> TokenResponse:
    service = _build_auth_service(request)
    telemetry = _AuthRouteTelemetry("signup_organization_frictionless")
    user: User | None = None
    issued_session: IssuedAuthSession | None = None
    try:
        user = service.register_frictionless_organization(
            session,
            payload=payload,
            timing_recorder=telemetry.capture,
        )
        issued_session = service.issue_session_tokens(
            user,
            session=session,
            device=payload.device,
            **_request_client_context(request, device_id=_payload_device_id(payload.device)),
            timing_recorder=telemetry.capture,
        )
        session.commit()
        session.refresh(user)
    except DuplicateUserError as exc:
        _rollback_with_telemetry(session, telemetry)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthError as exc:
        _rollback_with_telemetry(session, telemetry)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _build_token_response(
        service=service,
        session=session,
        request=request,
        telemetry=telemetry,
        user=user,
        issued_session=issued_session,
    )

@api_v2_router.post("/login", response_model=TokenResponse)
def login_user(
    payload: LoginRequest,
    session: Session = Depends(get_session),
    request: Request = None,
    x_device_id: Annotated[str | None, Header(alias="X-Device-Id")] = None,
    x_trusted_device_token: Annotated[str | None, Header(alias="X-Trusted-Device-Token")] = None,
) -> TokenResponse:
    service = _build_auth_service(request)
    analytics = AnalyticsService()
    telemetry = _AuthRouteTelemetry("login")
    issued_session: IssuedAuthSession | None = None
    user: User | None = None
    device = _device_with_trusted_token(payload.device, x_trusted_device_token)
    telemetry.log_entry(
        method=request.method if request is not None else "POST",
        path=str(request.url.path) if request is not None else "/api/v2/auth/login",
        modules_hydrated=getattr(request.app.state, "modules_hydrated", None) if request is not None else None,
    )
    try:
        login_started_at = perf_counter()
        user = service.authenticate_user(
            session,
            email=payload.email,
            password=payload.password,
            timing_recorder=telemetry.capture,
        )
        telemetry.mark("service.authenticate_user_ms", login_started_at)
        analytics_success_started_at = perf_counter()
        analytics.track_event(session, name="login_success", user_id=user.id, metadata={})
        telemetry.mark("analytics.login_success_ms", analytics_success_started_at)
        token_started_at = perf_counter()
        issued_session = service.issue_session_tokens(
            user,
            session=session,
            device=device,
            **_request_client_context(request, device_id=x_device_id or _payload_device_id(device)),
            timing_recorder=telemetry.capture,
        )
        telemetry.mark("service.issue_access_token_ms", token_started_at)
        service.record_login_attempt(
            session,
            email=payload.email,
            success=True,
            **_request_client_context(request, device_id=x_device_id or _payload_device_id(device)),
        )
        commit_started_at = perf_counter()
        session.commit()
        telemetry.mark("db.commit_ms", commit_started_at)
        refresh_started_at = perf_counter()
        session.refresh(user)
        telemetry.mark("db.refresh_user_ms", refresh_started_at)
    except InvalidCredentialsError as exc:
        analytics_failure_started_at = perf_counter()
        analytics.track_event(session, name="login_failure", user_id=None, metadata={"email": payload.email})
        telemetry.mark("analytics.login_failure_ms", analytics_failure_started_at)
        _rollback_with_telemetry(session, telemetry)
        try:
            service.record_login_attempt(
                session,
                email=payload.email,
                success=False,
                **_request_client_context(request, device_id=x_device_id or _payload_device_id(device)),
            )
            session.commit()
        except Exception:
            session.rollback()
        _record_login_attempt(
            request,
            email=payload.email,
            success=False,
            user_id=None,
            device_id=x_device_id or _payload_device_id(device),
            failure_reason=str(exc),
        )
        telemetry.log_failure(status_code=status.HTTP_401_UNAUTHORIZED, user_id=None, error=str(exc))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AuthError as exc:
        analytics_failure_started_at = perf_counter()
        analytics.track_event(session, name="login_failure", user_id=None, metadata={"email": payload.email})
        telemetry.mark("analytics.login_failure_ms", analytics_failure_started_at)
        _rollback_with_telemetry(session, telemetry)
        try:
            service.record_login_attempt(
                session,
                email=payload.email,
                success=False,
                **_request_client_context(request, device_id=x_device_id or _payload_device_id(device)),
            )
            session.commit()
        except Exception:
            session.rollback()
        _record_login_attempt(
            request,
            email=payload.email,
            success=False,
            user_id=user.id if user is not None else None,
            device_id=x_device_id or _payload_device_id(device),
            failure_reason=str(exc),
        )
        telemetry.log_failure(
            status_code=status.HTTP_400_BAD_REQUEST, user_id=user.id if user is not None else None, error=str(exc)
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        _rollback_with_telemetry(session, telemetry)
        try:
            service.record_login_attempt(
                session,
                email=payload.email,
                success=False,
                **_request_client_context(request, device_id=x_device_id or _payload_device_id(device)),
            )
            session.commit()
        except Exception:
            session.rollback()
        _record_login_attempt(
            request,
            email=payload.email,
            success=False,
            user_id=user.id if user is not None else None,
            device_id=x_device_id or _payload_device_id(device),
            failure_reason=str(exc),
        )
        telemetry.log_failure(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            user_id=user.id if user is not None else None,
            error=str(exc),
        )
        raise
    _record_login_attempt(
        request,
        email=payload.email,
        success=True,
        user_id=user.id,
        device_id=x_device_id or _payload_device_id(device),
    )
    telemetry.log_success(status_code=status.HTTP_200_OK, user_id=user.id)

    return _build_token_response(
        service=service,
        session=session,
        request=request,
        telemetry=telemetry,
        user=user,
        issued_session=issued_session,
    )


@api_v2_router.post("/refresh", response_model=TokenResponse)
def refresh_auth_session(
    payload: RefreshTokenRequest,
    request: Request,
    session: Session = Depends(get_session),
    x_device_id: Annotated[str | None, Header(alias="X-Device-Id")] = None,
    x_trusted_device_token: Annotated[str | None, Header(alias="X-Trusted-Device-Token")] = None,
) -> TokenResponse:
    service = _build_auth_service(request)
    telemetry = _AuthRouteTelemetry("refresh")
    issued_session: IssuedAuthSession | None = None
    user: User | None = None
    telemetry.log_entry(
        method=request.method,
        path=str(request.url.path),
        modules_hydrated=getattr(request.app.state, "modules_hydrated", None),
    )
    try:
        refresh_started_at = perf_counter()
        device = _device_with_trusted_token(payload.device, x_trusted_device_token)
        user, issued_session = service.refresh_session_tokens(
            session,
            refresh_token=payload.refresh_token,
            device=device,
            **_request_client_context(request, device_id=x_device_id or _payload_device_id(device)),
            timing_recorder=telemetry.capture,
        )
        telemetry.mark("service.refresh_session_tokens_ms", refresh_started_at)
        commit_started_at = perf_counter()
        session.commit()
        telemetry.mark("db.commit_ms", commit_started_at)
        refresh_user_started_at = perf_counter()
        session.refresh(user)
        telemetry.mark("db.refresh_user_ms", refresh_user_started_at)
    except (InvalidRefreshTokenError, InvalidSessionError) as exc:
        _rollback_with_telemetry(session, telemetry)
        telemetry.log_failure(
            status_code=status.HTTP_401_UNAUTHORIZED,
            user_id=user.id if user is not None else None,
            error=str(exc),
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AuthError as exc:
        _rollback_with_telemetry(session, telemetry)
        telemetry.log_failure(
            status_code=status.HTTP_400_BAD_REQUEST,
            user_id=user.id if user is not None else None,
            error=str(exc),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        _rollback_with_telemetry(session, telemetry)
        telemetry.log_failure(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            user_id=user.id if user is not None else None,
            error=str(exc),
        )
        raise
    logger.info(
        "auth.token.refresh user_id=%s session_id=%s device_id=%s",
        user.id,
        issued_session.session_id if issued_session is not None else None,
        x_device_id,
    )
    telemetry.log_success(status_code=status.HTTP_200_OK, user_id=user.id)
    return _build_token_response(
        service=service,
        session=session,
        request=request,
        telemetry=telemetry,
        user=user,
        issued_session=issued_session,
    )


@api_v2_router.post("/logout", response_model=ActionStatusResponse)
def logout_user(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ActionStatusResponse:
    service = _build_auth_service(request)
    auth_session = getattr(request.state, "auth_session", None)
    session_id = getattr(auth_session, "id", None)
    if not isinstance(session_id, str) or not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authenticated session is invalid.")
    try:
        service.revoke_session(
            session,
            session_id=session_id,
            user_id=current_user.id,
            reason="logout",
        )
        session.commit()
    except InvalidSessionError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    logger.info("auth.session.logout user_id=%s session_id=%s", current_user.id, session_id)
    return ActionStatusResponse(detail="Logged out successfully.")


@api_v2_router.post("/confirm-email", response_model=ActionStatusResponse)
def confirm_email(
    payload: ConfirmEmailRequest,
    session: Session = Depends(get_session),
    request: Request = None,
) -> ActionStatusResponse:
    service = _build_auth_service(request)
    try:
        service.confirm_email_address(session, code=payload.code)
        session.commit()
    except AuthError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ActionStatusResponse(detail="Email address confirmed.")


@api_v2_router.post("/recovery/request", response_model=ActionStatusResponse)
def request_account_recovery(
    payload: AccountRecoveryRequest,
    session: Session = Depends(get_session),
    request: Request = None,
) -> ActionStatusResponse:
    service = _build_auth_service(request)
    analytics = AnalyticsService()
    user = None
    recovery_code = None
    try:
        user, recovery_code = service.prepare_account_recovery(session, email=payload.email)
        session.commit()
    except AuthError as exc:
        analytics.track_event(session, name="login_failure", user_id=None, metadata={"email": payload.email})
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if user is not None and recovery_code is not None:
        try:
            service.send_account_recovery_email(user=user, recovery_code=recovery_code)
        except Exception as exc:
            _log_email_dispatch_exception(flow="account_recovery", recipient=user.email, exc=exc)

    return ActionStatusResponse(detail="If an account exists for that email, recovery instructions have been sent.")


@api_v2_router.post("/recovery/challenge", response_model=AccountRecoveryChallengeResponse)
def request_recovery_challenge(
    payload: AccountRecoveryRequest,
    session: Session = Depends(get_session),
    request: Request = None,
) -> AccountRecoveryChallengeResponse:
    service = _build_auth_service(request)
    try:
        email, questions = service.recovery_challenge_for_email(session, email=payload.email)
        session.commit()
    except AuthError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return AccountRecoveryChallengeResponse(
        email=email,
        questions=_build_recovery_challenge_questions(list(questions)),
    )


@api_v2_router.post("/recovery/reset-with-questions", response_model=ActionStatusResponse)
def reset_account_with_recovery_questions(
    payload: AccountRecoveryQuestionResetRequest,
    session: Session = Depends(get_session),
    request: Request = None,
) -> ActionStatusResponse:
    service = _build_auth_service(request)
    try:
        service.reset_password_with_recovery_questions(session, payload=payload)
        session.commit()
    except SecurityCooldownError as exc:
        session.commit()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except InvalidCredentialsError as exc:
        session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AuthError as exc:
        session.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ActionStatusResponse(detail="Account recovery completed.")


@api_v2_router.post("/recovery/reset", response_model=ActionStatusResponse)
def reset_account_with_recovery(
    payload: AccountRecoveryResetRequest,
    session: Session = Depends(get_session),
    request: Request = None,
) -> ActionStatusResponse:
    service = _build_auth_service(request)
    try:
        service.reset_password_with_recovery(session, code=payload.code, new_password=payload.new_password)
        session.commit()
    except AuthError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ActionStatusResponse(detail="Account recovery completed.")


@router.get("/api/v2/session/bootstrap", response_model=SessionBootstrapResponse)
def get_session_bootstrap(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SessionBootstrapResponse:
    service = _build_auth_service(request)
    try:
        response = _build_session_bootstrap_response(
            service=service,
            session=session,
            request=request,
            user=current_user,
        )
        session.commit()
    except AuthError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return response


@api_v2_router.get("/me", response_model=CurrentUserResponse)
def read_current_user_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CurrentUserResponse:
    return AuthService().get_current_user_profile(session, current_user, app=request.app)


@api_v2_router.patch("/me", response_model=CurrentUserResponse)
def update_current_user_profile(
    payload: CurrentUserUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CurrentUserResponse:
    service = AuthService()
    try:
        service.update_current_user_profile(
            session,
            user=current_user,
            payload=payload,
        )
        session.commit()
    except AuthError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return service.get_current_user_profile(session, current_user, app=request.app)


@api_v2_router.post("/change-password", response_model=CurrentUserResponse)
def change_current_user_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CurrentUserResponse:
    service = AuthService()
    try:
        service.change_password(session, user=current_user, payload=payload)
        session.commit()
        session.refresh(current_user)
        return service.get_current_user_profile(session, current_user, app=request.app)
    except InvalidCredentialsError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AuthError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_v2_router.post("/pin/verify", response_model=ActionStatusResponse)
def verify_sensitive_action_pin(
    payload: PinVerificationRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    request: Request = None,
) -> ActionStatusResponse:
    service = AuthService()
    try:
        service.verify_security_pin(
            session,
            user=current_user,
            pin=payload.pin,
            action_type=payload.action_type,
        )
        auth_session = getattr(request.state, "auth_session", None) if request is not None else None
        auth_session_id = getattr(auth_session, "id", None)
        if isinstance(auth_session_id, str) and auth_session_id:
            cache_backend = getattr(request.app.state, "cache_backend", None) if request is not None else None
            if cache_backend is not None:
                cache_backend.set(
                    f"auth:pin:{current_user.id}:{auth_session_id}:{payload.action_type}",
                    "1",
                    ttl_seconds=300,
                )
        session.commit()
    except SecurityCooldownError as exc:
        session.commit()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except InvalidCredentialsError as exc:
        session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AuthError as exc:
        session.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ActionStatusResponse(detail="Security PIN verified.")


router.include_router(api_v2_router)
