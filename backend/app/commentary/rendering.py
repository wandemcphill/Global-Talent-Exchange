from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping


DEFAULT_COMMENTATOR_PROFILES: tuple[dict[str, object], ...] = (
    {
        "name": "The General",
        "style": "tactical",
        "tone_intensity": 0.32,
        "summary": "Calm, structural, and clinical under pressure.",
        "catchphrases": ["Read the shape.", "That is deliberate football."],
        "bias_rules": {"persona": "analyst", "focus": "structure", "governance_weight": 0.7},
        "voice_config": {"preset": "analyst", "tone": "tactical", "commentator_role": "analyst"},
        "is_default": True,
    },
    {
        "name": "The Hype Beast",
        "style": "hype",
        "tone_intensity": 0.94,
        "summary": "Explosive, loud, and obsessed with moments.",
        "catchphrases": ["THIS PLACE IS MELTING!", "ABSOLUTE MADNESS!"],
        "bias_rules": {"persona": "hype", "focus": "moments", "pressure_weight": 1.0},
        "voice_config": {"preset": "hype", "tone": "hype", "commentator_role": "lead"},
        "is_default": False,
    },
    {
        "name": "The Storyteller",
        "style": "dramatic",
        "tone_intensity": 0.61,
        "summary": "Narrative-driven and legacy-aware.",
        "catchphrases": ["The script bends again.", "Another chapter finds its author."],
        "bias_rules": {"persona": "storyteller", "focus": "legacy", "history_weight": 1.0},
        "voice_config": {"preset": "play_by_play", "tone": "dramatic", "commentator_role": "lead"},
        "is_default": False,
    },
    {
        "name": "The Villain",
        "style": "comedic",
        "tone_intensity": 0.74,
        "summary": "Biased, confrontational, and delighted by chaos.",
        "catchphrases": ["Pain travels fast.", "Pressure eats weak teams alive."],
        "bias_rules": {"persona": "villain", "focus": "pressure", "taunt_losing_side": True},
        "voice_config": {"preset": "play_by_play", "tone": "dramatic", "commentator_role": "lead"},
        "is_default": False,
    },
)


@dataclass(frozen=True, slots=True)
class CommentaryProfileSnapshot:
    id: str
    name: str
    style: str
    tone_intensity: float
    summary: str | None
    catchphrases: tuple[str, ...]
    bias_rules: dict[str, Any]
    voice_config: dict[str, Any]
    is_default: bool = False

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "CommentaryProfileSnapshot":
        return cls(
            id=str(payload.get("id") or payload.get("name") or "commentary-profile"),
            name=str(payload.get("name") or "Commentator"),
            style=str(payload.get("style") or "tactical"),
            tone_intensity=float(payload.get("tone_intensity") or 0.5),
            summary=str(payload.get("summary")) if payload.get("summary") is not None else None,
            catchphrases=tuple(str(item) for item in list(payload.get("catchphrases") or []) if str(item).strip()),
            bias_rules=dict(payload.get("bias_rules") or {}),
            voice_config=dict(payload.get("voice_config") or {}),
            is_default=bool(payload.get("is_default")),
        )


@dataclass(frozen=True, slots=True)
class RenderedCommentaryVariant:
    profile_id: str
    profile_name: str
    style: str
    line: str
    tone: str
    commentator: str
    intensity: float
    audio_channel: str
    voice_config: dict[str, Any]


def fallback_commentary_profiles() -> tuple[CommentaryProfileSnapshot, ...]:
    return tuple(CommentaryProfileSnapshot.from_mapping(item) for item in DEFAULT_COMMENTATOR_PROFILES)


def render_commentary_variant(
    *,
    profile: CommentaryProfileSnapshot,
    context: Mapping[str, Any],
    base_line: str,
    variant_index: int = 0,
) -> RenderedCommentaryVariant:
    style = profile.style.strip().lower() or "tactical"
    if style == "tactical":
        body = _tactical_line(context=context, base_line=base_line)
        tone = "tactical"
        commentator = "analyst"
        audio_channel = "match_bed"
    elif style == "hype":
        body = _hype_line(context=context, base_line=base_line)
        tone = "hype"
        commentator = "lead"
        audio_channel = "headline"
    elif style == "dramatic":
        body = _story_line(context=context, base_line=base_line)
        tone = "dramatic"
        commentator = "lead"
        audio_channel = "headline"
    else:
        body = _villain_line(context=context, base_line=base_line)
        tone = "dramatic"
        commentator = "lead"
        audio_channel = "headline"
    line = _decorate_with_catchphrase(profile=profile, context=context, body=body, variant_index=variant_index)
    intensity = _render_intensity(profile=profile, context=context)
    return RenderedCommentaryVariant(
        profile_id=profile.id,
        profile_name=profile.name,
        style=profile.style,
        line=line,
        tone=tone,
        commentator=commentator,
        intensity=intensity,
        audio_channel=audio_channel,
        voice_config=dict(profile.voice_config),
    )


def _tactical_line(*, context: Mapping[str, Any], base_line: str) -> str:
    player = _name(context, "player_name", fallback="The move")
    team = _name(context, "team_name", fallback="the side")
    build_up = _label(context.get("build_up_pattern")) or _label(context.get("possession_route")) or "the rotation"
    governance = _governance_hook(context)
    if str(context.get("event_family") or "") == "goal":
        if governance:
            return f"{governance} That structure freed {player} for {team}."
        return f"{build_up.capitalize()} opened the lane and {player} punished it for {team}."
    if str(context.get("event_family") or "") == "shot":
        return f"The trigger comes from {build_up}; {player} attacks the window for {team}."
    if str(context.get("event_family") or "") == "card":
        return f"{team} lose their defensive margin there, and the card was invited by the spacing."
    if str(context.get("event_family") or "") == "substitution":
        return f"{team} are rebalancing the shape, not just refreshing legs."
    return base_line.strip() or f"{team} keep working the details of the phase."


