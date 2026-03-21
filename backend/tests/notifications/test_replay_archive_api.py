from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.common.enums.competition_type import CompetitionType
from app.common.enums.replay_visibility import ReplayVisibility
from app.core.events import DomainEvent
from app.replay_archive.service import ensure_replay_archive


def _build_replay_payload(
    participant_user_id: str,
    *,
    fixture_id: str,
    stage_name: str,
    round_number: int,
    is_final: bool,
    competition_allows_public: bool,
    replay_visibility: ReplayVisibility,
) -> dict:
    scheduled_start = datetime.now(timezone.utc) - timedelta(minutes=8)
    return {
        "fixture_id": fixture_id,
        "scheduled_start": scheduled_start,
        "started_at": scheduled_start,
        "final_whistle_at": scheduled_start + timedelta(minutes=5),
        "live": False,
        "home_club": {"club_id": "club-home", "club_name": "Lagos Stars"},
        "away_club": {"club_id": "club-away", "club_name": "Abuja Meteors"},
        "scoreline": {"home_goals": 2, "away_goals": 1},
        "participant_user_ids": [participant_user_id],
        "competition_context": {
            "competition_id": "league-elite",
            "competition_type": CompetitionType.LEAGUE,
            "competition_name": "Elite League",
            "stage_name": stage_name,
            "round_number": round_number,
            "is_final": is_final,
            "competition_allows_public": competition_allows_public,
            "replay_visibility": replay_visibility,
        },
        "timeline": [
            {
                "event_id": f"{fixture_id}-goal-1",
                "minute": 12,
                "event_type": "goals",
                "club_id": "club-home",
                "club_name": "Lagos Stars",
                "player_id": "player-1",
                "player_name": "Ayo Bello",
                "description": "Left-foot finish",
                "home_score": 1,
                "away_score": 0,
            },
            {
                "event_id": f"{fixture_id}-assist-1",
                "minute": 12,
                "event_type": "assists",
                "club_id": "club-home",
                "club_name": "Lagos Stars",
                "player_id": "player-2",
                "player_name": "Kunle Ade",
                "secondary_player_id": "player-1",
                "secondary_player_name": "Ayo Bello",
                "description": "Threaded through ball",
                "home_score": 1,
                "away_score": 0,
            },
            {
                "event_id": f"{fixture_id}-card-1",
                "minute": 33,
                "event_type": "yellow_cards",
                "club_id": "club-away",
                "club_name": "Abuja Meteors",
                "player_id": "player-3",
                "player_name": "Musa Kane",
                "description": "Late challenge",
                "home_score": 1,
                "away_score": 0,
            },
            {
                "event_id": f"{fixture_id}-injury-1",
                "minute": 40,
                "event_type": "injuries",
                "club_id": "club-away",
                "club_name": "Abuja Meteors",
                "player_id": "player-4",
                "player_name": "Tayo Musa",
                "description": "Hamstring issue",
                "home_score": 1,
                "away_score": 0,
            },
            {
                "event_id": f"{fixture_id}-sub-1",
                "minute": 55,
                "event_type": "substitutions",
                "club_id": "club-away",
                "club_name": "Abuja Meteors",
                "player_id": "player-5",
                "player_name": "Ola Nwosu",
                "secondary_player_id": "player-4",
                "secondary_player_name": "Tayo Musa",
                "description": "Forced substitution",
                "home_score": 1,
                "away_score": 0,
            },
            {
                "event_id": f"{fixture_id}-goal-2",
                "minute": 61,
                "event_type": "goals",
                "club_id": "club-away",
                "club_name": "Abuja Meteors",
                "player_id": "player-6",
                "player_name": "Sani Jude",
                "description": "Header from a corner",
                "home_score": 1,
                "away_score": 1,
            },
            {
                "event_id": f"{fixture_id}-goal-3",
                "minute": 80,
                "event_type": "goals",
                "club_id": "club-home",
                "club_name": "Lagos Stars",
                "player_id": "player-7",
                "player_name": "Femi Ojo",
                "description": "Wins it late",
                "home_score": 2,
                "away_score": 1,
            },
            {
                "event_id": f"{fixture_id}-chance-1",
                "minute": 84,
                "event_type": "missed_chances",
                "club_id": "club-home",
                "club_name": "Lagos Stars",
                "player_id": "player-8",
                "player_name": "Dele Martins",
                "description": "Misses from close range",
                "home_score": 2,
                "away_score": 1,
            },
        ],
    }


