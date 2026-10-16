from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class Persona:
    name: str
    tone: str
    voice: str
    signature: str
    cadence: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


PERSONAS: tuple[Persona, ...] = (
    Persona(
        name="Coach Rage",
        tone="angry, blunt",
        voice="deep_aggressive",
        signature="This defending is criminal.",
        cadence="short_bursts",
    ),
    Persona(
        name="Street Analyst",
        tone="pidgin, hype",
        voice="energetic_african",
        signature="Omo, this match no get respect for structure.",
        cadence="hype_run_on",
    ),
    Persona(
        name="Professor XG",
        tone="calm, tactical",
        voice="neutral_analyst",
        signature="The spacing tells the real story.",
        cadence="measured_breakdown",
    ),
)


def list_personas() -> tuple[Persona, ...]:
    return PERSONAS


def get_persona(name: str) -> Persona:
    normalized = name.strip().lower()
    for persona in PERSONAS:
        if persona.name.lower() == normalized:
            return persona
    raise KeyError(f"Unknown persona: {name}")


def select_persona(
    clip: Mapping[str, object],
    *,
    story_tags: Sequence[str] = (),
) -> Persona:
    event_type = str(clip.get("event_type") or "").strip().lower()
    tags = {str(tag).strip().lower() for tag in story_tags if str(tag).strip()}
    if "rivalry" in tags or event_type == "red_card":
        return get_persona("Coach Rage")
    if "underdog" in tags or int(clip.get("viral_score") or 0) >= 85:
        return get_persona("Street Analyst")
    if event_type == "winner":
        return get_persona("Coach Rage")
    return get_persona("Professor XG")
