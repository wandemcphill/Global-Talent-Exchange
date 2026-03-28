from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import logging
from threading import Lock
from typing import Any, Protocol

from fastapi import FastAPI
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.trust_middleware import SharedTrustMiddleware
from app.feedback_engine.service import FeedbackEngine
from app.models.competition_match import CompetitionMatch
from app.models.manager_duel import ManagerDuel
from app.runtime_config.service import ensure_runtime_config_loader
from app.users.follow_service import build_follow_notification_service
from app.viral.aggregation_worker import (
    clip_low_trust_velocity_key,
    clip_metrics_key,
    clip_velocity_key,
)
from app.viral.campaign_integration import CampaignViralIntegrationHook
from app.viral.cascade import ensure_viral_cascade_engine
from app.viral.scorer import TrendingScoreWeights, ViralRankingInput, score_trending_clip
from app.viral.schemas import ViralTrendingClipView, ViralTrendingMetricsView, ViralTrendingResponse
from app.viral.service import ViralFeedError, ViralFeedService
from app.viral.trust import ensure_trust_score_service
from app.viral.trust_metrics import ClipTrustMetricsReader, build_clip_trust_metrics_reader

logger = logging.getLogger(__name__)

LEADERBOARD_KEY = "leaderboard:clips"
LEADERBOARD_PAYLOAD_KEY = "leaderboard:clips:payloads"
DEFAULT_VELOCITY_THRESHOLD = 0.3
DEFAULT_HOT_AGE_HOURS = 24.0
DEFAULT_LEADERBOARD_SIZE = 100
DEFAULT_MATCH_CANDIDATE_LIMIT = 24
CASCADE_PIN_SCORE_BOOST = 1_000_000.0


@dataclass(slots=True)
class LeaderboardEnvelope:
    clip_id: str
    score: float
    payload: dict[str, Any]


class ViralLeaderboardStore(Protocol):
    def upsert(self, entries: list[LeaderboardEnvelope]) -> None:
        ...

    def replace(self, entries: list[LeaderboardEnvelope]) -> None:
        ...

    def top(self, limit: int) -> list[LeaderboardEnvelope]:
        ...


