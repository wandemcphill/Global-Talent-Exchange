from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from backend.app.models.user import User


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
