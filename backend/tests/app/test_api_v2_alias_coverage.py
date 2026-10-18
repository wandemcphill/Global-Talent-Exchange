from __future__ import annotations

import pytest
from fastapi.routing import APIRoute

from app.modules import ensure_modules_loaded

VERSIONED_ROUTE_CASES = (
    ("GET", "/api/v2/auth/me"),
    ("POST", "/api/v2/auth/refresh"),
    ("GET", "/api/v2/kyc"),
    ("GET", "/api/v2/portfolio/clubs"),
    ("GET", "/api/v2/competitions/creator-league"),
    ("GET", "/api/v2/admin/treasury/settings"),
    ("GET", "/api/v2/admin/wallets/purchase-orders"),
    ("GET", "/api/v2/player-cards/watchlist"),
)


def test_full_app_routes_are_flattened_after_module_hydration(mounted_app) -> None:
    ensure_modules_loaded(mounted_app)

    included_routers = [route for route in mounted_app.router.routes if type(route).__name__ == "_IncludedRouter"]
    assert not included_routers, included_routers


@pytest.mark.parametrize(("method", "path"), VERSIONED_ROUTE_CASES)
def test_full_app_registers_expected_versioned_routes(mounted_app, method: str, path: str) -> None:
    ensure_modules_loaded(mounted_app)

    matches = [
        route
        for route in mounted_app.router.routes
        if isinstance(route, APIRoute) and route.path == path and method in (route.methods or ())
    ]
    assert matches, f"missing {method} {path} from app.router.routes"


@pytest.mark.parametrize("path", ("/api/v2/players/markets",))
def test_static_versioned_alias_is_not_shadowed_by_parameterized_route(mounted_app, path: str) -> None:
    from starlette.routing import Match

    scope = {"type": "http", "path": path, "method": "GET"}
    for route in mounted_app.router.routes:
        match, _ = route.matches(dict(scope))
        if match is Match.FULL:
            assert route.path == path
            return
    pytest.fail(f"No route matched GET {path}")
