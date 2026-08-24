from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_round import CompetitionRound
from app.models.competition_rule_set import CompetitionRuleSet
from app.models.user import User


def _seed_match_context(session: Session) -> None:
    competition = UserCompetition(
        id="competition-router",
        host_user_id="user-alpha",
        name="Router Cup",
        format="league",
        visibility="public",
        status="live",
        start_mode="scheduled",
        currency="coin",
        metadata_json={},
    )
    round_ = CompetitionRound(
        id="round-router",
        competition_id=competition.id,
        round_number=1,
        stage="league",
        status="live",
        metadata_json={},
    )
    rule_set = CompetitionRuleSet(
        id="rules-router",
        competition_id=competition.id,
        format="league",
        min_participants=2,
        max_participants=20,
        league_win_points=3,
        league_draw_points=1,
        league_loss_points=0,
        league_tie_break_order=["points", "goal_diff", "goals_for"],
        cup_allowed_participant_sizes=[],
    )
    match = CompetitionMatch(
        id="match-router",
        competition_id=competition.id,
        round_id=round_.id,
        round_number=1,
        stage="final",
        home_club_id="club-alpha",
        away_club_id="club-bravo",
        status="in_progress",
        metadata_json={},
    )
    participants = [
        CompetitionParticipant(id="participant-router-1", competition_id=competition.id, club_id="club-alpha"),
        CompetitionParticipant(id="participant-router-2", competition_id=competition.id, club_id="club-bravo"),
    ]
    session.add_all([competition, round_, rule_set, match, *participants])
    session.commit()


def test_challenge_creation_acceptance_and_share_links(
    client,
    session: Session,
    user_state: dict[str, User],
) -> None:
    create_response = client.post(
        "/api/clubs/club-alpha/challenges",
        json={
            "title": "Challenge My Club: Alpha vs Bravo",
            "message": "Settle the city bragging rights this weekend.",
            "stakes_text": "LA bragging rights",
            "target_club_id": "club-bravo",
            "visibility": "public",
            "country_code": "US",
            "region_name": "California",
            "city_name": "Los Angeles",
            "accept_by": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        },
    )
    assert create_response.status_code == 201
    challenge_payload = create_response.json()
    challenge_id = challenge_payload["challenge"]["id"]
    assert challenge_payload["challenge"]["status"] == "open"
    assert challenge_payload["card"]["spectator_hype_score"] >= 0

    publish_response = client.post(f"/api/challenges/{challenge_id}/publish")
    assert publish_response.status_code == 200
    publish_payload = publish_response.json()
    assert publish_payload["links"][0]["is_primary"] is True
    primary_link_code = publish_payload["links"][0]["link_code"]

    extra_link_response = client.post(
        f"/api/challenges/{challenge_id}/links",
        json={"channel": "social", "is_primary": False, "metadata_json": {"source": "x"}},
    )
    assert extra_link_response.status_code == 201
    assert extra_link_response.json()["channel"] == "social"

    user_state["user"] = session.get(User, "user-bravo")
    accept_response = client.post(
        f"/api/challenges/{challenge_id}/accept",
        json={
            "responding_club_id": "club-bravo",
            "message": "Accepted. Bring your best XI.",
            "scheduled_for": (datetime.now(UTC) + timedelta(hours=6)).isoformat(),
        },
    )
    assert accept_response.status_code == 200
    accept_payload = accept_response.json()
    assert accept_payload["challenge"]["accepted_club_id"] == "club-bravo"
    assert accept_payload["challenge"]["status"] == "scheduled"
    assert accept_payload["card"]["countdown_seconds"] is not None
    assert accept_payload["rivalry"]["derby_indicator"] is True

    share_event_response = client.post(
        f"/api/challenges/{challenge_id}/share-events",
        json={
            "link_code": primary_link_code,
            "event_type": "share",
            "source_platform": "social",
            "country_code": "US",
        },
    )
    assert share_event_response.status_code == 201

    get_by_link = client.get(f"/api/challenges/links/{primary_link_code}")
    assert get_by_link.status_code == 200
    page_payload = get_by_link.json()
    assert page_payload["share_stats"]["share_count"] == 1
    assert page_payload["card"]["primary_web_path"].startswith("/challenge/")

    challenge_list = client.get("/api/clubs/club-alpha/challenges", params={"direction": "issued"})
    assert challenge_list.status_code == 200
    listed = challenge_list.json()["challenges"]
    assert len(listed) == 1
    assert listed[0]["challenge_id"] == challenge_id


def test_social_follow_match_share_and_live_match_surfaces(
    client,
    session: Session,
) -> None:
    _seed_match_context(session)

    follow_response = client.post(
        "/api/social/follows",
        json={"target_type": "club", "club_id": "club-bravo"},
    )
    assert follow_response.status_code == 201
    assert follow_response.json()["target_key"] == "club:club-bravo"

    share_response = client.post(
        "/api/matches/match-router/share-links",
        json={"reward_amount_minor": 50},
    )
    assert share_response.status_code == 201
    share_payload = share_response.json()
    share_code = share_payload["share_code"]
    assert "50 GTex" in share_payload["share_text"]

    record_share_response = client.post(
        f"/api/match-share-links/{share_code}/events",
        json={"event_type": "open", "source_platform": "social"},
    )
    assert record_share_response.status_code == 201

    share_page_response = client.get(f"/api/match-share-links/{share_code}")
    assert share_page_response.status_code == 200
    assert share_page_response.json()["link"]["click_count"] == 1

    reaction_response = client.post(
        "/api/matches/match-router/live-reactions",
        json={"reaction_type": "hype", "intensity_score": 80, "club_id": "club-alpha"},
    )
    assert reaction_response.status_code == 201
    assert reaction_response.json()["reactions"][0]["reaction_type"] == "hype"

    chat_response = client.post(
        "/api/matches/match-router/chat",
        json={"body": "That goal was insane!", "club_id": "club-alpha"},
    )
    assert chat_response.status_code == 201
    assert chat_response.json()["messages"][0]["body"] == "That goal was insane!"




def test_identity_metrics_refresh_allows_owner(client, user_state) -> None:
    response = client.post("/api/clubs/club-alpha/identity/metrics/refresh")
    assert response.status_code == 200
    assert response.json()["club_id"] == "club-alpha"


def test_identity_metrics_refresh_rejects_other_owner(client, user_state, session) -> None:
    user_state["user"] = session.get(User, "user-bravo")
    response = client.post("/api/clubs/club-alpha/identity/metrics/refresh")
    assert response.status_code == 403
