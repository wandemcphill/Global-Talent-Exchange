from __future__ import annotations

import logging
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.analytics.service import AnalyticsService
from app.auth.dependencies import get_current_user, get_session
from app.auth.schemas import (
    AccountRecoveryRequest,
    AccountRecoveryResetRequest,
    ActionStatusResponse,
    ChangePasswordRequest,
    ConfirmEmailRequest,
    CurrentUserResponse,
    CurrentUserUpdateRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.auth.service import AuthError, AuthService, DuplicateUserError, InvalidCredentialsError
from app.models.user import User
from app.wallets.service import WalletService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])
legacy_router = APIRouter(prefix="/auth")
api_router = APIRouter(prefix="/api/auth")


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
    token: str,
    session_id: str,
    expires_in: int,
) -> TokenResponse:
    user_public_started_at = perf_counter()
    user_public = service.build_user_public(session, user)
    telemetry.mark("service.build_user_public_ms", user_public_started_at)
    permissions_started_at = perf_counter()
    permissions = service.resolve_user_permissions(request, user, session=session) if request is not None else []
    telemetry.mark("service.resolve_permissions_ms", permissions_started_at)
    landing_route_started_at = perf_counter()
    landing_route = service.resolve_landing_route(user, session=session)
    telemetry.mark("service.resolve_landing_route_ms", landing_route_started_at)
    return TokenResponse(
        access_token=token,
        session_id=session_id,
        expires_in=expires_in,
        user=user_public,
        permissions=permissions,
        landing_route=landing_route,
    )


