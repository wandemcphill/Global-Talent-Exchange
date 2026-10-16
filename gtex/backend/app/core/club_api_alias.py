"""Compatibility alias so /api/v2/clubs/* resolves to the /api/clubs/* handlers.

The shared frontend API contract (`shared/api_contract.json`) resolves every club
endpoint to its ``/api/v2/clubs/...`` canonical path, and the Flutter client rewrites
outgoing club requests accordingly. The club routers, however, are only mounted under
``/api/clubs`` (they predate the ``/api/v2`` alias convention and mix relative-prefix
and full-path route declarations, so they can't be dual-mounted cleanly).

Without this shim every club call from the app 404s with ``{"detail":"Not Found"}`` --
which surfaced in the UI as "Live club snapshot unavailable / Not Found". This ASGI
middleware rewrites the request path from ``/api/v2/clubs`` to ``/api/clubs`` before
routing, leaving all other paths untouched.
"""

from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send

_V2_PREFIX = "/api/v2/clubs"
_LEGACY_PREFIX = "/api/clubs"


class ClubApiV2AliasMiddleware:
    """Route ``/api/v2/clubs/*`` requests to the legacy ``/api/clubs/*`` handlers."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") == "http":
            path = scope.get("path", "")
            if path == _V2_PREFIX or path.startswith(_V2_PREFIX + "/"):
                new_path = _LEGACY_PREFIX + path[len(_V2_PREFIX):]
                scope = dict(scope)
                scope["path"] = new_path
                if scope.get("raw_path") is not None:
                    scope["raw_path"] = new_path.encode("latin-1")
        await self.app(scope, receive, send)
