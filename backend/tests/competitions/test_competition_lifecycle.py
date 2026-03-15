from __future__ import annotations

from datetime import date, datetime, timezone

from backend.app.models.calendar_engine import CalendarEvent


def _create_competition(client, *, name: str, format: str, capacity: int) -> str:
    response = client.post(
        "/api/competitions",
        json={
            "name": name,
            "format": format,
            "visibility": "public",
            "entry_fee": "0.00",
            "currency": "credit",
            "capacity": capacity,
            "creator_id": f"host-{name}",
            "payout_structure": [{"place": 1, "percent": "1.00"}],
            "scheduled_start_at": datetime(2026, 3, 20, tzinfo=timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _publish_and_join(client, competition_id: str, club_ids: list[str]) -> None:
    publish = client.post(f"/api/competitions/{competition_id}/publish", json={"open_for_join": True})
    assert publish.status_code == 200
    for club_id in club_ids:
        join = client.post(f"/api/competitions/{competition_id}/join", json={"user_id": club_id})
        assert join.status_code == 200


def test_league_round_and_fixture_generation(client) -> None:
    competition_id = _create_competition(client, name="League Fixtures", format="league", capacity=4)
    _publish_and_join(client, competition_id, ["club-a", "club-b", "club-c", "club-d"])

    seed = client.post(f"/api/competitions/{competition_id}/seed", json={"seed_method": "random"})
    assert seed.status_code == 200
    launch = client.post(f"/api/competitions/{competition_id}/launch")
    assert launch.status_code == 200

    rounds = client.get(f"/api/competitions/{competition_id}/rounds").json()
    fixtures = client.get(f"/api/competitions/{competition_id}/fixtures").json()

    assert len(rounds) == 3
    assert len(fixtures) == 6
    assert {match["stage"] for match in fixtures} == {"league"}


def test_standings_update_after_match_completion(client) -> None:
    competition_id = _create_competition(client, name="League Standings", format="league", capacity=2)
    _publish_and_join(client, competition_id, ["club-e", "club-f"])

    seed = client.post(f"/api/competitions/{competition_id}/seed", json={"seed_method": "random"})
    assert seed.status_code == 200
    launch = client.post(f"/api/competitions/{competition_id}/launch")
    assert launch.status_code == 200

    fixtures = client.get(f"/api/competitions/{competition_id}/fixtures").json()
    assert len(fixtures) == 1
    match = fixtures[0]

    event = client.post(
        f"/api/competitions/{competition_id}/matches/{match['id']}/events",
        json={"event_type": "goal", "minute": 12, "club_id": match["home_club_id"], "highlight": True},
    )
    assert event.status_code == 201

    result = client.post(
        f"/api/competitions/{competition_id}/matches/{match['id']}/result",
        json={"home_score": 2, "away_score": 1},
    )
    assert result.status_code == 200

    standings = client.get(f"/api/competitions/{competition_id}/standings").json()
    assert len(standings) == 2
    leader = standings[0]
    assert leader["points"] == 3
    assert leader["wins"] == 1


def test_cup_playoff_progression_and_settlement(client) -> None:
    competition_id = _create_competition(client, name="Cup Progression", format="cup", capacity=4)
    _publish_and_join(client, competition_id, ["club-g", "club-h", "club-i", "club-j"])

    seeded = client.post(f"/api/competitions/{competition_id}/seed", json={"seed_method": "random"}).json()
    assert seeded["status"] == "seeded"

    launched = client.post(f"/api/competitions/{competition_id}/launch").json()
    assert launched["status"] == "live"

    fixtures = client.get(f"/api/competitions/{competition_id}/fixtures").json()
    assert len(fixtures) == 2
    for match in fixtures:
        result = client.post(
            f"/api/competitions/{competition_id}/matches/{match['id']}/result",
            json={"home_score": 1, "away_score": 0, "winner_club_id": match["home_club_id"]},
        )
        assert result.status_code == 200

    advanced = client.post(f"/api/competitions/{competition_id}/advance", json={"force": False}).json()
    assert advanced["status"] in {"live", "completed"}

    fixtures = client.get(f"/api/competitions/{competition_id}/fixtures").json()
    final_matches = [match for match in fixtures if match["round_number"] == 2]
    assert len(final_matches) == 1

    final_match = final_matches[0]
    client.post(
        f"/api/competitions/{competition_id}/matches/{final_match['id']}/result",
        json={"home_score": 2, "away_score": 0, "winner_club_id": final_match["home_club_id"]},
    )

    completed = client.post(f"/api/competitions/{competition_id}/advance", json={"force": False}).json()
    assert completed["status"] == "completed"

    settled = client.post(f"/api/competitions/{competition_id}/finalize", json={"settle": True}).json()
    assert settled["status"] == "settled"


def test_schedule_blackout_avoids_exclusive_window(client, app_session_factory) -> None:
    blocked_date = date(2026, 3, 20)
    with app_session_factory() as session:
        session.add(
            CalendarEvent(
                event_key="world-cup-block",
                title="World Cup",
                source_type="gtx",
                starts_on=blocked_date,
                ends_on=blocked_date,
                exclusive_windows=True,
                pause_other_gtx_competitions=True,
                status="scheduled",
            )
        )
        session.commit()

    competition_id = _create_competition(client, name="Blackout League", format="league", capacity=4)
    preview = client.post(
        f"/api/competitions/{competition_id}/schedule/preview",
        json={"start_date": blocked_date.isoformat()},
    )
    assert preview.status_code == 200
    payload = preview.json()
    assert "Schedule avoided calendar blackout windows." in payload["warnings"]
    assert blocked_date.isoformat() not in payload["assigned_dates"]
