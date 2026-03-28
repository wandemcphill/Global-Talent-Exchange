from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping

from app.copilot.feature_builder import CopilotFeatureBundle


class CopilotTimingEngine:
    def evaluate(
        self,
        *,
        features: CopilotFeatureBundle,
        prediction: Mapping[str, Any],
        hook_analysis: Mapping[str, Any],
        now: datetime | None = None,
    ) -> dict[str, Any]:
        resolved_now = now.astimezone(UTC) if isinstance(now, datetime) and now.tzinfo is not None else now or datetime.now(UTC)
        hour = resolved_now.hour
        competition_density = float(features.current_trends.get("competition_density", 0.35))
        engagement_score = float(features.audience_affinity.get("engagement_score", 0.42))
        skip_rate = float(features.audience_affinity.get("skip_rate", 0.24))

        time_window_bonus = 0.22 if 17 <= hour <= 22 else 0.12 if 11 <= hour <= 14 else 0.04
        audience_activity = self._clamp(0.32 + (engagement_score * 0.42) + time_window_bonus - (skip_rate * 0.12))
        hook_score = float(hook_analysis.get("hook_score", 0.5))
        viral_probability = float(prediction.get("viral_probability", 0.5))
        post_now = (
            viral_probability >= 0.68
            and hook_score >= 0.55
            and competition_density < 0.68
            and audience_activity >= 0.5
        )
        if post_now:
            best_time_in_minutes = 0
            reason = "current audience activity is healthy and competition pressure is still manageable"
        elif competition_density >= 0.72:
            best_time_in_minutes = max(18, int(round((competition_density * 36) - (audience_activity * 8))))
            reason = "high competition window"
        elif audience_activity < 0.45:
            best_time_in_minutes = max(12, int(round((0.5 - audience_activity) * 60)))
            reason = "audience activity is still ramping"
        else:
            best_time_in_minutes = max(8, int(round((competition_density * 24) + 6)))
            reason = "waiting slightly improves the first test window"

        return {
            "post_now": post_now,
            "best_time_in_minutes": best_time_in_minutes,
            "reason": reason,
            "competition_density": round(competition_density, 4),
            "audience_activity": round(audience_activity, 4),
        }

    @staticmethod
    def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
        return max(minimum, min(value, maximum))


__all__ = ["CopilotTimingEngine"]
