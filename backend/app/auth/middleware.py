from __future__ import annotations

from fastapi import Request, status
from fastapi.security import HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.dependencies import _resolve_authenticated_user
from app.core.api_contract import build_versioned_path
from app.core.errors import error_response

# Declare protection against the path a router actually mounts. The versioned
# `/api/v2/...` alias of each entry is derived below, never hand-listed.
#
# `register_versioned_route_aliases` clones every route onto its `/api/v2/...`
# alias at startup, so each protected surface is reachable under at least two
# paths. Enumerating those by hand is what produced the bug this derivation
# fixes: v2 entries were added for `profile`, `session`, and `wallet` but not
# for `admin`, leaving all 321 canonical `/api/v2/admin/...` paths outside the
# middleware. Most survived on their handler's `Depends(get_current_admin)`;
# `GET /api/v2/admin/access/permissions` has no handler guard and served the
# admin permission catalogue to unauthenticated callers, while the legacy
# `/api/admin/access/permissions` correctly returned 401.
#
# Deriving with `build_versioned_path` — the same function the alias registrar
# uses — means the two cannot disagree again.
_PROTECTED_PATH_PREFIX_SOURCES = (
    "/api/admin",
    "/api/profile",
    "/api/session",
    "/api/wallet",
    "/api/wallets",
    "/wallets",
    "/wallet",
    "/policies/me",
    "/users/me",
    "/internal",
)
_PROTECTED_EXACT_PATH_SOURCES = (
    "/api/auth/me",
    "/api/auth/logout",
    "/api/auth/change-password",
)


def _with_versioned_aliases(paths: tuple[str, ...]) -> frozenset[str]:
    """Expand each path to itself plus its `/api/v2/...` alias."""
    expanded: set[str] = set()
    for path in paths:
        expanded.add(path)
        versioned = build_versioned_path(path)
        if versioned is not None:
            expanded.add(versioned)
    return frozenset(expanded)


PROTECTED_PATH_PREFIXES = tuple(sorted(_with_versioned_aliases(_PROTECTED_PATH_PREFIX_SOURCES)))
PROTECTED_EXACT_PATHS = _with_versioned_aliases(_PROTECTED_EXACT_PATH_SOURCES)


class AuthEnforcementMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method.upper() == "OPTIONS":
            return await call_next(request)
        if not self._requires_auth(request.url.path):
            return await call_next(request)

        authorization = request.headers.get("authorization", "").strip()
        if not authorization:
            return error_response(
                status.HTTP_401_UNAUTHORIZED,
                message="Authentication credentials were not provided.",
                code="unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            scheme, token = authorization.split(" ", maxsplit=1)
        except ValueError:
            return error_response(
                status.HTTP_401_UNAUTHORIZED,
                message="Authentication credentials were not provided.",
                code="unauthorized",
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
                return error_response(
                    status_code,
                    message=str(detail),
                    code="unauthorized" if status_code == status.HTTP_401_UNAUTHORIZED else f"http_{status_code}",
                    headers=headers,
                )
        return await call_next(request)

    @staticmethod
    def _requires_auth(path: str) -> bool:
        if path in PROTECTED_EXACT_PATHS:
            return True
        return any(_path_matches_prefix(path, prefix) for prefix in PROTECTED_PATH_PREFIXES)


def _path_matches_prefix(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")
