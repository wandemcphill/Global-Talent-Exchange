from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class PersonalizedFeedContext:
    user_id: str
    favorite_club: str | None = None
    watched_players: tuple[str, ...] = field(default_factory=tuple)
    rival_clubs: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PersonalizedFeedContext":
        return cls(
            user_id=str(payload.get("user_id") or "anonymous"),
            favorite_club=_clean(payload.get("favorite_club")),
            watched_players=tuple(_clean_list(payload.get("watched_players"))),
            rival_clubs=tuple(_clean_list(payload.get("rival_clubs"))),
        )


def rank_for_user(stories: list[dict[str, Any]], user: dict[str, Any] | PersonalizedFeedContext) -> list[dict[str, Any]]:
    context = user if isinstance(user, PersonalizedFeedContext) else PersonalizedFeedContext.from_dict(user)
    ranked: list[dict[str, Any]] = []
    for story in stories:
        item = dict(story)
        metadata = dict(item.get("metadata") or {})
        boost = _personalization_boost(item, context)
        if boost:
            item["priority"] = min(10, int(item.get("priority") or 1) + boost)
        metadata["personalization"] = {
            "user_id": context.user_id,
            "boost": boost,
            "favorite_club": context.favorite_club,
            "watched_players": list(context.watched_players),
            "rival_clubs": list(context.rival_clubs),
        }
        item["metadata"] = metadata
        ranked.append(item)
    return sorted(ranked, key=lambda item: (-int(item.get("priority") or 0), str(item.get("headline") or "")))


def _personalization_boost(story: dict[str, Any], context: PersonalizedFeedContext) -> int:
    text = " ".join(
        str(value or "")
        for value in (
            story.get("headline"),
            story.get("body"),
            story.get("club"),
            story.get("player_id"),
            story.get("player_name"),
        )
    ).lower()
    boost = 0
    if context.favorite_club and context.favorite_club.lower() in text:
        boost += 2
    if any(player.lower() in text for player in context.watched_players):
        boost += 3
    if any(club.lower() in text for club in context.rival_clubs):
        boost += 1
    if story.get("is_regen") and context.watched_players:
        boost += 1
    return boost


def _clean(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _clean_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = value.split(",")
    return [item for item in (_clean(raw) for raw in value) if item]


__all__ = ["PersonalizedFeedContext", "rank_for_user"]
