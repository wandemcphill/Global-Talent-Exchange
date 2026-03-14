from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, get_session
from backend.app.auth.schemas import (
    ChangePasswordRequest,
    CurrentUserResponse,
    CurrentUserUpdateRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from backend.app.auth.service import AuthError, AuthService, DuplicateUserError, InvalidCredentialsError
from backend.app.analytics.service import AnalyticsService
from backend.app.models.user import User
from backend.app.users.schemas import UserPublic
from backend.app.wallets.service import WalletService

router = APIRouter(tags=["auth"])
legacy_router = APIRouter(prefix="/auth")
api_router = APIRouter(prefix="/api/auth")


def _build_auth_service(request: Request | None) -> AuthService:
    if request is not None and hasattr(request.app.state, "event_publisher"):
        return AuthService(wallet_service=WalletService(event_publisher=request.app.state.event_publisher))
    return AuthService()


@legacy_router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: RegisterRequest,
    session: Session = Depends(get_session),
    request: Request = None,
) -> TokenResponse:
    service = _build_auth_service(request)
    analytics = AnalyticsService()
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
            username=payload.username,
            password=payload.password,
            display_name=payload.full_name,
        )
        analytics.track_event(session, name="signup_completed", user_id=user.id, metadata={})
        token, expires_in = service.issue_access_token(user)
        session.commit()
        session.refresh(user)
    except DuplicateUserError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserPublic.model_validate(user),
        permissions=service.resolve_user_permissions(request, user) if request is not None else [],
        landing_route=service.resolve_landing_route(user),
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
        token, expires_in = service.issue_access_token(user)
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
        user=UserPublic.model_validate(user),
        permissions=service.resolve_user_permissions(request, user) if request is not None else [],
        landing_route=service.resolve_landing_route(user),
    )


@api_router.get("/me", response_model=CurrentUserResponse)
def read_current_user_profile(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CurrentUserResponse:
    return AuthService().get_current_user_profile(session, current_user)


@api_router.patch("/me", response_model=CurrentUserResponse)
def update_current_user_profile(
    payload: CurrentUserUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CurrentUserResponse:
    service = AuthService()
    try:
        profile = service.update_current_user_profile(
            session,
            user=current_user,
            payload=payload,
        )
        session.commit()
    except AuthError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return profile


@api_router.post("/change-password", response_model=CurrentUserResponse)
def change_current_user_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CurrentUserResponse:
    service = AuthService()
    try:
        service.change_password(session, user=current_user, payload=payload)
        session.commit()
        session.refresh(current_user)
        return service.get_current_user_profile(session, current_user)
    except InvalidCredentialsError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AuthError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


router.include_router(legacy_router)
router.include_router(api_router)
