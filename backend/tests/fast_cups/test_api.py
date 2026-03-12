from __future__ import annotations

from datetime import timedelta


def test_fast_cup_api_surfaces_upcoming_join_bracket_countdown_and_summary(api_client, base_now) -> None:
    upcoming_response = api_client.get(
        "/fast-cups/upcoming",
        params={"now": base_now.isoformat(), "horizon_intervals": 1},
    )
    assert upcoming_response.status_code == 200

    cups = upcoming_response.json()["cups"]
    assert len(cups) == 8

    senior_32 = next(cup for cup in cups if cup["division"] == "senior" and cup["size"] == 32)
    join_at = senior_32["slot"]["registration_opens_at"]

    for index in range(1, 33):
        response = api_client.post(
            f"/fast-cups/{senior_32['cup_id']}/join",
            json={
                "club_id": f"senior-club-{index:03d}",
                "club_name": f"Senior Club {index:03d}",
                "division": "senior",
                "rating": 5000 - index,
                "registered_at": join_at,
                "existing_windows": [],
            },
        )
        assert response.status_code == 200

    bracket_response = api_client.get(f"/fast-cups/{senior_32['cup_id']}/bracket")
    assert bracket_response.status_code == 200
    bracket_payload = bracket_response.json()
    assert bracket_payload["total_rounds"] == 5
    assert bracket_payload["rounds"][0]["matches"][0]["home"]["club_id"] == "senior-club-001"
    assert bracket_payload["rounds"][0]["matches"][0]["away"]["club_id"] == "senior-club-032"

    countdown_response = api_client.get(
        f"/fast-cups/{senior_32['cup_id']}/countdown",
        params={"now": base_now.isoformat()},
    )
    assert countdown_response.status_code == 200
    countdown_payload = countdown_response.json()
    assert countdown_payload["status"] == "ready"
    assert countdown_payload["slots_remaining"] == 0

    early_summary_response = api_client.get(
        f"/fast-cups/{senior_32['cup_id']}/result-summary",
        params={"now": base_now.isoformat()},
    )
    assert early_summary_response.status_code == 409

    kickoff_plus_duration = base_now + timedelta(minutes=30)
    summary_response = api_client.get(
        f"/fast-cups/{senior_32['cup_id']}/result-summary",
        params={"now": kickoff_plus_duration.isoformat()},
    )
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload["champion"]["club_id"] == "senior-club-001"
    assert summary_payload["expected_duration_minutes"] == 30
    assert len(summary_payload["events"]) == 6
    assert summary_payload["penalty_shootouts"] >= 1