@dataclass(slots=True)
class InMemoryViralLeaderboardStore:
    _entries: dict[str, tuple[float, str]] = field(default_factory=dict, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def upsert(self, entries: list[LeaderboardEnvelope]) -> None:
        if not entries:
            return
        with self._lock:
            for entry in entries:
                self._entries[entry.clip_id] = (float(entry.score), json.dumps(entry.payload, default=str))

    def replace(self, entries: list[LeaderboardEnvelope]) -> None:
        with self._lock:
            self._entries = {
                entry.clip_id: (float(entry.score), json.dumps(entry.payload, default=str))
                for entry in entries
            }

    def top(self, limit: int) -> list[LeaderboardEnvelope]:
        if limit <= 0:
            return []
        with self._lock:
            ordered = sorted(
                self._entries.items(),
                key=lambda item: (-item[1][0], item[0]),
            )[:limit]
        return [
            LeaderboardEnvelope(
                clip_id=clip_id,
                score=score,
                payload=json.loads(payload),
            )
            for clip_id, (score, payload) in ordered
        ]


@dataclass(slots=True)
class RedisViralLeaderboardStore:
    redis_url: str
    leaderboard_key: str = LEADERBOARD_KEY
    payload_key: str = LEADERBOARD_PAYLOAD_KEY
    _client: Redis = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = Redis.from_url(self.redis_url, decode_responses=True)

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except RedisError:
            logger.warning("viral.ranking.redis.ping_failed")
            return False

    def upsert(self, entries: list[LeaderboardEnvelope]) -> None:
        if not entries:
            return
        mapping = {entry.clip_id: float(entry.score) for entry in entries}
        payload_mapping = {entry.clip_id: json.dumps(entry.payload, default=str) for entry in entries}
        try:
            pipeline = self._client.pipeline()
            pipeline.zadd(self.leaderboard_key, mapping)
            pipeline.hset(self.payload_key, mapping=payload_mapping)
            pipeline.execute()
        except RedisError:
            logger.warning("viral.ranking.redis.upsert_failed entry_count=%s", len(entries))

    def replace(self, entries: list[LeaderboardEnvelope]) -> None:
        mapping = {entry.clip_id: float(entry.score) for entry in entries}
        payload_mapping = {entry.clip_id: json.dumps(entry.payload, default=str) for entry in entries}
        try:
            pipeline = self._client.pipeline()
            pipeline.delete(self.leaderboard_key)
            pipeline.delete(self.payload_key)
            if mapping:
                pipeline.zadd(self.leaderboard_key, mapping)
                pipeline.hset(self.payload_key, mapping=payload_mapping)
            pipeline.execute()
        except RedisError:
            logger.warning("viral.ranking.redis.replace_failed entry_count=%s", len(entries))

    def top(self, limit: int) -> list[LeaderboardEnvelope]:
        if limit <= 0:
            return []
        try:
            ranked = self._client.zrevrange(self.leaderboard_key, 0, limit - 1, withscores=True)
            clip_ids = [clip_id for clip_id, _score in ranked]
            payloads = self._client.hmget(self.payload_key, clip_ids) if clip_ids else []
        except RedisError:
            logger.warning("viral.ranking.redis.top_failed limit=%s", limit)
            return []
        envelopes: list[LeaderboardEnvelope] = []
        for (clip_id, score), payload in zip(ranked, payloads):
            if payload is None:
                continue
            envelopes.append(
                LeaderboardEnvelope(
                    clip_id=clip_id,
                    score=float(score),
                    payload=json.loads(payload),
                )
            )
        return envelopes


@dataclass(frozen=True, slots=True)
class ClipLiveMetricsSnapshot:
    views: float = 0.0
    completions: float = 0.0
    total_watch_time: float = 0.0
    loops: float = 0.0
    shares: float = 0.0
    comments: float = 0.0
    skips: float = 0.0
    views_last_10min: int = 0
    views_last_60min: int = 0
    low_trust_views_last_10min: int = 0
    low_trust_views_last_60min: int = 0

    @property
    def has_metrics(self) -> bool:
        return any(
            value > 0
            for value in (
                self.views,
                self.completions,
                self.total_watch_time,
                self.loops,
                self.shares,
                self.comments,
                self.skips,
                float(self.views_last_10min),
                float(self.views_last_60min),
            )
        )


class ClipLiveMetricsStore(Protocol):
    def get_snapshot(self, clip_id: str, *, now: datetime) -> ClipLiveMetricsSnapshot | None:
        ...


@dataclass(slots=True)
class InMemoryClipLiveMetricsStore:
    def get_snapshot(self, clip_id: str, *, now: datetime) -> ClipLiveMetricsSnapshot | None:
        return None


@dataclass(slots=True)
class RedisClipLiveMetricsStore:
    redis_url: str
    _client: Redis = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = Redis.from_url(self.redis_url, decode_responses=True)

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except RedisError:
            logger.warning("viral.ranking.redis.metrics_ping_failed")
            return False

    def get_snapshot(self, clip_id: str, *, now: datetime) -> ClipLiveMetricsSnapshot | None:
        try:
            pipeline = self._client.pipeline()
            pipeline.hgetall(clip_metrics_key(clip_id))
            pipeline.hgetall(clip_velocity_key(clip_id))
            pipeline.hgetall(clip_low_trust_velocity_key(clip_id))
            metrics_payload, velocity_payload, low_trust_payload = pipeline.execute()
        except RedisError:
            logger.warning("viral.ranking.redis.metrics_fetch_failed clip_id=%s", clip_id)
            return None
        if not metrics_payload and not velocity_payload:
            return None
        return ClipLiveMetricsSnapshot(
            views=_as_float(metrics_payload.get("views")),
            completions=_as_float(metrics_payload.get("completions")),
            total_watch_time=_as_float(metrics_payload.get("total_watch_time")),
            loops=_as_float(metrics_payload.get("loops")),
            shares=_as_float(metrics_payload.get("shares")),
            comments=_as_float(metrics_payload.get("comments")),
            skips=_as_float(metrics_payload.get("skips")),
            views_last_10min=_sum_velocity_bucket_window(velocity_payload, now=now, minutes=10),
            views_last_60min=_sum_velocity_bucket_window(velocity_payload, now=now, minutes=60),
            low_trust_views_last_10min=_sum_velocity_bucket_window(low_trust_payload, now=now, minutes=10),
            low_trust_views_last_60min=_sum_velocity_bucket_window(low_trust_payload, now=now, minutes=60),
        )


@dataclass(slots=True)
class _ReplayCandidate:
    match_id: str
    updated_at: datetime


@dataclass(slots=True)
class ViralRankingService:
    session: Session
    leaderboard_store: ViralLeaderboardStore
    settings: Settings | None = None
    velocity_threshold: float = DEFAULT_VELOCITY_THRESHOLD
    hot_age_hours: float = DEFAULT_HOT_AGE_HOURS
    leaderboard_size: int = DEFAULT_LEADERBOARD_SIZE
    match_candidate_limit: int = DEFAULT_MATCH_CANDIDATE_LIMIT
    feed_service: ViralFeedService | None = None
    notification_service: Any | None = None
    metrics_store: ClipLiveMetricsStore | None = None
    trust_middleware: SharedTrustMiddleware | None = None
    trust_reader: ClipTrustMetricsReader | None = None
    feedback_engine: FeedbackEngine | None = None
    campaign_integration_hook: CampaignViralIntegrationHook | None = None
    runtime_config_loader: Any | None = None

    def __post_init__(self) -> None:
        if self.settings is None:
            self.settings = get_settings()
        if self.feed_service is None:
            self.feed_service = ViralFeedService(session=self.session, settings=self.settings)
        if self.feedback_engine is None:
            self.feedback_engine = FeedbackEngine(session=self.session)
        if self.metrics_store is None:
            self.metrics_store = build_clip_live_metrics_store(settings=self.settings)
        if self.trust_middleware is None:
            self.trust_middleware = SharedTrustMiddleware(session=self.session)
        if self.trust_reader is None:
            self.trust_reader = build_clip_trust_metrics_reader(settings=self.settings)
        if self.campaign_integration_hook is None:
            self.campaign_integration_hook = CampaignViralIntegrationHook(
                session=self.session,
                settings=self.settings,
                feedback_engine=self.feedback_engine,
            )

    def get_trending(self, *, limit: int = 20, refresh: bool = False) -> ViralTrendingResponse:
        normalized_limit = max(1, min(int(limit), self.leaderboard_size))
        has_entries = bool(self.leaderboard_store.top(1))
        refreshed = False
        if refresh or not has_entries:
            self.recompute(scope="all")
            refreshed = True
        return self._response_from_store(limit=normalized_limit, refreshed=refreshed)

    def recompute(self, *, scope: str = "all") -> ViralTrendingResponse:
        if scope not in {"all", "hot"}:
            raise ValueError(f"Unsupported viral ranking scope: {scope}")
        ranked = self._rank_candidates(scope=scope)
        if scope == "all":
            self.leaderboard_store.replace(ranked)
        else:
            self.leaderboard_store.upsert(ranked)
        if self.notification_service is not None:
            self.notification_service.process_viral_clips([entry.payload for entry in ranked])
        return self._response_from_entries(ranked, refreshed=True)

    def _response_from_store(self, *, limit: int, refreshed: bool) -> ViralTrendingResponse:
        clips = [ViralTrendingClipView.model_validate(entry.payload) for entry in self.leaderboard_store.top(limit)]
        return ViralTrendingResponse(
            clips=clips,
            generated_at=datetime.now(UTC),
            refreshed=refreshed,
            leaderboard_key=LEADERBOARD_KEY,
        )

    def _response_from_entries(self, entries: list[LeaderboardEnvelope], *, refreshed: bool) -> ViralTrendingResponse:
        clips = [ViralTrendingClipView.model_validate(entry.payload) for entry in entries[: self.leaderboard_size]]
        return ViralTrendingResponse(
            clips=clips,
            generated_at=datetime.now(UTC),
            refreshed=refreshed,
            leaderboard_key=LEADERBOARD_KEY,
        )

    def _rank_candidates(self, *, scope: str) -> list[LeaderboardEnvelope]:
        ranked: list[LeaderboardEnvelope] = []
        ranked_at = datetime.now(UTC)
        runtime_snapshot = None
        if self.runtime_config_loader is not None:
            try:
                runtime_snapshot = self.runtime_config_loader.get_snapshot()
            except Exception:
                runtime_snapshot = None
        velocity_threshold = (
            float(runtime_snapshot.trust_thresholds.velocity_threshold)
            if runtime_snapshot is not None
            else self.velocity_threshold
        )
        ad_weight_adjustments = self.feedback_engine.viral_weight_adjustments()
        ranking_weights = TrendingScoreWeights(
            completion_rate=(
                float(runtime_snapshot.viral_weights.completion_rate)
                if runtime_snapshot is not None
                else 0.35
            )
            + float(ad_weight_adjustments.get("completion_rate", 0.0)),
            loop_rate=(
                float(runtime_snapshot.viral_weights.loop_rate)
                if runtime_snapshot is not None
                else 0.20
            ),
            share_rate=(
                float(runtime_snapshot.viral_weights.share_rate)
                if runtime_snapshot is not None
                else 0.20
            )
            + float(ad_weight_adjustments.get("share_rate", 0.0)),
            comment_rate=(
                float(runtime_snapshot.viral_weights.comment_rate)
                if runtime_snapshot is not None
                else 0.10
            )
            + float(ad_weight_adjustments.get("comment_rate", 0.0)),
            avg_watch_time=(
                float(runtime_snapshot.viral_weights.avg_watch_time)
                if runtime_snapshot is not None
                else 0.10
            )
            + float(ad_weight_adjustments.get("avg_watch_time", 0.0)),
            skip_penalty=max(
                0.01,
                (
                    float(runtime_snapshot.viral_weights.skip_penalty)
                    if runtime_snapshot is not None
                    else 0.15
                )
                - float(ad_weight_adjustments.get("skip_penalty", 0.0)),
            ),
            velocity_multiplier=(
                float(runtime_snapshot.viral_weights.velocity_multiplier)
                if runtime_snapshot is not None
                else 1.20
            ),
        )
        for candidate in self._recent_replay_candidates():
            age_hours = self._age_hours(candidate.updated_at)
            bucket = "hot" if age_hours <= self.hot_age_hours else "cold"
            if scope == "hot" and bucket != "hot":
                continue
            try:
                feed = self.feed_service.build_match_feed(candidate.match_id, allocate_impressions=False)
            except ViralFeedError:
                continue
            for clip in feed.clips:
                trust_decision = self.trust_middleware.decision_for_user_id(self._creator_user_id_from_clip(clip))
                if trust_decision.blocked or not trust_decision.ranking_eligible:
                    continue
                clip_trust = self.trust_reader.resolve(clip_id=clip.clip_id, metadata=clip.metadata)
                if not clip_trust.viral_boost_eligible:
                    continue
                ranking_input = self._ranking_input(
                    clip,
                    age_hours=age_hours,
                    ranked_at=ranked_at,
                    trust_weight=trust_decision.weight,
                )
                result = score_trending_clip(
                    ranking_input,
                    velocity_threshold=velocity_threshold,
                    weights=ranking_weights,
                )
                payload_metadata = dict(clip.metadata or {})
                payload_metadata["trust_score"] = trust_decision.trust_score
                payload_metadata["trust_weight"] = trust_decision.weight
                payload_metadata["avg_trust_score"] = round(clip_trust.avg_trust_score, 4)
                payload_metadata["clip_trust_score"] = round(clip_trust.clip_trust_score, 4)
                payload_metadata["trust_rejected"] = False
                payload_metadata["raw_trending_score"] = round(result.score, 6)
                sort_score = round(result.score * clip_trust.clip_trust_score, 6)
                payload_metadata["trust_weighted_trending_score"] = sort_score
                cascade_payload = payload_metadata.get("cascade")
                if isinstance(cascade_payload, dict) and bool(cascade_payload.get("cascade")):
                    cascade_payload = dict(cascade_payload)
                    cascade_payload["base_trending_score"] = result.score
                    cascade_payload["trending_pinned"] = True
                    payload_metadata["cascade"] = cascade_payload
                    sort_score = CASCADE_PIN_SCORE_BOOST + sort_score
                trending_clip = ViralTrendingClipView(
                    **clip.model_dump(exclude={"metadata"}),
                    metadata=payload_metadata,
                    rank=1,
                    trending_score=round(result.score * clip_trust.clip_trust_score, 6),
                    age_hours=round(age_hours, 4),
                    recompute_bucket=bucket,
                    last_ranked_at=ranked_at,
                    trending_metrics=ViralTrendingMetricsView(**result.metrics.as_dict()),
                )
                ranked.append(
                    LeaderboardEnvelope(
                        clip_id=clip.clip_id,
                        score=sort_score,
                        payload=trending_clip.model_dump(mode="json"),
                    )
                )
        for clip in self.campaign_integration_hook.list_campaign_clips(limit=self.match_candidate_limit):
            creator_user_id = self._creator_user_id_from_clip(clip)
            trust_decision = self.trust_middleware.decision_for_user_id(creator_user_id)
            if trust_decision.blocked or not trust_decision.ranking_eligible:
                continue
            clip_trust = self.trust_reader.resolve(clip_id=clip.clip_id, metadata=clip.metadata)
            if not clip_trust.viral_boost_eligible:
                continue
            age_hours = self._age_hours(self._campaign_clip_updated_at(clip))
            bucket = "hot" if age_hours <= self.hot_age_hours else "cold"
            if scope == "hot" and bucket != "hot":
                continue
            ranking_input = self._ranking_input(
                clip,
                age_hours=age_hours,
                ranked_at=ranked_at,
                trust_weight=trust_decision.weight,
            )
            result = score_trending_clip(
                ranking_input,
                velocity_threshold=velocity_threshold,
                weights=ranking_weights,
            )
            payload_metadata = dict(clip.metadata or {})
            payload_metadata["trust_score"] = trust_decision.trust_score
            payload_metadata["trust_weight"] = trust_decision.weight
            payload_metadata["avg_trust_score"] = round(clip_trust.avg_trust_score, 4)
            payload_metadata["clip_trust_score"] = round(clip_trust.clip_trust_score, 4)
            payload_metadata["trust_rejected"] = False
            payload_metadata["raw_trending_score"] = round(result.score, 6)
            sort_score = round(result.score * clip_trust.clip_trust_score, 6)
            payload_metadata["trust_weighted_trending_score"] = sort_score
            trending_clip = ViralTrendingClipView(
                **clip.model_dump(exclude={"metadata"}),
                metadata=payload_metadata,
                rank=1,
                trending_score=sort_score,
                age_hours=round(age_hours, 4),
                recompute_bucket=bucket,
                last_ranked_at=ranked_at,
                trending_metrics=ViralTrendingMetricsView(**result.metrics.as_dict()),
            )
            ranked.append(
                LeaderboardEnvelope(
                    clip_id=clip.clip_id,
                    score=sort_score,
                    payload=trending_clip.model_dump(mode="json"),
                )
            )
        ranked.sort(
            key=lambda item: (
                -item.score,
                -float(item.payload.get("viral_score", 0)),
                str(item.clip_id),
            )
        )
        limited = ranked[: self.leaderboard_size]
        for index, entry in enumerate(limited, start=1):
            entry.payload["rank"] = index
            metadata = dict(entry.payload.get("metadata") or {})
            creator_id = metadata.get("creator_id")
            if isinstance(creator_id, str) and creator_id.strip() and float(entry.payload.get("trending_score", 0.0) or 0.0) >= 0.45:
                analytics_payload = dict(entry.payload.get("analytics") or {})
                self.feedback_engine.record_viral_success(
                    creator_id=creator_id,
                    clip_id=entry.clip_id,
                    trending_score=float(entry.payload.get("trending_score", 0.0) or 0.0),
                    analytics=analytics_payload,
                )
        return limited

    def _recent_replay_candidates(self) -> list[_ReplayCandidate]:
        try:
            inspector = inspect(self.session.connection())
        except Exception:
            return []
        candidates: list[_ReplayCandidate] = []

        if inspector.has_table(CompetitionMatch.__tablename__):
            competition_matches = list(
                self.session.scalars(
                    select(CompetitionMatch).order_by(CompetitionMatch.updated_at.desc()).limit(self.match_candidate_limit)
                ).all()
            )
            for row in competition_matches:
                if not isinstance((row.metadata_json or {}).get("replay_payload"), dict):
                    continue
                candidates.append(
                    _ReplayCandidate(
                        match_id=row.id,
                        updated_at=row.completed_at or row.updated_at or row.created_at or datetime.now(UTC),
                    )
                )

        if inspector.has_table(ManagerDuel.__tablename__):
            manager_duels = list(
                self.session.scalars(
                    select(ManagerDuel).order_by(ManagerDuel.updated_at.desc()).limit(self.match_candidate_limit)
                ).all()
            )
            for row in manager_duels:
                if not isinstance((row.metadata_json or {}).get("replay_payload"), dict):
                    continue
                candidates.append(
                    _ReplayCandidate(
                        match_id=row.id,
                        updated_at=row.completed_at or row.updated_at or row.created_at or datetime.now(UTC),
                    )
                )

        candidates.sort(key=lambda item: item.updated_at, reverse=True)
        return candidates[: self.match_candidate_limit]

    def _ranking_input(
        self,
        clip,
        *,
        age_hours: float,
        ranked_at: datetime,
        trust_weight: float,
    ) -> ViralRankingInput:
        analytics = clip.analytics
        resolved_weight = max(float(trust_weight), 0.0)
        views = max(int(round(int(analytics.view_count) * resolved_weight)), 1)
        completions = max(0, min(int(getattr(analytics, "completions", 0) or round(analytics.completion_rate * views)), views))
        total_watch_time = float(getattr(analytics, "total_watch_time", 0.0) or 0.0) * resolved_weight
        if total_watch_time <= 0.0:
            total_watch_time = round(float(analytics.watch_time) * views * resolved_weight, 2)
        loops = float(getattr(analytics, "loops", 0.0) or 0.0) * resolved_weight
        if loops <= 0.0:
            loops = round(float(analytics.loop_rate) * views * resolved_weight, 2)
        skips = max(0, int(getattr(analytics, "skips", 0) or max(views - completions, 0)))
        views_last_60min = int(round((getattr(analytics, "views_last_60min", 0) or 0) * resolved_weight))
        views_last_10min = int(round((getattr(analytics, "views_last_10min", 0) or 0) * resolved_weight))
        live_snapshot = self.metrics_store.get_snapshot(clip.clip_id, now=ranked_at) if self.metrics_store is not None else None
        if live_snapshot is not None and live_snapshot.has_metrics:
            views += int(round(float(live_snapshot.views) * resolved_weight))
            completions = min(
                max(0, completions + int(round(float(live_snapshot.completions) * resolved_weight))),
                views,
            )
            total_watch_time = round(total_watch_time + (float(live_snapshot.total_watch_time) * resolved_weight), 2)
            loops = round(loops + (float(live_snapshot.loops) * resolved_weight), 2)
            skips = max(0, skips + int(round(float(live_snapshot.skips) * resolved_weight)))
            if live_snapshot.views_last_60min > 0:
                views_last_60min = int(round(int(live_snapshot.views_last_60min) * resolved_weight))
            if live_snapshot.views_last_10min > 0:
                views_last_10min = int(round(int(live_snapshot.views_last_10min) * resolved_weight))
        if views_last_60min <= 0 or views_last_10min <= 0:
            views_last_10min, views_last_60min = self._estimate_velocity_windows(
                views=views,
                completion_rate=float(analytics.completion_rate),
                loop_rate=float(analytics.loop_rate),
                share_rate=float(analytics.share_rate),
                age_hours=age_hours,
            )
        return ViralRankingInput(
            clip_id=clip.clip_id,
            views=views,
            completions=completions,
            total_watch_time=total_watch_time,
            loops=loops,
            shares=(
                int(round(int(analytics.shares) * resolved_weight)) + int(round(float(live_snapshot.shares) * resolved_weight))
                if live_snapshot is not None
                else int(round(int(analytics.shares) * resolved_weight))
            ),
            comments=(
                int(round(int(analytics.comments) * resolved_weight)) + int(round(float(live_snapshot.comments) * resolved_weight))
                if live_snapshot is not None
                else int(round(int(analytics.comments) * resolved_weight))
            ),
            skips=skips,
            views_last_10min=views_last_10min,
            views_last_60min=views_last_60min,
            age_hours=age_hours,
            duration_seconds=clip.duration_seconds,
        )

    def _estimate_velocity_windows(
        self,
        *,
        views: int,
        completion_rate: float,
        loop_rate: float,
        share_rate: float,
        age_hours: float,
    ) -> tuple[int, int]:
        freshness_signal = max(0.04, min(1.0, 1.0 / (1.0 + (age_hours / 2.5))))
        recent_view_share = min(0.70, 0.08 + (freshness_signal * 0.45) + (share_rate * 2.0))
        views_last_60min = max(1, min(views, int(round(views * recent_view_share))))
        ten_minute_share = min(0.88, 0.10 + (completion_rate * 0.15) + (loop_rate * 0.40) + (share_rate * 4.0))
        views_last_10min = max(1, min(views_last_60min, int(round(views_last_60min * ten_minute_share))))
        return views_last_10min, views_last_60min

    def _age_hours(self, updated_at: datetime) -> float:
        resolved = updated_at if updated_at.tzinfo is not None else updated_at.replace(tzinfo=UTC)
        return max((datetime.now(UTC) - resolved.astimezone(UTC)).total_seconds() / 3600.0, 0.0)

    @staticmethod
    def _campaign_clip_updated_at(clip) -> datetime:
        metadata = dict(getattr(clip, "metadata", {}) or {})
        raw_value = metadata.get("published_at")
        if isinstance(raw_value, str):
            try:
                parsed = datetime.fromisoformat(raw_value)
            except ValueError:
                parsed = None
            if parsed is not None:
                return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
        return datetime.now(UTC)

    @staticmethod
    def _creator_user_id_from_clip(clip) -> str | None:
        metadata = dict(getattr(clip, "metadata", {}) or {})
        for key in ("creator_user_id", "creator_id", "author_user_id"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None


def build_viral_leaderboard_store(*, settings: Settings | None = None) -> ViralLeaderboardStore:
    resolved_settings = settings or get_settings()
    if resolved_settings.redis_url:
        redis_store = RedisViralLeaderboardStore(resolved_settings.redis_url)
        if redis_store.ping():
            return redis_store
    return InMemoryViralLeaderboardStore()


def build_clip_live_metrics_store(*, settings: Settings | None = None) -> ClipLiveMetricsStore:
    resolved_settings = settings or get_settings()
    if resolved_settings.redis_url:
        redis_store = RedisClipLiveMetricsStore(resolved_settings.redis_url)
        if redis_store.ping():
            return redis_store
    return InMemoryClipLiveMetricsStore()


def ensure_viral_leaderboard_store(app: FastAPI, *, settings: Settings | None = None) -> ViralLeaderboardStore:
    store = getattr(app.state, "viral_leaderboard_store", None)
    if store is None:
        store = build_viral_leaderboard_store(settings=settings or getattr(app.state, "settings", None))
        app.state.viral_leaderboard_store = store
    return store


def build_viral_ranking_service(*, app: FastAPI, session: Session) -> ViralRankingService:
    settings = getattr(app.state, "settings", None) or get_settings()
    cascade_engine = ensure_viral_cascade_engine(app, settings=settings)
    runtime_config_loader = ensure_runtime_config_loader(app)
    feedback_engine = FeedbackEngine(session=session)
    return ViralRankingService(
        session=session,
        settings=settings,
        leaderboard_store=ensure_viral_leaderboard_store(app, settings=settings),
        feed_service=ViralFeedService(
            session=session,
            settings=settings,
            cascade_engine=cascade_engine,
            feedback_engine=feedback_engine,
            runtime_config_loader=runtime_config_loader,
        ),
        notification_service=build_follow_notification_service(app=app, session=session),
        metrics_store=build_clip_live_metrics_store(settings=settings),
        trust_middleware=SharedTrustMiddleware(
            session=session,
            trust_service=ensure_trust_score_service(app, settings=settings),
        ),
        feedback_engine=feedback_engine,
        runtime_config_loader=runtime_config_loader,
    )


def _as_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _sum_velocity_bucket_window(payload: dict[str, str], *, now: datetime, minutes: int) -> int:
    current_bucket = int(now.astimezone(UTC).timestamp() // 60)
    threshold = current_bucket - max(minutes, 1) + 1
    total = 0.0
    for key, value in payload.items():
        try:
            bucket = int(key)
        except (TypeError, ValueError):
            continue
        if bucket < threshold or bucket > current_bucket:
            continue
        total += _as_float(value)
    return max(int(round(total)), 0)


__all__ = [
    "DEFAULT_HOT_AGE_HOURS",
    "DEFAULT_LEADERBOARD_SIZE",
    "DEFAULT_MATCH_CANDIDATE_LIMIT",
    "DEFAULT_VELOCITY_THRESHOLD",
    "LEADERBOARD_KEY",
    "LeaderboardEnvelope",
    "RedisViralLeaderboardStore",
    "ViralRankingService",
    "build_viral_leaderboard_store",
    "build_viral_ranking_service",
    "ensure_viral_leaderboard_store",
]