@legacy_router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: RegisterRequest,
    session: Session = Depends(get_session),
    request: Request = None,
) -> TokenResponse:
    service = _build_auth_service(request)
    analytics = AnalyticsService()
    confirmation_code: str | None = None
    telemetry = _AuthRouteTelemetry("register")
    user: User | None = None
    telemetry.log_entry(
        method=request.method if request is not None else "POST",
        path=str(request.url.path) if request is not None else "/auth/register",
        modules_hydrated=getattr(request.app.state, "modules_hydrated", None) if request is not None else None,
    )
    try:
        analytics_started_at = perf_counter()
        analytics.track_event(session, name="signup_started", user_id=None, metadata={"email": payload.email})
        telemetry.mark("analytics.signup_started_ms", analytics_started_at)
        if not payload.is_over_18:
            underage_started_at = perf_counter()
            analytics.track_event(session, name="underage_signup_blocked", user_id=None, metadata={"email": payload.email})
            telemetry.mark("analytics.underage_signup_blocked_ms", underage_started_at)
            raise AuthError("You must be at least 18 years old to sign up.")
        register_started_at = perf_counter()
        user = service.register_user(
            session,
            email=payload.email,
            full_name=payload.full_name,
            phone_number=payload.phone_number,
            is_over_18=payload.is_over_18,
            region_code=payload.region_code,
            username=payload.username,
            password=payload.password,
            display_name=payload.full_name,
            timing_recorder=telemetry.capture,
        )
        telemetry.mark("service.register_user_ms", register_started_at)
        confirmation_started_at = perf_counter()
        confirmation_code = service.prepare_signup_confirmation(session, user=user)
        telemetry.mark("service.prepare_signup_confirmation_ms", confirmation_started_at)
        analytics_completed_started_at = perf_counter()
        analytics.track_event(session, name="signup_completed", user_id=user.id, metadata={})
        telemetry.mark("analytics.signup_completed_ms", analytics_completed_started_at)
        token_started_at = perf_counter()
        token, expires_in, session_id = service.issue_access_token_with_session(
            user,
            session=session,
            timing_recorder=telemetry.capture,
        )
        telemetry.mark("service.issue_access_token_ms", token_started_at)
        commit_started_at = perf_counter()
        session.commit()
        telemetry.mark("db.commit_ms", commit_started_at)
        refresh_started_at = perf_counter()
        session.refresh(user)
        telemetry.mark("db.refresh_user_ms", refresh_started_at)
    except DuplicateUserError as exc:
        _rollback_with_telemetry(session, telemetry)
        telemetry.log_failure(status_code=status.HTTP_409_CONFLICT, user_id=user.id if user is not None else None, error=str(exc))
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthError as exc:
        _rollback_with_telemetry(session, telemetry)
        telemetry.log_failure(status_code=status.HTTP_400_BAD_REQUEST, user_id=user.id if user is not None else None, error=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        _rollback_with_telemetry(session, telemetry)
        telemetry.log_failure(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, user_id=user.id if user is not None else None, error=str(exc))
        raise
    else:
        if confirmation_code is not None:
            try:
                email_started_at = perf_counter()
                service.send_signup_confirmation_email(user=user, confirmation_code=confirmation_code)
                telemetry.mark("email.signup_confirmation_ms", email_started_at)
            except Exception as exc:
                _log_email_dispatch_exception(flow="signup_confirmation", recipient=user.email, exc=exc)
        telemetry.log_success(status_code=status.HTTP_201_CREATED, user_id=user.id)

    return _build_token_response(
        service=service,
        session=session,
        request=request,
        telemetry=telemetry,
        user=user,
        token=token,
        session_id=session_id,
        expires_in=expires_in,
    )


@legacy_router.post("/login", response_model=TokenResponse)
def login_user(
    payload: LoginRequest,
    session: Session = Depends(get_session),
    request: Request = None,
) -> TokenResponse:
    service = _build_auth_service(request)
    analytics = AnalyticsService()
    telemetry = _AuthRouteTelemetry("login")
    user: User | None = None
    telemetry.log_entry(
        method=request.method if request is not None else "POST",
        path=str(request.url.path) if request is not None else "/auth/login",
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
        token, expires_in, session_id = service.issue_access_token_with_session(
            user,
            session=session,
            timing_recorder=telemetry.capture,
        )
        telemetry.mark("service.issue_access_token_ms", token_started_at)
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
        telemetry.log_failure(status_code=status.HTTP_401_UNAUTHORIZED, user_id=None, error=str(exc))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AuthError as exc:
        analytics_failure_started_at = perf_counter()
        analytics.track_event(session, name="login_failure", user_id=None, metadata={"email": payload.email})
        telemetry.mark("analytics.login_failure_ms", analytics_failure_started_at)
        _rollback_with_telemetry(session, telemetry)
        telemetry.log_failure(status_code=status.HTTP_400_BAD_REQUEST, user_id=user.id if user is not None else None, error=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        _rollback_with_telemetry(session, telemetry)
        telemetry.log_failure(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, user_id=user.id if user is not None else None, error=str(exc))
        raise
    telemetry.log_success(status_code=status.HTTP_200_OK, user_id=user.id)

    return _build_token_response(
        service=service,
        session=session,
        request=request,
        telemetry=telemetry,
        user=user,
        token=token,
        session_id=session_id,
        expires_in=expires_in,
    )


@legacy_router.post("/confirm-email", response_model=ActionStatusResponse)
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


@legacy_router.post("/recovery/request", response_model=ActionStatusResponse)
def request_account_recovery(
    payload: AccountRecoveryRequest,
    session: Session = Depends(get_session),
    request: Request = None,
) -> ActionStatusResponse:
    service = _build_auth_service(request)
    user = None
    recovery_code = None
    try:
        user, recovery_code = service.prepare_account_recovery(session, email=payload.email)
        session.commit()
    except AuthError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if user is not None and recovery_code is not None:
        try:
            service.send_account_recovery_email(user=user, recovery_code=recovery_code)
        except Exception as exc:
            _log_email_dispatch_exception(flow="account_recovery", recipient=user.email, exc=exc)

    return ActionStatusResponse(detail="If an account exists for that email, recovery instructions have been sent.")


@legacy_router.post("/recovery/reset", response_model=ActionStatusResponse)
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


@api_router.get("/me", response_model=CurrentUserResponse)
def read_current_user_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CurrentUserResponse:
    return AuthService().get_current_user_profile(session, current_user, app=request.app)


@api_router.patch("/me", response_model=CurrentUserResponse)
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


@api_router.post("/change-password", response_model=CurrentUserResponse)
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


router.include_router(legacy_router)
router.include_router(api_router)
