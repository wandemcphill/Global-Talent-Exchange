from __future__ import annotations

import logging

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


@legacy_router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: RegisterRequest,
    session: Session = Depends(get_session),
    request: Request = None,
) -> TokenResponse:
    service = _build_auth_service(request)
    analytics = AnalyticsService()
    confirmation_code: str | None = None
    try:
        analytics.track_event(session, name="signup_started", user_id=None, metadata={"email": payload.email})
        if not payload.is_over_18:
            analytics.track_event(session, name="underage_signup_blocked", user_id=None, metadata={"email": payload.email})
            raise AuthError("You must be at least 18 years old to sign up.")
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
        )
        confirmation_code = service.prepare_signup_confirmation(session, user=user)
        analytics.track_event(session, name="signup_completed", user_id=user.id, metadata={})
        token, expires_in = service.issue_access_token(user, session=session)
        session.commit()
        session.refresh(user)
    except DuplicateUserError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    else:
        if confirmation_code is not None:
            try:
                service.send_signup_confirmation_email(user=user, confirmation_code=confirmation_code)
            except Exception as exc:
                _log_email_dispatch_exception(flow="signup_confirmation", recipient=user.email, exc=exc)

    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=service.build_user_public(session, user),
        permissions=service.resolve_user_permissions(request, user, session=session) if request is not None else [],
        landing_route=service.resolve_landing_route(user, session=session),
    )


@legacy_router.post("/login", response_model=TokenResponse)
def login_user(
    payload: LoginRequest,
    session: Session = Depends(get_session),
    request: Request = None,
) -> TokenResponse:
    service = _build_auth_service(request)
    analytics = AnalyticsService()
    try:
        user = service.authenticate_user(session, email=payload.email, password=payload.password)
        analytics.track_event(session, name="login_success", user_id=user.id, metadata={})
        token, expires_in = service.issue_access_token(user, session=session)
        session.commit()
        session.refresh(user)
    except InvalidCredentialsError as exc:
        analytics.track_event(session, name="login_failure", user_id=None, metadata={"email": payload.email})
        session.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AuthError as exc:
        analytics.track_event(session, name="login_failure", user_id=None, metadata={"email": payload.email})
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=service.build_user_public(session, user),
        permissions=service.resolve_user_permissions(request, user, session=session) if request is not None else [],
        landing_route=service.resolve_landing_route(user, session=session),
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
