from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.clip_variant import ClipVariant
from app.models.creator_clip_monetization import CreatorClipRevenueAttribution
from app.models.user import User
from app.models.user_affinity_profile import UserAffinityProfile
from app.services.creator_insights_service import CreatorInsightsService

SUPPORTED_COPILOT_FORMATS: tuple[str, ...] = ("meme", "instant", "debate", "tactical", "cinematic")
DEFAULT_FORMAT_PERFORMANCE: dict[str, dict[str, float | int]] = {
    "meme": {"avg_viral_score": 0.71, "avg_completion_rate": 0.64, "winner_rate": 0.28, "sample_size": 0},
    "instant": {"avg_viral_score": 0.69, "avg_completion_rate": 0.67, "winner_rate": 0.24, "sample_size": 0},
    "debate": {"avg_viral_score": 0.62, "avg_completion_rate": 0.61, "winner_rate": 0.18, "sample_size": 0},
    "tactical": {"avg_viral_score": 0.55, "avg_completion_rate": 0.58, "winner_rate": 0.14, "sample_size": 0},
    "cinematic": {"avg_viral_score": 0.6, "avg_completion_rate": 0.63, "winner_rate": 0.16, "sample_size": 0},
}


@dataclass(frozen=True, slots=True)
class CopilotFeatureBundle:
    creator_id: str
    creator_history: dict[str, Any]
    format_performance: dict[str, dict[str, float | int]]
    current_trends: dict[str, Any]
    audience_affinity: dict[str, Any]
    clip_metadata: dict[str, Any]


