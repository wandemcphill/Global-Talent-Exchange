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


# --- club identity / jerseys (legacy compat router) were fully public --------


def test_club_identity_patch_requires_authentication(client):
    path = f"/api/clubs/{uuid4()}/identity"
    _assert_gated(client.patch(path, json={}), path)


def test_club_jerseys_patch_requires_authentication(client):
    path = f"/api/clubs/{uuid4()}/jerseys"
    _assert_gated(client.patch(path, json={}), path)


# --- player lifecycle: contracts, injuries, transfer bids were fully public --


def test_player_contract_create_requires_authentication(client):
    path = f"/api/players/{uuid4()}/contracts"
    payload = {"wage_amount": "100.00", "starts_on": "2026-01-01", "ends_on": "2027-01-01"}
    _assert_gated(client.post(path, json=payload), path)


def test_player_contract_renew_requires_authentication(client):
    path = f"/api/players/{uuid4()}/contracts/{uuid4()}/renew"
    _assert_gated(client.post(path, json={"new_ends_on": "2028-01-01"}), path)


def test_player_injury_create_requires_authentication(client):
    path = f"/api/players/{uuid4()}/injuries"
    _assert_gated(client.post(path, json={}), path)


def test_player_injury_recover_requires_authentication(client):
    path = f"/api/players/{uuid4()}/injuries/{uuid4()}/recover"
    _assert_gated(client.post(path, json={}), path)


def test_transfer_bid_create_requires_authentication(client):
    path = f"/api/transfers/windows/{uuid4()}/bids"
    payload = {"player_id": str(uuid4()), "bid_amount": "100.00"}
    _assert_gated(client.post(path, json=payload), path)


def test_transfer_bid_accept_requires_authentication(client):
    path = f"/api/transfers/windows/{uuid4()}/bids/{uuid4()}/accept"
    _assert_gated(client.post(path, json={"contract_ends_on": "2028-01-01"}), path)


def test_transfer_bid_reject_requires_authentication(client):
    path = f"/api/transfers/windows/{uuid4()}/bids/{uuid4()}/reject"
    _assert_gated(client.post(path, json={}), path)


def test_regen_transfer_listing_requires_authentication(client):
    path = f"/api/players/{uuid4()}/regen/transfer-listing"
    _assert_gated(client.post(path, json={}), path)


def test_regen_big_club_approach_requires_authentication(client):
    path = f"/api/players/{uuid4()}/regen/big-club-approaches"
    _assert_gated(client.post(path, json={"approaching_club_id": str(uuid4())}), path)


def test_regen_pressure_resolution_requires_authentication(client):
    path = f"/api/players/{uuid4()}/regen/pressure-resolution"
    _assert_gated(client.post(path, json={"resolution_type": "stay"}), path)


def test_regen_special_training_requires_authentication(client):
    path = f"/api/players/{uuid4()}/regen/special-training"
    _assert_gated(client.post(path, json={}), path)


def test_resolve_regen_bid_requires_authentication(client):
    path = f"/api/transfers/windows/{uuid4()}/players/{uuid4()}/resolve-regen-bid"
    _assert_gated(client.post(path, json={}), path)


# --- tournaments: creation, joining, result reporting were fully public -----


def test_tournament_create_requires_authentication(client):
    path = "/api/tournaments"
    payload = {"name": "Security Probe Cup", "game_type": "gtex_pvp"}
    _assert_gated(client.post(path, json=payload), path)


def test_tournament_join_requires_authentication(client):
    path = f"/api/tournaments/{uuid4()}/join"
    _assert_gated(client.post(path, json={"user_id": str(uuid4())}), path)


def test_tournament_join_rejects_joining_as_another_user(client, member_headers):
    path = f"/api/tournaments/{uuid4()}/join"
    response = client.post(path, json={"user_id": str(uuid4())}, headers=member_headers)
    assert response.status_code == 403, response.text


def test_tournament_match_result_requires_authentication(client):
    path = f"/api/tournaments/{uuid4()}/matches/{uuid4()}/result"
    _assert_gated(client.post(path, json={"winner_user_id": str(uuid4())}), path)


def test_tournament_advance_requires_authentication(client):
    path = f"/api/tournaments/{uuid4()}/advance"
    _assert_gated(client.post(path, json={}), path)


# --- ultimate league: competitor writes and match results were fully public -


