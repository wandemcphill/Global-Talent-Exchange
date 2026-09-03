"""End-to-end proof that the versioned admin surface is guarded.

`AuthEnforcementMiddleware` protects by path prefix. Its list carried
`/api/v2/profile`, `/api/v2/session`, and `/api/v2/wallet` but no
`/api/v2/admin`, while `register_versioned_route_aliases` clones every route
onto its `/api/v2/...` alias at startup. Every canonical `/api/v2/admin/...`
path therefore bypassed the middleware.

Most admin handlers survived on their own `Depends(get_current_admin)`.
`GET /api/v2/admin/access/permissions` does not have one — `list_permission_catalog`
takes no parameters at all — so it served the full admin permission and
capability catalogue to unauthenticated callers.

The unit-level checks live in ``test_auth_middleware.py``. These exercise the
real app so a future refactor cannot make ``_requires_auth`` pass while the
wired middleware still lets the request through, and so that blocking
anonymous callers is not confused with breaking real admins.
"""

from __future__ import annotations

import pytest

ADMIN_PATH_PAIRS = (
    ("/api/admin/access/permissions", "/api/v2/admin/access/permissions"),
    ("/api/admin/payment-rails", "/api/v2/admin/payment-rails"),
    ("/api/admin/treasury", "/api/v2/admin/treasury"),
)


@pytest.mark.parametrize(("legacy_path", "versioned_path"), ADMIN_PATH_PAIRS)
def test_admin_routes_reject_anonymous_callers_on_both_paths(client, legacy_path: str, versioned_path: str) -> None:
    assert client.get(legacy_path).status_code == 401
    assert client.get(versioned_path).status_code == 401


def test_versioned_permission_catalog_is_not_readable_anonymously(client) -> None:
    """The one route with no handler-level guard at all.

    Before the fix this returned 200 with the admin permission catalogue.
    """
    response = client.get("/api/v2/admin/access/permissions")
    assert response.status_code == 401
    assert "permissions" not in response.text


def test_authenticated_admin_still_reaches_the_versioned_admin_surface(client, bootstrap_admin_headers) -> None:
    """Blocking anonymous callers must not block real admins.

    Without this, tightening the prefix list to 401-everything would look like
    a passing security fix while breaking every admin screen.
    """
    response = client.get("/api/v2/admin/access/permissions", headers=bootstrap_admin_headers)
    assert response.status_code == 200, response.text
    # Responses are envelope-wrapped by _install_envelope_middleware.
    assert response.json()["data"]["permissions"]
