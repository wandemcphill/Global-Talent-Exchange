from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _publish(client, headers: dict[str, str], *, title: str = "Desk flash") -> dict:
    response = client.post(
        "/api/admin/story-feed",
        headers=headers,
        json={
            "story_type": "featured_update",
            "title": title,
            "body": "Moderation desk story body for schedule and reject coverage.",
            "featured": True,
            "country_code": "NG",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_admin_can_schedule_story_and_hide_until_due(client, bootstrap_admin_headers) -> None:
    published = _publish(client, bootstrap_admin_headers, title="Schedule me")
    story_id = published["id"]
    scheduled_for = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()

    schedule_response = client.post(
        f"/api/admin/story-feed/{story_id}/schedule",
        headers=bootstrap_admin_headers,
        json={"scheduled_for": scheduled_for},
    )
    assert schedule_response.status_code == 200, schedule_response.text
    scheduled = schedule_response.json()
    assert scheduled["moderation_status"] == "scheduled"
    assert scheduled["scheduled_for"] is not None

    public_feed = client.get("/api/story-feed")
    assert public_feed.status_code == 200, public_feed.text
    assert all(item["id"] != story_id for item in public_feed.json())

    admin_feed = client.get("/api/admin/story-feed", headers=bootstrap_admin_headers)
    assert admin_feed.status_code == 200, admin_feed.text
    assert any(item["id"] == story_id and item["moderation_status"] == "scheduled" for item in admin_feed.json())


def test_admin_can_reject_story_and_remove_from_public_feed(client, bootstrap_admin_headers) -> None:
    published = _publish(client, bootstrap_admin_headers, title="Reject me")
    story_id = published["id"]

    reject_response = client.post(
        f"/api/admin/story-feed/{story_id}/reject",
        headers=bootstrap_admin_headers,
        json={"reason": "Tone mismatch"},
    )
    assert reject_response.status_code == 200, reject_response.text
    rejected = reject_response.json()
    assert rejected["moderation_status"] == "rejected"
    assert rejected["featured"] is False
    assert rejected["metadata_json"]["moderation"]["reason"] == "Tone mismatch"

    public_feed = client.get("/api/story-feed")
    assert public_feed.status_code == 200, public_feed.text
    assert all(item["id"] != story_id for item in public_feed.json())


def test_due_scheduled_story_auto_publishes_on_list(client, bootstrap_admin_headers) -> None:
    published = _publish(client, bootstrap_admin_headers, title="Due soon")
    story_id = published["id"]

    from app.models.story_feed import StoryFeedItem
    from app.story_feed_engine.service import MODERATION_SCHEDULED

    with client.app.state.session_factory() as session:
        item = session.get(StoryFeedItem, story_id)
        assert item is not None
        item.moderation_status = MODERATION_SCHEDULED
        item.scheduled_for = datetime.now(timezone.utc) - timedelta(minutes=5)
        session.commit()

    public_feed = client.get("/api/story-feed")
    assert public_feed.status_code == 200, public_feed.text
    matched = next(item for item in public_feed.json() if item["id"] == story_id)
    assert matched["moderation_status"] == "published"
    assert matched["scheduled_for"] is None


def test_schedule_in_the_past_is_rejected(client, bootstrap_admin_headers) -> None:
    published = _publish(client, bootstrap_admin_headers, title="Bad schedule")
    response = client.post(
        f"/api/admin/story-feed/{published['id']}/schedule",
        headers=bootstrap_admin_headers,
        json={"scheduled_for": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()},
    )
    assert response.status_code == 400, response.text