class CopilotFeatureBuilder:
    def __init__(
        self,
        session: Session,
        *,
        insights_service: CreatorInsightsService | None = None,
    ) -> None:
        self.session = session
        self.insights_service = insights_service or CreatorInsightsService(session=session)

    def build(
        self,
        *,
        actor: User,
        creator_id: str,
        draft: Mapping[str, Any],
    ) -> CopilotFeatureBundle:
        creator_history = self._creator_history(actor=actor, creator_id=creator_id)
        return CopilotFeatureBundle(
            creator_id=creator_id,
            creator_history=creator_history,
            format_performance=self._format_performance(),
            current_trends=self._current_trends(),
            audience_affinity=self._audience_affinity(actor=actor, creator_history=creator_history, draft=draft),
            clip_metadata=self._clip_metadata(draft=draft),
        )

    def _creator_history(self, *, actor: User, creator_id: str) -> dict[str, Any]:
        insights_payload = self.insights_service.build_creator_insights(actor=actor, creator_id=creator_id)
        attributions = self._safe_scalars(
            select(CreatorClipRevenueAttribution)
            .where(CreatorClipRevenueAttribution.creator_user_id == actor.id)
            .order_by(CreatorClipRevenueAttribution.created_at.desc())
            .limit(40)
        )
        recent_formats: Counter[str] = Counter()
        total_views = 0
        peak_views = 0
        for item in attributions:
            metadata = dict(item.metadata_json or {})
            format_key = self._normalized_label(metadata.get("format"))
            if format_key:
                recent_formats[format_key] += 1
            total_views += int(item.views or 0)
            peak_views = max(peak_views, int(item.views or 0))
        clip_count = len(attributions)
        return {
            "insights": insights_payload,
            "avg_views": round(total_views / clip_count, 2) if clip_count else 0.0,
            "peak_views": peak_views,
            "recent_clip_count": clip_count,
            "recent_formats": dict(recent_formats),
        }

    def _format_performance(self) -> dict[str, dict[str, float | int]]:
        variants = self._safe_scalars(
            select(ClipVariant).order_by(ClipVariant.created_at.desc()).limit(240)
        )
        if not variants:
            return {
                format_type: dict(values)
                for format_type, values in DEFAULT_FORMAT_PERFORMANCE.items()
            }

        scores: dict[str, list[float]] = defaultdict(list)
        completion: dict[str, list[float]] = defaultdict(list)
        winners: Counter[str] = Counter()
        sample_size: Counter[str] = Counter()
        for variant in variants:
            format_type = self._normalized_label(variant.format_type)
            if format_type not in SUPPORTED_COPILOT_FORMATS:
                continue
            scores[format_type].append(self._normalize_variant_score(variant.viral_score))
            completion[format_type].append(self._clamp(float(variant.completion_rate or 0.0)))
            sample_size[format_type] += 1
            if variant.is_winner:
                winners[format_type] += 1

        payload: dict[str, dict[str, float | int]] = {}
        for format_type in SUPPORTED_COPILOT_FORMATS:
            if sample_size[format_type] == 0:
                payload[format_type] = dict(DEFAULT_FORMAT_PERFORMANCE[format_type])
                continue
            payload[format_type] = {
                "avg_viral_score": round(sum(scores[format_type]) / len(scores[format_type]), 4),
                "avg_completion_rate": round(sum(completion[format_type]) / len(completion[format_type]), 4),
                "winner_rate": round(winners[format_type] / sample_size[format_type], 4),
                "sample_size": int(sample_size[format_type]),
            }
        return payload

    def _current_trends(self) -> dict[str, Any]:
        recent_attributions = self._safe_scalars(
            select(CreatorClipRevenueAttribution)
            .order_by(CreatorClipRevenueAttribution.created_at.desc())
            .limit(160)
        )
        if not recent_attributions:
            return {
                "tempo": "steady",
                "competition_density": 0.35,
                "top_formats": ["instant", "meme"],
                "top_tags": [],
                "top_event_types": [],
                "activity_last_hour": 0,
            }

        now = datetime.now(UTC)
        last_hour_cutoff = now - timedelta(hours=1)
        durations: list[float] = []
        share_rates: list[float] = []
        format_counts: Counter[str] = Counter()
        tag_counts: Counter[str] = Counter()
        event_counts: Counter[str] = Counter()
        activity_last_hour = 0

        for item in recent_attributions:
            metadata = dict(item.metadata_json or {})
            duration_seconds = self._as_float(metadata.get("duration_seconds"))
            if duration_seconds > 0:
                durations.append(duration_seconds)
            share_rate = self._as_float(metadata.get("share_rate"))
            if share_rate > 0:
                share_rates.append(share_rate)
            format_key = self._normalized_label(metadata.get("format"))
            if format_key in SUPPORTED_COPILOT_FORMATS:
                format_counts[format_key] += 1
            event_type = self._normalized_label(metadata.get("event_type"))
            if event_type:
                event_counts[event_type] += 1
            tag_counts.update(self._normalized_tags(metadata.get("tags")))
            created_at = self._to_utc(getattr(item, "created_at", None))
            if created_at is not None and created_at >= last_hour_cutoff:
                activity_last_hour += 1

        avg_duration = sum(durations) / len(durations) if durations else 22.0
        avg_share_rate = sum(share_rates) / len(share_rates) if share_rates else 0.025
        competition_density = self._clamp(activity_last_hour / 18.0)
        tempo = "high" if avg_duration <= 20.0 or avg_share_rate >= 0.045 else "steady"
        return {
            "tempo": tempo,
            "competition_density": round(competition_density, 4),
            "top_formats": [format_type for format_type, _count in format_counts.most_common(3)],
            "top_tags": [tag for tag, _count in tag_counts.most_common(5)],
            "top_event_types": [event_type for event_type, _count in event_counts.most_common(3)],
            "activity_last_hour": activity_last_hour,
        }

    def _audience_affinity(
        self,
        *,
        actor: User,
        creator_history: Mapping[str, Any],
        draft: Mapping[str, Any],
    ) -> dict[str, Any]:
        profile = self.session.get(UserAffinityProfile, actor.id)
        state = dict(profile.state_json or {}) if profile is not None else {}
        dominant_cluster = (
            self._normalized_label(state.get("audience_cluster"))
            or self._normalized_label(state.get("cluster"))
            or self._normalized_label(draft.get("audience_cluster"))
            or self._normalized_label(
                ((creator_history.get("insights") or {}).get("creator_metrics") or {}).get("audience_cluster")
            )
            or "general"
        )
        favorite_formats = self._normalized_score_map(
            profile.favorite_formats_json if profile is not None else {}
        )
        return {
            "favorite_formats": favorite_formats,
            "engagement_score": self._clamp(self._as_float(getattr(profile, "engagement_score", 0.42))),
            "skip_rate": self._clamp(self._as_float(getattr(profile, "skip_rate", 0.24))),
            "session_duration": max(self._as_float(getattr(profile, "session_duration", 0.0)), 0.0),
            "dominant_cluster": dominant_cluster,
        }

    def _clip_metadata(self, *, draft: Mapping[str, Any]) -> dict[str, Any]:
        preferred_format = self._normalized_label(draft.get("preferred_format")) or "instant"
        return {
            "title": str(draft.get("title") or "Untitled draft"),
            "duration_seconds": max(self._as_float(draft.get("duration_seconds")), 1.0),
            "event_type": self._normalized_label(draft.get("event_type")) or "goal",
            "tags": self._normalized_tags(draft.get("tags")),
            "preferred_format": preferred_format,
            "intro_seconds": self._clamp(self._as_float(draft.get("intro_seconds")), minimum=0.0, maximum=12.0),
            "visual_intensity": self._clamp(self._as_float(draft.get("visual_intensity")), minimum=0.0, maximum=1.0),
            "event_density": self._clamp(self._as_float(draft.get("event_density")), minimum=0.0, maximum=1.0),
            "audience_cluster": self._normalized_label(draft.get("audience_cluster")) or "general",
            "has_reaction_overlay": bool(draft.get("has_reaction_overlay")),
        }

    def _safe_scalars(self, stmt) -> list[Any]:
        try:
            return list(self.session.scalars(stmt).all())
        except SQLAlchemyError:
            return []

    @staticmethod
    def _normalized_label(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip().lower().replace("_", "-")
        return normalized or None

    @staticmethod
    def _normalized_tags(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        tags: list[str] = []
        for item in value:
            if not isinstance(item, str):
                continue
            normalized = item.strip().lower().replace("_", "-")
            if normalized:
                tags.append(normalized)
        return tags

    @classmethod
    def _normalized_score_map(cls, value: Mapping[str, Any] | None) -> dict[str, float]:
        if not isinstance(value, Mapping):
            return {}
        payload: dict[str, float] = {}
        for key, raw_value in value.items():
            normalized_key = cls._normalized_label(key)
            if normalized_key is None:
                continue
            payload[normalized_key] = cls._clamp(cls._as_float(raw_value))
        return payload

    @staticmethod
    def _normalize_variant_score(value: object) -> float:
        numeric = CopilotFeatureBuilder._as_float(value)
        if numeric > 1.0:
            numeric = numeric / 100.0
        return CopilotFeatureBuilder._clamp(numeric)

    @staticmethod
    def _to_utc(value: object) -> datetime | None:
        if not isinstance(value, datetime):
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _as_float(value: object) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
        return max(minimum, min(value, maximum))


__all__ = ["CopilotFeatureBuilder", "CopilotFeatureBundle", "SUPPORTED_COPILOT_FORMATS"]
