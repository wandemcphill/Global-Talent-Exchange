from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any


_NON_ALPHANUMERIC_RE = re.compile(r"[^a-zA-Z0-9]+")
_SHOCK_FIRE = "\U0001F633\U0001F525"
_EYES = "\U0001F440"

_EVENT_TAGS: dict[str, tuple[str, ...]] = {
    "goal": ("#goal", "#football"),
    "penalty_goal": ("#goal", "#penalty", "#football"),
    "penalty_scored": ("#goal", "#penalty", "#football"),
    "equalizer": ("#equalizer", "#football"),
    "winner": ("#winner", "#football"),
    "save": ("#save", "#football"),
    "goalkeeper_save": ("#save", "#football"),
    "double_save": ("#save", "#football"),
    "red_card": ("#redcard", "#football"),
}


def _normalize_tag(value: str) -> str | None:
    raw = value.strip()
    if not raw:
        return None
    token = raw if raw.startswith("#") else f"#{raw}"
    normalized = _NON_ALPHANUMERIC_RE.sub("", token[1:])
    if not normalized:
        return None
    if normalized.islower():
        return f"#{normalized}"
    return f"#{normalized[:1].upper()}{normalized[1:]}"


def _normalize_name_tag(value: str | None) -> str | None:
    if not value:
        return None
    title_case = "".join(part[:1].upper() + part[1:] for part in _NON_ALPHANUMERIC_RE.split(value) if part)
    return _normalize_tag(title_case)


def generate_hashtags(event: Mapping[str, Any], limit: int = 8) -> list[str]:
    event_type = str(event.get("event_type") or event.get("type") or "highlight").strip().lower()
    tags: list[str | None] = [
        *(_EVENT_TAGS.get(event_type) or ("#football", "#highlights")),
        _normalize_name_tag(event.get("team_name")),
        _normalize_name_tag(event.get("opponent_name")),
        _normalize_name_tag(event.get("player_name")),
        "#fyp",
        "#viral",
        "#gtex",
    ]
    custom_tags = event.get("hashtags") or event.get("custom_hashtags") or ()
    if isinstance(custom_tags, Sequence) and not isinstance(custom_tags, (str, bytes)):
        tags.extend(_normalize_tag(str(tag)) for tag in custom_tags)

    resolved: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        if raw is None:
            continue
        normalized = raw.lower() if raw.startswith("#") and raw[1:].islower() else raw
        if normalized in seen:
            continue
        seen.add(normalized)
        resolved.append(raw)
        if len(resolved) >= max(limit, 1):
            break
    return resolved


def build_caption(
    clip: Mapping[str, Any],
    *,
    hashtags: Sequence[str] | None = None,
    style: str = "immediate",
) -> str:
    resolved_hashtags = list(hashtags or generate_hashtags(clip))
    if style == "immediate":
        base = str(clip.get("raw_caption") or clip.get("caption") or "").strip()
        if not base:
            base = "THIS JUST HAPPENED"
        if _SHOCK_FIRE not in base:
            base = f"{base} {_SHOCK_FIRE}"
    else:
        base = str(clip.get("polished_caption") or clip.get("caption") or "").strip()
        if not base:
            player_name = str(clip.get("player_name") or "").strip()
            team_name = str(clip.get("team_name") or "this team").strip()
            minute = int(clip.get("minute") or 0)
            event_type = str(clip.get("event_type") or "moment").replace("_", " ").strip()
            subject = player_name or team_name
            if minute > 0:
                base = f"{minute}' {event_type} from {subject} {_EYES}"
            else:
                base = f"{event_type.title()} from {subject} {_EYES}"
    return " ".join(part for part in (base.strip(), " ".join(resolved_hashtags).strip()) if part)


__all__ = ["build_caption", "generate_hashtags"]
