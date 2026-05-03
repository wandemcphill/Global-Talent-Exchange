from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _base_payload(**overrides):
    payload = {
        "name": "Manager Evening Cup",
        "format": "cup",
        "visibility": "public",
        "entry_fee": "5.00",
        "currency": "credit",
        "capacity": 8,
        "max_players": 8,
        "payout_structure": [{"place": 1, "percent": "1.00"}],
        "scheduled_start_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    }
    payload.update(overrides)
    return payload


def _error_detail(response):
    payload = response.json()
    return payload.get("detail") or payload.get("message")


def test_user_competition_cannot_use_gtex_name(client) -> None:
    response = client.post(
        "/api/competitions",
        json=_base_payload(name="GTEX Weekend Cup"),
    )

    assert response.status_code == 400
    assert _error_detail(response) == "reserved_gtex_name"


def test_admin_can_create_free_gtex_competition(client, competition_admin_headers) -> None:
    response = client.post(
        "/api/admin/competitions",
        headers=competition_admin_headers,
        json=_base_payload(
            name="GTEX Official Cup",
            host_type="GTEX_HOSTED",
            entry_fee="25.00",
            buyInAmount="25.00",
        ),
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["host_type"] == "gtex_hosted"
    assert float(payload["entry_fee"]) == 0.0
    assert payload["currency"] == "coin"


def test_passcode_and_start_lock_join_rules(client, competition_admin_headers, auth_user_factory) -> None:
    create_response = client.post(
        "/api/competitions",
        json=_base_payload(
            name="Private Manager Cup",
            entry_fee="0.00",
            passcode="locker-room",
        ),
    )
    assert create_response.status_code == 201, create_response.text
    competition_id = create_response.json()["id"]
    publish = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=competition_admin_headers,
        json={"open_for_join": True},
    )
    assert publish.status_code == 200, publish.text
    entrant = auth_user_factory(suffix="passcode-entrant")

    missing_passcode = client.post(
        f"/api/competitions/{competition_id}/join",
        headers=entrant["headers"],
        json={"user_id": entrant["user_id"]},
    )
    assert missing_passcode.status_code == 409
    assert _error_detail(missing_passcode) == "passcode_required"

    joined = client.post(
        f"/api/competitions/{competition_id}/join",
        headers=entrant["headers"],
        json={"user_id": entrant["user_id"], "passcode": "locker-room"},
    )
    assert joined.status_code == 200, joined.text
    assert joined.json()["participant_count"] == 1

    late_response = client.post(
        "/api/competitions",
        json=_base_payload(
            name="Started Manager Cup",
            entry_fee="0.00",
            scheduled_start_at=(datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
        ),
    )
    assert late_response.status_code == 201, late_response.text
    late_id = late_response.json()["id"]
    publish_late = client.post(
        f"/api/competitions/{late_id}/publish",
        headers=competition_admin_headers,
        json={"open_for_join": True},
    )
    assert publish_late.status_code == 200, publish_late.text
    late_entrant = auth_user_factory(suffix="late-entrant")

    blocked = client.post(
        f"/api/competitions/{late_id}/join",
        headers=late_entrant["headers"],
        json={"user_id": late_entrant["user_id"]},
    )
    assert blocked.status_code == 409
    assert _error_detail(blocked) == "competition_started"
