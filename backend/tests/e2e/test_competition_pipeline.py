from __future__ import annotations

from datetime import UTC, date, datetime

from app.common.enums.competition_type import CompetitionType
from app.common.enums.fixture_window import FixtureWindow
from app.common.enums.replay_visibility import ReplayVisibility
from app.common.schemas.competition import ScheduledFixture


def _assert_subsequence(event_names: list[str], required: tuple[str, ...]) -> None:
    cursor = 0
    for event_name in required:
        cursor = event_names.index(event_name, cursor) + 1


def test_competition_pipeline_dispatches_advancement_replay_and_notifications(
    app_client,
    user_factory,
) -> None:
    app, client = app_client
    home_user = user_factory(
        club_id="cup-home",
        email="cuphome@example.com",
        username="cuphome",
        display_name="Cup Home Manager",
    )
    away_user = user_factory(
        club_id="cup-away",
        email="cupaway@example.com",
        username="cupaway",
        display_name="Cup Away Manager",
    )
    spectator = user_factory(
        club_id=None,
        email="cup-spectator@example.com",
        username="cup_spectator",
        display_name="Cup Spectator",
    )

    fixture = ScheduledFixture(
        fixture_id="fast-cup-quarterfinal-01",
        competition_id="fast-cup-2026",
        competition_type=CompetitionType.FAST_CUP,
        round_number=4,
        home_club_id="cup-home",
        away_club_id="cup-away",
        match_date=date(2026, 3, 11),
        window=FixtureWindow.FAST_CUP_OPEN,
        stage_name="Quarterfinal",
        replay_visibility=ReplayVisibility.PUBLIC,
        is_cup_match=True,
        allow_penalties=True,
    )

    before_events = len(app.state.event_publisher.published_events)
    app.state.match_dispatcher.dispatch_match_simulation(
        fixture,
        competition_name="Weekend Fast Cup",
        stage_name="Quarterfinal",
        scheduled_kickoff_at=datetime(2026, 3, 11, 18, 0, tzinfo=UTC),
        simulation_seed=29,
        home_club_name="Lagos Stars",
        away_club_name="Abuja Meteors",
        home_strength_rating=84,
        away_strength_rating=82,
        home_user_id=home_user.user_id,
        away_user_id=away_user.user_id,
    )

    new_events = app.state.event_publisher.published_events[before_events:]
    event_names = [event.name for event in new_events]
    _assert_subsequence(
        event_names,
        (
            "competition_engine.queue.match_simulation.queued",
            "competition.match.execution.started",
            "competition.match.simulation.completed",
            "competition.match.commentary.generated",
            "competition.match.live",
            "competition.match.result.generated",
            "competition_engine.queue.bracket_advancement.queued",
            "competition.match.advancement.requested",
            "competition.match.advancement.dispatched",
            "competition.match.replay.prepared",
            "competition.replay.archived",
            "competition.match.execution.completed",
        ),
    )
    assert "competition.match.notifications.dispatched" in event_names
    assert "competition.match.standings.updated" not in event_names

    advancement_event = next(
        event
        for event in new_events
        if event.name == "competition.match.advancement.requested"
    )
    assert advancement_event.payload["stage_code"] == "Quarterfinal"
    assert advancement_event.payload["winner_club_id"] in {"cup-home", "cup-away"}

    home_notifications_response = client.get("/notifications/me?limit=20", headers=home_user.headers)
    assert home_notifications_response.status_code == 200
    home_templates = {item["template_key"] for item in home_notifications_response.json()}
    assert "match_live_now" in home_templates
    assert {"you_won", "you_lost"} & home_templates

    away_notifications_response = client.get("/notifications/me?limit=20", headers=away_user.headers)
    assert away_notifications_response.status_code == 200
    away_templates = {item["template_key"] for item in away_notifications_response.json()}
    assert "match_live_now" in away_templates
    assert {"you_won", "you_lost"} & away_templates

    featured_response = client.get("/replays/public/featured?limit=10")
    assert featured_response.status_code == 200
    featured_payload = featured_response.json()
    replay_summary = next(item for item in featured_payload if item["fixture_id"] == fixture.fixture_id)
    assert replay_summary["competition_context"]["featured_public"] is True

    spectator_detail_response = client.get(f"/replays/{replay_summary['replay_id']}", headers=spectator.headers)
    assert spectator_detail_response.status_code == 200
    spectator_detail = spectator_detail_response.json()
    assert spectator_detail["competition_context"]["resolved_visibility"] == "public"
    assert spectator_detail["timeline"]
