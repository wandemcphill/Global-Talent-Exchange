from __future__ import annotations

from typing import Any, Mapping

from app.copilot.feature_builder import CopilotFeatureBundle, SUPPORTED_COPILOT_FORMATS


class CopilotRecommendationEngine:
    exploration_factor = 0.2

    def recommend(
        self,
        *,
        features: CopilotFeatureBundle,
        prediction: Mapping[str, Any],
        format_scores: Mapping[str, float],
    ) -> dict[str, Any]:
        creator_metrics = ((features.creator_history.get("insights") or {}).get("creator_metrics") or {})
        tempo = str(features.current_trends.get("tempo") or "steady")
        best_format = str(prediction.get("best_format") or "instant")
        sorted_formats = sorted(
            (
                (format_type, float(format_scores.get(format_type, 0.0)))
                for format_type in SUPPORTED_COPILOT_FORMATS
            ),
            key=lambda item: (-item[1], item[0]),
        )

        recommended_variants: list[dict[str, Any]] = []
        rationale: list[str] = []
        selected_formats: set[str] = set()
        for format_type, score in sorted_formats:
            if len(recommended_variants) >= 2:
                break
            if tempo == "high" and format_type == "tactical":
                continue
            recommended_variants.append(
                {
                    "type": format_type,
                    "confidence": round(score, 4),
                    "reason": self._reason_for_format(
                        format_type=format_type,
                        features=features,
                        creator_metrics=creator_metrics,
                        best_format=best_format,
                    ),
                    "exploratory": False,
                }
            )
            selected_formats.add(format_type)

        exploratory_format = self._exploratory_format(
            features=features,
            best_format=best_format,
            selected_formats=selected_formats,
            sorted_formats=sorted_formats,
        )
        if exploratory_format is not None:
            exploratory_score = max(0.45, float(format_scores.get(exploratory_format, 0.45)) - 0.08)
            recommended_variants.append(
                {
                    "type": exploratory_format,
                    "confidence": round(exploratory_score, 4),
                    "reason": "exploration slot preserved to avoid over-optimization lock-in",
                    "exploratory": True,
                }
            )
            selected_formats.add(exploratory_format)

        if tempo == "high":
            rationale.append("Trend tempo is high, so fast-payoff variants are prioritized.")
        if creator_metrics.get("best_format"):
            rationale.append(f"Creator history still leans toward {creator_metrics['best_format']}.")
        rationale.append("One slot stays exploratory so the system keeps creative variance alive.")

        return {
            "recommended_variants": recommended_variants,
            "exploration_factor": self.exploration_factor,
            "rationale": rationale,
        }

    def _exploratory_format(
        self,
        *,
        features: CopilotFeatureBundle,
        best_format: str,
        selected_formats: set[str],
        sorted_formats: list[tuple[str, float]],
    ) -> str | None:
        preferred_format = str(features.clip_metadata.get("preferred_format") or "instant")
        if preferred_format not in selected_formats and preferred_format != best_format:
            return preferred_format
        for format_type, _score in sorted_formats:
            if format_type not in selected_formats and format_type != best_format:
                return format_type
        return None

    def _reason_for_format(
        self,
        *,
        format_type: str,
        features: CopilotFeatureBundle,
        creator_metrics: Mapping[str, Any],
        best_format: str,
    ) -> str:
        if format_type == creator_metrics.get("best_format"):
            return "creator history says this format is the strongest converter"
        if format_type == best_format:
            return "the prediction model sees the highest upside in this format"
        favorite_formats = features.audience_affinity.get("favorite_formats") or {}
        if float(favorite_formats.get(format_type, 0.0)) >= 0.55:
            return "audience affinity is already leaning in this direction"
        if str(features.current_trends.get("tempo") or "steady") == "high" and format_type in {"meme", "instant"}:
            return "current trend tempo rewards immediate payoff and faster cut density"
        return "this adds a second viable lane without drifting too far from the model"


__all__ = ["CopilotRecommendationEngine"]
