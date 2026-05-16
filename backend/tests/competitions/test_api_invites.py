from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _error_message(response) -> str:
    payload = response.json()
    return payload.get("message") or payload.get("detail")


def test_invite_generation_listing_and_join_flow(client, competition_admin_headers, auth_user_factory) -> None:
    host = auth_user_factory(suffix="invite-host")
    blocked_user = auth_user_factory(suffix="invite-blocked")
    invited_user = auth_user_factory(suffix="invite-accepted", funded_credit="100.0000")
    created = client.post(
        "/api/competitions",
        headers=host["headers"],
        json={
            "name": "Invite Only League",
            "format": "league",
            "visibility": "invite_only",
            "entry_fee": "10.00",
            "currency": "credit",
            "capacity": 10,
        },
    ).json()
    competition_id = created["id"]
    client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=competition_admin_headers,
        json={"open_for_join": True},
    )

    invite_response = client.post(
        f"/api/competitions/{competition_id}/invites",
        headers=host["headers"],
        json={
            "issued_by": host["user_id"],
            "max_uses": 2,
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "note": "Alpha clubs",
        },
    )
    assert invite_response.status_code == 201
    invite = invite_response.json()
    invite_code = invite["invite_code"]
    assert invite["issued_by"] == host["user_id"]
    assert invite["max_uses"] == 2
    assert invite["uses"] == 0

    invites_response = client.get(f"/api/competitions/{competition_id}/invites")
    assert invites_response.status_code == 200
    assert invites_response.json() == {
        "competition_id": competition_id,
        "invites": [invite],
    }

    blocked_join = client.post(
        f"/api/competitions/{competition_id}/join",
        headers=blocked_user["headers"],
        json={"user_id": blocked_user["user_id"]},
    )
    assert blocked_join.status_code == 409
    assert _error_message(blocked_join) == "invite_required"

    detail_response = client.get(
        f"/api/competitions/{competition_id}",
        params={"viewer_id": invited_user["user_id"], "invite_code": invite_code},
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["join_eligibility"]["eligible"] is True
    assert detail["join_eligibility"]["requires_invite"] is False
    assert detail["join_eligibility"].get("reason") is None

    join_response = client.post(
        f"/api/competitions/{competition_id}/join",
        headers=invited_user["headers"],
        json={"user_id": invited_user["user_id"], "invite_code": invite_code},
    )
    assert join_response.status_code == 200
    joined = join_response.json()
    assert joined["participant_count"] == 1

    refreshed_invites = client.get(f"/api/competitions/{competition_id}/invites").json()["invites"]
    assert refreshed_invites[0]["uses"] == 1


def test_only_creator_can_issue_invites(client, auth_user_factory) -> None:
    host = auth_user_factory(suffix="invite-owner")
    intruder = auth_user_factory(suffix="invite-intruder")
    created = client.post(
        "/api/competitions",
        headers=host["headers"],
        json={
            "name": "Restricted Cup",
            "format": "cup",
            "visibility": "invite_only",
            "entry_fee": "0.00",
            "currency": "credit",
            "capacity": 8,
        },
    ).json()
    competition_id = created["id"]

    forbidden_response = client.post(
        f"/api/competitions/{competition_id}/invites",
        headers=intruder["headers"],
        json={"issued_by": intruder["user_id"], "max_uses": 1},
    )
    assert forbidden_response.status_code == 403
    assert _error_message(forbidden_response) == "invite_forbidden"
