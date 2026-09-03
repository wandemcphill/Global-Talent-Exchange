"""Auth boundary for the player-agency router.

``evaluate_contract_decision`` and ``evaluate_transfer_decision`` had no auth
dependency at all: the router declares no dependencies, neither POST handler
took one, and ``/api/players`` is not in
``AuthEnforcementMiddleware.PROTECTED_PATH_PREFIXES``.

Both call into ``PlayerAgencyService`` -- the same evaluation engine
``player_lifecycle_service.py`` and ``transfer_market/service.py`` use for
real, authenticated contract and transfer offers -- and it mutates the
player's persistent agent state (``contract_stance``, cooldown timers,
``transfer_appetite``, the cached decision) as a side effect of evaluating
the offer. Currently that mutation is only ``session.flush()``-ed, never
committed by any caller in this call chain, so it does not survive past the
request today. It is still worth closing: a fabricated offer submitted by
anyone should not be able to reach that write path at all, committed or not,
and the missing commit is an unrelated bug that could be "fixed" without
anyone noticing the auth gap it would then expose.

These tests pin authentication on both mutation endpoints. They deliberately
assert "not 401" rather than a specific success code for the authenticated
call: the point is that the request gets past the auth boundary, not that
this fixture-less player id resolves.
"""

from __future__ import annotations

import pytest

AGENCY_MUTATIONS: list[tuple[str, str, dict[str, object]]] = [
    ("POST", "/api/players/p-agency-auth/agency/contract-decision", {}),
    ("POST", "/api/players/p-agency-auth/agency/transfer-decision", {}),
]


@pytest.mark.parametrize(("method", "path", "body"), AGENCY_MUTATIONS)
def test_player_agency_mutations_reject_anonymous_callers(
    client, method: str, path: str, body: dict[str, object]
) -> None:
    response = client.request(method, path, json=body)
    assert response.status_code == 401, f"{method} {path} -> {response.status_code}: {response.text}"
    assert response.json()["code"] == "unauthorized"


@pytest.fixture(scope="module")
def agency_auth_headers(client, app_session_factory) -> dict[str, str]:
    """One signed-in user reused across every case.

    Signing up per-parametrised-case trips the auth rate limiter, which would
    make this suite fail for a reason unrelated to what it is testing.
    """
    del app_session_factory
    from uuid import uuid4

    from tests.support.secrets import TEST_PASSWORD
    from tests.support.signup_payloads import user_signup_payload

    suffix = f"agency-auth-{uuid4().hex[:8]}"
    response = client.post(
        "/auth/signup/user",
        json=user_signup_payload(
            email=f"{suffix}@example.com",
            username=suffix.replace("-", "_"),
            password=TEST_PASSWORD,
            full_name="Agency Auth Boundary",
        ),
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.parametrize(("method", "path", "body"), AGENCY_MUTATIONS)
def test_player_agency_mutations_pass_auth_for_signed_in_callers(
    client, agency_auth_headers, method: str, path: str, body: dict[str, object]
) -> None:
    response = client.request(method, path, json=body, headers=agency_auth_headers)
    # Authenticated callers must clear the auth boundary. They then hit normal
    # request/domain validation (422/404) for this synthetic id.
    assert response.status_code != 401, f"{method} {path} -> {response.text}"


def test_player_agency_snapshot_stays_public(client) -> None:
    """The read-only GET is unchanged: no write, no auth required."""
    response = client.get("/api/players/p-agency-auth/agency")
    assert response.status_code != 401, response.text
