from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
import logging
from typing import Any

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from app.models.analytics_event import AnalyticsEvent
from app.models.clip_variant import ClipVariant

logger = logging.getLogger(__name__)

CLIP_VIEW_EVENT_NAMES = frozenset({"clip.view"})
CLIP_COMPLETE_EVENT_NAMES = frozenset({"clip.complete", "sponsored_clip.watch"})
CLIP_SHARE_EVENT_NAMES = frozenset({"clip.share"})
CLIP_IMPRESSION_EVENT_NAMES = frozenset({"sponsored_clip.impression"})
CLIP_MONETIZATION_EVENT_NAMES = frozenset({"sponsored_clip.conversion"})
CLIP_GENERATED_EVENT_NAMES = frozenset({"clip.generated", "campaign_clip.created"})
CLIP_ANALYTICS_EVENT_NAMES = frozenset(
    set()
    .union(CLIP_VIEW_EVENT_NAMES)
    .union(CLIP_COMPLETE_EVENT_NAMES)
    .union(CLIP_SHARE_EVENT_NAMES)
    .union(CLIP_IMPRESSION_EVENT_NAMES)
    .union(CLIP_MONETIZATION_EVENT_NAMES)
    .union(CLIP_GENERATED_EVENT_NAMES)
)
DEFAULT_CLIP_ANALYTICS_LOOKBACK_DAYS = 90


