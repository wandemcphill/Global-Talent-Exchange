from __future__ import annotations

from dataclasses import dataclass

from app.agents.agent_brain import AgentDecision, AgentProfile


FORMAT_STYLE_PRESETS: dict[str, tuple[str, str]] = {
    "instant_clip": ("instant_clip", "snap_replay"),
    "cinematic_replay": ("cinematic_replay", "hero_arc"),
    "debate_clip": ("debate_clip", "question_hook"),
    "tactical_breakdown": ("tactical_breakdown", "freeze_frame"),
    "meme_version": ("meme_version", "reaction_loop"),
}


@dataclass(frozen=True, slots=True)
class VariantPlan:
    format_key: str
    title: str
    description: str
    overlay_text: str
    style_preset: str
    narrative_device: str
    commentary_prompt: str | None = None


class VariantPlanner:
    def plan(self, *, profile: AgentProfile, decision: AgentDecision) -> list[VariantPlan]:
        if decision.candidate is None:
            return []
        candidate = decision.candidate
        variants: list[VariantPlan] = []
        for format_key in decision.selected_formats:
            style_preset, narrative_device = FORMAT_STYLE_PRESETS.get(format_key, ("instant_clip", "raw_moment"))
            overlay_text = self._overlay_text(profile=profile, decision=decision, format_key=format_key)
            variants.append(
                VariantPlan(
                    format_key=format_key,
                    title=self._title(format_key, candidate.event_type),
                    description=f"{profile.identity.display_name} pushes a {format_key.replace('_', ' ')} treatment.",
                    overlay_text=overlay_text,
                    style_preset=style_preset,
                    narrative_device=narrative_device,
                    commentary_prompt=self._commentary_prompt(profile=profile, format_key=format_key),
                )
            )
        return variants

    @staticmethod
    def _title(format_key: str, event_type: str) -> str:
        format_label = format_key.replace("_", " ")
        return f"{format_label.title()} for {event_type.replace('_', ' ')}"

    @staticmethod
    def _overlay_text(*, profile: AgentProfile, decision: AgentDecision, format_key: str) -> str:
        if decision.candidate is None:
            return profile.identity.display_name
        subject = decision.candidate.player_name or decision.candidate.team_name or "This moment"
        if format_key == "meme_version":
            return f"{subject} just broke the timeline"
        if format_key == "debate_clip":
            return "Was this the real turning point?"
        if format_key == "tactical_breakdown":
            return "Pause here. The shape changed everything."
        if format_key == "cinematic_replay":
            return f"{subject} in full focus"
        return f"{subject} right now"

    @staticmethod
    def _commentary_prompt(*, profile: AgentProfile, format_key: str) -> str:
        style_label = profile.identity.style.replace("_", " ")
        if format_key == "debate_clip":
            return f"Open with a polarizing question in a {style_label} voice."
        if format_key == "tactical_breakdown":
            return f"Explain the tactical swing in one sharp sentence with {style_label} tone."
        if format_key == "meme_version":
            return f"Write a punchy reaction caption in {style_label} tone."
        return f"Keep the commentary concise and high-tempo in {style_label} tone."


__all__ = [
    "VariantPlan",
    "VariantPlanner",
]
