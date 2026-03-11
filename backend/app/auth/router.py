from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_session
from backend.app.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from backend.app.auth.service import AuthError, AuthService, DuplicateUserError, InvalidCredentialsError
from backend.app.users.schemas import UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterRequest, session: Session = Depends(get_session)) -> TokenResponse:
    service = AuthService()
    try:
        user = service.register_user(
            session,
            email=payload.email,
            username=payload.username,
            password=payload.password,
            display_name=payload.display_name,
        )
        token, expires_in = service.issue_access_token(user)
        session.commit()
        session.refresh(user)
    except DuplicateUserError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return TokenResponse(access_token=token, expires_in=expires_in, user=UserPublic.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login_user(payload: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    service = AuthService()
    try:
        user = service.authenticate_user(session, email=payload.email, password=payload.password)
        token, expires_in = service.issue_access_token(user)
        session.commit()
        session.refresh(user)
    except InvalidCredentialsError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AuthError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return TokenResponse(access_token=token, expires_in=expires_in, user=UserPublic.model_validate(user))
