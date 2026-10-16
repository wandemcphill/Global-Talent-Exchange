from __future__ import annotations

from services.influencers.personas import Persona
from services.tts.voice_manager import VoiceManager, VoiceProfile


_VOICE_PRESET_ALIASES = {
    "deep_aggressive": "hype",
    "energetic_african": "african_radio",
    "neutral_analyst": "analyst",
}


def resolve_voice_style(persona: Persona) -> str:
    return _VOICE_PRESET_ALIASES.get(persona.voice, "default")


def resolve_voice_profile(persona: Persona, *, voice_manager: VoiceManager | None = None) -> VoiceProfile:
    manager = voice_manager or VoiceManager({})
    return manager.resolve(resolve_voice_style(persona), tone=persona.tone)
