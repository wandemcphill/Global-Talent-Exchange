from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import logging

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.security import TokenError, decode_access_token
from app.db import get_session as get_database_session
from app.models.auth_session import AuthSession
from app.models.user import PublicAccountType, User, UserRole
from app.services.runtime_control_service import RuntimeControlService

bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)
_AUTH_SESSION_TOUCH_INTERVAL_SECONDS = 60


@dataclass(frozen=True)
class IdentityContext:
    user_id: str
    session_id: str
    device_id: str


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
        logger.warning("auth.request.failed reason=missing_credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        logger.warning("auth.request.failed reason=invalid_access_token error=%s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        logger.warning("auth.request.failed reason=missing_subject")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is missing a subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_session_id = payload.get("sid")
    if not isinstance(token_session_id, str) or not token_session_id:
        logger.warning("auth.request.failed user_id=%s reason=missing_session_claim", subject)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is missing a session identifier.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = session.get(User, subject)
    if user is None or not user.is_active:
        logger.warning("auth.request.failed user_id=%s session_id=%s reason=user_not_found", subject, token_session_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The authenticated user could not be loaded.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    auth_session = session.get(AuthSession, token_session_id)
    if auth_session is None or auth_session.user_id != user.id:
        logger.warning(
            "auth.request.failed user_id=%s session_id=%s reason=session_not_found", user.id, token_session_id
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated session is invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if auth_session.revoked_at is not None:
        logger.warning("auth.request.failed user_id=%s session_id=%s reason=session_revoked", user.id, token_session_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated session has been revoked.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    expires_at = _as_utc_datetime(auth_session.expires_at)
    if expires_at <= _utcnow():
        logger.warning("auth.request.failed user_id=%s session_id=%s reason=session_expired", user.id, token_session_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated session has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if _should_touch_auth_session(auth_session):
        auth_session.last_used_at = _utcnow()

    from app.access_control.service import AccessControlService

    AccessControlService(session).bind_user_access_context(user)
    if request is not None:
        request.state.auth_token_payload = payload
        request.state.auth_session = auth_session
        request.state.authenticated_user_id = user.id
        request.state.authenticated_session_id = auth_session.id
        control = RuntimeControlService(request.app).get_account_control(user_id=user.id)
        if control is not None and control.freeze_login:
            logger.warning(
                "auth.request.failed user_id=%s session_id=%s reason=login_frozen", user.id, token_session_id
            )
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


def _enforce_account_type(user: User, allowed: set[PublicAccountType], detail: str) -> User:
    if user.account_type not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
    return user


def get_current_trader_user(
    current_user: User = Depends(get_current_wallet_user),
) -> User:
    return _enforce_account_type(
        current_user,
        {PublicAccountType.COIN_TRADER},
        "Coin trader account access is required for this action.",
    )


def get_current_football_user(
    current_user: User = Depends(get_current_user),
) -> User:
    return _enforce_account_type(
        current_user,
        {PublicAccountType.USER},
        "Football user account access is required for this action.",
    )


def get_current_trading_user(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_wallet_user),
) -> User:
    del request
    _enforce_account_type(
        current_user,
        {PublicAccountType.USER},
        "Football player trading is only available to football user accounts.",
    )
    from app.risk_ops_engine.service import RiskActionBlockedError, RiskOpsService
    from app.wallets.funding_service import WalletFundingError, WalletFundingService

    try:
        RiskOpsService(session).assert_trading_allowed(current_user.id)
        WalletFundingService().assert_verified_for_trading(session, current_user)
    except RiskActionBlockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except WalletFundingError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return current_user


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


def _raise_missing_identity() -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing identity context",
    )


def _should_touch_auth_session(auth_session: AuthSession) -> bool:
    last_used_at = _as_utc_datetime(auth_session.last_used_at)
    return (_utcnow() - last_used_at).total_seconds() >= _AUTH_SESSION_TOUCH_INTERVAL_SECONDS


def _resolve_identity_context(
    *,
    request: Request,
    current_user: User,
    credentials: HTTPAuthorizationCredentials | None,
    x_user_id: str | None,
    x_session_id: str | None,
    x_device_id: str | None,
) -> IdentityContext:
    if not x_user_id or not x_session_id or not x_device_id:
        _raise_missing_identity()
    token_payload = getattr(request.state, "auth_token_payload", None)
    if not isinstance(token_payload, dict) and credentials is not None:
        try:
            token_payload = decode_access_token(credentials.credentials)
        except TokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
    if not isinstance(token_payload, dict):
        _raise_missing_identity()
    token_session_id = token_payload.get("sid")
    if not isinstance(token_session_id, str) or not token_session_id:
        _raise_missing_identity()
    if x_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identity header user does not match authenticated user.",
        )
    if x_session_id != token_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identity header session does not match authenticated session.",
        )
    return IdentityContext(
        user_id=x_user_id,
        session_id=x_session_id,
        device_id=x_device_id,
    )


def get_identity_context(
    request: Request,
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
    x_device_id: str | None = Header(default=None, alias="X-Device-Id"),
) -> IdentityContext:
    return _resolve_identity_context(
        request=request,
        current_user=current_user,
        credentials=credentials,
        x_user_id=x_user_id,
        x_session_id=x_session_id,
        x_device_id=x_device_id,
    )


def get_optional_identity_context(
    request: Request,
    current_user: User | None = Depends(get_optional_current_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
    x_device_id: str | None = Header(default=None, alias="X-Device-Id"),
) -> IdentityContext | None:
    has_identity_headers = any(value is not None for value in (x_user_id, x_session_id))
    if not has_identity_headers:
        return None
    if current_user is None:
        _raise_missing_identity()
    return _resolve_identity_context(
        request=request,
        current_user=current_user,
        credentials=credentials,
        x_user_id=x_user_id,
        x_session_id=x_session_id,
        x_device_id=x_device_id,
    )


def require_identity(identity: IdentityContext = Depends(get_identity_context)) -> IdentityContext:
    if not identity.user_id or not identity.session_id:
        _raise_missing_identity()
    return identity


def get_current_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access is required for this action.",
        )
    return current_user


def _utcnow():
    from app.models.base import utcnow

    return utcnow()


def _as_utc_datetime(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=_utcnow().tzinfo)
    return value.astimezone(_utcnow().tzinfo)
