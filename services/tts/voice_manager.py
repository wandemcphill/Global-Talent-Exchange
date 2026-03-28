from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class VoiceProfile:
    preset: str
    voice_id: str
    stability: float = 0.4
    similarity_boost: float = 0.8
    style: float | None = None
    speaker_boost: bool | None = None

    def as_settings(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "stability": self.stability,
            "similarity_boost": self.similarity_boost,
        }
        if self.style is not None:
            payload["style"] = self.style
        if self.speaker_boost is not None:
            payload["use_speaker_boost"] = self.speaker_boost
        return payload


class VoiceManager:
    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        env = environ or {}
        self._presets: dict[str, VoiceProfile] = {
            "default": VoiceProfile(
                preset="default",
                voice_id=env.get("GTE_TTS_VOICE_DEFAULT", "football-commentator"),
                stability=float(env.get("GTE_TTS_VOICE_DEFAULT_STABILITY", "0.40")),
                similarity_boost=float(env.get("GTE_TTS_VOICE_DEFAULT_SIMILARITY", "0.80")),
            ),
            "hype": VoiceProfile(
                preset="hype",
                voice_id=env.get("GTE_TTS_VOICE_HYPE", "excited-commentator"),
                stability=float(env.get("GTE_TTS_VOICE_HYPE_STABILITY", "0.32")),
                similarity_boost=float(env.get("GTE_TTS_VOICE_HYPE_SIMILARITY", "0.86")),
                style=float(env.get("GTE_TTS_VOICE_HYPE_STYLE", "0.75")),
            ),
            "calm": VoiceProfile(
                preset="calm",
                voice_id=env.get("GTE_TTS_VOICE_CALM", "analysis-voice"),
                stability=float(env.get("GTE_TTS_VOICE_CALM_STABILITY", "0.52")),
                similarity_boost=float(env.get("GTE_TTS_VOICE_CALM_SIMILARITY", "0.72")),
            ),
            "african_radio": VoiceProfile(
                preset="african_radio",
                voice_id=env.get("GTE_TTS_VOICE_AFRICAN_RADIO", "pidgin-energy"),
                stability=float(env.get("GTE_TTS_VOICE_AFRICAN_STABILITY", "0.36")),
                similarity_boost=float(env.get("GTE_TTS_VOICE_AFRICAN_SIMILARITY", "0.84")),
                style=float(env.get("GTE_TTS_VOICE_AFRICAN_STYLE", "0.68")),
            ),
            "play_by_play": VoiceProfile(
                preset="play_by_play",
                voice_id=env.get("GTE_TTS_VOICE_PLAY_BY_PLAY", env.get("GTE_TTS_VOICE_DEFAULT", "football-commentator")),
                stability=float(env.get("GTE_TTS_VOICE_PLAY_BY_PLAY_STABILITY", "0.40")),
                similarity_boost=float(env.get("GTE_TTS_VOICE_PLAY_BY_PLAY_SIMILARITY", "0.82")),
            ),
            "analyst": VoiceProfile(
                preset="analyst",
                voice_id=env.get("GTE_TTS_VOICE_ANALYST", env.get("GTE_TTS_VOICE_CALM", "analysis-voice")),
                stability=float(env.get("GTE_TTS_VOICE_ANALYST_STABILITY", "0.56")),
                similarity_boost=float(env.get("GTE_TTS_VOICE_ANALYST_SIMILARITY", "0.74")),
            ),
        }

    def available_presets(self) -> tuple[str, ...]:
        return tuple(sorted(self._presets))

    def resolve(
        self,
        requested: str | None,
        *,
        tone: str | None = None,
        commentator: str | None = None,
    ) -> VoiceProfile:
        normalized_request = str(requested or "").strip().lower()
        if normalized_request in self._presets:
            return self._presets[normalized_request]
        normalized_commentator = str(commentator or "").strip().lower()
        if normalized_commentator in self._presets:
            return self._presets[normalized_commentator]
        if normalized_commentator == "lead":
            return self._presets["play_by_play"]
        if normalized_commentator == "analysis":
            return self._presets["analyst"]
        normalized_tone = str(tone or "").strip().lower()
        if normalized_tone == "hype":
            return self._presets["hype"]
        if normalized_tone in {"analysis", "analytical", "calm", "tactical"}:
            return self._presets["calm"]
        if normalized_request:
            return VoiceProfile(preset=normalized_request, voice_id=normalized_request)
        return self._presets["default"]
