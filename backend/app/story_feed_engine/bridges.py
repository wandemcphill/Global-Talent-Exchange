"""Bridges from generative news pipes into the durable story_feed desk."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.gtex_news_engine import _flatten_news_payload
from app.story_feed_engine.service import StoryFeedService

NEWS_ENGINE_SOURCE = "gtex_news_engine"
PUBLIC_EXIT_STAGES = frozenset({"formal_request", "training_exile", "termination_petition", "force_sale_window"})


def publish_news_engine_payload(
    session: Session,
    payload: dict[str, list[dict[str, Any]]] | list[dict[str, Any]],
    *,
    max_stories: int = 40,
) -> dict[str, int]:
    """Flatten a news_engine daily/breaking payload into story_feed (idempotent)."""
    if isinstance(payload, list):
        stories = [dict(item) for item in payload]
    else:
        stories = _flatten_news_payload(payload)
    service = StoryFeedService(session)
    created = 0
    skipped = 0
    for story in stories[: max(1, max_stories)]:
        item_created = _publish_news_story(service, story)
        if item_created:
            created += 1
        else:
            skipped += 1
    return {"created": created, "skipped": skipped, "seen": min(len(stories), max_stories)}


def _publish_news_story(service: StoryFeedService, story: dict[str, Any]) -> bool:
    news_id = str(story.get("id") or "").strip()
    headline = str(story.get("headline") or "").strip()
    body = str(story.get("body") or "").strip()
    if not news_id or not headline or not body:
        return False

    story_type = str(story.get("type") or "news").strip().lower() or "news"
    player_id = story.get("player_id")
    subject_type: str | None
    subject_id: str | None
    if player_id:
        subject_type = "player"
        subject_id = str(player_id)
    else:
        subject_type = "gtex_news_engine"
        subject_id = news_id

    priority = int(story.get("priority") or 0)
    meta = {
        "news_id": news_id,
        "journalist": story.get("journalist"),
        "club": story.get("club"),
        "player_name": story.get("player_name"),
        "is_regen": bool(story.get("is_regen")),
        "priority": priority,
        "news_type": story_type,
        "engine_metadata": dict(story.get("metadata") or {}),
    }
    _, created = service.publish_idempotent(
        idempotency_key=f"{NEWS_ENGINE_SOURCE}:{news_id}",
        source=NEWS_ENGINE_SOURCE,
        story_type=story_type,
        title=headline[:200],
        body=body,
        audience="public",
        subject_type=subject_type,
        subject_id=subject_id,
        featured=priority >= 8,
        metadata_json=meta,
    )
    return created


def publish_exit_petition_story(
    session: Session,
    *,
    player_id: str,
    stage: str,
    message: str,
    player_name: str | None = None,
    country_code: str | None = None,
    reason: str | None = None,
) -> bool:
    """Publish when a living-star exit stage becomes public. Returns created."""
    normalized = stage.strip().lower()
    if normalized not in PUBLIC_EXIT_STAGES:
        return False
    name = (player_name or "A regen star").strip()
    title = {
        "formal_request": f"{name} lodges a formal transfer request",
        "training_exile": f"{name} refuses full training intensity",
        "termination_petition": f"{name} petitions to terminate their contract",
        "force_sale_window": f"{name} enters a force-sale window",
    }.get(normalized, f"{name} exit pressure rises")
    body_parts = [message.strip() or "Exit pressure has escalated."]
    if reason:
        body_parts.append(f"Petition note: {reason.strip()[:280]}")
    _, created = StoryFeedService(session).publish_idempotent(
        idempotency_key=f"exit_petition:{player_id}:{normalized}",
        source="regen_living_star",
        story_type="regen_exit_petition",
        title=title[:200],
        body=" ".join(body_parts),
        audience="public",
        subject_type="player",
        subject_id=player_id,
        country_code=country_code,
        featured=normalized in {"termination_petition", "force_sale_window"},
        metadata_json={"stage": normalized, "reason": reason},
    )
    return created


def publish_app_update_story(
    session: Session,
    *,
    announcement_key: str,
    title: str,
    body: str,
    metadata_json: dict[str, Any] | None = None,
) -> bool:
    """Publish platform announcements tagged as app updates into the desk."""
    meta = dict(metadata_json or {})
    story_kind = str(meta.get("story_type") or meta.get("kind") or meta.get("channel") or "").lower()
    key_lower = announcement_key.strip().lower()
    is_app_update = (
        story_kind in {"app_update", "release", "changelog"}
        or key_lower.startswith("app_update")
        or key_lower.startswith("release_")
        or bool(meta.get("app_update"))
    )
    if not is_app_update:
        return False
    _, created = StoryFeedService(session).publish_idempotent(
        idempotency_key=f"app_update:{announcement_key.strip()}",
        source="platform_announcement",
        story_type="app_update",
        title=title.strip()[:200],
        body=body.strip(),
        audience="public",
        subject_type="platform",
        subject_id=announcement_key.strip()[:64],
        featured=True,
        metadata_json=meta,
    )
    return created


__all__ = [
    "NEWS_ENGINE_SOURCE",
    "PUBLIC_EXIT_STAGES",
    "publish_app_update_story",
    "publish_exit_petition_story",
    "publish_news_engine_payload",
]
