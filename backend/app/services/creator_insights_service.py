from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import json
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.cache import CacheBackend, NullCacheBackend, build_cache_backend
from app.models.creator_clip_monetization import CreatorClipRevenueAttribution
from app.models.highlight_share import HighlightShareAmplification, HighlightShareExport
from app.models.user import User
from app.viral.analytics import ClipOptimizationFeedback, ViralFeedbackLoopService, track_clip

PROFILE_TTL_SECONDS = 3600
UNKNOWN_FORMAT = "unknown"
UNKNOWN_CLUSTER = "general"


@dataclass(frozen=True, slots=True)
class _ClipInsightRecord:
    export_id: str
    format_key: str | None
    duration_seconds: float | None
    duration_bucket: str | None
    audience_cluster: str | None
    hook_style: str | None
    is_viral: bool
    score: float
    tracked_metrics: dict[str, Any]
    feedback: ClipOptimizationFeedback


class CreatorInsightsService:
    def __init__(
        self,
        session: Session,
        *,
        cache_backend: CacheBackend | None = None,
        feedback_service: ViralFeedbackLoopService | None = None,
    ) -> None:
        self.session = session
        self.cache_backend = cache_backend or build_cache_backend()
        self.feedback_service = feedback_service or ViralFeedbackLoopService.from_settings(get_settings())

    @staticmethod
    def profile_cache_key(creator_id: str) -> str:
        return f"creator:{creator_id}:profile"

    def build_creator_insights(self, *, actor: User, creator_id: str) -> dict[str, Any]:
        records = self._clip_records(actor=actor)
        creator_metrics = self._creator_metrics(records)
        analyzer = self._analyzer(records=records, creator_metrics=creator_metrics)
        viral_feedback_loop = self._feedback_summary(records)
        recommendations = self._recommendations(
            records=records,
            creator_metrics=creator_metrics,
            feedback_summary=viral_feedback_loop,
        )
        payload = {
            "creator_id": creator_id,
            "profile_key": self.profile_cache_key(creator_id),
            "creator_metrics": creator_metrics,
            "analyzer": analyzer,
            "recommendations": recommendations,
            "viral_feedback_loop": viral_feedback_loop,
        }
        self._store_profile(creator_id=creator_id, payload=payload)
        return payload

    def _clip_records(self, *, actor: User) -> list[_ClipInsightRecord]:
        attributions = list(
            self.session.scalars(
                select(CreatorClipRevenueAttribution)
                .where(CreatorClipRevenueAttribution.creator_user_id == actor.id)
                .order_by(CreatorClipRevenueAttribution.created_at.desc())
            ).all()
        )
        if not attributions:
            return []

        export_ids = tuple({item.export_id for item in attributions})
        exports = {
            item.id: item
            for item in self.session.scalars(
                select(HighlightShareExport).where(HighlightShareExport.id.in_(export_ids))
            ).all()
        }
        amplification_rows = list(
            self.session.scalars(
                select(HighlightShareAmplification).where(HighlightShareAmplification.export_id.in_(export_ids))
            ).all()
        )
        amplifications_by_export: dict[str, list[HighlightShareAmplification]] = defaultdict(list)
        for item in amplification_rows:
            amplifications_by_export[item.export_id].append(item)

        records: list[_ClipInsightRecord] = []
        for attribution in attributions:
            export = exports.get(attribution.export_id)
            metadata = dict(attribution.metadata_json or {})
            duration_seconds = self._resolve_duration_seconds(metadata=metadata, export=export)
            format_key = self._resolve_format_key(metadata=metadata, export=export)
            audience_cluster = self._resolve_audience_cluster(
                metadata=metadata,
                export=export,
                amplifications=amplifications_by_export.get(attribution.export_id, []),
            )
            hook_style = self._resolve_hook_style(metadata=metadata)
            metrics_input = self._metrics_input(attribution=attribution, metadata=metadata)
            tracked_metrics = track_clip(attribution.export_id, metrics_input)
            feedback = self.feedback_service.analyze_clip(
                clip_id=attribution.export_id,
                metrics=metrics_input,
                clip_context={
                    "title": self._resolve_title(metadata=metadata, export=export),
                    "duration_seconds": duration_seconds or 1.0,
                    "format": format_key,
                    "hook_style": hook_style,
                    "audience_cluster": audience_cluster,
                    "crowd_spike": bool(metadata.get("crowd_spike")),
                    "late_drama": bool(metadata.get("late_drama")),
                    "upset": bool(metadata.get("upset")),
                    "is_final": bool(metadata.get("is_final")),
                },
            )
            records.append(
                _ClipInsightRecord(
                    export_id=attribution.export_id,
                    format_key=format_key,
                    duration_seconds=duration_seconds,
                    duration_bucket=self._duration_bucket(duration_seconds),
                    audience_cluster=audience_cluster,
                    hook_style=hook_style,
                    is_viral=bool(attribution.is_viral),
                    score=self._performance_score(tracked_metrics=tracked_metrics, feedback=feedback, is_viral=bool(attribution.is_viral)),
                    tracked_metrics=tracked_metrics,
                    feedback=feedback,
                )
            )
        return records

    def _creator_metrics(self, records: list[_ClipInsightRecord]) -> dict[str, Any]:
        if not records:
            return {
                "avg_completion_rate": 0.0,
                "avg_share_rate": 0.0,
                "avg_loop_rate": 0.0,
                "viral_hit_rate": 0.0,
                "best_format": None,
                "worst_format": None,
                "optimal_duration": None,
                "audience_cluster": None,
            }

        format_stats = self._group_stats(records, lambda item: item.format_key)
        duration_stats = self._group_stats(records, lambda item: item.duration_bucket)
        audience_stats = self._group_stats(records, lambda item: item.audience_cluster)

        best_format = self._top_group(format_stats)
        worst_format = self._bottom_group(format_stats)
        dominant_cluster = self._top_group(audience_stats)
        return {
            "avg_completion_rate": self._average(float(item.tracked_metrics["completion_rate"]) for item in records),
            "avg_share_rate": self._average(float(item.tracked_metrics["share_rate"]) for item in records),
            "avg_loop_rate": self._average(float(item.tracked_metrics["loop_rate"]) for item in records),
            "viral_hit_rate": round(sum(1 for item in records if item.is_viral) / len(records), 4),
            "best_format": None if best_format == UNKNOWN_FORMAT else best_format,
            "worst_format": None if worst_format == UNKNOWN_FORMAT else worst_format,
            "optimal_duration": self._top_group(duration_stats),
            "audience_cluster": None if dominant_cluster == UNKNOWN_CLUSTER and not audience_stats else dominant_cluster,
        }

    def _analyzer(self, *, records: list[_ClipInsightRecord], creator_metrics: Mapping[str, Any]) -> dict[str, Any]:
        patterns: list[str] = []
        format_stats = self._group_stats(records, lambda item: item.format_key)
        duration_stats = self._group_stats(records, lambda item: item.duration_bucket)
        hook_stats = self._group_stats(records, lambda item: item.hook_style)

        best_format = self._top_group(format_stats)
        worst_format = self._bottom_group(format_stats)
        if best_format and worst_format and best_format != worst_format:
            uplift = self._relative_lift(
                format_stats[best_format]["avg_score"],
                format_stats[worst_format]["avg_score"],
            )
            patterns.append(f"{best_format} clips outperform {worst_format} by +{uplift}%")

        optimal_duration = creator_metrics.get("optimal_duration")
        if optimal_duration:
            patterns.append(f"Videos {optimal_duration} perform best")

        best_hook = self._top_group(hook_stats)
        worst_hook = self._bottom_group(hook_stats)
        if best_hook and worst_hook and best_hook != worst_hook:
            uplift = self._relative_lift(
                hook_stats[best_hook]["avg_score"],
                hook_stats[worst_hook]["avg_score"],
            )
            patterns.append(f"{best_hook} hooks outperform {worst_hook} by +{uplift}%")

        if not patterns and records:
            patterns.append("Current clip history is too narrow for strong pattern separation yet")
        if not patterns:
            patterns.append("Not enough clip history to detect stable performance patterns yet")

        return {
            "strongest_format": creator_metrics.get("best_format"),
            "patterns": patterns,
            "clips_analyzed": len(records),
        }

    def _recommendations(
        self,
        *,
        records: list[_ClipInsightRecord],
        creator_metrics: Mapping[str, Any],
        feedback_summary: Mapping[str, Any],
    ) -> dict[str, Any]:
        best_duration_bucket = creator_metrics.get("optimal_duration")
        optimal_length = self._optimal_length(records=records, duration_bucket=best_duration_bucket)
        best_hook = self._top_group(self._group_stats(records, lambda item: item.hook_style))
        shorten_signals = int(feedback_summary.get("shorten_clip_signals", 0) or 0)
        increase_similar = int(feedback_summary.get("increase_similar_signals", 0) or 0)
        viral_hit_rate = float(creator_metrics.get("viral_hit_rate", 0.0) or 0.0)
        clip_count = len(records)

        hook_style = best_hook
        if hook_style is None:
            hook_style = "fast-start" if shorten_signals > 0 or (optimal_length is not None and self._as_duration_value(optimal_length) <= 20) else "narrative-build"

        if clip_count >= 3 and (viral_hit_rate >= 0.4 or increase_similar >= 2):
            posting_strategy = "high frequency"
        elif clip_count >= 3:
            posting_strategy = "consistent testing"
        else:
            posting_strategy = "controlled testing"

        return {
            "best_format": creator_metrics.get("best_format"),
            "optimal_length": optimal_length,
            "hook_style": hook_style,
            "posting_strategy": posting_strategy,
        }

    def _feedback_summary(self, records: list[_ClipInsightRecord]) -> dict[str, Any]:
        if not records:
            return {
                "clips_analyzed": 0,
                "high_retention_clips": 0,
                "shorten_clip_signals": 0,
                "caption_adjustment_signals": 0,
                "increase_similar_signals": 0,
                "recommended_actions": [],
            }

        action_counts: Counter[str] = Counter()
        for item in records:
            action_counts.update(item.feedback.actions)
        recommended_actions = [
            action
            for action, _count in sorted(action_counts.items(), key=lambda entry: (-entry[1], entry[0]))[:3]
        ]
        return {
            "clips_analyzed": len(records),
            "high_retention_clips": sum(1 for item in records if item.feedback.performance_tier == "high_retention"),
            "shorten_clip_signals": sum(1 for item in records if item.feedback.shorten_clips),
            "caption_adjustment_signals": sum(1 for item in records if item.feedback.adjust_captions),
            "increase_similar_signals": sum(1 for item in records if item.feedback.increase_similar_clips),
            "recommended_actions": recommended_actions,
        }

    def _store_profile(self, *, creator_id: str, payload: Mapping[str, Any]) -> None:
        if isinstance(self.cache_backend, NullCacheBackend):
            return
        self.cache_backend.set(
            self.profile_cache_key(creator_id),
            json.dumps(payload, default=str),
            PROFILE_TTL_SECONDS,
        )

    def _group_stats(
        self,
        records: list[_ClipInsightRecord],
        key_builder,
    ) -> dict[str, dict[str, float | int]]:
        buckets: dict[str, list[float]] = defaultdict(list)
        for item in records:
            key = key_builder(item)
            if key is None:
                continue
            buckets[str(key)].append(item.score)
        return {
            key: {
                "count": len(scores),
                "avg_score": round(sum(scores) / len(scores), 4),
            }
            for key, scores in buckets.items()
            if scores
        }

    def _top_group(self, stats: Mapping[str, Mapping[str, float | int]]) -> str | None:
        if not stats:
            return None
        return sorted(
            stats.items(),
            key=lambda item: (-float(item[1]["avg_score"]), -int(item[1]["count"]), item[0]),
        )[0][0]

    def _bottom_group(self, stats: Mapping[str, Mapping[str, float | int]]) -> str | None:
        if not stats:
            return None
        return sorted(
            stats.items(),
            key=lambda item: (float(item[1]["avg_score"]), int(item[1]["count"]), item[0]),
        )[0][0]

    @staticmethod
    def _average(values) -> float:
        materialized = list(values)
        if not materialized:
            return 0.0
        return round(sum(materialized) / len(materialized), 4)

    @staticmethod
    def _relative_lift(best_score: float, comparison_score: float) -> int:
        baseline = max(float(comparison_score), 0.1)
        delta = ((float(best_score) - float(comparison_score)) / baseline) * 100
        return max(0, int(round(delta)))

    @staticmethod
    def _performance_score(
        *,
        tracked_metrics: Mapping[str, Any],
        feedback: ClipOptimizationFeedback,
        is_viral: bool,
    ) -> float:
        completion_rate = float(tracked_metrics["completion_rate"])
        share_rate = min(float(tracked_metrics["share_rate"]) / 0.08, 1.0)
        loop_rate = min(float(tracked_metrics["loop_rate"]) / 0.3, 1.0)
        viral_component = 1.0 if is_viral else 0.0
        score = (completion_rate * 0.45) + (share_rate * 0.25) + (loop_rate * 0.2) + (viral_component * 0.1)
        if feedback.increase_similar_clips:
            score += 0.03
        if feedback.shorten_clips:
            score -= 0.03
        return round(max(0.0, min(score, 1.0)), 4)

    def _metrics_input(
        self,
        *,
        attribution: CreatorClipRevenueAttribution,
        metadata: Mapping[str, Any],
    ) -> dict[str, Any]:
        views = max(int(attribution.views or 0), int(metadata.get("views", 0) or 0), 1)
        share_rate = self._as_rate(metadata.get("share_rate"))
        comment_rate = self._as_rate(metadata.get("comment_rate"))
        metrics = dict(metadata)
        metrics.setdefault("views", views)
        metrics.setdefault("completion_rate", metadata.get("completion_rate", metadata.get("completion")))
        metrics.setdefault("loop_rate", metadata.get("loop_rate"))
        if "shares" not in metrics and share_rate is not None:
            metrics["shares"] = int(round(share_rate * views))
        if "comments" not in metrics and comment_rate is not None:
            metrics["comments"] = int(round(comment_rate * views))
        if "watch_time" not in metrics and "avg_watch_time" in metadata:
            metrics["watch_time"] = metadata.get("avg_watch_time")
        return metrics

    def _resolve_format_key(
        self,
        *,
        metadata: Mapping[str, Any],
        export: HighlightShareExport | None,
    ) -> str | None:
        candidates = [
            metadata.get("format"),
            metadata.get("content_format"),
            metadata.get("clip_format"),
            metadata.get("format_key"),
            metadata.get("template_code"),
            metadata.get("template"),
            (export.metadata_json or {}).get("template", {}).get("code") if export is not None else None,
            getattr(export, "aspect_ratio", None),
        ]
        for candidate in candidates:
            normalized = self._normalize_label(candidate)
            if normalized is None:
                continue
            if normalized in {"social-vertical", "9:16"}:
                return "vertical"
            if normalized in {"social-square", "1:1"}:
                return "square"
            if normalized in {"social-landscape", "16:9"}:
                return "landscape"
            return normalized
        return UNKNOWN_FORMAT

    def _resolve_duration_seconds(
        self,
        *,
        metadata: Mapping[str, Any],
        export: HighlightShareExport | None,
    ) -> float | None:
        candidates = [
            metadata.get("duration_seconds"),
            metadata.get("duration"),
            metadata.get("clip_duration_seconds"),
            metadata.get("length_seconds"),
            metadata.get("optimal_length_seconds"),
            (export.metadata_json or {}).get("duration_seconds") if export is not None else None,
        ]
        for value in candidates:
            duration = self._as_float(value)
            if duration is not None and duration > 0:
                return round(duration, 2)
        return None

    def _resolve_audience_cluster(
        self,
        *,
        metadata: Mapping[str, Any],
        export: HighlightShareExport | None,
        amplifications: list[HighlightShareAmplification],
    ) -> str | None:
        candidates = [
            metadata.get("audience_cluster"),
            metadata.get("audience"),
            metadata.get("target_audience"),
        ]
        for candidate in candidates:
            normalized = self._normalize_label(candidate)
            if normalized is not None:
                return normalized

        channel_labels = [
            self._normalize_label(item.channel)
            for item in amplifications
            if self._normalize_label(item.channel) is not None
        ]
        if not channel_labels and export is not None:
            export_channel = self._normalize_label((export.metadata_json or {}).get("distribution_channel"))
            if export_channel is not None:
                channel_labels.append(export_channel)
        if not channel_labels:
            return UNKNOWN_CLUSTER

        primary_channel = Counter(channel_labels).most_common(1)[0][0]
        if primary_channel in {"story-feed", "tiktok", "reels", "shorts"}:
            return "short-form-mobile"
        if primary_channel in {"youtube"}:
            return "lean-back-fans"
        if primary_channel in {"x", "twitter"}:
            return "debate-core"
        return primary_channel

    def _resolve_hook_style(self, *, metadata: Mapping[str, Any]) -> str | None:
        for key in ("hook_style", "hook_profile", "opening_style"):
            normalized = self._normalize_label(metadata.get(key))
            if normalized is not None:
                return normalized
        hook_text = str(metadata.get("hook") or "").strip().lower()
        if hook_text.startswith("fast") or hook_text.startswith("instant"):
            return "fast-start"
        if hook_text.startswith("slow") or hook_text.startswith("build"):
            return "slow-build"
        return None

    def _resolve_title(
        self,
        *,
        metadata: Mapping[str, Any],
        export: HighlightShareExport | None,
    ) -> str:
        for candidate in (metadata.get("title"), metadata.get("share_title"), getattr(export, "share_title", None)):
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return "This clip"

    def _optimal_length(self, *, records: list[_ClipInsightRecord], duration_bucket: str | None) -> str | None:
        if duration_bucket is None:
            return None
        durations = [
            item.duration_seconds
            for item in records
            if item.duration_bucket == duration_bucket and item.duration_seconds is not None
        ]
        if durations:
            return f"{int(round(sum(durations) / len(durations)))}s"
        if "-" in duration_bucket:
            lower, upper = duration_bucket.replace("s", "").split("-", 1)
            return f"{int(round((int(lower) + int(upper)) / 2))}s"
        if duration_bucket.endswith("s+"):
            return duration_bucket
        return None

    @staticmethod
    def _duration_bucket(duration_seconds: float | None) -> str | None:
        if duration_seconds is None:
            return None
        if duration_seconds < 15:
            return "0-14s"
        if duration_seconds <= 20:
            return "15-20s"
        if duration_seconds <= 30:
            return "21-30s"
        if duration_seconds <= 45:
            return "31-45s"
        return "46s+"

    @staticmethod
    def _normalize_label(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip().lower().replace("_", "-")
        return normalized or None

    @staticmethod
    def _as_float(value: object) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _as_rate(self, value: object) -> float | None:
        numeric = self._as_float(value)
        if numeric is None:
            return None
        if numeric > 1.0 and numeric <= 100.0:
            numeric = numeric / 100.0
        return max(0.0, min(numeric, 1.0))

    def _as_duration_value(self, value: str) -> int:
        try:
            return int(value.replace("s", "").replace("+", ""))
        except ValueError:
            return 0


__all__ = ["CreatorInsightsService"]
