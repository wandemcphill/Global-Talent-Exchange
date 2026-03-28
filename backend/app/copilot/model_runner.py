from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.copilot.feature_builder import CopilotFeatureBundle, SUPPORTED_COPILOT_FORMATS


@dataclass(frozen=True, slots=True)
class CopilotPredictionResult:
    viral_probability: float
    expected_views: int
    best_format: str
    risk_flags: list[str]
    format_scores: dict[str, float]


class CopilotModelRunner:
    def run(
        self,
        *,
        features: CopilotFeatureBundle,
        hook_score: float,
    ) -> CopilotPredictionResult:
        creator_metrics = ((features.creator_history.get("insights") or {}).get("creator_metrics") or {})
        clip_metadata = features.clip_metadata
        preferred_format = str(clip_metadata.get("preferred_format") or "instant")
        best_history_format = creator_metrics.get("best_format")
        worst_history_format = creator_metrics.get("worst_format")
        dominant_cluster = features.audience_affinity.get("dominant_cluster")
        format_scores: dict[str, float] = {}

        for format_type in SUPPORTED_COPILOT_FORMATS:
            system_prior = features.format_performance.get(format_type, {})
            audience_preference = float(
                (features.audience_affinity.get("favorite_formats") or {}).get(format_type, 0.0)
            )
            trend_bonus = 0.08 if format_type in set(features.current_trends.get("top_formats") or []) else 0.0
            creator_bonus = 0.18 if format_type == best_history_format else 0.0
            creator_penalty = -0.1 if format_type == worst_history_format else 0.0
            preferred_bonus = 0.08 if format_type == preferred_format else 0.0
            tempo_bonus = self._tempo_bonus(format_type=format_type, tempo=str(features.current_trends.get("tempo") or "steady"))
            duration_bonus = self._duration_bonus(
                format_type=format_type,
                duration_seconds=float(clip_metadata.get("duration_seconds") or 18.0),
            )
            event_bonus = self._event_bonus(
                format_type=format_type,
                event_type=str(clip_metadata.get("event_type") or "goal"),
                dominant_cluster=str(dominant_cluster or "general"),
            )
            overlay_bonus = 0.03 if clip_metadata.get("has_reaction_overlay") and format_type in {"meme", "instant"} else 0.0
            system_score = float(system_prior.get("avg_viral_score", 0.58))
            winner_rate = float(system_prior.get("winner_rate", 0.16))
            format_scores[format_type] = self._clamp(
                0.22
                + (system_score * 0.24)
                + (winner_rate * 0.12)
                + (audience_preference * 0.14)
                + creator_bonus
                + creator_penalty
                + preferred_bonus
                + trend_bonus
                + tempo_bonus
                + duration_bonus
                + event_bonus
                + overlay_bonus
            )

        best_format = sorted(
            format_scores.items(),
            key=lambda item: (-item[1], item[0]),
        )[0][0]
        duration_alignment = self._duration_alignment(
            duration_seconds=float(clip_metadata.get("duration_seconds") or 18.0),
            optimal_bucket=creator_metrics.get("optimal_duration"),
        )
        trend_alignment = self._trend_alignment(features=features, best_format=best_format)
        share_rate_score = self._normalize_ratio(float(creator_metrics.get("avg_share_rate", 0.0)), ceiling=0.08)
        completion_score = self._normalize_ratio(float(creator_metrics.get("avg_completion_rate", 0.0)), ceiling=1.0)
        loop_score = self._normalize_ratio(float(creator_metrics.get("avg_loop_rate", 0.0)), ceiling=1.0)
        viral_hit_rate = self._normalize_ratio(float(creator_metrics.get("viral_hit_rate", 0.0)), ceiling=1.0)
        competition_penalty = float(features.current_trends.get("competition_density", 0.35)) * 0.1

        viral_probability = self._clamp(
            0.12
            + (format_scores[best_format] * 0.3)
            + (hook_score * 0.22)
            + (completion_score * 0.12)
            + (share_rate_score * 0.1)
            + (loop_score * 0.08)
            + (viral_hit_rate * 0.1)
            + (duration_alignment * 0.08)
            + (trend_alignment * 0.08)
            - competition_penalty
        )

        avg_views = float(features.creator_history.get("avg_views", 0.0) or 0.0)
        baseline_views = max(avg_views, 18000.0 if features.creator_history.get("recent_clip_count", 0) < 3 else 4000.0)
        expected_views = int(
            round(
                baseline_views
                * (0.72 + viral_probability)
                * (0.9 + (format_scores[best_format] * 0.38))
            )
        )

        risk_flags = self._risk_flags(
            features=features,
            hook_score=hook_score,
            best_format=best_format,
            preferred_format=preferred_format,
            duration_alignment=duration_alignment,
            trend_alignment=trend_alignment,
            format_scores=format_scores,
        )

        return CopilotPredictionResult(
            viral_probability=round(viral_probability, 4),
            expected_views=max(expected_views, 1000),
            best_format=best_format,
            risk_flags=risk_flags,
            format_scores={key: round(value, 4) for key, value in format_scores.items()},
        )

    def _risk_flags(
        self,
        *,
        features: CopilotFeatureBundle,
        hook_score: float,
        best_format: str,
        preferred_format: str,
        duration_alignment: float,
        trend_alignment: float,
        format_scores: Mapping[str, float],
    ) -> list[str]:
        clip_metadata = features.clip_metadata
        risk_flags: list[str] = []
        if duration_alignment < 0.45:
            duration_seconds = float(clip_metadata.get("duration_seconds") or 0.0)
            risk_flags.append("too long" if duration_seconds > 20 else "too short")
        if hook_score < 0.5:
            risk_flags.append("low hook strength")
        if float(features.current_trends.get("competition_density", 0.0)) >= 0.72:
            risk_flags.append("high competition window")
        if trend_alignment < 0.38:
            risk_flags.append("weak trend alignment")
        if preferred_format != best_format and (format_scores.get(best_format, 0.0) - format_scores.get(preferred_format, 0.0)) >= 0.1:
            risk_flags.append("format mismatch")
        return risk_flags[:4]

    @staticmethod
    def _tempo_bonus(*, format_type: str, tempo: str) -> float:
        if tempo == "high":
            if format_type in {"meme", "instant"}:
                return 0.12
            if format_type == "tactical":
                return -0.08
        if tempo == "steady" and format_type in {"cinematic", "debate"}:
            return 0.04
        return 0.0

    @staticmethod
    def _duration_bonus(*, format_type: str, duration_seconds: float) -> float:
        if duration_seconds <= 18:
            return 0.08 if format_type in {"meme", "instant"} else -0.02 if format_type == "tactical" else 0.0
        if duration_seconds <= 28:
            return 0.05 if format_type in {"debate", "cinematic"} else 0.0
        return 0.06 if format_type == "tactical" else -0.06 if format_type == "meme" else -0.02

    @staticmethod
    def _event_bonus(*, format_type: str, event_type: str, dominant_cluster: str) -> float:
        if event_type in {"goal", "reaction", "upset"} and format_type in {"meme", "instant"}:
            return 0.06
        if event_type in {"analysis", "breakdown"} and format_type in {"tactical", "debate"}:
            return 0.08
        if dominant_cluster.startswith("debate") and format_type == "debate":
            return 0.05
        return 0.0

    @classmethod
    def _duration_alignment(cls, *, duration_seconds: float, optimal_bucket: object) -> float:
        if not isinstance(optimal_bucket, str) or not optimal_bucket.strip():
            return 0.58
        bucket = optimal_bucket.strip().lower()
        if bucket == "0-14s":
            return 1.0 if duration_seconds < 15 else 0.3
        if bucket == "15-20s":
            return 1.0 if 15 <= duration_seconds <= 20 else 0.35
        if bucket == "21-30s":
            return 1.0 if 21 <= duration_seconds <= 30 else 0.4
        if bucket == "31-45s":
            return 1.0 if 31 <= duration_seconds <= 45 else 0.45
        if bucket == "46s+":
            return 1.0 if duration_seconds >= 46 else 0.4
        return 0.58

    @classmethod
    def _trend_alignment(cls, *, features: CopilotFeatureBundle, best_format: str) -> float:
        clip_metadata = features.clip_metadata
        top_formats = set(features.current_trends.get("top_formats") or [])
        top_tags = set(features.current_trends.get("top_tags") or [])
        top_event_types = set(features.current_trends.get("top_event_types") or [])
        event_match = 0.25 if str(clip_metadata.get("event_type") or "") in top_event_types else 0.0
        format_match = 0.35 if best_format in top_formats else 0.0
        tag_overlap = len(set(clip_metadata.get("tags") or []) & top_tags)
        tag_score = min(0.25, tag_overlap * 0.08)
        tempo_score = 0.15 if str(features.current_trends.get("tempo") or "steady") == "high" and best_format in {"meme", "instant"} else 0.08
        return cls._clamp(format_match + event_match + tag_score + tempo_score, minimum=0.0, maximum=1.0)

    @classmethod
    def _normalize_ratio(cls, value: float, *, ceiling: float) -> float:
        if ceiling <= 0:
            return 0.0
        return cls._clamp(value / ceiling)

    @staticmethod
    def _clamp(value: float, minimum: float = 0.05, maximum: float = 0.99) -> float:
        return max(minimum, min(value, maximum))


__all__ = ["CopilotModelRunner", "CopilotPredictionResult"]
