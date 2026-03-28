from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.clip_variant import ClipVariant
from app.viral.analytics import track_clip
from app.viral.comparator import ViralVariantScoringComparator
from app.viral.editor import ViralContentFormatPlan

CLIP_ID_SEPARATOR = "::"

FORMAT_KEY_TO_VARIANT_TYPE: dict[str, str] = {
    "instant_clip": "instant",
    "cinematic_replay": "cinematic",
    "debate_clip": "debate",
    "tactical_breakdown": "tactical",
    "meme_version": "meme",
}


@dataclass(frozen=True, slots=True)
class VariantMetricProfile:
    view_multiplier: float
    watch_multiplier: float
    loop_multiplier: float
    share_multiplier: float
    comment_multiplier: float
    completion_delta: float
    drop_off_multiplier: float


_VARIANT_METRIC_PROFILES: dict[str, VariantMetricProfile] = {
    "instant": VariantMetricProfile(0.24, 0.84, 0.94, 1.10, 0.92, 0.03, 0.86),
    "cinematic": VariantMetricProfile(0.18, 1.18, 0.82, 0.86, 0.96, 0.07, 1.08),
    "debate": VariantMetricProfile(0.16, 0.90, 0.88, 0.94, 1.34, -0.03, 0.80),
    "tactical": VariantMetricProfile(0.14, 1.22, 0.76, 0.74, 1.12, -0.05, 1.12),
    "meme": VariantMetricProfile(0.22, 0.74, 1.24, 1.40, 1.08, 0.01, 0.78),
}


def build_base_clip_id(match_id: str, highlight_id: str) -> str:
    return f"{match_id}{CLIP_ID_SEPARATOR}{highlight_id}"


def build_variant_id(base_clip_id: str, format_type: str) -> str:
    return f"{base_clip_id}{CLIP_ID_SEPARATOR}{format_type}"


def parse_base_clip_id(clip_id: str) -> tuple[str, str] | None:
    if CLIP_ID_SEPARATOR not in clip_id:
        return None
    match_id, highlight_id = clip_id.split(CLIP_ID_SEPARATOR, 1)
    if not match_id or not highlight_id:
        return None
    return match_id, highlight_id


@dataclass(slots=True)
class ViralClipVariantManager:
    session: Session
    comparator: ViralVariantScoringComparator

    def ensure_variants(
        self,
        *,
        base_clip_id: str,
        format_plans: list[ViralContentFormatPlan],
        baseline_metrics: dict[str, Any],
        created_at: datetime,
        clip_metadata: dict[str, Any] | None = None,
    ) -> list[ClipVariant]:
        try:
            connection = self.session.connection()
            if not inspect(connection).has_table(ClipVariant.__tablename__):
                return []
        except SQLAlchemyError:
            return []
        existing_variants = self.list_variants(base_clip_id)
        existing_by_format = {variant.format_type: variant for variant in existing_variants}
        created = False
        normalized_created_at = created_at.astimezone(UTC) if created_at.tzinfo is not None else created_at.replace(tzinfo=UTC)

        for plan in format_plans:
            format_type = FORMAT_KEY_TO_VARIANT_TYPE.get(plan.format_key)
            if format_type is None or format_type in existing_by_format:
                continue
            tracked_metrics = self._tracked_metrics(
                variant_id=build_variant_id(base_clip_id, format_type),
                format_type=format_type,
                baseline_metrics=baseline_metrics,
            )
            score = self.comparator.score_variant(tracked_metrics).total
            metadata = {
                "format_key": plan.format_key,
                "format_title": plan.title,
                "format_description": plan.description,
                "style_preset": plan.editor.style_preset,
                "share_targets": list(plan.editor.share_targets),
                "publish_strategy": plan.editor.publish_strategy,
                "overlay_text": plan.editor.overlay_text,
                "commentary_prompt": plan.editor.commentary_prompt,
            }
            if clip_metadata:
                metadata.update(clip_metadata)
            self.session.add(
                ClipVariant(
                    variant_id=build_variant_id(base_clip_id, format_type),
                    base_clip_id=base_clip_id,
                    format_type=format_type,
                    created_at=normalized_created_at,
                    updated_at=normalized_created_at,
                    view_count=int(tracked_metrics["view_count"]),
                    watch_time=float(tracked_metrics["watch_time"]),
                    loop_rate=float(tracked_metrics["loop_rate"]),
                    shares=int(tracked_metrics["shares"]),
                    comments=int(tracked_metrics["comments"]),
                    completion_rate=float(tracked_metrics["completion_rate"]),
                    drop_off_point_seconds=tracked_metrics["drop_off_point_seconds"],
                    share_rate=float(tracked_metrics["share_rate"]),
                    comment_rate=float(tracked_metrics["comment_rate"]),
                    viral_score=float(score),
                    distribution_weight=0.2,
                    promotion_status="exploring",
                    promotion_enabled=True,
                    pushed_to_trending=False,
                    is_winner=False,
                    metadata_json=metadata,
                )
            )
            created = True

        if created:
            self.session.flush()
        return self.list_variants(base_clip_id)

    def list_variants(self, base_clip_id: str) -> list[ClipVariant]:
        try:
            connection = self.session.connection()
            if not inspect(connection).has_table(ClipVariant.__tablename__):
                return []
            return list(
                self.session.scalars(
                    select(ClipVariant)
                    .where(ClipVariant.base_clip_id == base_clip_id)
                    .order_by(ClipVariant.created_at.asc(), ClipVariant.format_type.asc())
                ).all()
            )
        except SQLAlchemyError:
            return []

    def _tracked_metrics(
        self,
        *,
        variant_id: str,
        format_type: str,
        baseline_metrics: dict[str, Any],
    ) -> dict[str, Any]:
        profile = _VARIANT_METRIC_PROFILES[format_type]
        baseline_views = max(int(baseline_metrics.get("views", 0)), 1)
        baseline_watch_time = max(float(baseline_metrics.get("watch_time", 0.0)), 0.0)
        baseline_loops = max(float(baseline_metrics.get("loops", 0.0)), 0.0)
        baseline_shares = max(int(baseline_metrics.get("shares", 0)), 0)
        baseline_comments = max(int(baseline_metrics.get("comments", 0)), 0)
        baseline_completion = self._bounded_ratio(baseline_metrics.get("completion", 0.0))
        baseline_drop_off = baseline_metrics.get("drop_off_point_seconds")
        drop_off_value = float(baseline_drop_off) if baseline_drop_off is not None else None

        seeded_metrics = {
            "views": min(950, max(80, int(round(baseline_views * profile.view_multiplier)))),
            "watch_time": round(baseline_watch_time * profile.watch_multiplier, 2),
            "loops": round(baseline_loops * profile.loop_multiplier, 2),
            "shares": max(0, int(round(baseline_shares * profile.share_multiplier))),
            "comments": max(0, int(round(baseline_comments * profile.comment_multiplier))),
            "completion": round(
                max(0.12, min(baseline_completion + profile.completion_delta, 0.97)),
                4,
            ),
            "drop_off_point_seconds": round(drop_off_value * profile.drop_off_multiplier, 2) if drop_off_value is not None else None,
        }
        return track_clip(variant_id, seeded_metrics)

    def _bounded_ratio(self, value: object) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = 0.0
        return max(0.0, min(numeric, 1.0))


__all__ = [
    "FORMAT_KEY_TO_VARIANT_TYPE",
    "ViralClipVariantManager",
    "build_base_clip_id",
    "build_variant_id",
    "parse_base_clip_id",
]
