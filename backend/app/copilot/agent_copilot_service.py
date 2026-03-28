from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from app.agents.agent_brain import AgentDecisionContext, AgentMomentCandidate, AgentProfile
from app.agents.learning_engine import AgentLearningState
from app.copilot.feature_builder import CopilotFeatureBundle, SUPPORTED_COPILOT_FORMATS
from app.copilot.prediction_service import CopilotPredictionService

FORMAT_KEY_TO_COPILOT_TYPE: dict[str, str] = {
    "instant_clip": "instant",
    "cinematic_replay": "cinematic",
    "debate_clip": "debate",
    "tactical_breakdown": "tactical",
    "meme_version": "meme",
}
COPILOT_TYPE_TO_FORMAT_KEY: dict[str, str] = {value: key for key, value in FORMAT_KEY_TO_COPILOT_TYPE.items()}


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(float(value), maximum))


@dataclass(frozen=True, slots=True)
class AgentCopilotAnalysis:
    viral_probability: float
    expected_views: int
    best_format_key: str
    risk_flags: tuple[str, ...]
    format_scores: dict[str, float]
    confidence: float
    winner_variant_score: float
    global_exposure_feedback: float


@dataclass(slots=True)
class AgentCopilotService:
    prediction_service: CopilotPredictionService | None = None

    def __post_init__(self) -> None:
        if self.prediction_service is None:
            self.prediction_service = CopilotPredictionService()

    def analyze(
        self,
        *,
        profile: AgentProfile,
        learning_state: AgentLearningState,
        context: AgentDecisionContext,
        candidate: AgentMomentCandidate,
    ) -> AgentCopilotAnalysis:
        assert self.prediction_service is not None
        bundle = self._build_features(
            profile=profile,
            learning_state=learning_state,
            context=context,
            candidate=candidate,
        )
        result = self.prediction_service.analyze(features=bundle)
        prediction = dict(result["prediction"])
        raw_scores = dict(result["format_scores"])
        normalized_scores = {
            COPILOT_TYPE_TO_FORMAT_KEY.get(format_type, format_type): round(_clamp(score, 0.0, 1.2), 4)
            for format_type, score in raw_scores.items()
        }
        best_copilot_type = str(prediction.get("best_format") or "instant").strip().lower()
        best_format_key = COPILOT_TYPE_TO_FORMAT_KEY.get(best_copilot_type, "instant_clip")
        winner_variant_score = round(max(normalized_scores.get(best_format_key, 0.0), 0.0), 4)
        global_exposure_feedback = round(max(context.global_exposure_feedback.get(best_format_key, 0.0), 0.0), 4)
        confidence = round(
            _clamp(
                float(prediction.get("viral_probability") or 0.0)
                * (0.80 + (winner_variant_score * 0.30) + (global_exposure_feedback * 0.20)),
                0.0,
                2.0,
            ),
            4,
        )
        return AgentCopilotAnalysis(
            viral_probability=round(float(prediction.get("viral_probability") or 0.0), 4),
            expected_views=max(int(prediction.get("expected_views") or 0), 0),
            best_format_key=best_format_key,
            risk_flags=tuple(str(item) for item in (prediction.get("risk_flags") or [])),
            format_scores=normalized_scores,
            confidence=confidence,
            winner_variant_score=winner_variant_score,
            global_exposure_feedback=global_exposure_feedback,
        )

    def _build_features(
        self,
        *,
        profile: AgentProfile,
        learning_state: AgentLearningState,
        context: AgentDecisionContext,
        candidate: AgentMomentCandidate,
    ) -> CopilotFeatureBundle:
        top_event_types = [
            event_type
            for event_type, _count in Counter(item.event_type for item in context.candidate_pool).most_common(3)
        ]
        favorite_formats = {
            FORMAT_KEY_TO_COPILOT_TYPE.get(format_key, format_key): round(_clamp(score / 2.0, 0.0, 1.0), 4)
            for format_key, score in learning_state.preferred_formats.items()
            if FORMAT_KEY_TO_COPILOT_TYPE.get(format_key, format_key) in SUPPORTED_COPILOT_FORMATS
        }
        format_performance: dict[str, dict[str, float | int]] = {}
        for copilot_type in SUPPORTED_COPILOT_FORMATS:
            format_key = COPILOT_TYPE_TO_FORMAT_KEY[copilot_type]
            preference_score = learning_state.preferred_formats.get(format_key, 0.0)
            winner_score = context.winner_variant_scores.get(format_key, 0.0)
            exposure_feedback = context.global_exposure_feedback.get(format_key, 0.0)
            format_performance[copilot_type] = {
                "avg_viral_score": round(
                    _clamp(0.45 + (preference_score * 0.08) + (winner_score * 0.25) + (exposure_feedback * 0.12), 0.05, 0.99),
                    4,
                ),
                "avg_completion_rate": round(
                    _clamp(0.48 + (preference_score * 0.06), 0.05, 0.99),
                    4,
                ),
                "winner_rate": round(_clamp(winner_score, 0.0, 0.99), 4),
                "sample_size": max(int(learning_state.total_posts), 0),
            }
        preferred_format_key = (
            profile.strategy.preferred_formats[0]
            if profile.strategy.preferred_formats
            else "instant_clip"
        )
        return CopilotFeatureBundle(
            creator_id=profile.identity.agent_id,
            creator_history={
                "avg_views": max(int(learning_state.average_reward * 12_000), 1_000),
                "peak_views": max(int(learning_state.total_rewards * 4_000), 2_000),
                "recent_clip_count": max(int(learning_state.total_posts), 0),
                "recent_formats": dict(learning_state.preferred_formats),
                "insights": {
                    "creator_metrics": {
                        "best_format": FORMAT_KEY_TO_COPILOT_TYPE.get(preferred_format_key, "instant"),
                        "worst_format": None,
                        "avg_share_rate": round(_clamp(learning_state.average_reward / 20.0, 0.0, 0.08), 4),
                        "avg_completion_rate": round(_clamp(0.48 + (learning_state.average_reward * 0.10), 0.0, 0.95), 4),
                        "avg_loop_rate": round(_clamp(learning_state.exploration_rate * 0.35, 0.0, 0.8), 4),
                        "viral_hit_rate": round(_clamp(learning_state.win_streak / 10.0, 0.0, 1.0), 4),
                        "optimal_duration": "0-14s" if profile.strategy.avg_duration <= 14 else "15-20s" if profile.strategy.avg_duration <= 20 else "21-30s",
                    }
                },
            },
            format_performance=format_performance,
            current_trends={
                "tempo": "high" if profile.strategy.tempo == "fast" or candidate.event_type in {"goal", "winner", "equalizer"} else "steady",
                "competition_density": round(_clamp(context.recent_agent_ratio, 0.0, 1.0), 4),
                "top_formats": [
                    FORMAT_KEY_TO_COPILOT_TYPE.get(format_key, format_key)
                    for format_key, _score in sorted(
                        context.winner_variant_scores.items(),
                        key=lambda item: (-item[1], item[0]),
                    )[:3]
                ],
                "top_tags": list(candidate.detected_events[:5]),
                "top_event_types": top_event_types,
                "activity_last_hour": int(context.recent_dispatch_total),
            },
            audience_affinity={
                "favorite_formats": favorite_formats,
                "engagement_score": round(_clamp(0.42 + (learning_state.average_reward * 0.08), 0.0, 1.0), 4),
                "skip_rate": round(_clamp(0.28 - (learning_state.average_reward * 0.04), 0.0, 1.0), 4),
                "session_duration": float(profile.strategy.avg_duration),
                "dominant_cluster": str(profile.strategy.audience_bias or "general"),
            },
            clip_metadata={
                "title": f"{candidate.event_type}:{candidate.minute}",
                "duration_seconds": float(profile.strategy.avg_duration),
                "event_type": candidate.event_type,
                "tags": list(candidate.detected_events),
                "preferred_format": FORMAT_KEY_TO_COPILOT_TYPE.get(preferred_format_key, "instant"),
                "intro_seconds": 0.6 if profile.strategy.tempo == "fast" else 1.1,
                "visual_intensity": round(_clamp(candidate.priority_score / 2.5, 0.0, 1.0), 4),
                "event_density": round(_clamp(max(len(candidate.detected_events), 1) / 4.0, 0.0, 1.0), 4),
                "audience_cluster": str(profile.strategy.audience_bias or "general"),
                "has_reaction_overlay": profile.identity.style in {"chaotic_meme", "instant_reaction", "debate_hunter"},
            },
        )


__all__ = [
    "AgentCopilotAnalysis",
    "AgentCopilotService",
    "COPILOT_TYPE_TO_FORMAT_KEY",
    "FORMAT_KEY_TO_COPILOT_TYPE",
]
