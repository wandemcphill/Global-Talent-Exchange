"""Guards against `live_matches.router.stream_unity_spatial_match` returning.

`register_domain_modules` (app/core/module.py) treats any route collision on
a path starting with `/api/` as non-fatal: whichever module registers first
is kept, and any later module's route at the same (path, methods)
fingerprint is silently dropped — no error, no warning visible outside DEBUG
logs.

`live_matches/router.py` and `api_v1/router.py` both declared
`WEBSOCKET /api/v2/ws/match/{match_id}`. `live_matches` is in
`EAGER_MODULE_NAMES` and registers at startup; `api_v1` is lazy and registers
on first request, so registration order deterministically favoured
`live_matches`'s `stream_unity_spatial_match`. `api_v1`'s
`stream_match_commentary` — the correct owner: it branches on `?format=unity`
to serve both plain commentary and the Unity spatial bridge, with delivery
deduplication and metrics `stream_unity_spatial_match` lacked — stayed in
source, reviewable and importable, but was dead code at runtime. Its own test
suite failed with "Unity live access token is required." on plain (non-unity)
connections, because the wrong handler was answering.

This is deliberately scoped to that one path rather than a blanket
"no router may duplicate any other router's route" assertion. `with_api_alias`
modules (see `_with_api_alias` in app/modules.py) legitimately register the
same handler under `/`, `/api/...`, and `/api/v2/...` — and
`register_versioned_route_aliases` then independently derives its own
`/api/v2/...` alias from the bare and `/api/...` forms, which frequently
duplicates the module's own third registration. That produces hundreds of
route-table duplicates across the app, but every one of them still dispatches
to the *same* endpoint function, so it is wasteful rather than wrong. Fixing
that pattern app-wide is a distinct, much larger change than the collision
this file guards, which was two *different* implementations answering the
same request.
"""

from __future__ import annotations


def test_versioned_match_websocket_is_served_by_the_api_v1_router(mounted_app, mounted_app_client) -> None:
    # /api/players is outside CORE_BOOT_PATHS and LAZY_HYDRATION_BYPASS_PREFIXES,
    # so this forces the lazy api_v1 module to register alongside the eager ones.
    mounted_app_client.get("/api/players")
    assert mounted_app.state.modules_hydrated is True

    matches = [
        route for route in mounted_app.router.routes if getattr(route, "path", None) == "/api/v2/ws/match/{match_id}"
    ]
    assert len(matches) == 1, matches
    endpoint = matches[0].endpoint
    assert endpoint.__module__ == "app.api_v1.router"
    assert endpoint.__qualname__ == "stream_match_commentary"
