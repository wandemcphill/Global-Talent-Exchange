from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from math import ceil, exp
import json
import logging
import re
from threading import Lock
from typing import Any, Protocol

from fastapi import FastAPI
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.feedback_engine.service import FeedbackEngine
from app.models.analytics_event import AnalyticsEvent
from app.models.competition_match import CompetitionMatch
from app.models.manager_duel import ManagerDuel
from app.moments.priority_cache import ensure_moment_priority_cache
from app.orchestrator.orchestrator_service import build_attention_orchestrator_service
from app.runtime_config.service import ensure_runtime_config_loader
from app.users.follow_service import (
    FOLLOWING_FEED_KEY_TEMPLATE,
    build_follow_graph_service,
    build_follow_notification_service,
    following_feed_cache_subject,
)
from app.viral.cold_start import ColdStartManager
from app.viral.social_boost import SocialBoostService
from app.viral.ingestion_schemas import ClipEventType
from app.viral.ranking_service import build_viral_ranking_service
from app.viral.schemas import (
    PersonalizedFeedAffinityView,
    PersonalizedFeedClipView,
    PersonalizedFeedRefreshResponse,
    PersonalizedFeedResponse,
    PersonalizedFeedScoreBreakdownView,
    ViralTrendingClipView,
)
from app.viral.session_tracker import ensure_viral_session_tracker
from app.viral.service import ViralFeedService

logger = logging.getLogger(__name__)

FOR_YOU_FEED_KEY_TEMPLATE = "user:{user_id}:feed"
FOR_YOU_FEED_PAYLOAD_KEY_TEMPLATE = "user:{user_id}:feed:payloads"
FOR_YOU_FEED_HISTORY_KEY_TEMPLATE = "user:{user_id}:feed:history"
FOR_YOU_SEEN_CLIPS_KEY_TEMPLATE = "user:{user_id}:seen_clips"
DEFAULT_FEED_CACHE_TTL_SECONDS = 900
DEFAULT_HISTORY_TTL_SECONDS = 259_200
DEFAULT_HISTORY_LIMIT = 120
DEFAULT_CACHE_SIZE = 100
DEFAULT_CANDIDATE_MULTIPLIER = 5
DEFAULT_MAX_CANDIDATES = 80
DEFAULT_ANALYTICS_LOOKBACK_DAYS = 90
DEFAULT_ANALYTICS_EVENT_LIMIT = 500
DEFAULT_HYBRID_FOR_YOU_SHARE = 0.60
DEFAULT_HYBRID_FOLLOWING_SHARE = 0.40
_NON_ALPHANUMERIC_RE = re.compile(r"[^a-z0-9]+")

VIEW_EVENT_NAMES = frozenset({ClipEventType.VIEW.topic_name, "clip_view"})
LIKE_EVENT_NAMES = frozenset({ClipEventType.LIKE.topic_name, "clip_like"})
SHARE_EVENT_NAMES = frozenset({ClipEventType.SHARE.topic_name, "clip_share"})
AFFINITY_EVENT_NAMES = frozenset((*VIEW_EVENT_NAMES, *LIKE_EVENT_NAMES, *SHARE_EVENT_NAMES))


@dataclass(slots=True)
class PersonalizedFeedEnvelope:
    clip_id: str
    score: float
    payload: dict[str, Any]


@dataclass(slots=True)
class SeenClipHistory:
    clip_id: str
    creator_key: str | None
    format_key: str | None
    similarity_key: str
    served_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "creator_key": self.creator_key,
            "format_key": self.format_key,
            "similarity_key": self.similarity_key,
            "served_at": self.served_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SeenClipHistory | None":
        clip_id = payload.get("clip_id")
        similarity_key = payload.get("similarity_key")
        served_at = payload.get("served_at")
        if not isinstance(clip_id, str) or not clip_id.strip():
            return None
        if not isinstance(similarity_key, str) or not similarity_key.strip():
            return None
        if not isinstance(served_at, str) or not served_at.strip():
            return None
        creator_key = payload.get("creator_key")
        format_key = payload.get("format_key")
        return cls(
            clip_id=clip_id,
            creator_key=creator_key if isinstance(creator_key, str) and creator_key.strip() else None,
            format_key=format_key if isinstance(format_key, str) and format_key.strip() else None,
            similarity_key=similarity_key,
            served_at=served_at,
        )


class PersonalizedFeedStore(Protocol):
    def replace(self, user_id: str, entries: list[PersonalizedFeedEnvelope]) -> None:
        ...

    def top(self, user_id: str, limit: int) -> list[PersonalizedFeedEnvelope]:
        ...

    def mark_served(self, user_id: str, entries: list[SeenClipHistory]) -> None:
        ...

    def recent_history(self, user_id: str, limit: int) -> list[SeenClipHistory]:
        ...

    def mark_seen(self, user_id: str, clip_ids: list[str]) -> None:
        ...

    def seen_clip_ids(self, user_id: str) -> set[str]:
        ...


