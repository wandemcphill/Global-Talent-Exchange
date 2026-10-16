"""Auth boundary for the player-lifecycle segment router.

Every mutation on this router (contracts, injuries, transfer bids, regen
lifecycle) used to be reachable with no credentials at all: the router
declares no dependencies, none of the POST handlers took an auth dependency,
and ``/api/transfers`` and ``/api/players`` are not in
``AuthEnforcementMiddleware.PROTECTED_PATH_PREFIXES``.

That let an anonymous caller enumerate pending bids through the (public) list
endpoint and then accept or reject them - and ``accept_bid`` terminates the
selling club's contract and writes a new ``PlayerContract`` for the buying
club, i.e. it moves a tradeable player between clubs.

These tests pin authentication on the mutation surface. They deliberately
assert "not 401" rather than a specific success code for the authenticated
call: the point is that the request gets past the auth boundary and on to
domain validation, not that these particular fixture-less ids resolve.
"""

from __future__ import annotations

import pytest

# (method, path, body) for every mutation on the player-lifecycle router.
LIFECYCLE_MUTATIONS: list[tuple[str, str, dict[str, object]]] = [
    ("POST", "/api/players/p-auth/contracts", {}),
    ("POST", "/api/players/p-auth/contracts/c-auth/renew", {}),
    ("POST", "/api/players/p-auth/injuries", {}),
    ("POST", "/api/players/p-auth/injuries/i-auth/recover", {}),
    ("POST", "/api/transfers/windows/w-auth/bids", {}),
    ("POST", "/api/transfers/windows/w-auth/bids/b-auth/accept", {}),
    ("POST", "/api/transfers/windows/w-auth/bids/b-auth/reject", {}),
    ("POST", "/api/players/p-auth/regen/contract-offers/quote", {}),
    ("POST", "/api/players/p-auth/regen/transfer-listing", {}),
    ("POST", "/api/players/p-auth/regen/big-club-approaches", {}),
    ("POST", "/api/players/p-auth/regen/pressure-resolution", {}),
    ("POST", "/api/players/p-auth/regen/special-training", {}),
    ("POST", "/api/transfers/windows/w-auth/players/p-auth/resolve-regen-bid", {}),
]


@pytest.mark.parametrize(("method", "path", "body"), LIFECYCLE_MUTATIONS)
def test_player_lifecycle_mutations_reject_anonymous_callers(
    client, method: str, path: str, body: dict[str, object]
) -> None:
    response = client.request(method, path, json=body)
    assert response.status_code == 401, f"{method} {path} -> {response.status_code}: {response.text}"
    assert response.json()["code"] == "unauthorized"


@pytest.fixture(scope="module")
def lifecycle_auth_headers(client, app_session_factory) -> dict[str, str]:
    """One signed-in user reused across every case.

    Signing up per-parametrised-case trips the auth rate limiter, which would
    make this suite fail for a reason unrelated to what it is testing.
    """
    del app_session_factory
    from uuid import uuid4

    from tests.support.secrets import TEST_PASSWORD
    from tests.support.signup_payloads import user_signup_payload

    suffix = f"lifecycle-auth-{uuid4().hex[:8]}"
    response = client.post(
        "/auth/signup/user",
        json=user_signup_payload(
            email=f"{suffix}@example.com",
            username=suffix.replace("-", "_"),
            password=TEST_PASSWORD,
            full_name="Lifecycle Auth Boundary",
        ),
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.parametrize(("method", "path", "body"), LIFECYCLE_MUTATIONS)
def test_player_lifecycle_mutations_pass_auth_for_signed_in_callers(
    client, lifecycle_auth_headers, method: str, path: str, body: dict[str, object]
) -> None:
    response = client.request(method, path, json=body, headers=lifecycle_auth_headers)
    # Authenticated callers must clear the auth boundary. They then hit normal
    # request/domain validation (422/404) for these synthetic ids.
    assert response.status_code != 401, f"{method} {path} -> {response.text}"
