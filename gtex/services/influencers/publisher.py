from __future__ import annotations

from typing import Any, Mapping, Sequence

from services.influencers.avatar import AvatarSpec, build_avatar_spec
from services.influencers.personas import Persona, get_persona, select_persona
from services.influencers.voice import resolve_voice_profile, resolve_voice_style
from services.publisher.scheduler import PublisherSchedulePolicy, build_publish_jobs


def _persona_intro(persona: Persona) -> str:
    if persona.name == "Coach Rage":
        return "This back line has lost all discipline."
    if persona.name == "Street Analyst":
        return "Omo, see drama. This match dey move mad."
    return "The tactical tradeoffs are the real headline here."


def _build_script(persona: Persona, clip: Mapping[str, Any], *, story_tags: Sequence[str]) -> str:
    player = str(clip.get("player_name") or "somebody").strip()
    team = str(clip.get("team_name") or "the team").strip()
    opponent = str(clip.get("opponent_name") or "their rivals").strip()
    event_type = str(clip.get("event_type") or "moment").replace("_", " ").strip()
    tags = ", ".join(sorted({str(tag).strip() for tag in story_tags if str(tag).strip()}))
    ending = persona.signature
    if persona.name == "Street Analyst":
        return f"{_persona_intro(persona)} {player} just gave {team} one {event_type} against {opponent}. Storyline: {tags or 'chaos'}."
    if persona.name == "Coach Rage":
        return f"{_persona_intro(persona)} {team} got a {event_type} through {player} against {opponent}. {ending}"
    return f"{_persona_intro(persona)} {player} changed the geometry for {team} against {opponent} with that {event_type}. Context: {tags or 'momentum swing'}."


def generate_persona_content(
    persona: Persona | str,
    clip: Mapping[str, Any],
    *,
    story_tags: Sequence[str] = (),
) -> dict[str, Any]:
    resolved_persona = get_persona(persona) if isinstance(persona, str) else persona
    voice_profile = resolve_voice_profile(resolved_persona)
    avatar = build_avatar_spec(resolved_persona)
    script = _build_script(resolved_persona, clip, story_tags=story_tags)
    caption = f"{resolved_persona.name}: {script}"
    return {
        "persona": resolved_persona.as_dict(),
        "caption": caption,
        "audio_script": script,
        "voice_style": resolve_voice_style(resolved_persona),
        "voice_id": voice_profile.voice_id,
        "voice_settings": voice_profile.as_settings(),
        "avatar": avatar.as_dict(),
        "hashtags": (
            "#gtex",
            f"#{resolved_persona.name.replace(' ', '')}",
            "#football",
        ),
    }


def build_publishable_persona_clip(
    clip: Mapping[str, Any],
    *,
    persona: Persona | str | None = None,
    story_tags: Sequence[str] = (),
    talking_head: bool = False,
) -> dict[str, Any]:
    resolved_persona = (
        get_persona(persona)
        if isinstance(persona, str)
        else persona
        if persona is not None
        else select_persona(clip, story_tags=story_tags)
    )
    avatar: AvatarSpec = build_avatar_spec(resolved_persona, talking_head=talking_head)
    persona_payload = generate_persona_content(resolved_persona, clip, story_tags=story_tags)
    clip_id = str(clip.get("clip_id") or clip.get("match_id") or "persona_clip")
    existing_tags = tuple(str(tag) for tag in clip.get("hashtags") or () if str(tag).strip())
    combined_tags = tuple(dict.fromkeys((*existing_tags, *persona_payload["hashtags"])))
    metadata = dict(clip.get("metadata") or {})
    metadata["persona"] = resolved_persona.as_dict()
    metadata["avatar"] = avatar.as_dict()
    metadata["audio_script"] = persona_payload["audio_script"]
    metadata["voice_style"] = persona_payload["voice_style"]
    return {
        **dict(clip),
        "clip_id": f"{clip_id}_{resolved_persona.name.lower().replace(' ', '_')}",
        "caption": persona_payload["caption"],
        "raw_caption": persona_payload["caption"],
        "polished_caption": persona_payload["caption"],
        "hashtags": combined_tags,
        "metadata": metadata,
    }


def build_persona_publish_jobs(
    clip: Mapping[str, Any],
    *,
    persona: Persona | str | None = None,
    story_tags: Sequence[str] = (),
    policy: PublisherSchedulePolicy | None = None,
) -> list[Any]:
    publishable = build_publishable_persona_clip(clip, persona=persona, story_tags=story_tags)
    return build_publish_jobs(publishable, policy=policy)
