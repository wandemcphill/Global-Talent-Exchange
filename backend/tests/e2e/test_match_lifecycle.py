from __future__ import annotations

from datetime import date, timedelta

from app.leagues.models import LeagueClub


def _clubs() -> tuple[LeagueClub, ...]:
    return (
        LeagueClub(club_id="club-1", club_name="Lagos Stars", strength_rating=88),
        LeagueClub(club_id="club-2", club_name="Abuja Meteors", strength_rating=85),
        LeagueClub(club_id="club-3", club_name="Kano Waves", strength_rating=81),
        LeagueClub(club_id="club-4", club_name="Enugu City", strength_rating=78),
    )


def _assert_subsequence(event_names: list[str], required: tuple[str, ...]) -> None:
    cursor = 0
    for event_name in required:
        cursor = event_names.index(event_name, cursor) + 1


def test_match_lifecycle_runs_from_fixture_to_replay_archive_and_notifications(
    app_client,
    user_factory,
) -> None:
    app, client = app_client
    league_service = app.state.match_execution_worker.league_service
    clubs = _clubs()
    participants = {
        user.club_id: user
        for user in (
            user_factory(
                club_id="club-1",
                email="manager1@example.com",
                username="manager1",
                display_name="Lagos Stars Manager",
            ),
            user_factory(
                club_id="club-2",
                email="manager2@example.com",
                username="manager2",
                display_name="Abuja Meteors Manager",
            ),
            user_factory(
                club_id="club-3",
                email="manager3@example.com",
                username="manager3",
                display_name="Kano Waves Manager",
            ),
            user_factory(
                club_id="club-4",
                email="manager4@example.com",
                username="manager4",
                display_name="Enugu City Manager",
            ),
        )
    }
    spectator = user_factory(
        club_id=None,
        email="spectator-e2e@example.com",
        username="spectator_e2e",
        display_name="Spectator E2E",
    )

    season = league_service.register_season(
        season_id="league-lifecycle-e2e",
        buy_in_tier=1000,
        season_start=date(2026, 3, 11),
        clubs=clubs,
    )
    fixture = next(
        item
        for item in sorted(season.fixtures, key=lambda value: (value.round_number, value.kickoff_at))
        if item.round_number >= 3
    )
    user_ids_by_club = {club_id: user.user_id for club_id, user in participants.items()}

    before_events = len(app.state.event_publisher.published_events)
    app.state.league_match_execution.schedule_fixture(
        season_id=season.season_id,
        fixture=fixture,
        clubs=clubs,
        competition_name="Elite League",
        club_user_ids=user_ids_by_club,
        simulation_seed=17,
        reference_at=fixture.kickoff_at - timedelta(minutes=5),
    )

    new_events = app.state.event_publisher.published_events[before_events:]
    event_names = [event.name for event in new_events]
    _assert_subsequence(
        event_names,
        (
            "competition.match.scheduled",
            "competition_engine.queue.match_simulation.queued",
            "competition.match.execution.started",
            "competition.match.simulation.completed",
            "competition.match.commentary.generated",
            "competition.match.live",
            "competition.match.result.generated",
            "competition.match.standings.updated",
            "competition.match.replay.prepared",
            "competition.replay.archived",
            "competition.match.execution.completed",
        ),
    )
    assert "competition_engine.queue.notification.queued" in event_names
    assert "competition.notification" in event_names
    assert "competition.match.notifications.dispatched" in event_names

    updated_state = league_service.get_season_state(season.season_id)
    completed_fixture = next(item for item in updated_state.fixtures if item.fixture_id == fixture.fixture_id)
    assert completed_fixture.result is not None
    assert updated_state.completed_fixture_count == 1

    home_user = participants[fixture.home_club_id]
    notification_response = client.get("/notifications/me?limit=20", headers=home_user.headers)
    assert notification_response.status_code == 200
    template_keys = {item["template_key"] for item in notification_response.json()}
    assert "match_starts_10m" in template_keys
    assert "match_live_now" in template_keys
    assert {"you_won", "you_lost"} & template_keys

    replay_list_response = client.get("/replays/me?limit=10", headers=home_user.headers)
    assert replay_list_response.status_code == 200
    replay_summaries = replay_list_response.json()
    replay_summary = next(item for item in replay_summaries if item["fixture_id"] == fixture.fixture_id)

    replay_detail_response = client.get(f"/replays/{replay_summary['replay_id']}", headers=home_user.headers)
    assert replay_detail_response.status_code == 200
    replay_detail = replay_detail_response.json()
    assert replay_detail["fixture_id"] == fixture.fixture_id
    assert replay_detail["timeline"]
    assert replay_detail["competition_context"]["competition_name"] == "Elite League"

    featured_response = client.get("/replays/public/featured?limit=10")
    assert featured_response.status_code == 200
    featured_fixture_ids = {item["fixture_id"] for item in featured_response.json()}
    assert fixture.fixture_id in featured_fixture_ids

    spectator_response = client.get(f"/replays/{replay_summary['replay_id']}", headers=spectator.headers)
    assert spectator_response.status_code == 200
