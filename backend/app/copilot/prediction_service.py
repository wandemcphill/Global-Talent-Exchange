from __future__ import annotations

from typing import Any

from app.copilot.feature_builder import CopilotFeatureBundle
from app.copilot.model_runner import CopilotModelRunner


class CopilotPredictionService:
    def __init__(self, *, model_runner: CopilotModelRunner | None = None) -> None:
        self.model_runner = model_runner or CopilotModelRunner()

    def analyze(self, *, features: CopilotFeatureBundle) -> dict[str, Any]:
        hook_analysis = self._hook_analysis(features=features)
        prediction_result = self.model_runner.run(
            features=features,
            hook_score=float(hook_analysis["hook_score"]),
        )
        return {
            "prediction": {
                "viral_probability": prediction_result.viral_probability,
                "expected_views": prediction_result.expected_views,
                "best_format": prediction_result.best_format,
                "risk_flags": prediction_result.risk_flags,
            },
            "hook_analysis": hook_analysis,
            "format_scores": prediction_result.format_scores,
        }

    def _hook_analysis(self, *, features: CopilotFeatureBundle) -> dict[str, Any]:
        clip_metadata = features.clip_metadata
        intro_seconds = float(clip_metadata.get("intro_seconds") or 1.2)
        visual_intensity = float(clip_metadata.get("visual_intensity") or 0.55)
        event_density = float(clip_metadata.get("event_density") or 0.55)
        has_reaction_overlay = bool(clip_metadata.get("has_reaction_overlay"))
        intro_score = self._clamp(1.0 - (intro_seconds / 3.5), minimum=0.0, maximum=1.0)
        hook_score = self._clamp(
            (intro_score * 0.5)
            + (visual_intensity * 0.24)
            + (event_density * 0.2)
            + (0.06 if has_reaction_overlay else 0.0)
        )

        if intro_seconds > 2.0:
            suggestion = "start with goal moment, not buildup"
        elif event_density < 0.45:
            suggestion = "pack more decisive actions into the opening beat"
        elif visual_intensity < 0.4:
            suggestion = "increase early motion, text, or framing contrast"
        elif not has_reaction_overlay and str(clip_metadata.get("preferred_format") or "") in {"meme", "instant"}:
            suggestion = "add reaction overlay to sharpen the first impression"
        else:
            suggestion = "hook is competitive; keep the payoff inside the first beat"

        intro_strength = "elite" if hook_score >= 0.78 else "solid" if hook_score >= 0.56 else "weak"
        return {
            "hook_score": round(hook_score, 4),
            "suggestion": suggestion,
            "intro_strength": intro_strength,
            "event_density": round(event_density, 4),
            "visual_intensity": round(visual_intensity, 4),
        }

    @staticmethod
    def _clamp(value: float, minimum: float = 0.05, maximum: float = 0.99) -> float:
        return max(minimum, min(value, maximum))


__all__ = ["CopilotPredictionService"]