@dataclass(slots=True)
class InMemoryPersonalizedFeedStore:
    feed_ttl_seconds: int = DEFAULT_FEED_CACHE_TTL_SECONDS
    history_ttl_seconds: int = DEFAULT_HISTORY_TTL_SECONDS
    max_history: int = DEFAULT_HISTORY_LIMIT
    _feeds: dict[str, dict[str, tuple[float, str]]] = field(default_factory=dict, init=False, repr=False)
    _history: dict[str, list[str]] = field(default_factory=dict, init=False, repr=False)
    _seen: dict[str, set[str]] = field(default_factory=dict, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def replace(self, user_id: str, entries: list[PersonalizedFeedEnvelope]) -> None:
        with self._lock:
            self._feeds[user_id] = {
                entry.clip_id: (float(entry.score), json.dumps(entry.payload, default=str))
                for entry in entries
            }

    def top(self, user_id: str, limit: int) -> list[PersonalizedFeedEnvelope]:
        if limit <= 0:
            return []
        with self._lock:
            ranked = sorted(
                self._feeds.get(user_id, {}).items(),
                key=lambda item: (-item[1][0], item[0]),
            )[:limit]
        return [
            PersonalizedFeedEnvelope(
                clip_id=clip_id,
                score=score,
                payload=json.loads(payload),
            )
            for clip_id, (score, payload) in ranked
        ]

    def mark_served(self, user_id: str, entries: list[SeenClipHistory]) -> None:
        if not entries:
            return
        with self._lock:
            serialized = [json.dumps(entry.as_dict(), default=str) for entry in entries]
            history = list(self._history.get(user_id, []))
            self._history[user_id] = (serialized + history)[: self.max_history]

    def recent_history(self, user_id: str, limit: int) -> list[SeenClipHistory]:
        if limit <= 0:
            return []
        with self._lock:
            raw_entries = list(self._history.get(user_id, []))[:limit]
        history: list[SeenClipHistory] = []
        for raw in raw_entries:
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            entry = SeenClipHistory.from_dict(payload)
            if entry is not None:
                history.append(entry)
        return history

    def mark_seen(self, user_id: str, clip_ids: list[str]) -> None:
        normalized = {clip_id.strip() for clip_id in clip_ids if clip_id.strip()}
        if not normalized:
            return
        with self._lock:
            seen = self._seen.setdefault(user_id, set())
            seen.update(normalized)

    def seen_clip_ids(self, user_id: str) -> set[str]:
        with self._lock:
            return set(self._seen.get(user_id, set()))


@dataclass(slots=True)
class RedisPersonalizedFeedStore:
    redis_url: str
    feed_ttl_seconds: int = DEFAULT_FEED_CACHE_TTL_SECONDS
    history_ttl_seconds: int = DEFAULT_HISTORY_TTL_SECONDS
    seen_ttl_seconds: int = DEFAULT_HISTORY_TTL_SECONDS
    max_history: int = DEFAULT_HISTORY_LIMIT
    _client: Redis = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = Redis.from_url(self.redis_url, decode_responses=True)

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except RedisError:
            logger.warning("viral.personalized_feed.redis.ping_failed")
            return False

    def replace(self, user_id: str, entries: list[PersonalizedFeedEnvelope]) -> None:
        feed_key = self.feed_key(user_id)
        payload_key = self.payload_key(user_id)
        mapping = {entry.clip_id: float(entry.score) for entry in entries}
        payload_mapping = {entry.clip_id: json.dumps(entry.payload, default=str) for entry in entries}
        try:
            pipeline = self._client.pipeline()
            pipeline.delete(feed_key)
            pipeline.delete(payload_key)
            if mapping:
                pipeline.zadd(feed_key, mapping)
                pipeline.expire(feed_key, self.feed_ttl_seconds)
                pipeline.hset(payload_key, mapping=payload_mapping)
                pipeline.expire(payload_key, self.feed_ttl_seconds)
            pipeline.execute()
        except RedisError:
            logger.warning("viral.personalized_feed.redis.replace_failed user_id=%s entry_count=%s", user_id, len(entries))

    def top(self, user_id: str, limit: int) -> list[PersonalizedFeedEnvelope]:
        if limit <= 0:
            return []
        try:
            ranked = self._client.zrevrange(self.feed_key(user_id), 0, limit - 1, withscores=True)
            clip_ids = [clip_id for clip_id, _score in ranked]
            payloads = self._client.hmget(self.payload_key(user_id), clip_ids) if clip_ids else []
        except RedisError:
            logger.warning("viral.personalized_feed.redis.top_failed user_id=%s limit=%s", user_id, limit)
            return []
        entries: list[PersonalizedFeedEnvelope] = []
        for (clip_id, score), payload in zip(ranked, payloads):
            if payload is None:
                continue
            try:
                decoded = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if not isinstance(decoded, dict):
                continue
            entries.append(
                PersonalizedFeedEnvelope(
                    clip_id=clip_id,
                    score=float(score),
                    payload=decoded,
                )
            )
        return entries

    def mark_served(self, user_id: str, entries: list[SeenClipHistory]) -> None:
        if not entries:
            return
        history_key = self.history_key(user_id)
        serialized = [json.dumps(entry.as_dict(), default=str) for entry in entries]
        try:
            pipeline = self._client.pipeline()
            pipeline.lpush(history_key, *serialized)
            pipeline.ltrim(history_key, 0, max(self.max_history - 1, 0))
            pipeline.expire(history_key, self.history_ttl_seconds)
            pipeline.execute()
        except RedisError:
            logger.warning("viral.personalized_feed.redis.history_write_failed user_id=%s", user_id)

    def recent_history(self, user_id: str, limit: int) -> list[SeenClipHistory]:
        if limit <= 0:
            return []
        try:
            raw_entries = self._client.lrange(self.history_key(user_id), 0, limit - 1)
        except RedisError:
            logger.warning("viral.personalized_feed.redis.history_read_failed user_id=%s limit=%s", user_id, limit)
            return []
        history: list[SeenClipHistory] = []
        for raw in raw_entries:
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            entry = SeenClipHistory.from_dict(payload)
            if entry is not None:
                history.append(entry)
        return history

    def mark_seen(self, user_id: str, clip_ids: list[str]) -> None:
        normalized = [clip_id.strip() for clip_id in clip_ids if clip_id.strip()]
        if not normalized:
            return
        try:
            pipeline = self._client.pipeline()
            pipeline.sadd(self.seen_key(user_id), *normalized)
            pipeline.expire(self.seen_key(user_id), self.seen_ttl_seconds)
            pipeline.execute()
        except RedisError:
            logger.warning("viral.personalized_feed.redis.seen_write_failed user_id=%s", user_id)

    def seen_clip_ids(self, user_id: str) -> set[str]:
        try:
            return {str(item) for item in self._client.smembers(self.seen_key(user_id))}
        except RedisError:
            logger.warning("viral.personalized_feed.redis.seen_read_failed user_id=%s", user_id)
            return set()

    @staticmethod
    def feed_key(user_id: str) -> str:
        return FOR_YOU_FEED_KEY_TEMPLATE.format(user_id=user_id)

    @staticmethod
    def payload_key(user_id: str) -> str:
        return FOR_YOU_FEED_PAYLOAD_KEY_TEMPLATE.format(user_id=user_id)

    @staticmethod
    def history_key(user_id: str) -> str:
        return FOR_YOU_FEED_HISTORY_KEY_TEMPLATE.format(user_id=user_id)

    @staticmethod
    def seen_key(user_id: str) -> str:
        return FOR_YOU_SEEN_CLIPS_KEY_TEMPLATE.format(user_id=user_id)


@dataclass(slots=True)
class UserAffinityScore:
    total: float = 0.0
    view_signal: float = 0.0
    like_signal: float = 0.0
    share_signal: float = 0.0
    format_preference: float = 0.0
    creator_preference: float = 0.0


@dataclass(slots=True)
class UserInteractionSnapshot:
    total_weight: float = 0.0
    total_views: int = 0
    total_likes: int = 0
    total_shares: int = 0
    clip_views: Counter[str] = field(default_factory=Counter)
    clip_likes: Counter[str] = field(default_factory=Counter)
    clip_shares: Counter[str] = field(default_factory=Counter)
    creator_views: Counter[str] = field(default_factory=Counter)
    creator_likes: Counter[str] = field(default_factory=Counter)
    creator_shares: Counter[str] = field(default_factory=Counter)
    format_views: Counter[str] = field(default_factory=Counter)
    format_likes: Counter[str] = field(default_factory=Counter)
    format_shares: Counter[str] = field(default_factory=Counter)
    creator_weight: Counter[str] = field(default_factory=Counter)
    format_weight: Counter[str] = field(default_factory=Counter)

    def record(self, *, event_name: str, clip_id: str | None, creator_key: str | None, format_key: str | None) -> None:
        if event_name in VIEW_EVENT_NAMES:
            self.total_views += 1
            if clip_id:
                self.clip_views[clip_id] += 1
            if creator_key:
                self.creator_views[creator_key] += 1
            if format_key:
                self.format_views[format_key] += 1
            weight = 1.0
        elif event_name in LIKE_EVENT_NAMES:
            self.total_likes += 1
            if clip_id:
                self.clip_likes[clip_id] += 1
            if creator_key:
                self.creator_likes[creator_key] += 1
            if format_key:
                self.format_likes[format_key] += 1
            weight = 2.0
        elif event_name in SHARE_EVENT_NAMES:
            self.total_shares += 1
            if clip_id:
                self.clip_shares[clip_id] += 1
            if creator_key:
                self.creator_shares[creator_key] += 1
            if format_key:
                self.format_shares[format_key] += 1
            weight = 3.0
        else:
            return
        self.total_weight += weight
        if creator_key:
            self.creator_weight[creator_key] += weight
        if format_key:
            self.format_weight[format_key] += weight

    def clip_interactions(self, clip_id: str) -> int:
        return int(self.clip_views[clip_id] + self.clip_likes[clip_id] + self.clip_shares[clip_id])


@dataclass(slots=True)
class ClipAffinityCalculator:
    session: Session
    analytics_lookback_days: int = DEFAULT_ANALYTICS_LOOKBACK_DAYS
    analytics_event_limit: int = DEFAULT_ANALYTICS_EVENT_LIMIT

    def build_snapshot(self, user_id: str) -> UserInteractionSnapshot:
        try:
            if not inspect(self.session.connection()).has_table(AnalyticsEvent.__tablename__):
                return UserInteractionSnapshot()
        except Exception:
            return UserInteractionSnapshot()
        since = datetime.now(UTC) - timedelta(days=self.analytics_lookback_days)
        stmt = (
            select(AnalyticsEvent)
            .where(
                AnalyticsEvent.user_id == user_id,
                AnalyticsEvent.created_at >= since,
                AnalyticsEvent.name.in_(tuple(AFFINITY_EVENT_NAMES)),
            )
            .order_by(AnalyticsEvent.created_at.desc())
            .limit(self.analytics_event_limit)
        )
        snapshot = UserInteractionSnapshot()
        for event in self.session.scalars(stmt).all():
            metadata = dict(event.metadata_json or {})
            snapshot.record(
                event_name=str(event.name),
                clip_id=_first_non_empty(metadata, "clip_id", "base_clip_id"),
                creator_key=_normalize_identifier(
                    _first_non_empty(metadata, "creator_id", "creator_key", "creator_handle", "creator_name", "team_name")
                ),
                format_key=_normalize_identifier(
                    _first_non_empty(metadata, "format_type", "format_key", "clip_format")
                ),
            )
        return snapshot

    def score_clip(self, *, snapshot: UserInteractionSnapshot, clip) -> UserAffinityScore:
        clip_id = str(getattr(clip, "clip_id", "") or "")
        creator_key = _creator_key_from_clip(clip)
        format_key = _format_key_from_clip(clip)

        view_signal = min(
            1.0,
            (snapshot.clip_views[clip_id] / 3.0)
            + (0.35 * _ratio(snapshot.creator_views, creator_key, snapshot.total_views))
            + (0.20 * _ratio(snapshot.format_views, format_key, snapshot.total_views)),
        )
        like_signal = min(
            1.0,
            (snapshot.clip_likes[clip_id] / 2.0)
            + (0.40 * _ratio(snapshot.creator_likes, creator_key, snapshot.total_likes))
            + (0.20 * _ratio(snapshot.format_likes, format_key, snapshot.total_likes)),
        )
        share_signal = min(
            1.0,
            (snapshot.clip_shares[clip_id] / 2.0)
            + (0.45 * _ratio(snapshot.creator_shares, creator_key, snapshot.total_shares))
            + (0.20 * _ratio(snapshot.format_shares, format_key, snapshot.total_shares)),
        )
        format_preference = _ratio(snapshot.format_weight, format_key, snapshot.total_weight)
        creator_preference = _ratio(snapshot.creator_weight, creator_key, snapshot.total_weight)
        total = min(
            1.0,
            (0.20 * view_signal)
            + (0.20 * like_signal)
            + (0.15 * share_signal)
            + (0.20 * format_preference)
            + (0.25 * creator_preference),
        )
        return UserAffinityScore(
            total=round(total, 6),
            view_signal=round(view_signal, 6),
            like_signal=round(like_signal, 6),
            share_signal=round(share_signal, 6),
            format_preference=round(format_preference, 6),
            creator_preference=round(creator_preference, 6),
        )


@dataclass(slots=True)
class _HistoryCounters:
    clip_counts: Counter[str] = field(default_factory=Counter)
    creator_counts: Counter[str] = field(default_factory=Counter)
    format_counts: Counter[str] = field(default_factory=Counter)
    similarity_counts: Counter[str] = field(default_factory=Counter)


@dataclass(slots=True)
class _PersonalizedCandidate:
    clip: Any
    creator_key: str | None
    creator_user_id: str | None
    format_key: str | None
    similarity_key: str
    viral_input: float
    affinity: UserAffinityScore
    recency_score: float
    history_penalty: float
    social_boost: float
    following_boost: float
    creator_boost: float = 0.0
    orchestrator_weight: float = 1.0
    session_boost: float = 1.0
    cold_start_exploration: bool = False


@dataclass(slots=True)
class PersonalizedFeedRankingService:
    session: Session
    feed_store: PersonalizedFeedStore
    settings: Settings | None = None
    cache_size: int = DEFAULT_CACHE_SIZE
    candidate_multiplier: int = DEFAULT_CANDIDATE_MULTIPLIER
    max_candidates: int = DEFAULT_MAX_CANDIDATES
    history_limit: int = DEFAULT_HISTORY_LIMIT
    feed_service: ViralFeedService | None = None
    affinity_calculator: ClipAffinityCalculator | None = None
    follow_graph_service: Any | None = None
    social_boost_service: SocialBoostService | None = None
    notification_service: Any | None = None
    feedback_engine: FeedbackEngine | None = None
    cold_start_manager: ColdStartManager | None = None
    runtime_config_loader: Any | None = None
    ranking_service: Any | None = None
    attention_orchestrator: Any | None = None
    session_tracker: Any | None = None
    moment_priority_cache: Any | None = None
    hybrid_for_you_share: float = DEFAULT_HYBRID_FOR_YOU_SHARE
    hybrid_following_share: float = DEFAULT_HYBRID_FOLLOWING_SHARE

    def __post_init__(self) -> None:
        if self.settings is None:
            self.settings = get_settings()
        if self.feed_service is None:
            self.feed_service = ViralFeedService(session=self.session, settings=self.settings)
        if self.affinity_calculator is None:
            self.affinity_calculator = ClipAffinityCalculator(session=self.session)
        if self.feedback_engine is None:
            self.feedback_engine = FeedbackEngine(session=self.session)
        if self.cold_start_manager is None:
            self.cold_start_manager = ColdStartManager(
                session=self.session,
                feedback_engine=self.feedback_engine,
            )
        if self.social_boost_service is None and self.follow_graph_service is not None:
            self.social_boost_service = SocialBoostService(follow_graph_service=self.follow_graph_service)

    def _apply_dynamic_config(self) -> None:
        if self.runtime_config_loader is None:
            return
        try:
            snapshot = self.runtime_config_loader.get_snapshot()
        except Exception:
            return
        self.hybrid_for_you_share = float(snapshot.feed_weights.hybrid_for_you_share)
        self.hybrid_following_share = float(snapshot.feed_weights.hybrid_following_share)

    def get_for_you(
        self,
        *,
        user_id: str,
        limit: int = 20,
        refresh: bool = False,
        session_id: str | None = None,
    ) -> PersonalizedFeedResponse:
        self._apply_dynamic_config()
        resolved_limit = max(1, min(int(limit), self.cache_size))
        return self._build_response(
            cache_subject=user_id,
            user_id=user_id,
            limit=resolved_limit,
            refresh=refresh,
            feed_key=FOR_YOU_FEED_KEY_TEMPLATE.format(user_id=user_id),
            feed_type="for_you",
            mix={
                "for_you": round(self.hybrid_for_you_share, 2),
                "following": round(self.hybrid_following_share, 2),
            },
            ranker=lambda: self._allocate_ranked_entries(
                self._blend_entries(
                    algorithmic=self._rank_mode_candidates(
                        user_id=user_id,
                        limit=resolved_limit,
                        mode="for_you",
                        allocate=False,
                        session_id=session_id,
                    ),
                    following=self._rank_mode_candidates(
                        user_id=user_id,
                        limit=resolved_limit,
                        mode="following",
                        allocate=False,
                        session_id=session_id,
                    ),
                    limit=resolved_limit,
                ),
                limit=resolved_limit,
            ),
        )

    def get_following(
        self,
        *,
        user_id: str,
        limit: int = 20,
        refresh: bool = False,
        session_id: str | None = None,
    ) -> PersonalizedFeedResponse:
        self._apply_dynamic_config()
        resolved_limit = max(1, min(int(limit), self.cache_size))
        return self._build_response(
            cache_subject=following_feed_cache_subject(user_id),
            user_id=user_id,
            limit=resolved_limit,
            refresh=refresh,
            feed_key=FOLLOWING_FEED_KEY_TEMPLATE.format(user_id=user_id),
            feed_type="following",
            mix={"for_you": 0.0, "following": 1.0},
            ranker=lambda: self._rank_mode_candidates(
                user_id=user_id,
                limit=resolved_limit,
                mode="following",
                session_id=session_id,
            ),
        )

    def refresh_for_you(
        self,
        *,
        user_id: str,
        cursor: int,
        limit: int = 20,
        session_id: str | None = None,
    ) -> PersonalizedFeedRefreshResponse:
        resolved_limit = max(1, min(int(limit), self.cache_size))
        current_entries = self.feed_store.top(user_id, resolved_limit)
        current_clip_ids = [
            PersonalizedFeedClipView.model_validate(entry.payload).clip_id
            for entry in current_entries
        ]
        refreshed = self.get_for_you(
            user_id=user_id,
            limit=resolved_limit,
            refresh=True,
            session_id=session_id,
        )
        resolved_cursor = max(int(cursor), -1)
        replace_indices: list[int] = []
        new_items: list[PersonalizedFeedClipView] = []
        for index, clip in enumerate(refreshed.clips):
            if index <= resolved_cursor:
                continue
            current_clip_id = current_clip_ids[index] if index < len(current_clip_ids) else None
            if current_clip_id == clip.clip_id:
                continue
            replace_indices.append(index)
            new_items.append(clip)
        return PersonalizedFeedRefreshResponse(
            new_items=new_items,
            replace_indices=replace_indices,
        )

    def record_delivery(self, response: PersonalizedFeedResponse) -> None:
        if not response.clips:
            return
        cache_subject = response.user_id
        if response.feed_type == "following":
            cache_subject = following_feed_cache_subject(response.user_id)
        self._record_clip_delivery(
            cache_subject=cache_subject,
            user_id=response.user_id,
            clips=response.clips,
        )

    def record_refresh_delivery(self, *, user_id: str, clips: list[PersonalizedFeedClipView]) -> None:
        if not clips:
            return
        self._record_clip_delivery(
            cache_subject=user_id,
            user_id=user_id,
            clips=clips,
        )

    def _build_response(
        self,
        *,
        cache_subject: str,
        user_id: str,
        limit: int,
        refresh: bool,
        feed_key: str,
        feed_type: str,
        mix: dict[str, float],
        ranker,
    ) -> PersonalizedFeedResponse:
        if not refresh:
            cached_entries = self.feed_store.top(cache_subject, limit)
            if cached_entries:
                clips = [PersonalizedFeedClipView.model_validate(entry.payload) for entry in cached_entries]
                return PersonalizedFeedResponse(
                    user_id=user_id,
                    clips=clips,
                    generated_at=datetime.now(UTC),
                    feed_key=feed_key,
                    feed_type=feed_type,
                    mix=mix,
                    cache_hit=True,
                )

        ranked_entries = ranker()
        self.feed_store.replace(cache_subject, ranked_entries)
        clips = [PersonalizedFeedClipView.model_validate(entry.payload) for entry in ranked_entries[:limit]]
        return PersonalizedFeedResponse(
            user_id=user_id,
            clips=clips,
            generated_at=datetime.now(UTC),
            feed_key=feed_key,
            feed_type=feed_type,
            mix=mix,
            cache_hit=False,
        )

    def _rank_mode_candidates(
        self,
        *,
        user_id: str,
        limit: int,
        mode: str,
        allocate: bool = True,
        session_id: str | None = None,
    ) -> list[PersonalizedFeedEnvelope]:
        snapshot = None
        if self.runtime_config_loader is not None:
            try:
                snapshot = self.runtime_config_loader.get_snapshot()
            except Exception:
                snapshot = None
        feed_weights = snapshot.feed_weights if snapshot is not None else None
        candidate_limit = min(self.max_candidates, max(limit * self.candidate_multiplier, limit))
        seen_clip_ids = self.feed_store.seen_clip_ids(user_id)
        candidate_clips = self._resolve_candidate_clips(
            limit=max(candidate_limit, 1),
            excluded_clip_ids=seen_clip_ids,
        )
        if self.attention_orchestrator is not None:
            candidate_clips = self.attention_orchestrator.filter_available(candidate_clips)
        if not candidate_clips:
            return []
        if self.notification_service is not None:
            self.notification_service.process_new_clips(candidate_clips)

        match_updates = self._match_updated_at_map({clip.match_id for clip in candidate_clips})
        max_viral_score = max(float(getattr(clip, "viral_score", 0.0) or 0.0) for clip in candidate_clips) or 1.0
        snapshot = self.affinity_calculator.build_snapshot(user_id)
        new_user = bool(mode == "for_you" and self.cold_start_manager.is_new_user(user_id))
        history_subject = user_id if mode == "for_you" else following_feed_cache_subject(user_id)
        history = self.feed_store.recent_history(history_subject, limit=self.history_limit)
        history_counters = self._history_counters(history)
        creator_user_by_clip = {
            str(getattr(clip, "clip_id", "") or ""): (
                self.follow_graph_service.resolve_creator_user_id(clip)
                if self.follow_graph_service is not None
                else None
            )
            for clip in candidate_clips
        }
        creator_user_ids = {creator_user_id for creator_user_id in creator_user_by_clip.values() if creator_user_id}
        social_context = (
            self.social_boost_service.build_context(
                user_id=user_id,
                creator_user_ids=creator_user_ids,
            )
            if self.social_boost_service is not None and creator_user_ids
            else None
        )

        candidates: list[_PersonalizedCandidate] = []
        for clip in candidate_clips:
            clip_id = str(getattr(clip, "clip_id", "") or "")
            creator_user_id = creator_user_by_clip.get(clip_id)
            social_breakdown = (
                self.social_boost_service.boost_for_creator(
                    creator_user_id=creator_user_id,
                    context=social_context,
                )
                if self.social_boost_service is not None
                else None
            )
            candidates.append(
                self._candidate_from_clip(
                    clip,
                    max_viral_score=max_viral_score,
                    snapshot=snapshot,
                    history_counters=history_counters,
                    updated_at=match_updates.get(clip.match_id),
                    creator_user_id=creator_user_id,
                    social_boost=(social_breakdown.rank_score_boost if social_breakdown is not None else 0.0),
                    following_boost=(social_breakdown.followed_boost if social_breakdown is not None else 0.0),
                    session_id=session_id,
                )
            )

        if new_user and mode == "for_you":
            return self._build_cold_start_entries(
                candidates=candidates,
                limit=limit,
                exploration_rate=(
                    float(feed_weights.exploration_rate)
                    if feed_weights is not None
                    else self.cold_start_manager.exploration_rate(is_new_user=True)
                ),
                allocate=allocate,
            )

        selected_candidates: list[tuple[_PersonalizedCandidate, float, float, float, float, float, float]] = []
        selected_creator_counts: Counter[str] = Counter()
        selected_format_counts: Counter[str] = Counter()
        selected_similarity_counts: Counter[str] = Counter()
        remaining = list(candidates)

        while remaining and len(selected_candidates) < min(self.cache_size, len(candidates)):
            best_index = 0
            best_sort_key: tuple[object, ...] | None = None
            best_score = 0.0
            best_repetition = 0.0
            best_diversity = 0.0
            best_following_boost = 0.0
            best_base_score = 0.0
            best_session_boost = 1.0

            for index, candidate in enumerate(remaining):
                diversity_penalty = self._diversity_penalty(
                    candidate,
                    selected_creator_counts=selected_creator_counts,
                    selected_format_counts=selected_format_counts,
                    selected_similarity_counts=selected_similarity_counts,
                )
                repetition_penalty = min(1.0, candidate.history_penalty + diversity_penalty)
                base_score = max(
                    (
                        (float(feed_weights.viral_score) if feed_weights is not None else 0.40)
                        * candidate.viral_input
                    )
                    + (
                        (float(feed_weights.user_affinity) if feed_weights is not None else 0.30)
                        * candidate.affinity.total
                    )
                    + (
                        (float(feed_weights.recency) if feed_weights is not None else 0.20)
                        * candidate.recency_score
                    )
                    - (
                        (float(feed_weights.repetition_penalty) if feed_weights is not None else 0.10)
                        * repetition_penalty
                    ),
                    0.0,
                )
                session_boost = candidate.session_boost
                session_multiplier = self._session_multiplier(session_boost)
                score = round(max(base_score, 0.0) * session_multiplier, 6)
                if self.attention_orchestrator is not None:
                    score = round(
                        score * max(candidate.orchestrator_weight, 0.0001),
                        6,
                    )
                score = round(
                    max(
                        score
                        + max(candidate.social_boost, 0.0)
                        + max(candidate.following_boost, 0.0)
                        + max(candidate.creator_boost, 0.0),
                        0.0,
                    ),
                    6,
                )
                sort_key = (
                    score,
                    round(candidate.orchestrator_weight, 6),
                    round(session_boost, 6),
                    round(candidate.creator_boost, 6),
                    round(candidate.following_boost, 6),
                    round(candidate.social_boost, 6),
                    round(candidate.affinity.total, 6),
                    round(candidate.recency_score, 6),
                    round(float(getattr(candidate.clip, "viral_score", 0.0) or 0.0), 6),
                    str(getattr(candidate.clip, "clip_id", "")),
                )
                if best_sort_key is None or sort_key > best_sort_key:
                    best_index = index
                    best_sort_key = sort_key
                    best_score = score
                    best_repetition = round(repetition_penalty, 6)
                    best_diversity = round(diversity_penalty, 6)
                    best_following_boost = round(candidate.following_boost, 6)
                    best_base_score = round(base_score, 6)
                    best_session_boost = round(session_boost, 6)

            chosen = remaining.pop(best_index)
            selected_candidates.append(
                (
                    chosen,
                    best_score,
                    best_repetition,
                    best_diversity,
                    best_following_boost,
                    best_base_score,
                    best_session_boost,
                )
            )
            if chosen.creator_key:
                selected_creator_counts[chosen.creator_key] += 1
            if chosen.format_key:
                selected_format_counts[chosen.format_key] += 1
            selected_similarity_counts[chosen.similarity_key] += 1

        envelopes: list[PersonalizedFeedEnvelope] = []
        feed_source = "following" if mode == "following" else "for_you"
        for rank, (candidate, score, repetition_penalty, diversity_penalty, following_boost, base_score, session_boost) in enumerate(selected_candidates, start=1):
            clip_view = PersonalizedFeedClipView(
                **self._base_clip_payload(candidate.clip),
                rank=rank,
                score=score,
                feed_source=feed_source,
                score_breakdown=PersonalizedFeedScoreBreakdownView(
                    viral_score=round(candidate.viral_input, 6),
                    user_affinity=round(candidate.affinity.total, 6),
                    recency_score=round(candidate.recency_score, 6),
                    repetition_penalty=repetition_penalty,
                    diversity_penalty=diversity_penalty,
                    base_score=round(base_score, 6),
                    orchestrator_weight=round(candidate.orchestrator_weight, 6),
                    session_boost=round(session_boost, 6),
                    final_score=round(score, 6),
                    social_boost=round(candidate.social_boost, 6),
                    creator_boost=round(candidate.creator_boost, 6),
                    following_boost=round(following_boost, 6),
                    cold_start_exploration=bool(candidate.cold_start_exploration),
                    affinity=PersonalizedFeedAffinityView(
                        view_signal=round(candidate.affinity.view_signal, 6),
                        like_signal=round(candidate.affinity.like_signal, 6),
                        share_signal=round(candidate.affinity.share_signal, 6),
                        format_preference=round(candidate.affinity.format_preference, 6),
                        creator_preference=round(candidate.affinity.creator_preference, 6),
                    ),
                ),
            )
            envelopes.append(
                PersonalizedFeedEnvelope(
                    clip_id=clip_view.clip_id,
                    score=score,
                    payload=clip_view.model_dump(mode="json"),
                )
            )
        balanced_envelopes = self._rebalance_entry_mix(envelopes, limit=limit)
        if not allocate:
            return self._rerank_entries(balanced_envelopes)
        return self._allocate_ranked_entries(balanced_envelopes, limit=limit)

    def _blend_entries(
        self,
        *,
        algorithmic: list[PersonalizedFeedEnvelope],
        following: list[PersonalizedFeedEnvelope],
        limit: int,
    ) -> list[PersonalizedFeedEnvelope]:
        target_for_you = max(1, min(limit, round(limit * self.hybrid_for_you_share)))
        target_following = max(0, limit - target_for_you)
        selected: list[PersonalizedFeedEnvelope] = []
        seen_clip_ids: set[str] = set()

        for entry in algorithmic:
            if len(selected) >= target_for_you:
                break
            if entry.clip_id in seen_clip_ids:
                continue
            selected.append(entry)
            seen_clip_ids.add(entry.clip_id)

        for entry in following:
            if len([item for item in selected if item.payload.get("feed_source") == "following"]) >= target_following:
                break
            if entry.clip_id in seen_clip_ids:
                continue
            selected.append(entry)
            seen_clip_ids.add(entry.clip_id)

        for pool in (algorithmic, following):
            for entry in pool:
                if len(selected) >= limit:
                    break
                if entry.clip_id in seen_clip_ids:
                    continue
                selected.append(entry)
                seen_clip_ids.add(entry.clip_id)
            if len(selected) >= limit:
                break

        balanced = self._rebalance_entry_mix(selected[:limit], limit=limit)
        return self._rerank_entries(balanced)

    def _build_cold_start_entries(
        self,
        *,
        candidates: list[_PersonalizedCandidate],
        limit: int,
        exploration_rate: float,
        allocate: bool = True,
    ) -> list[PersonalizedFeedEnvelope]:
        ordered = sorted(
            candidates,
            key=lambda candidate: (
                -round(
                    candidate.viral_input
                    + candidate.recency_score
                    + candidate.creator_boost
                    + candidate.social_boost,
                    6,
                ),
                -round(float(getattr(candidate.clip, "viral_score", 0.0) or 0.0), 6),
                str(getattr(candidate.clip, "clip_id", "")),
            ),
        )
        exploit_count = max(1, min(limit, round(limit * max(1.0 - exploration_rate, 0.0))))
        exploration_count = max(0, limit - exploit_count)
        exploit = ordered[:exploit_count]
        exploration_pool = ordered[exploit_count:]
        exploration: list[_PersonalizedCandidate] = []
        if exploration_count > 0 and exploration_pool:
            step = max(len(exploration_pool) // exploration_count, 1)
            for index in range(0, len(exploration_pool), step):
                exploration.append(replace(exploration_pool[index], cold_start_exploration=True))
                if len(exploration) >= exploration_count:
                    break

        selected: list[_PersonalizedCandidate] = []
        while exploit or exploration:
            if exploit:
                selected.append(exploit.pop(0))
            if exploration and len(selected) < limit:
                selected.append(exploration.pop(0))
            if len(selected) >= limit:
                break

        envelopes: list[PersonalizedFeedEnvelope] = []
        for rank, candidate in enumerate(selected[:limit], start=1):
            base_score = round(max(candidate.viral_input + candidate.recency_score, 0.0), 6)
            score = round(
                max(base_score, 0.0) * self._session_multiplier(candidate.session_boost),
                6,
            )
            if self.attention_orchestrator is not None:
                score = round(
                    score * max(candidate.orchestrator_weight, 0.0001),
                    6,
                )
            score = round(
                max(
                    score
                    + max(candidate.creator_boost, 0.0)
                    + max(candidate.social_boost, 0.0)
                    + max(candidate.following_boost, 0.0),
                    0.0,
                ),
                6,
            )
            clip_view = PersonalizedFeedClipView(
                **self._base_clip_payload(candidate.clip),
                rank=rank,
                score=score,
                feed_source="for_you",
                score_breakdown=PersonalizedFeedScoreBreakdownView(
                    viral_score=round(candidate.viral_input, 6),
                    user_affinity=0.0,
                    recency_score=round(candidate.recency_score, 6),
                    repetition_penalty=0.0,
                    diversity_penalty=0.0,
                    base_score=round(base_score, 6),
                    orchestrator_weight=round(candidate.orchestrator_weight, 6),
                    session_boost=round(candidate.session_boost, 6),
                    final_score=round(score, 6),
                    social_boost=round(candidate.social_boost, 6),
                    creator_boost=round(candidate.creator_boost, 6),
                    following_boost=round(candidate.following_boost, 6),
                    cold_start_exploration=bool(candidate.cold_start_exploration),
                    affinity=PersonalizedFeedAffinityView(),
                ),
            )
            envelopes.append(
                PersonalizedFeedEnvelope(
                    clip_id=clip_view.clip_id,
                    score=score,
                    payload=clip_view.model_dump(mode="json"),
                )
            )
        balanced_envelopes = self._rebalance_entry_mix(envelopes, limit=limit)
        if not allocate:
            return self._rerank_entries(balanced_envelopes)
        return self._allocate_ranked_entries(balanced_envelopes, limit=limit)

    def _candidate_from_clip(
        self,
        clip,
        *,
        max_viral_score: float,
        snapshot: UserInteractionSnapshot,
        history_counters: _HistoryCounters,
        updated_at: datetime | None,
        creator_user_id: str | None,
        social_boost: float,
        following_boost: float,
        session_id: str | None,
    ) -> _PersonalizedCandidate:
        creator_key = _creator_key_from_clip(clip)
        creator_id = _creator_id_from_clip(clip)
        format_key = _format_key_from_clip(clip)
        similarity_key = _similarity_key_from_clip(
            clip,
            creator_key=creator_key,
            format_key=format_key,
        )
        affinity = self.affinity_calculator.score_clip(snapshot=snapshot, clip=clip)
        age_hours = self._age_hours(updated_at)
        recency_score = round(exp(-age_hours / 12.0), 6)
        clip_id = str(getattr(clip, "clip_id", "") or "")
        viral_input = round(min(max(float(getattr(clip, "viral_score", 0.0) or 0.0) / max_viral_score, 0.0), 1.0), 6)

        exact_seen_signal = min(
            (history_counters.clip_counts[clip_id] + snapshot.clip_interactions(clip_id)) / 2.0,
            1.0,
        )
        similarity_seen_signal = min(history_counters.similarity_counts[similarity_key] / 3.0, 1.0)
        creator_seen_signal = min(history_counters.creator_counts[creator_key] / 4.0, 1.0) if creator_key else 0.0
        format_seen_signal = min(history_counters.format_counts[format_key] / 5.0, 1.0) if format_key else 0.0
        history_penalty = min(
            1.0,
            (0.55 * exact_seen_signal)
            + (0.20 * similarity_seen_signal)
            + (0.15 * creator_seen_signal)
            + (0.10 * format_seen_signal),
        )
        creator_boost = 0.0
        if creator_id is not None:
            creator_boost += self.feedback_engine.creator_recommendation_boost(creator_id)
            creator_boost += self.cold_start_manager.creator_boost(creator_id)
        orchestrator_weight = 1.0
        if self.attention_orchestrator is not None:
            orchestrator = getattr(clip, "orchestrator", None)
            orchestrator_weight = float(getattr(orchestrator, "orchestrator_weight", 0.0) or 0.0)
            if orchestrator_weight <= 0.0:
                orchestrator_weight = self.attention_orchestrator.weight_for_clip(clip)
        session_boost = self._session_affinity(session_id=session_id, clip=clip)

        return _PersonalizedCandidate(
            clip=clip,
            creator_key=creator_key,
            creator_user_id=creator_user_id,
            format_key=format_key,
            similarity_key=similarity_key,
            viral_input=viral_input,
            affinity=affinity,
            recency_score=recency_score,
            history_penalty=round(history_penalty, 6),
            social_boost=round(social_boost, 6),
            following_boost=round(following_boost, 6),
            creator_boost=round(creator_boost, 6),
            orchestrator_weight=round(max(orchestrator_weight, 0.0001), 6),
            session_boost=session_boost,
        )

    def _resolve_candidate_clips(self, *, limit: int, excluded_clip_ids: set[str] | None = None) -> list[Any]:
        candidates: list[Any] = []
        seen_clip_ids: set[str] = set()
        blocked_clip_ids = excluded_clip_ids or set()
        if self.moment_priority_cache is not None:
            try:
                priority_payloads = self.moment_priority_cache.top(
                    limit=max(limit, 1),
                    excluded_clip_ids=blocked_clip_ids,
                )
            except Exception:
                priority_payloads = []
            for payload in priority_payloads:
                try:
                    clip = ViralTrendingClipView.model_validate(payload)
                except Exception:
                    continue
                clip_id = str(getattr(clip, "clip_id", "") or "")
                if not clip_id or clip_id in seen_clip_ids or clip_id in blocked_clip_ids:
                    continue
                candidates.append(clip)
                seen_clip_ids.add(clip_id)
        if self.ranking_service is not None:
            try:
                ranked_candidates = self.ranking_service.get_candidates(limit=max(limit, 1), refresh=False)
            except Exception:
                ranked_candidates = []
            for clip in ranked_candidates:
                clip_id = str(getattr(clip, "clip_id", "") or "")
                if not clip_id or clip_id in seen_clip_ids or clip_id in blocked_clip_ids:
                    continue
                candidates.append(clip)
                seen_clip_ids.add(clip_id)
        feed = self.feed_service.build_feed(limit=max(limit, 1), allocate_impressions=False)
        for clip in feed.clips:
            clip_id = str(getattr(clip, "clip_id", "") or "")
            if not clip_id or clip_id in seen_clip_ids or clip_id in blocked_clip_ids:
                continue
            candidates.append(clip)
            seen_clip_ids.add(clip_id)
        return candidates

    def _rebalance_entry_mix(
        self,
        entries: list[PersonalizedFeedEnvelope],
        *,
        limit: int,
    ) -> list[PersonalizedFeedEnvelope]:
        if self.attention_orchestrator is None or not entries:
            return entries[: max(int(limit), 0)]
        max_items = max(int(limit), 0)
        if max_items <= 0:
            return []

        human_available = sum(1 for entry in entries if not self._is_agent_entry(entry))
        agent_available = len(entries) - human_available
        if human_available == 0 or agent_available == 0:
            return entries[:max_items]

        config = self.attention_orchestrator.config()
        human_target = min(human_available, max_items, ceil(max_items * float(config.min_human_exposure_guarantee)))
        agent_cap = min(agent_available, max_items, int(max_items * float(config.max_agent_feed_ratio)))

        selected: list[PersonalizedFeedEnvelope] = []
        selected_clip_ids: set[str] = set()
        human_count = 0
        agent_count = 0

        def append_entry(candidate: PersonalizedFeedEnvelope) -> None:
            nonlocal human_count, agent_count
            if candidate.clip_id in selected_clip_ids or len(selected) >= max_items:
                return
            selected.append(candidate)
            selected_clip_ids.add(candidate.clip_id)
            if self._is_agent_entry(candidate):
                agent_count += 1
            else:
                human_count += 1

        for entry in entries:
            if len(selected) >= max_items:
                break
            if self._is_agent_entry(entry):
                if human_count < human_target or agent_count >= agent_cap:
                    continue
            elif human_count >= human_target:
                continue
            append_entry(entry)

        for entry in entries:
            if len(selected) >= max_items:
                break
            if self._is_agent_entry(entry):
                continue
            append_entry(entry)

        for entry in entries:
            if len(selected) >= max_items:
                break
            if not self._is_agent_entry(entry):
                continue
            if agent_count >= agent_cap and human_count >= min(human_available, max_items):
                append_entry(entry)
                continue
            if agent_count >= agent_cap:
                continue
            append_entry(entry)

        if len(selected) < max_items:
            for entry in entries:
                if len(selected) >= max_items:
                    break
                append_entry(entry)

        return selected[:max_items]

    @staticmethod
    def _is_agent_entry(entry: PersonalizedFeedEnvelope) -> bool:
        metadata = entry.payload.get("metadata") if isinstance(entry.payload, dict) else None
        if not isinstance(metadata, dict):
            return False
        origin = str(metadata.get("origin") or "").strip().lower()
        if origin == "creator_agent":
            return True
        if bool(metadata.get("is_agent_generated", False)):
            return True
        agent_id = metadata.get("agent_id")
        return isinstance(agent_id, str) and bool(agent_id.strip())

    def _record_clip_delivery(
        self,
        *,
        cache_subject: str,
        user_id: str,
        clips: list[PersonalizedFeedClipView],
    ) -> None:
        if not clips:
            return
        self.feed_store.mark_served(cache_subject, self._history_entries(clips))
        self.feed_store.mark_seen(user_id, [clip.clip_id for clip in clips])

    @staticmethod
    def _session_multiplier(session_boost: float) -> float:
        return round(0.7 + (0.3 * max(0.0, min(float(session_boost), 1.0))), 6)

    def _session_affinity(self, *, session_id: str | None, clip) -> float:
        if self.session_tracker is None:
            return 1.0
        normalized_session_id = (session_id or "").strip()
        if not normalized_session_id:
            return 1.0
        try:
            return round(
                max(
                    0.0,
                    min(
                        float(self.session_tracker.get_affinity(session_id=normalized_session_id, clip=clip)),
                        1.0,
                    ),
                ),
                6,
            )
        except Exception:
            return 1.0

    def _allocate_ranked_entries(self, entries: list[PersonalizedFeedEnvelope], *, limit: int) -> list[PersonalizedFeedEnvelope]:
        if self.attention_orchestrator is None:
            return entries
        clip_views = [PersonalizedFeedClipView.model_validate(entry.payload) for entry in entries]
        allocated_clips = self.attention_orchestrator.allocate_impressions(clip_views, limit=max(limit, 1))
        reranked: list[PersonalizedFeedEnvelope] = []
        for rank, clip_view in enumerate(allocated_clips, start=1):
            clip_view.rank = rank
            clip_view.score_breakdown.final_score = round(float(clip_view.score), 6)
            reranked.append(
                PersonalizedFeedEnvelope(
                    clip_id=clip_view.clip_id,
                    score=float(clip_view.score),
                    payload=clip_view.model_dump(mode="json"),
                )
            )
        return reranked

    def _base_clip_payload(self, clip) -> dict[str, Any]:
        return clip.model_dump(
            exclude={
                "rank",
                "score",
                "feed_source",
                "score_breakdown",
                "trending_score",
                "age_hours",
                "recompute_bucket",
                "last_ranked_at",
                "trending_metrics",
            }
        )

    def _rerank_entries(self, entries: list[PersonalizedFeedEnvelope]) -> list[PersonalizedFeedEnvelope]:
        reranked: list[PersonalizedFeedEnvelope] = []
        for rank, entry in enumerate(entries, start=1):
            payload = dict(entry.payload)
            payload["rank"] = rank
            reranked.append(
                PersonalizedFeedEnvelope(
                    clip_id=entry.clip_id,
                    score=entry.score,
                    payload=payload,
                )
            )
        return reranked

    def _diversity_penalty(
        self,
        candidate: _PersonalizedCandidate,
        *,
        selected_creator_counts: Counter[str],
        selected_format_counts: Counter[str],
        selected_similarity_counts: Counter[str],
    ) -> float:
        similarity_signal = min(selected_similarity_counts[candidate.similarity_key] / 2.0, 1.0)
        creator_signal = min(selected_creator_counts[candidate.creator_key] / 2.0, 1.0) if candidate.creator_key else 0.0
        format_signal = min(selected_format_counts[candidate.format_key] / 3.0, 1.0) if candidate.format_key else 0.0
        return round(
            min(
                1.0,
                (0.50 * similarity_signal)
                + (0.30 * creator_signal)
                + (0.20 * format_signal),
            ),
            6,
        )

    def _history_entries(self, clips: list[PersonalizedFeedClipView]) -> list[SeenClipHistory]:
        served_at = datetime.now(UTC).isoformat()
        entries: list[SeenClipHistory] = []
        for clip in clips:
            creator_key = _creator_key_from_clip(clip)
            format_key = _format_key_from_clip(clip)
            entries.append(
                SeenClipHistory(
                    clip_id=clip.clip_id,
                    creator_key=creator_key,
                    format_key=format_key,
                    similarity_key=_similarity_key_from_clip(
                        clip,
                        creator_key=creator_key,
                        format_key=format_key,
                    ),
                    served_at=served_at,
                )
            )
        return entries

    def _history_counters(self, history: list[SeenClipHistory]) -> _HistoryCounters:
        counters = _HistoryCounters()
        for entry in history:
            counters.clip_counts[entry.clip_id] += 1
            counters.similarity_counts[entry.similarity_key] += 1
            if entry.creator_key:
                counters.creator_counts[entry.creator_key] += 1
            if entry.format_key:
                counters.format_counts[entry.format_key] += 1
        return counters

    def _match_updated_at_map(self, match_ids: set[str]) -> dict[str, datetime]:
        if not match_ids:
            return {}
        bind = self.session.get_bind()
        if bind is None:
            return {}
        inspector = inspect(bind)
        updated_at_by_match: dict[str, datetime] = {}

        if inspector.has_table(CompetitionMatch.__tablename__):
            for row in self.session.scalars(select(CompetitionMatch).where(CompetitionMatch.id.in_(match_ids))).all():
                updated_at_by_match[row.id] = row.completed_at or row.updated_at or row.created_at or datetime.now(UTC)

        unresolved_match_ids = match_ids.difference(updated_at_by_match.keys())
        if unresolved_match_ids and inspector.has_table(ManagerDuel.__tablename__):
            for row in self.session.scalars(select(ManagerDuel).where(ManagerDuel.id.in_(unresolved_match_ids))).all():
                updated_at_by_match[row.id] = row.completed_at or row.updated_at or row.created_at or datetime.now(UTC)

        return updated_at_by_match

    def _age_hours(self, updated_at: datetime | None) -> float:
        if updated_at is None:
            return 0.0
        resolved = updated_at if updated_at.tzinfo is not None else updated_at.replace(tzinfo=UTC)
        return max((datetime.now(UTC) - resolved.astimezone(UTC)).total_seconds() / 3600.0, 0.0)


def build_personalized_feed_store(*, settings: Settings | None = None) -> PersonalizedFeedStore:
    resolved_settings = settings or get_settings()
    if resolved_settings.redis_url:
        redis_store = RedisPersonalizedFeedStore(resolved_settings.redis_url)
        if redis_store.ping():
            return redis_store
    return InMemoryPersonalizedFeedStore()


def ensure_personalized_feed_store(app: FastAPI, *, settings: Settings | None = None) -> PersonalizedFeedStore:
    store = getattr(app.state, "personalized_feed_store", None)
    if store is None:
        store = build_personalized_feed_store(settings=settings or getattr(app.state, "settings", None))
        app.state.personalized_feed_store = store
    return store


def build_personalized_feed_service(*, app: FastAPI, session: Session) -> PersonalizedFeedRankingService:
    settings = getattr(app.state, "settings", None) or get_settings()
    feedback_engine = FeedbackEngine(session=session)
    return PersonalizedFeedRankingService(
        session=session,
        settings=settings,
        feed_store=ensure_personalized_feed_store(app, settings=settings),
        follow_graph_service=build_follow_graph_service(app=app, session=session),
        notification_service=build_follow_notification_service(app=app, session=session),
        feedback_engine=feedback_engine,
        cold_start_manager=ColdStartManager(session=session, feedback_engine=feedback_engine),
        runtime_config_loader=ensure_runtime_config_loader(app),
        ranking_service=build_viral_ranking_service(app=app, session=session),
        attention_orchestrator=build_attention_orchestrator_service(app=app, session=session),
        session_tracker=ensure_viral_session_tracker(app),
        moment_priority_cache=ensure_moment_priority_cache(app),
    )


def _ratio(counter: Counter[str], key: str | None, total: float) -> float:
    if key is None or total <= 0:
        return 0.0
    return min(max(float(counter[key]) / float(total), 0.0), 1.0)


def _first_non_empty(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _normalize_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _NON_ALPHANUMERIC_RE.sub("_", value.strip().lower()).strip("_")
    return normalized or None


def _creator_key_from_clip(clip) -> str | None:
    metadata = dict(getattr(clip, "metadata", {}) or {})
    creator_candidate = _first_non_empty(metadata, "creator_id", "creator_key", "creator_handle", "creator_name")
    if creator_candidate:
        return _normalize_identifier(creator_candidate)

    distribution_accounts = getattr(clip, "distribution_accounts", []) or []
    for account in distribution_accounts:
        handle = account.get("handle") if isinstance(account, dict) else getattr(account, "handle", None)
        if isinstance(handle, str) and handle.strip():
            return _normalize_identifier(handle)

    team_name = getattr(clip, "team_name", None)
    if isinstance(team_name, str) and team_name.strip():
        return _normalize_identifier(team_name)

    player_name = getattr(clip, "player_name", None)
    if isinstance(player_name, str) and player_name.strip():
        return _normalize_identifier(player_name)
    return None


def _creator_id_from_clip(clip) -> str | None:
    metadata = dict(getattr(clip, "metadata", {}) or {})
    creator_candidate = _first_non_empty(metadata, "creator_id", "creator_key")
    if creator_candidate:
        return creator_candidate
    return None


def _format_key_from_clip(clip) -> str | None:
    metadata = dict(getattr(clip, "metadata", {}) or {})
    format_candidate = _first_non_empty(metadata, "format_type", "format_key", "clip_format")
    if format_candidate:
        return _normalize_identifier(format_candidate)

    editor = getattr(clip, "editor", None)
    editor_format = getattr(editor, "format_key", None)
    if isinstance(editor_format, str) and editor_format.strip():
        return _normalize_identifier(editor_format)

    formats = getattr(clip, "formats", []) or []
    if formats:
        first = formats[0]
        format_key = first.get("format_key") if isinstance(first, dict) else getattr(first, "format_key", None)
        if isinstance(format_key, str) and format_key.strip():
            return _normalize_identifier(format_key)
    return None


def _similarity_key_from_clip(
    clip,
    *,
    creator_key: str | None,
    format_key: str | None,
) -> str:
    event_key = _normalize_identifier(getattr(clip, "event_type", None) or "clip") or "clip"
    team_key = _normalize_identifier(getattr(clip, "team_name", None))
    player_key = _normalize_identifier(getattr(clip, "player_name", None))
    anchor = team_key or creator_key or "unknown"
    tail = player_key or format_key or "default"
    return f"{event_key}:{anchor}:{tail}"


__all__ = [
    "ClipAffinityCalculator",
    "FOR_YOU_FEED_KEY_TEMPLATE",
    "InMemoryPersonalizedFeedStore",
    "PersonalizedFeedRankingService",
    "RedisPersonalizedFeedStore",
    "SeenClipHistory",
    "UserAffinityScore",
    "UserInteractionSnapshot",
    "build_personalized_feed_service",
    "build_personalized_feed_store",
    "ensure_personalized_feed_store",
]