def test_ultimate_league_upsert_competitor_requires_authentication(client):
    competitor_id = str(uuid4())
    path = f"/api/ultimate-league/competitors/{competitor_id}"
    payload = {"competitor_id": competitor_id, "display_name": "Probe", "elo_rating": 1200}
    _assert_gated(client.put(path, json=payload), path)


def test_ultimate_league_matchmaking_batch_requires_authentication(client):
    path = "/api/ultimate-league/matchmaking/batch"
    _assert_gated(client.post(path, json={"competitor_ids": []}), path)


def test_ultimate_league_match_result_requires_authentication(client):
    path = "/api/ultimate-league/matches/result"
    payload = {
        "home_competitor_id": str(uuid4()),
        "away_competitor_id": str(uuid4()),
        "home_score": 1,
        "away_score": 0,
    }
    _assert_gated(client.post(path, json=payload), path)


def test_ultimate_league_tournament_create_requires_authentication(client):
    path = "/api/ultimate-league/tournaments"
    _assert_gated(client.post(path, json={"tournament_id": str(uuid4()), "tier": "bronze"}), path)


def test_ultimate_league_tactical_preset_upsert_requires_authentication(client):
    path = "/api/ultimate-league/tactical-presets"
    payload = {
        "seller_competitor_id": str(uuid4()),
        "title": "Probe",
        "formation": "4-4-2",
        "style": "balanced",
        "price_gtex": "1.0000",
    }
    _assert_gated(client.post(path, json=payload), path)


# --- regen ecosystem: academy/scout/agent writes and award votes were public


def test_regen_academy_upsert_requires_authentication(client):
    path = "/academy"
    payload = {"club_user_id": str(uuid4()), "club_id": str(uuid4())}
    _assert_gated(client.post(path, json=payload), path)


def test_regen_academy_upsert_rejects_another_users_club_user_id(client, member_headers):
    path = "/academy"
    payload = {"club_user_id": str(uuid4()), "club_id": str(uuid4())}
    response = client.post(path, json=payload, headers=member_headers)
    assert response.status_code == 403, response.text


def test_regen_academy_generate_requires_authentication(client):
    path = "/academy/generate"
    payload = {"club_user_id": str(uuid4()), "club_id": str(uuid4())}
    _assert_gated(client.post(path, json=payload), path)


def test_regen_academy_promote_requires_authentication(client):
    path = f"/academy/promote/{uuid4()}"
    _assert_gated(client.post(path, json={}), path)


def test_regen_scout_create_requires_authentication(client):
    path = "/scouts"
    payload = {"club_user_id": str(uuid4()), "club_id": str(uuid4()), "region": "west-africa", "skill_rating": 50}
    _assert_gated(client.post(path, json=payload), path)


def test_regen_scout_create_rejects_another_users_club_user_id(client, member_headers):
    path = "/scouts"
    payload = {"club_user_id": str(uuid4()), "club_id": str(uuid4()), "region": "west-africa", "skill_rating": 50}
    response = client.post(path, json=payload, headers=member_headers)
    assert response.status_code == 403, response.text


def test_regen_scout_discover_requires_authentication(client):
    path = f"/scouts/{uuid4()}/discover"
    _assert_gated(client.post(path, json={}), path)


def test_regen_agent_create_requires_authentication(client):
    path = "/agents"
    _assert_gated(client.post(path, json={"name": "Probe Agency"}), path)


def test_regen_career_event_trigger_requires_authentication(client):
    path = f"/players/{uuid4()}/career-events"
    _assert_gated(client.post(path, json={}), path)


def test_regen_award_vote_requires_authentication(client):
    path = f"/regens/awards/{uuid4()}/vote"
    payload = {"user_id": str(uuid4()), "player_id": str(uuid4())}
    _assert_gated(client.post(path, json=payload), path)


def test_regen_award_vote_rejects_voting_as_another_user(client, member_headers):
    path = f"/regens/awards/{uuid4()}/vote"
    payload = {"user_id": str(uuid4()), "player_id": str(uuid4())}
    response = client.post(path, json=payload, headers=member_headers)
    assert response.status_code == 403, response.text


# --- tournament mutation surface ---------------------------------------------


@pytest.mark.parametrize(
    "method,path,payload",
    [
        (
            "post",
            "/api/tournaments",
            {
                "name": "Security Probe Tournament",
                "game_type": "prediction",
                "entry_fee": 0,
                "max_players": 4,
            },
        ),
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