def _hype_line(*, context: Mapping[str, Any], base_line: str) -> str:
    player = _name(context, "player_name", fallback="Somebody")
    team = _name(context, "team_name", fallback="the side")
    governance = _governance_hook(context)
    if str(context.get("event_family") or "") == "goal":
        if governance:
            return f"{governance} {player} rips the roof off for {team}!"
        return f"THIS IS ABSOLUTE MADNESS! {player} has detonated for {team}!"
    if str(context.get("event_family") or "") == "shot":
        return f"{player} lets it fly and {team} have the crowd holding its breath!"
    if str(context.get("event_family") or "") == "card":
        return f"The temperature just exploded and {team} are playing with fire now!"
    if str(context.get("late_drama")):
        return f"Every touch feels radioactive now and {team} are living on the edge!"
    return base_line.strip().upper() if base_line.strip() else f"{team} keep throwing chaos into this match!"


def _story_line(*, context: Mapping[str, Any], base_line: str) -> str:
    player = _name(context, "player_name", fallback="The hero")
    team = _name(context, "team_name", fallback="the side")
    rivalry = _label(context.get("rivalry_label"))
    history = _label(context.get("player_history_hook")) or _label(context.get("legacy_hook"))
    governance = _governance_hook(context)
    board_pressure = _label(context.get("board_pressure_hook"))
    if str(context.get("event_family") or "") == "goal":
        fragments = ["From the brink"]
        if rivalry:
            fragments.append(f"inside {rivalry}")
        if governance:
            fragments.append(governance.lower())
        fragments.append(f"{player} writes another page for {team}.")
        return "... ".join(fragment.strip(". ") for fragment in fragments if fragment)
    if board_pressure:
        return f"{board_pressure} and the story tightens around {team}."
    if history:
        return f"{history.capitalize()} and now the story turns again around {player}."
    return base_line.strip() or f"The narrative shifts again, and {team} are at the center of it."


def _villain_line(*, context: Mapping[str, Any], base_line: str) -> str:
    player = _name(context, "player_name", fallback="That player")
    team = _name(context, "team_name", fallback="that club")
    opponent = _name(context, "opponent_team_name", fallback="the other side")
    governance = _governance_hook(context)
    board_pressure = _label(context.get("board_pressure_hook"))
    family = str(context.get("event_family") or "")
    if family == "goal":
        if board_pressure:
            return f"{board_pressure} and {opponent} can smell blood now."
        if governance:
            return f"{governance} And now {opponent} have to swallow the consequences."
        return f"{opponent} were warned. {player} makes them pay for every soft decision."
    if family == "shot":
        return f"{player} smells weakness and {opponent} nearly gift {team} another one."
    if family == "card":
        if board_pressure:
            return f"{board_pressure} and this panic is making it worse."
        return f"That is panic football, plain and simple."
    if family == "substitution":
        return f"That bench move screams damage control from {team}."
    return base_line.strip() or f"The pressure is exposing somebody here, and {team} know it."


def _decorate_with_catchphrase(
    *,
    profile: CommentaryProfileSnapshot,
    context: Mapping[str, Any],
    body: str,
    variant_index: int,
) -> str:
    line = " ".join(body.split()).strip()
    if not profile.catchphrases:
        return line
    importance = int(context.get("importance") or 1)
    should_prefix = bool(context.get("is_major_moment")) or bool(context.get("late_drama")) or importance >= 4
    if not should_prefix:
        return line
    catchphrase = profile.catchphrases[_stable_index(profile=profile, context=context, variant_index=variant_index) % len(profile.catchphrases)]
    if catchphrase.upper() in line.upper():
        return line
    return f"{catchphrase} {line}".strip()


def _render_intensity(*, profile: CommentaryProfileSnapshot, context: Mapping[str, Any]) -> float:
    importance = max(0.0, min(1.0, (int(context.get("importance") or 1) - 1) / 4.0))
    late = 0.16 if bool(context.get("late_drama")) else 0.0
    major = 0.18 if bool(context.get("is_major_moment")) else 0.0
    base = 0.18 + float(profile.tone_intensity) * 0.48 + importance * 0.22 + late + major
    if str(profile.style).lower() == "tactical":
        base -= 0.08
    return round(max(0.18, min(1.0, base)), 3)


def _stable_index(*, profile: CommentaryProfileSnapshot, context: Mapping[str, Any], variant_index: int) -> int:
    digest = hashlib.md5(
        "|".join(
            [
                profile.id,
                str(context.get("match_id") or ""),
                str(context.get("minute") or ""),
                str(context.get("event_type") or ""),
                str(variant_index),
            ]
        ).encode("utf-8")
    ).hexdigest()
    return int(digest[:8], 16)


def _governance_hook(context: Mapping[str, Any]) -> str | None:
    mandate = _label(context.get("governance_story_hook"))
    if mandate:
        return mandate
    formation = _label(context.get("governance_formation"))
    if formation:
        return f"Fans demanded {formation}"
    return None


def _label(value: object | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _name(context: Mapping[str, Any], key: str, *, fallback: str) -> str:
    value = _label(context.get(key))
    return value or fallback
