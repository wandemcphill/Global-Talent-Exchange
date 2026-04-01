from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.dependencies import _resolve_authenticated_user


PROTECTED_PATH_PREFIXES = (
    "/api/admin",
    "/api/session",
    "/api/wallets",
    "/wallets",
    "/policies/me",
    "/users/me",
    "/internal",
)
PROTECTED_EXACT_PATHS = frozenset(
    {
        "/api/auth/me",
        "/api/auth/logout",
        "/api/auth/change-password",
    }
)


class AuthEnforcementMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method.upper() == "OPTIONS":
            return await call_next(request)
        if not self._requires_auth(request.url.path):
            return await call_next(request)

        authorization = request.headers.get("authorization", "").strip()
        if not authorization:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authentication credentials were not provided."},
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            scheme, token = authorization.split(" ", maxsplit=1)
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authentication credentials were not provided."},
                headers={"WWW-Authenticate": "Bearer"},
            )
        credentials = HTTPAuthorizationCredentials(scheme=scheme, credentials=token.strip())
        with request.app.state.session_factory() as session:
            try:
                _resolve_authenticated_user(
                    credentials=credentials,
                    session=session,
                    allow_missing_credentials=False,
                    request=request,
                )
            except Exception as exc:
                status_code = getattr(exc, "status_code", status.HTTP_401_UNAUTHORIZED)
                detail = getattr(exc, "detail", "Authentication failed.")
                headers = getattr(exc, "headers", {"WWW-Authenticate": "Bearer"})
                return JSONResponse(
                    status_code=status_code,
                    content={"detail": detail},
                    headers=headers,
                )
        return await call_next(request)

    @staticmethod
    def _requires_auth(path: str) -> bool:
        if path in PROTECTED_EXACT_PATHS:
            return True
        return any(path.startswith(prefix) for prefix in PROTECTED_PATH_PREFIXES)
