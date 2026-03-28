from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.security import TokenError, decode_access_token
from app.db import get_session as get_database_session
from app.models.user import User, UserRole
from app.services.runtime_control_service import RuntimeControlService

bearer_scheme = HTTPBearer(auto_error=False)


def get_session() -> Iterator[Session]:
    yield from get_database_session()


def _resolve_authenticated_user(
    *,
    credentials: HTTPAuthorizationCredentials | None,
    session: Session,
    allow_missing_credentials: bool,
    request: Request | None = None,
) -> User | None:
    if credentials is None:
        if allow_missing_credentials:
            return None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is missing a subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = session.get(User, subject)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The authenticated user could not be loaded.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from app.access_control.service import AccessControlService

    AccessControlService(session).bind_user_access_context(user)
    if request is not None:
        control = RuntimeControlService(request.app).get_account_control(user_id=user.id)
        if control is not None and control.freeze_login:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=control.reason or "Account access is temporarily frozen.",
            )
    return user


def _enforce_runtime_scope(
    *,
    request: Request,
    user: User,
    scope: str,
    detail: str,
) -> User:
    control = RuntimeControlService(request.app).get_account_control(user_id=user.id)
    if control is None:
        return user
    if scope == "wallet" and control.freeze_wallet:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=control.reason or detail)
    if scope == "matches" and control.freeze_matches:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=control.reason or detail)
    if scope == "social" and control.freeze_social:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=control.reason or detail)
    return user


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    resolved_user = _resolve_authenticated_user(
        credentials=credentials,
        session=session,
        allow_missing_credentials=False,
        request=request,
    )
    assert resolved_user is not None
    return resolved_user


def get_optional_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User | None:
    return _resolve_authenticated_user(
        credentials=credentials,
        session=session,
        allow_missing_credentials=True,
        request=request,
    )


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required for this action.",
        )
    return current_user


def get_current_wallet_user(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> User:
    return _enforce_runtime_scope(
        request=request,
        user=current_user,
        scope="wallet",
        detail="Wallet access is temporarily frozen for this account.",
    )


def get_current_match_user(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> User:
    return _enforce_runtime_scope(
        request=request,
        user=current_user,
        scope="matches",
        detail="Match access is temporarily frozen for this account.",
    )


def get_current_social_user(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> User:
    return _enforce_runtime_scope(
        request=request,
        user=current_user,
        scope="social",
        detail="Social access is temporarily frozen for this account.",
    )



def get_current_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access is required for this action.",
        )
    return current_user