def test_replay_archive_preserves_integrity_and_supports_spectator_access(
    app_client,
    participant_user,
    spectator_user,
) -> None:
    app, client = app_client
    ensure_replay_archive(app)
    replay_event = DomainEvent(
        name="competition.replay.archived",
        payload=_build_replay_payload(
            participant_user.user_id,
            fixture_id="fixture-quarterfinal",
            stage_name="Quarterfinal",
            round_number=4,
            is_final=False,
            competition_allows_public=True,
            replay_visibility=ReplayVisibility.COMPETITION,
        ),
    )

    app.state.event_publisher.publish(replay_event)

    participant_list_response = client.get("/replays/me", headers=participant_user.headers)
    spectator_list_response = client.get("/replays/me", headers=spectator_user.headers)

    assert participant_list_response.status_code == 200
    assert spectator_list_response.status_code == 200
    participant_payload = participant_list_response.json()
    spectator_payload = spectator_list_response.json()
    assert participant_payload[0]["fixture_id"] == "fixture-quarterfinal"
    assert spectator_payload[0]["competition_context"]["resolved_visibility"] == "public"

    replay_id = participant_payload[0]["replay_id"]
    detail_response = client.get(f"/replays/{replay_id}", headers=participant_user.headers)

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["scoreline"] == {"home_goals": 2, "away_goals": 1}
    assert len(detail_payload["timeline"]) == 8
    assert len(detail_payload["scorers"]) == 3
    assert len(detail_payload["assisters"]) == 1
    assert len(detail_payload["cards"]) == 1
    assert len(detail_payload["injuries"]) == 1
    assert len(detail_payload["substitutions"]) == 1
    assert detail_payload["competition_context"]["competition_name"] == "Elite League"
    assert detail_payload["competition_context"]["featured_public"] is True


def test_public_featured_matches_and_countdown_expose_final_metadata(app_client, participant_user) -> None:
    app, client = app_client
    ensure_replay_archive(app)

    final_replay_event = DomainEvent(
        name="competition.replay.archived",
        payload=_build_replay_payload(
            participant_user.user_id,
            fixture_id="fixture-final-replay",
            stage_name="Final",
            round_number=6,
            is_final=True,
            competition_allows_public=False,
            replay_visibility=ReplayVisibility.COMPETITION,
        ),
    )
    final_countdown_event = DomainEvent(
        name="competition.match.scheduled",
        payload={
            "fixture_id": "fixture-final-upcoming",
            "scheduled_start": datetime.now(timezone.utc) + timedelta(minutes=9),
            "home_club": {"club_id": "club-home", "club_name": "Lagos Stars"},
            "away_club": {"club_id": "club-away", "club_name": "Abuja Meteors"},
            "competition_context": {
                "competition_id": "league-elite",
                "competition_type": CompetitionType.LEAGUE,
                "competition_name": "Elite League",
                "stage_name": "Final",
                "round_number": 6,
                "is_final": True,
                "competition_allows_public": False,
                "replay_visibility": ReplayVisibility.COMPETITION,
            },
        },
    )

    app.state.event_publisher.publish(final_replay_event)
    app.state.event_publisher.publish(final_countdown_event)

    featured_response = client.get("/replays/public/featured")
    countdown_response = client.get("/replays/countdown/fixture-final-upcoming")

    assert featured_response.status_code == 200
    featured_payload = featured_response.json()
    assert any(item["fixture_id"] == "fixture-final-replay" for item in featured_payload)
    assert any(item["competition_context"]["is_final"] is True for item in featured_payload)

    assert countdown_response.status_code == 200
    countdown_payload = countdown_response.json()
    assert countdown_payload["fixture_id"] == "fixture-final-upcoming"
    assert countdown_payload["competition_context"]["public_metadata_visible"] is True
    assert countdown_payload["competition_context"]["featured_public"] is True
    assert countdown_payload["next_notification_key"] in {"match_starts_1m", "match_live_now"}


def test_replay_archive_versions_survive_service_reinitialization(app_client, participant_user) -> None:
    app, client = app_client
    ensure_replay_archive(app)
    first_payload = _build_replay_payload(
        participant_user.user_id,
        fixture_id="fixture-persistent",
        stage_name="Semifinal",
        round_number=5,
        is_final=False,
        competition_allows_public=True,
        replay_visibility=ReplayVisibility.PUBLIC,
    )
    second_payload = dict(first_payload)
    second_payload["scoreline"] = {"home_goals": 3, "away_goals": 1}

    app.state.event_publisher.publish(DomainEvent(name="competition.replay.archived", payload=first_payload))
    app.state.event_publisher.publish(DomainEvent(name="competition.replay.archived", payload=second_payload))

    replay_id = client.get("/replays/me", headers=participant_user.headers).json()[0]["replay_id"]
    delattr(app.state, "replay_archive")

    rebuilt_archive = ensure_replay_archive(app)
    rebuilt_detail = rebuilt_archive.get_for_user(replay_id, user_id=participant_user.user_id)
    detail_response = client.get(f"/replays/{replay_id}", headers=participant_user.headers)

    assert rebuilt_detail is not None
    assert rebuilt_detail.version == 2
    assert rebuilt_detail.scoreline.home_goals == 3
    assert detail_response.status_code == 200
    assert detail_response.json()["version"] == 2
