from __future__ import annotations

from backend.app.models.user import User


def _as_user(user_state: dict[str, User], session, user_id: str) -> None:
    user = session.get(User, user_id)
    assert user is not None
    user_state["user"] = user


def test_creator_fan_chat_and_fan_wall_api_contracts(client, session, user_state) -> None:
    _as_user(user_state, session, "fan-season-share")

    room_response = client.get("/community/creator-matches/match-1/chat-room")
    assert room_response.status_code == 200, room_response.text
    room_payload = room_response.json()
    assert room_payload["layout_hints_json"]["avoid_video_overlay"] is True
    assert room_payload["access"]["visibility_priority"] == 300

    post_response = client.post(
        "/community/creator-matches/match-1/chat-room/messages",
        json={"body": "Front row for this one", "supported_club_id": "club-home"},
    )
    assert post_response.status_code == 201, post_response.text
    assert post_response.json()["visibility_priority"] == 300

    advice_response = client.post(
        "/community/creator-matches/match-1/tactical-advice",
        json={
            "advice_type": "substitution",
            "suggestion_text": "Sub striker now",
            "supported_club_id": "club-home",
        },
    )
    assert advice_response.status_code == 201, advice_response.text
    assert advice_response.json()["authority"] == "advisory_only"

    wall_response = client.get("/community/creator-matches/match-1/fan-wall")
    assert wall_response.status_code == 200, wall_response.text
    assert any(item["item_type"] == "tactical_advice" for item in wall_response.json()["items"])


def test_creator_fan_follow_group_competition_and_state_api_contracts(client, session, user_state) -> None:
    _as_user(user_state, session, "fan-season-share")

    follow_response = client.post("/community/creator-clubs/club-home/follow", json={})
    assert follow_response.status_code == 201, follow_response.text
    assert follow_response.json()["club_id"] == "club-home"

    group_response = client.post(
        "/community/creator-clubs/club-home/fan-groups",
        json={"name": "Speed Army", "identity_label": "Speed Army"},
    )
    assert group_response.status_code == 201, group_response.text
    group_id = group_response.json()["id"]

    competition_response = client.post(
        "/community/creator-clubs/club-home/fan-competitions",
        json={"title": "Speed Army Cup", "match_id": "match-1"},
    )
    assert competition_response.status_code == 201, competition_response.text
    fan_competition_id = competition_response.json()["id"]

    join_response = client.post(
        f"/community/fan-competitions/{fan_competition_id}/join",
        json={"fan_group_id": group_id},
    )
    assert join_response.status_code == 201, join_response.text

    state_response = client.get("/community/creator-clubs/club-home/fan-state", params={"match_id": "match-1"})
    assert state_response.status_code == 200, state_response.text
    state_payload = state_response.json()
    assert state_payload["following"] is True
    assert group_id in state_payload["fan_group_ids"]
    assert fan_competition_id in state_payload["fan_competition_ids"]

    _as_user(user_state, session, "fan-basic")
    denied_response = client.post(
        "/community/creator-matches/match-1/chat-room/messages",
        json={"body": "Let me in", "supported_club_id": "club-home"},
    )
    assert denied_response.status_code == 403, denied_response.text
    assert denied_response.json()["detail"] == "fan_chat_access_denied"


def test_creator_fan_chat_rate_limit_returns_429(client, session, user_state) -> None:
    _as_user(user_state, session, "fan-season-share")

    first_response = client.post(
        "/community/creator-matches/match-1/chat-room/messages",
        json={"body": "Front row energy", "supported_club_id": "club-home"},
    )
    assert first_response.status_code == 201, first_response.text

    second_response = client.post(
        "/community/creator-matches/match-1/chat-room/messages",
        json={"body": "Front row energy", "supported_club_id": "club-home"},
    )
    assert second_response.status_code == 429, second_response.text
    assert second_response.json()["detail"] == "fan_chat_rate_limited"
