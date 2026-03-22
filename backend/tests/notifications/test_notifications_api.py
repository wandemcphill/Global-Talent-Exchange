from __future__ import annotations

from app.core.events import DomainEvent


def test_my_notifications_cover_requested_competition_templates(app_client, participant_user) -> None:
    app, client = app_client
    base_payload = {
        "user_id": participant_user.user_id,
        "competition_id": "league-elite",
        "competition_name": "Elite League",
        "fixture_id": "fixture-101",
        "home_club_name": "Lagos Stars",
        "away_club_name": "Abuja Meteors",
        "resource_id": "fixture-101",
    }

    events = (
        DomainEvent(name="competition.match.starting", payload={**base_payload, "minutes_until_start": 10}),
        DomainEvent(name="competition.match.starting", payload={**base_payload, "minutes_until_start": 1}),
        DomainEvent(name="competition.match.live", payload=base_payload),
        DomainEvent(
            name="competition.match.result",
            payload={**base_payload, "result": "won", "home_goals": 2, "away_goals": 1},
        ),
        DomainEvent(
            name="competition.match.result",
            payload={
                **base_payload,
                "fixture_id": "fixture-102",
                "resource_id": "fixture-102",
                "result": "lost",
                "home_goals": 0,
                "away_goals": 1,
            },
        ),
        DomainEvent(
            name="competition.qualification.updated",
            payload={**base_payload, "qualification_status": "qualified", "resource_id": "qual-1"},
        ),
        DomainEvent(
            name="competition.qualification.updated",
            payload={**base_payload, "qualification_status": "playoff", "resource_id": "qual-2"},
        ),
        DomainEvent(
            name="competition.qualification.updated",
            payload={**base_payload, "qualification_status": "champions_league", "resource_id": "qual-3"},
        ),
        DomainEvent(
            name="competition.qualification.updated",
            payload={**base_payload, "qualification_status": "world_super_cup", "resource_id": "qual-4"},
        ),
        DomainEvent(
            name="competition.fast_cup.starting",
            payload={
                "competition_id": "fast-cup",
                "competition_name": "Fast Cup Weekend",
                "resource_id": "fast-cup-weekend",
            },
        ),
    )

    for event in events:
        app.state.event_publisher.publish(event)

    response = client.get("/notifications/me", headers=participant_user.headers)

    assert response.status_code == 200
    payload = response.json()
    template_keys = {item["template_key"] for item in payload}
    assert template_keys == {
        "match_starts_10m",
        "match_starts_1m",
        "match_live_now",
        "you_won",
        "you_lost",
        "qualified",
        "reached_playoff",
        "qualified_champions_league",
        "qualified_world_super_cup",
        "fast_cup_starts_soon",
    }
    assert any(item["message"] == "Lagos Stars vs Abuja Meteors starts in 10 minutes." for item in payload)
    assert any(item["message"] == "Lagos Stars vs Abuja Meteors starts in 1 minute." for item in payload)
    assert any(item["message"] == "Lagos Stars vs Abuja Meteors is live now." for item in payload)
    assert any(item["message"] == "You won Lagos Stars vs Abuja Meteors 2-1." for item in payload)
    assert any(item["message"] == "You lost Lagos Stars vs Abuja Meteors 0-1." for item in payload)
    assert any(item["message"] == "You qualified from Elite League." for item in payload)
    assert any(item["message"] == "You reached the playoff stage in Elite League." for item in payload)
    assert any(item["message"] == "You qualified for the Champions League from Elite League." for item in payload)
    assert any(item["message"] == "You qualified for the World Super Cup from Elite League." for item in payload)
    assert any(item["message"] == "The next fast cup starts in 15 minutes." for item in payload)