def _as_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _clip_id_from_metadata(metadata: dict[str, Any]) -> str | None:
    for key in ("clip_id", "base_clip_id"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _has_table(session: Session, table_name: str) -> bool:
    try:
        return bool(inspect(session.connection()).has_table(table_name))
    except Exception:
        return False


class AnalyticsService:
    def track_event(
        self,
        session: Session,
        *,
        name: str,
        user_id: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> AnalyticsEvent:
        event = AnalyticsEvent(
            name=name,
            user_id=user_id,
            metadata_json=metadata or {},
        )
        analytics_table_exists = _has_table(session, AnalyticsEvent.__tablename__)
        if analytics_table_exists:
            session.add(event)
        try:
            from app.users.affinity_service import UserAffinityService

            UserAffinityService(session).track_event(user_id=user_id, name=name, metadata=metadata)
        except Exception:
            logger.exception(
                "analytics.user_affinity_profile_update_failed name=%s user_id=%s",
                name,
                user_id,
            )
        try:
            from app.ads_engine.service import SponsoredClipTrackingService

            SponsoredClipTrackingService(session).track_event(name=name, metadata=metadata)
        except Exception:
            logger.exception(
                "analytics.sponsored_clip_update_failed name=%s user_id=%s",
                name,
                user_id,
            )
        try:
            from app.feedback_engine.service import FeedbackEngine

            FeedbackEngine(session).record_interaction_event(name=name, metadata=metadata)
        except Exception:
            logger.exception(
                "analytics.feedback_engine_update_failed name=%s user_id=%s",
                name,
                user_id,
            )
        if analytics_table_exists:
            session.flush()
        return event

    def summary(self, session: Session, *, since_days: int = 30) -> tuple[datetime, list[dict[str, Any]]]:
        since = datetime.now(timezone.utc) - timedelta(days=since_days)
        if not _has_table(session, AnalyticsEvent.__tablename__):
            return since, []
        rows = session.execute(
            select(AnalyticsEvent.name, func.count())
            .where(AnalyticsEvent.created_at >= since)
            .group_by(AnalyticsEvent.name)
            .order_by(func.count().desc())
        ).all()
        return since, [{"name": row[0], "count": int(row[1])} for row in rows]

    def funnel(self, session: Session, *, since_days: int = 30) -> tuple[datetime, list[dict[str, Any]]]:
        since = datetime.now(timezone.utc) - timedelta(days=since_days)
        if not _has_table(session, AnalyticsEvent.__tablename__):
            return since, []
        steps = [
            "signup_started",
            "signup_completed",
            "deposit_confirmed",
            "kyc_approved",
            "withdrawal_paid",
        ]
        results: list[dict[str, Any]] = []
        for step in steps:
            count = session.scalar(
                select(func.count(func.distinct(AnalyticsEvent.user_id)))
                .where(
                    AnalyticsEvent.created_at >= since,
                    AnalyticsEvent.name == step,
                    AnalyticsEvent.user_id.is_not(None),
                )
            )
            results.append({"name": step, "users": int(count or 0)})
        return since, results

    def clip_snapshot(
        self,
        session: Session,
        *,
        clip_id: str,
        fallback: dict[str, Any] | None = None,
        since_days: int = DEFAULT_CLIP_ANALYTICS_LOOKBACK_DAYS,
    ) -> dict[str, Any]:
        baseline = dict(fallback or self._aggregate_recent_clip_records(session).get(clip_id) or {})
        since = datetime.now(UTC) - timedelta(days=since_days)
        rows: list[AnalyticsEvent] = []
        if _has_table(session, AnalyticsEvent.__tablename__):
            rows = session.scalars(
                select(AnalyticsEvent)
                .where(
                    AnalyticsEvent.created_at >= since,
                    AnalyticsEvent.name.in_(tuple(CLIP_ANALYTICS_EVENT_NAMES)),
                )
                .order_by(AnalyticsEvent.created_at.desc())
                .limit(2_000)
            ).all()

        generated = 0
        impressions = 0
        views = 0
        completions = 0
        shares = 0
        monetized = 0
        total_watch_time = 0.0

        for event in rows:
            metadata = dict(event.metadata_json or {})
            if _clip_id_from_metadata(metadata) != clip_id:
                continue
            event_name = str(event.name)
            if event_name in CLIP_GENERATED_EVENT_NAMES:
                generated += 1
            if event_name in CLIP_IMPRESSION_EVENT_NAMES:
                impressions += 1
            if event_name in CLIP_VIEW_EVENT_NAMES:
                views += 1
            if event_name in CLIP_COMPLETE_EVENT_NAMES:
                completions += 1
                total_watch_time += max(
                    _as_float(metadata.get("watch_time_seconds"), default=_as_float(metadata.get("watch_time"))),
                    0.0,
                )
            if event_name in CLIP_SHARE_EVENT_NAMES:
                shares += 1
            if event_name in CLIP_MONETIZATION_EVENT_NAMES:
                monetized += 1

        views = max(views, _as_int(baseline.get("view_count")))
        completions = max(completions, _as_int(baseline.get("completions")))
        shares = max(shares, _as_int(baseline.get("shares")))
        impressions = max(impressions, views, _as_int(baseline.get("impressions")))
        total_watch_time = max(total_watch_time, _as_float(baseline.get("total_watch_time")))
        avg_watch_time = (
            round(total_watch_time / max(views, 1), 4)
            if views > 0
            else round(_as_float(baseline.get("watch_time")), 4)
        )
        completion_rate = round(completions / max(views, 1), 4) if views > 0 else 0.0

        revenue = self._clip_revenue(session, clip_id=clip_id)
        lifecycle = {
            "generated": max(generated, 1 if self._clip_exists(session, clip_id=clip_id) else 0),
            "viewed": views,
            "completed": completions,
            "shared": shares,
            "monetized": monetized or (1 if revenue > Decimal("0.0000") else 0),
        }

        variant = self._latest_variant(session, clip_id=clip_id)
        drop_off_point_seconds = (
            round(float(variant.drop_off_point_seconds), 2)
            if variant is not None and variant.drop_off_point_seconds is not None
            else (
                round(_as_float(baseline.get("drop_off_point_seconds")), 2)
                if baseline.get("drop_off_point_seconds") is not None
                else None
            )
        )
        comment_rate = round(_as_float(baseline.get("comment_rate")), 4)
        share_rate = round(shares / max(views, 1), 4) if views > 0 else round(_as_float(baseline.get("share_rate")), 4)

        return {
            "clip_id": clip_id,
            "analytics": {
                "clip_id": clip_id,
                "view_count": views,
                "completions": completions,
                "watch_time": avg_watch_time,
                "total_watch_time": round(total_watch_time, 4),
                "loops": _as_float(baseline.get("loops")),
                "loop_rate": round(_as_float(baseline.get("loop_rate")), 4),
                "shares": shares,
                "comments": _as_int(baseline.get("comments")),
                "skips": max(impressions - completions, _as_int(baseline.get("skips"))),
                "completion_rate": completion_rate,
                "drop_off_point_seconds": drop_off_point_seconds,
                "share_rate": share_rate,
                "comment_rate": comment_rate,
                "views_last_10min": _as_int(baseline.get("views_last_10min")),
                "views_last_60min": _as_int(baseline.get("views_last_60min")),
                "impressions": impressions,
            },
            "lifecycle": lifecycle,
            "revenue": revenue,
        }

    def clip_dashboard(self, session: Session, *, limit: int = 10) -> list[dict[str, Any]]:
        records = self._aggregate_recent_clip_records(session)
        scored: list[dict[str, Any]] = []
        for clip_id, payload in records.items():
            snapshot = self.clip_snapshot(session, clip_id=clip_id, fallback=payload)
            analytics = snapshot["analytics"]
            score = round(
                analytics["view_count"]
                + (analytics["shares"] * 8)
                + (float(snapshot["revenue"]) * 200)
                + (analytics["completion_rate"] * 100),
                4,
            )
            scored.append(
                {
                    "clip_id": clip_id,
                    "title": payload.get("title"),
                    "views": analytics["view_count"],
                    "completion_rate": analytics["completion_rate"],
                    "shares": analytics["shares"],
                    "revenue": snapshot["revenue"],
                    "score": score,
                }
            )
        scored.sort(key=lambda item: (-item["score"], item["clip_id"]))
        return scored[: max(limit, 1)]

    def clip_drop_off_dashboard(self, session: Session, *, limit: int = 10) -> list[dict[str, Any]]:
        records = self._aggregate_recent_clip_records(session)
        items: list[dict[str, Any]] = []
        for clip_id, payload in records.items():
            snapshot = self.clip_snapshot(session, clip_id=clip_id, fallback=payload)
            analytics = snapshot["analytics"]
            items.append(
                {
                    "clip_id": clip_id,
                    "title": payload.get("title"),
                    "views": analytics["view_count"],
                    "completion_rate": analytics["completion_rate"],
                    "drop_off_point_seconds": analytics.get("drop_off_point_seconds"),
                }
            )
        items.sort(
            key=lambda item: (
                item["completion_rate"],
                -(item["views"]),
                item["clip_id"],
            )
        )
        return items[: max(limit, 1)]

    def _aggregate_recent_clip_records(self, session: Session) -> dict[str, dict[str, Any]]:
        records: dict[str, dict[str, Any]] = defaultdict(dict)
        if not _has_table(session, AnalyticsEvent.__tablename__):
            return records
        rows = session.scalars(
            select(AnalyticsEvent)
            .where(AnalyticsEvent.name.in_(("campaign_clip.created", "clip.generated")))
            .order_by(AnalyticsEvent.created_at.desc())
            .limit(500)
        ).all()
        for event in rows:
            metadata = dict(event.metadata_json or {})
            payload = metadata.get("clip")
            if isinstance(payload, dict):
                clip_id = payload.get("clip_id")
                if isinstance(clip_id, str) and clip_id and clip_id not in records:
                    records[clip_id] = {
                        "title": payload.get("title"),
                        "view_count": ((payload.get("analytics") or {}) if isinstance(payload.get("analytics"), dict) else {}).get("view_count", 0),
                        "completions": ((payload.get("analytics") or {}) if isinstance(payload.get("analytics"), dict) else {}).get("completions", 0),
                        "watch_time": ((payload.get("analytics") or {}) if isinstance(payload.get("analytics"), dict) else {}).get("watch_time", 0.0),
                        "total_watch_time": ((payload.get("analytics") or {}) if isinstance(payload.get("analytics"), dict) else {}).get("total_watch_time", 0.0),
                        "shares": ((payload.get("analytics") or {}) if isinstance(payload.get("analytics"), dict) else {}).get("shares", 0),
                        "comments": ((payload.get("analytics") or {}) if isinstance(payload.get("analytics"), dict) else {}).get("comments", 0),
                        "completion_rate": ((payload.get("analytics") or {}) if isinstance(payload.get("analytics"), dict) else {}).get("completion_rate", 0.0),
                        "drop_off_point_seconds": ((payload.get("analytics") or {}) if isinstance(payload.get("analytics"), dict) else {}).get("drop_off_point_seconds"),
                    }
            else:
                clip_id = _clip_id_from_metadata(metadata)
                if clip_id is None or clip_id in records:
                    continue
                records[clip_id] = {"title": metadata.get("title")}
        return records

    def _clip_revenue(self, session: Session, *, clip_id: str) -> Decimal:
        try:
            from app.ads_engine.service import _spend_for_ad
            from app.models.sponsored_clip import SponsoredClip
        except Exception:
            return Decimal("0.0000")
        if not _has_table(session, SponsoredClip.__tablename__):
            return Decimal("0.0000")
        ads = session.scalars(select(SponsoredClip).where(SponsoredClip.clip_id == clip_id)).all()
        revenue = Decimal("0.0000")
        for ad in ads:
            revenue += _spend_for_ad(ad)
        return revenue.quantize(Decimal("0.0001"))

    def _latest_variant(self, session: Session, *, clip_id: str) -> ClipVariant | None:
        if not _has_table(session, ClipVariant.__tablename__):
            return None
        return session.scalar(
            select(ClipVariant)
            .where(ClipVariant.base_clip_id == clip_id)
            .order_by(ClipVariant.updated_at.desc())
            .limit(1)
        )

    def _clip_exists(self, session: Session, *, clip_id: str) -> bool:
        if self._latest_variant(session, clip_id=clip_id) is not None:
            return True
        if not _has_table(session, AnalyticsEvent.__tablename__):
            return False
        events = session.scalars(
            select(AnalyticsEvent)
            .where(AnalyticsEvent.name.in_(tuple(CLIP_GENERATED_EVENT_NAMES)))
            .order_by(AnalyticsEvent.created_at.desc())
            .limit(500)
        ).all()
        for event in events:
            metadata = dict(event.metadata_json or {})
            if _clip_id_from_metadata(metadata) == clip_id:
                return True
            payload = metadata.get("clip")
            if isinstance(payload, dict) and payload.get("clip_id") == clip_id:
                return True
        return False
