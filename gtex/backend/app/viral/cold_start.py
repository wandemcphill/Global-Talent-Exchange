from __future__ import annotations

from dataclasses import dataclass
from hashlib import md5
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.feedback_engine.service import FeedbackEngine
from app.models.analytics_event import AnalyticsEvent
from app.models.user_affinity_profile import UserAffinityProfile
from app.viral.ingestion_schemas import ClipEventType

DEFAULT_COLD_START_EXPLORATION_RATE = 0.50
DEFAULT_NEW_USER_EVENT_THRESHOLD = 5
DEFAULT_MIN_INITIAL_IMPRESSIONS = 200
DEFAULT_MAX_INITIAL_IMPRESSIONS = 500
DEFAULT_NEW_CREATOR_BOOST = 0.15
_RAW_AFFINITY_EVENT_NAMES = frozenset(
    {
        ClipEventType.VIEW.topic_name,
        ClipEventType.COMPLETE.topic_name,
        ClipEventType.LIKE.topic_name,
        ClipEventType.SHARE.topic_name,
        ClipEventType.SCROLL.topic_name,
        "clip_view",
        "clip_complete",
        "clip_like",
        "clip_share",
        "clip_scroll",
    }
)


def _table_exists(session: Session, table_name: str) -> bool:
    bind = session.connection()
    if bind is None:
        return False
    return bool(inspect(bind).has_table(table_name))


@dataclass(slots=True)
class ColdStartManager:
    session: Session
    feedback_engine: FeedbackEngine | None = None
    new_user_event_threshold: int = DEFAULT_NEW_USER_EVENT_THRESHOLD
    min_initial_impressions: int = DEFAULT_MIN_INITIAL_IMPRESSIONS
    max_initial_impressions: int = DEFAULT_MAX_INITIAL_IMPRESSIONS
    new_creator_boost: float = DEFAULT_NEW_CREATOR_BOOST

    def __post_init__(self) -> None:
        if self.feedback_engine is None:
            self.feedback_engine = FeedbackEngine(session=self.session)

    def is_new_user(self, user_id: str) -> bool:
        if not _table_exists(self.session, UserAffinityProfile.__tablename__):
            if not _table_exists(self.session, AnalyticsEvent.__tablename__):
                return True
            raw_threshold = max(1, min(int(self.new_user_event_threshold), 3))
            observed_events = self.session.scalars(
                select(AnalyticsEvent.id)
                .where(AnalyticsEvent.user_id == user_id)
                .where(AnalyticsEvent.name.in_(tuple(_RAW_AFFINITY_EVENT_NAMES)))
                .limit(raw_threshold)
            ).all()
            return len(observed_events) < raw_threshold
        profile = self.session.scalar(select(UserAffinityProfile).where(UserAffinityProfile.user_id == user_id))
        if profile is None:
            return True
        state = dict(profile.state_json or {})
        event_counts = state.get("event_counts")
        if isinstance(event_counts, dict):
            total = sum(int(value or 0) for value in event_counts.values())
            if total >= self.new_user_event_threshold:
                return False
        observed_events = self.session.scalars(
            select(AnalyticsEvent.id)
            .where(AnalyticsEvent.user_id == user_id)
            .limit(self.new_user_event_threshold)
        ).all()
        return len(observed_events) < self.new_user_event_threshold

    def exploration_rate(self, *, is_new_user: bool, configured_rate: float = DEFAULT_COLD_START_EXPLORATION_RATE) -> float:
        if not is_new_user:
            return 0.0
        return max(0.0, min(float(configured_rate), 1.0))

    def initial_impression_floor(self, *, clip_id: str, observed_views: int = 0) -> int:
        if int(observed_views) >= self.max_initial_impressions:
            return 0
        if self.max_initial_impressions <= self.min_initial_impressions:
            return self.min_initial_impressions
        digest = md5(clip_id.encode("utf-8")).digest()[0]
        spread = self.max_initial_impressions - self.min_initial_impressions
        return self.min_initial_impressions + (digest % (spread + 1))

    def creator_boost(self, creator_id: str | None) -> float:
        if creator_id is None:
            return 0.0
        published_clips = self.feedback_engine.published_campaign_clips(creator_id)
        viral_success_boost = self.feedback_engine.creator_distribution_weight(creator_id) - 1.0
        if published_clips >= 3 or viral_success_boost >= 0.20:
            return 0.0
        decay = min((published_clips * 0.04) + max(viral_success_boost, 0.0), self.new_creator_boost)
        return round(max(self.new_creator_boost - decay, 0.0), 4)

    @staticmethod
    def creator_id_from_clip(clip: Any) -> str | None:
        metadata = getattr(clip, "metadata", {}) or {}
        if not isinstance(metadata, dict):
            return None
        creator_id = metadata.get("creator_id")
        if isinstance(creator_id, str) and creator_id.strip():
            return creator_id.strip()
        return None


__all__ = ["ColdStartManager"]
