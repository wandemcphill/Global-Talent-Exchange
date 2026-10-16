from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.broadcast_network.schemas import BroadcastAudioManifestView, BroadcastAudioStemFrameView
from app.live_matches.schemas import LiveMatchStreamEventView


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


@dataclass(slots=True)
class CommentaryOrchestratorService:
    def build_manifest(
        self,
        *,
        match_id: str | None,
        channel_id: str | None = None,
        lead_voice_profile: str = "play_by_play",
        analyst_voice_profile: str = "analyst",
    ) -> BroadcastAudioManifestView:
        return BroadcastAudioManifestView(
            channel_id=channel_id,
            match_id=match_id,
            primary_voice_profile=lead_voice_profile,
            secondary_voice_profile=analyst_voice_profile,
            metadata={
                "dual_commentary_enabled": True,
                "interrupt_mode": "priority_staggered",
            },
        )

    def build_frames(
        self,
        events: Iterable[LiveMatchStreamEventView],
        *,
        channel_id: str | None = None,
    ) -> list[BroadcastAudioStemFrameView]:
        frames: list[BroadcastAudioStemFrameView] = []
        for event in events:
            if event.match_id is None:
                continue
            presentation_second = int(event.presentation_second or 0)
            sequence_id = int(event.sequence_id or event.sequence or 0) or None
            source_event_id = event.source_event_id or event.event_id
            commentary = event.experience.commentary if event.experience is not None else None
            crowd = event.experience.crowd if event.experience is not None else None
            crowd_mood = crowd.crowd_mood if crowd is not None else "tense"
            crowd_fx = crowd.stadium_fx if crowd is not None else "ambient_loop"
            importance = float(event.importance_score or event.meta.get("importance", 1.0) or 1.0)
            lead_voice = commentary.voice_profile if commentary is not None and commentary.voice_profile else "play_by_play"
            analyst_voice = "analyst"
            intensity = commentary.intensity if commentary is not None else _clamp((importance / 5.0), 0.2, 1.0)
            interrupt_priority = commentary.interrupt_priority if commentary is not None else self._interrupt_priority(event)

            if commentary is not None and commentary.line.strip():
                frames.append(
                    BroadcastAudioStemFrameView(
                        frame_id=f"{event.match_id}:{source_event_id or presentation_second}:commentary:lead",
                        channel_id=channel_id,
                        match_id=event.match_id,
                        stem_type="commentary",
                        source_event_id=source_event_id,
                        sequence_id=sequence_id,
                        presentation_second=presentation_second,
                        offset_ms=0,
                        intensity=round(float(intensity), 3),
                        cue_text=commentary.line,
                        speaker_role=commentary.speaker_role or commentary.commentator,
                        voice_profile=lead_voice,
                        voice_id=commentary.voice_id or lead_voice,
                        accent=commentary.accent,
                        speech_rate=float(commentary.speech_rate or self._speech_rate(commentary.tone, importance)),
                        interrupt_priority=interrupt_priority,
                        metadata={
                            "tone": commentary.tone,
                            "audio_channel": commentary.audio_channel,
                            "stem_routing": commentary.stem_routing,
                        },
                    )
                )
                if commentary.banter_layer:
                    frames.append(
                        BroadcastAudioStemFrameView(
                            frame_id=f"{event.match_id}:{source_event_id or presentation_second}:commentary:analyst",
                            channel_id=channel_id,
                            match_id=event.match_id,
                            stem_type="commentary",
                            source_event_id=source_event_id,
                            sequence_id=sequence_id,
                            presentation_second=presentation_second,
                            offset_ms=650,
                            intensity=round(max(float(intensity) - 0.12, 0.25), 3),
                            cue_text=self._analyst_line(event),
                            speaker_role="analyst",
                            voice_profile=analyst_voice,
                            voice_id=analyst_voice,
                            accent="neutral",
                            speech_rate=0.94,
                            interrupt_priority=max(interrupt_priority - 10, 0),
                            metadata={"interrupts": True},
                        )
                    )

            if crowd is not None:
                frames.append(
                    BroadcastAudioStemFrameView(
                        frame_id=f"{event.match_id}:{source_event_id or presentation_second}:crowd",
                        channel_id=channel_id,
                        match_id=event.match_id,
                        stem_type="crowd",
                        source_event_id=source_event_id,
                        sequence_id=sequence_id,
                        presentation_second=presentation_second,
                        offset_ms=0,
                        intensity=float(crowd.crowd_intensity or crowd.chant_level),
                        cue_text=crowd_mood,
                        interrupt_priority=max(interrupt_priority - 20, 0),
                        metadata={
                            "dominant_side": crowd.dominant_side,
                            "stadium_theme": crowd.stadium_theme,
                            "region_personality": crowd.region_personality,
                            "crowd_bias": crowd.crowd_bias,
                            "crowd_mood": crowd.crowd_mood,
                        },
                    )
                )
                frames.append(
                    BroadcastAudioStemFrameView(
                        frame_id=f"{event.match_id}:{source_event_id or presentation_second}:stadium_fx",
                        channel_id=channel_id,
                        match_id=event.match_id,
                        stem_type="stadium_fx",
                        source_event_id=source_event_id,
                        sequence_id=sequence_id,
                        presentation_second=presentation_second,
                        offset_ms=120,
                        intensity=float(crowd.crowd_intensity or crowd.chant_level),
                        cue_text=crowd_fx,
                        interrupt_priority=max(interrupt_priority - 5, 0),
                        metadata={"stadium_fx": crowd_fx},
                    )
                )
        return frames

    @staticmethod
    def _speech_rate(tone: str, importance: float) -> float:
        if tone in {"high_intensity", "dramatic", "hype"}:
            return round(_clamp(1.05 + (importance * 0.04), 1.0, 1.35), 3)
        return round(_clamp(0.92 + (importance * 0.02), 0.85, 1.1), 3)

    @staticmethod
    def _interrupt_priority(event: LiveMatchStreamEventView) -> int:
        raw_type = str(event.source_event_type or event.event_type or "").lower()
        if raw_type in {"goal", "penalty_goal", "penalty_scored"}:
            return 95
        if raw_type in {"red_card", "card"}:
            return 80
        if event.highlight_eligible:
            return 70
        return 35

    @staticmethod
    def _analyst_line(event: LiveMatchStreamEventView) -> str:
        team = event.team or "the side in possession"
        if event.event_type == "goal":
            return f"That move opened up because {team} attacked the weak lane."
        if event.event_type == "card":
            return f"{team} have to manage the emotional swing now."
        return f"{team} are changing the pressure profile of the match."


__all__ = ["CommentaryOrchestratorService"]
