"""Regression tests for endpoints that were reachable without authorization.

Each case below was verified against the pre-fix tree: the request succeeded
anonymously (or for a non-admin) and returned or mutated data it should not
have. They assert the gate exists, not merely that the route is registered.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

UNAUTHORIZED = {401, 403}


def _assert_gated(response, path: str) -> None:
    assert response.status_code in UNAUTHORIZED, f"{path} answered {response.status_code}: {response.text[:400]}"


# --- admin surfaces that were fully public -----------------------------------


def test_burn_events_require_admin(client):
    # Accepted a user_id filter, so this enumerated any account's burn history.
    _assert_gated(client.get("/admin/economy/burn-events"), "/admin/economy/burn-events")


def test_burn_events_reject_a_plain_authenticated_user(client, member_headers):
    response = client.get("/admin/economy/burn-events", headers=member_headers)
    _assert_gated(response, "/admin/economy/burn-events")


def test_revenue_share_rules_require_admin(client):
    _assert_gated(client.get("/admin/economy/revenue-share-rules"), "/admin/economy/revenue-share-rules")


def test_gift_combo_rules_require_admin(client):
    _assert_gated(client.get("/admin/economy/gift-combo-rules"), "/admin/economy/gift-combo-rules")


def test_admin_engine_bootstrap_requires_admin(client):
    # Exposed live feature flags, calendar rules and reward/fee configuration.
    _assert_gated(client.get("/admin-engine/bootstrap"), "/admin-engine/bootstrap")


def test_admin_engine_bootstrap_rejects_a_plain_authenticated_user(client, member_headers):
    response = client.get("/admin-engine/bootstrap", headers=member_headers)
    _assert_gated(response, "/admin-engine/bootstrap")


def test_burn_events_are_readable_by_an_admin(client, admin_headers):
    response = client.get("/admin/economy/burn-events", headers=admin_headers)
    assert response.status_code == 200, response.text


# --- competition invite codes -------------------------------------------------


def test_competition_invite_codes_are_not_public(client):
    # CompetitionInviteView carries invite_code, and /invites/accept takes one
    # from the request body, so listing them anonymously handed out entry.
    path = f"/api/competitions/{uuid4()}/invites"
    _assert_gated(client.get(path), path)


def test_competition_invite_codes_are_not_readable_by_any_authenticated_user(client, member_headers):
    path = f"/api/competitions/{uuid4()}/invites"
    response = client.get(path, headers=member_headers)
    # A non-host must not learn whether the competition exists, let alone its codes.
    assert response.status_code in UNAUTHORIZED | {404}, response.text
    assert "invite_code" not in response.text


# --- dynasty writes that trusted a body-supplied user_id ----------------------


@pytest.mark.parametrize("path", ["/api/v2/enter", "/api/v2/rent"])
def test_global_memory_writes_require_authentication(client, path: str):
    payload = {
        "user_id": str(uuid4()),
        "competition_id": str(uuid4()),
        "player_id": str(uuid4()),
        "performance_score": 100.0,
    }
    _assert_gated(client.post(path, json=payload), path)


@pytest.mark.parametrize("path", ["/api/v2/enter", "/api/v2/rent"])
def test_global_memory_writes_reject_another_users_id(client, member_headers, path: str):
    payload = {
        "user_id": str(uuid4()),
        "competition_id": str(uuid4()),
        "player_id": str(uuid4()),
        "performance_score": 100.0,
    }
    response = client.post(path, json=payload, headers=member_headers)
    assert response.status_code == 403, response.text


# --- other unauthenticated mutations -----------------------------------------


def _simulation_profile_payload(user_id: str) -> dict:
    return {
        "user_id": user_id,
        "club_id": str(uuid4()),
        "club_name": "Security Probe FC",
        "manager_rating": 1200,
        "tactical_profile": {"style": "balanced", "pressing": "medium", "tempo": "normal"},
        "squad_strength": 70,
        "squad_depth": 60,
        "preferred_match_type": ["quick"],
        "connection_quality": "good",
        "region": "eu",
        "availability": "online",
    }


def test_simulation_profile_upsert_requires_authentication(client):
    victim_id = str(uuid4())
    path = f"/api/simulation-matchmaking/profiles/{victim_id}"
    _assert_gated(client.put(path, json=_simulation_profile_payload(victim_id)), path)


def test_simulation_profile_upsert_rejects_another_users_profile(client, member_headers):
    # A well-formed payload, so the 403 proves the ownership check fires rather
    # than schema validation happening to reject the request.
    victim_id = str(uuid4())
    response = client.put(
        f"/api/simulation-matchmaking/profiles/{victim_id}",
        json=_simulation_profile_payload(victim_id),
        headers=member_headers,
    )
    assert response.status_code == 403, response.text


def test_regen_job_runner_requires_admin(client):
    # Bulk-generates academy intakes and scouting discoveries platform-wide.
    _assert_gated(client.post("/api/regens/jobs/academy-weekly", json={}), "/api/regens/jobs/academy-weekly")


def test_regen_job_runner_rejects_a_plain_authenticated_user(client, member_headers):
    response = client.post("/api/regens/jobs/academy-weekly", json={}, headers=member_headers)
    _assert_gated(response, "/api/regens/jobs/academy-weekly")


def test_value_snapshot_rebuild_requires_admin(client):
    path = "/api/v2/value-engine/snapshots/rebuild"
    _assert_gated(client.post(path, json={}), path)


def test_tactical_preset_purchase_requires_authentication(client):
    path = f"/api/ultimate-league/tactical-presets/{uuid4()}/purchase"
    _assert_gated(client.post(path, json={"buyer_competitor_id": str(uuid4())}), path)


def test_spectator_presence_does_not_leak_viewer_identities(client):
    # SpectatorPresenceView includes active_user_ids.
    path = f"/api/v2/matches/{uuid4()}/spectators"
    _assert_gated(client.get(path), path)


# --- unauthenticated requests must not become server errors -------------------


@pytest.mark.parametrize("token", ["a.b.x", "a.b.!!!", "not-a-token", "$.$.$"])
def test_malformed_bearer_tokens_return_401_not_500(client, token: str):
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401, response.text


# --- tournament mutation surface ---------------------------------------------

@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("post", "/api/tournaments", {
            "name": "Security Probe Tournament",
            "game_type": "prediction",
            "entry_fee": 0,
            "max_players": 4,
        }),
        ("post", f"/api/tournaments/{uuid4()}/join", {"user_id": str(uuid4())}),
        ("post", f"/api/tournaments/{uuid4()}/matches/{uuid4()}/result", {"winner_user_id": str(uuid4())}),
        ("post", f"/api/tournaments/{uuid4()}/advance", {}),
    ],
)
def test_tournament_mutations_require_authentication(client, method: str, path: str, payload: dict):
    response = getattr(client, method)(path, json=payload)
    _assert_gated(response, path)


# --- club identity mutation surface ------------------------------------------

@pytest.mark.parametrize(
    "path",
    [f"/api/clubs/{uuid4()}/identity", f"/api/clubs/{uuid4()}/jerseys"],
)
def test_club_identity_mutations_require_authentication(client, path: str):
    _assert_gated(client.patch(path, json={}), path)


# --- competition lifecycle mutation ownership -------------------------------

def test_competition_creation_alias_requires_authentication(client):
    response = client.post(
        "/api/competitions/create",
        json={
            "creator_id": str(uuid4()),
            "creator_name": "Security Probe",
            "name": "Anonymous Competition",
            "game_type": "prediction",
            "entry_fee": 0,
            "max_players": 4,
        },
    )
    _assert_gated(response, "/api/competitions/create")


def test_competition_leave_cannot_target_another_user(client, member_headers):
    competition_id = str(uuid4())
    response = client.post(
        f"/api/competitions/{competition_id}/leave",
        json={"user_id": str(uuid4())},
        headers=member_headers,
    )
    assert response.status_code == 403, response.text
