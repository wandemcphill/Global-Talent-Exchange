from __future__ import annotations

def test_create_patch_publish_join_leave_flow(client, competition_admin_headers, auth_user_factory) -> None:
    entrant = auth_user_factory(suffix="create-publish-join-leave")
    create_response = client.post(
        "/api/competitions",
        json={
            "name": "Weekend Skills League",
            "format": "league",
            "visibility": "public",
            "entry_fee": "12.50",
            "currency": "credit",
            "capacity": 12,
            "creator_id": "host-1",
            "creator_name": "Host One",
            "platform_fee_pct": "0.10",
            "host_fee_pct": "0.05",
            "payout_structure": [
                {"place": 1, "percent": "0.50"},
                {"place": 2, "percent": "0.30"},
                {"place": 3, "percent": "0.20"},
            ],
            "rules_summary": "Highest fantasy points across the league calendar.",
            "beginner_friendly": True,
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    competition_id = created["id"]
    assert created["status"] == "draft"
    assert created["name"] == "Weekend Skills League"
    assert created["creator_id"] == "host-1"
    assert created["participant_count"] == 0
    assert created["entry_fee"] == "12.50"
    assert created["platform_fee_pct"] == "0.10"
    assert created["host_fee_pct"] == "0.05"
    assert created["prize_pool"] == "0.0000"
    assert created["join_eligibility"] == {
        "eligible": False,
        "reason": "competition_not_open",
        "requires_invite": False,
    }

    patch_response = client.patch(
        f"/api/competitions/{competition_id}",
        json={
            "name": "Weekend Skills League Reloaded",
            "capacity": 16,
            "rules_summary": "Transparent player-vs-player fantasy scoring.",
        },
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["name"] == "Weekend Skills League Reloaded"
    assert patched["capacity"] == 16
    assert patched["rules_summary"] == "Transparent player-vs-player fantasy scoring."

    publish_response = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=competition_admin_headers,
        json={"open_for_join": True},
    )
    assert publish_response.status_code == 200
    published = publish_response.json()
    assert published["status"] == "open"

    join_response = client.post(
        f"/api/competitions/{competition_id}/join",
        headers=entrant["headers"],
        json={"user_id": entrant["user_id"], "user_name": "Club 22"},
    )
    assert join_response.status_code == 200
    joined = join_response.json()
    assert joined["participant_count"] == 1
    assert joined["join_eligibility"] == {
        "eligible": True,
        "reason": "already_joined",
        "requires_invite": False,
    }
    assert joined["prize_pool"] == "10.6250"

    detail_response = client.get(f"/api/competitions/{competition_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["name"] == "Weekend Skills League Reloaded"
    assert detail["participant_count"] == 1
    assert detail["status"] == "open"

    summary_response = client.get(f"/api/competitions/{competition_id}/summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["id"] == competition_id
    assert summary["rules_summary"] == "Transparent player-vs-player fantasy scoring."

    leave_response = client.post(
        f"/api/competitions/{competition_id}/leave",
        json={"user_id": entrant["user_id"]},
    )
    assert leave_response.status_code == 200
    left = leave_response.json()
    assert left["participant_count"] == 0
    assert left["status"] == "open"


def test_join_returns_conflict_before_publish(client, auth_user_factory) -> None:
    entrant = auth_user_factory(suffix="join-before-publish")
    create_response = client.post(
        "/api/competitions",
        json={
            "name": "Private Draft Cup",
            "format": "cup",
            "visibility": "private",
            "entry_fee": "5.00",
            "currency": "credit",
            "capacity": 8,
            "creator_id": "host-2",
            "payout_structure": [
                {"place": 1, "percent": "0.60"},
                {"place": 2, "percent": "0.25"},
                {"place": 3, "percent": "0.15"},
            ],
        },
    )
    competition_id = create_response.json()["id"]

    join_response = client.post(
        f"/api/competitions/{competition_id}/join",
        headers=entrant["headers"],
        json={"user_id": entrant["user_id"]},
    )
    assert join_response.status_code == 409
    assert join_response.json() == {"detail": "competition_not_open"}


def test_creator_can_publish_and_auto_run_full_competition(client, auth_user_factory) -> None:
    host = auth_user_factory(suffix="creator-host")
    challenger = auth_user_factory(suffix="creator-challenger")

    create_response = client.post(
        "/api/competitions/create",
        json={
            "name": "Creator Clash League",
            "format": "league",
            "type": "user_hosted",
            "visibility": "public",
            "entry_fee": "0.00",
            "currency": "coin",
            "capacity": 2,
            "max_players": 2,
            "creator_id": host["user_id"],
            "creator_name": "Host Club",
            "payout_structure": [
                {"place": 1, "percent": "1.00"},
            ],
            "rules": "Winner takes the league match.",
        },
    )
    assert create_response.status_code == 201
    competition_id = create_response.json()["id"]
    assert create_response.json()["match_type"] == "user_hosted"

    publish_response = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=host["headers"],
        json={"open_for_join": True},
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "open"

    host_join = client.post(
        "/api/competitions/join",
        headers=host["headers"],
        json={
            "competition_id": competition_id,
            "user_id": host["user_id"],
            "user_name": "Host Club",
        },
    )
    assert host_join.status_code == 200
    assert host_join.json()["status"] == "open"

    challenger_join = client.post(
        "/api/competitions/join",
        headers=challenger["headers"],
        json={
            "competition_id": competition_id,
            "user_id": challenger["user_id"],
            "user_name": "Challenger Club",
        },
    )
    assert challenger_join.status_code == 200
    settled = challenger_join.json()
    assert settled["status"] == "settled"
    assert settled["participant_count"] == 2

    fixtures = client.get(f"/api/competitions/{competition_id}/fixtures")
    assert fixtures.status_code == 200
    fixture_payload = fixtures.json()
    assert len(fixture_payload) == 1
    assert fixture_payload[0]["status"] == "completed"

    events = client.get(
        f"/api/competitions/{competition_id}/matches/{fixture_payload[0]['id']}/events"
    )
    assert events.status_code == 200
    assert len(events.json()) > 0


def test_non_owner_cannot_publish_someone_elses_competition(client, auth_user_factory) -> None:
    host = auth_user_factory(suffix="creator-owner")
    intruder = auth_user_factory(suffix="creator-intruder")

    create_response = client.post(
        "/api/competitions/create",
        json={
            "name": "Private Owner League",
            "format": "league",
            "type": "user_hosted",
            "visibility": "public",
            "entry_fee": "0.00",
            "currency": "coin",
            "capacity": 2,
            "creator_id": host["user_id"],
            "creator_name": "Owner Club",
            "payout_structure": [
                {"place": 1, "percent": "1.00"},
            ],
            "rules": "Only the owner should be allowed to publish.",
        },
    )
    assert create_response.status_code == 201
    competition_id = create_response.json()["id"]

    publish_response = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=intruder["headers"],
        json={"open_for_join": True},
    )
    assert publish_response.status_code == 403
    assert publish_response.json() == {
        "detail": "Admin access is required for this action."
    }
