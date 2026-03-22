from __future__ import annotations

def test_create_patch_publish_join_leave_flow(client) -> None:
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
        json={"open_for_join": True},
    )
    assert publish_response.status_code == 200
    published = publish_response.json()
    assert published["status"] == "open"

    join_response = client.post(
        f"/api/competitions/{competition_id}/join",
        json={"user_id": "club-22", "user_name": "Club 22"},
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
        json={"user_id": "club-22"},
    )
    assert leave_response.status_code == 200
    left = leave_response.json()
    assert left["participant_count"] == 0
    assert left["status"] == "open"


def test_join_returns_conflict_before_publish(client) -> None:
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
        json={"user_id": "club-9"},
    )
    assert join_response.status_code == 409
    assert join_response.json() == {"detail": "competition_not_open"}
