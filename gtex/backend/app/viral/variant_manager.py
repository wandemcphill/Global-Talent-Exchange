from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.clip_variant import ClipVariant
from app.viral.analytics import track_clip
from app.viral.comparator import ViralVariantScoringComparator
from app.viral.editor import ViralContentFormatPlan, build_content_format_plans

CLIP_ID_SEPARATOR = "::"

FORMAT_KEY_TO_VARIANT_TYPE: dict[str, str] = {
    "instant_clip": "instant",
    "cinematic_replay": "cinematic",
    "debate_clip": "debate",
    "tactical_breakdown": "tactical",
    "meme_version": "meme",
}
FORMAT_TYPE_TO_KEY: dict[str, str] = {value: key for key, value in FORMAT_KEY_TO_VARIANT_TYPE.items()}
DEFAULT_MOMENT_FORMATS = ["instant", "cinematic", "debate", "tactical", "meme"]
DEFAULT_MOMENT_DURATION_SECONDS = 14


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

    def generate_variants(self, moment_clip: Mapping[str, Any]) -> list[ClipVariant]:
        payload = dict(moment_clip or {})
        base_clip_id = self._string_value(payload.get("clip_id") or payload.get("moment_id"))
        if not base_clip_id:
            raise ValueError("Moment clip payload must include clip_id or moment_id.")

        event_type = self._string_value(payload.get("event_type"), default="generic").lower()
        title = self._string_value(
            payload.get("title"),
            default=f"{event_type.replace('_', ' ').title()} moment",
        )
        overlay_text = self._string_value(payload.get("overlay_text"), default=title)
        duration_seconds = max(
            self._int_value(payload.get("duration_seconds"), default=DEFAULT_MOMENT_DURATION_SECONDS),
            4,
        )
        priority_formats = self._moment_formats(event_type)
        format_plans = self._moment_format_plans(
            event_type=event_type,
            storage_key=self._string_value(payload.get("storage_key") or payload.get("cdn_path")),
            title=title,
            overlay_text=overlay_text,
            duration_seconds=duration_seconds,
            team_name=self._string_value(payload.get("team")),
            player_name=self._string_value(payload.get("player")),
        )
        return self.ensure_variants(
            base_clip_id=base_clip_id,
            format_plans=format_plans,
            baseline_metrics=self._moment_baseline_metrics(payload),
            created_at=self._datetime_value(payload.get("created_at")),
            clip_metadata={
                "source": "moment",
                "match_id": self._string_value(payload.get("match_id")),
                "moment_id": self._string_value(payload.get("moment_id"), default=base_clip_id),
                "source_event_id": self._string_value(payload.get("source_event_id")),
                "source_event_type": self._string_value(payload.get("source_event_type")),
                "event_type": event_type,
                "detected_events": list(payload.get("detected_events") or []),
                "priority_score": round(
                    self._float_value(payload.get("priority_score") or payload.get("final_score"), default=0.0),
                    4,
                ),
                "priority_formats": priority_formats[:3],
                "title": title,
            },
        )

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

    def _moment_format_plans(
        self,
        *,
        event_type: str,
        storage_key: str | None,
        title: str,
        overlay_text: str,
        duration_seconds: int,
        team_name: str | None,
        player_name: str | None,
    ) -> list[ViralContentFormatPlan]:
        plans = build_content_format_plans(
            storage_key=storage_key,
            title=title,
            event_type=event_type,
            overlay_text=overlay_text,
            duration_seconds=duration_seconds,
            team_name=team_name,
            player_name=player_name,
        )
        plans_by_key = {plan.format_key: plan for plan in plans}
        return [
            plans_by_key[format_key]
            for format_key in (FORMAT_TYPE_TO_KEY[format_type] for format_type in self._moment_formats(event_type))
            if format_key in plans_by_key
        ]

    def _moment_formats(self, event_type: str) -> list[str]:
        formats = list(DEFAULT_MOMENT_FORMATS)
        if event_type == "goal":
            formats = ["instant", "meme", "debate"]
        return formats + [format_type for format_type in DEFAULT_MOMENT_FORMATS if format_type not in formats]

    def _moment_baseline_metrics(self, moment_clip: Mapping[str, Any]) -> dict[str, Any]:
        event_type = self._string_value(moment_clip.get("event_type"), default="generic").lower()
        detected_events = {str(item).strip().lower() for item in list(moment_clip.get("detected_events") or [])}
        priority_score = max(
            self._float_value(moment_clip.get("priority_score") or moment_clip.get("final_score"), default=1.0),
            0.0,
        )
        duration_seconds = max(
            self._int_value(moment_clip.get("duration_seconds"), default=DEFAULT_MOMENT_DURATION_SECONDS),
            4,
        )
        goal_bonus = 190 if event_type == "goal" else 0
        late_bonus = 120 if "last_minute_win" in detected_events else 0
        estimated_views = max(240, int(round(260 + (priority_score * 230) + goal_bonus + late_bonus)))
        completion_rate = min(
            0.97,
            0.58
            + min(priority_score, 3.0) / 8.0
            + (0.06 if event_type == "goal" else 0.0),
        )
        loop_rate = min(
            0.62,
            0.12
            + min(priority_score, 3.0) / 10.0
            + (0.08 if event_type == "goal" else 0.0),
        )
        share_rate = min(
            0.18,
            0.03
            + min(priority_score, 3.0) / 40.0
            + (0.02 if event_type == "goal" else 0.0),
        )
        comment_rate = min(
            0.12,
            0.01
            + (0.03 if event_type in {"goal", "red_card"} else 0.0)
            + (0.02 if "last_minute_win" in detected_events else 0.0),
        )
        shares = max(0, int(round(estimated_views * share_rate)))
        comments = max(0, int(round(estimated_views * comment_rate)))
        watch_time = round(
            max(duration_seconds * 0.55, duration_seconds * completion_rate * (1.0 + loop_rate)),
            2,
        )
        return {
            "views": estimated_views,
            "watch_time": watch_time,
            "loops": round(loop_rate * estimated_views, 2),
            "shares": shares,
            "comments": comments,
            "completion": round(completion_rate, 4),
            "drop_off_point_seconds": round(duration_seconds * max(completion_rate, 0.48), 2),
            "views_last_10min": max(1, int(round(estimated_views * 0.42))),
            "views_last_60min": max(1, int(round(estimated_views * 0.66))),
        }

    @staticmethod
    def _datetime_value(value: object) -> datetime:
        if isinstance(value, datetime):
            return value.astimezone(UTC) if value.tzinfo is not None else value.replace(tzinfo=UTC)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
            except ValueError:
                parsed = None
            if parsed is not None:
                return parsed.astimezone(UTC) if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
        return datetime.now(UTC)

    @staticmethod
    def _string_value(value: object, *, default: str | None = None) -> str | None:
        if value is None:
            return default
        resolved = str(value).strip()
        if resolved:
            return resolved
        return default

    @staticmethod
    def _float_value(value: object, *, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _int_value(value: object, *, default: int = 0) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


__all__ = [
    "FORMAT_KEY_TO_VARIANT_TYPE",
    "ViralClipVariantManager",
    "build_base_clip_id",
    "build_variant_id",
    "parse_base_clip_id",
]
