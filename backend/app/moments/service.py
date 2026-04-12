from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
from threading import RLock
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from app.backbone.scale_events import enqueue_viral_dispatch
from app.core.events import DomainEvent, EventPublisher
from app.highlights.queue import HighlightRenderJob
from app.highlights.service import HighlightGenerationService
from app.moments.schemas import (
    LiveMomentView,
    LiveMomentsResponse,
    MomentBoostView,
    MomentClipView,
    MomentDestinationView,
)
from app.moments.priority_cache import ensure_moment_priority_cache
from app.viral.comparator import ViralVariantScoringComparator
from app.viral.promotion import ViralClipPromotionService
from app.viral.ranking_service import LeaderboardEnvelope, ViralLeaderboardStore, ensure_viral_leaderboard_store
from app.viral.schemas import (
    ViralCaptionView,
    ViralClipAnalyticsView,
    ViralEditPlanView,
    ViralFeedbackLoopView,
    ViralScoreBreakdownView,
    ViralTrendingClipView,
    ViralTrendingMetricsView,
)
from app.viral.variant_manager import ViralClipVariantManager

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _safe_segment(value: str, *, fallback: str) -> str:
    candidate = (value or "").strip()
    if not candidate:
        return fallback
    sanitized = "".join(
        character if character.isalnum() or character in {"-", "_", "."} else "_" for character in candidate
    )
    sanitized = sanitized.strip("._")
    return sanitized or fallback


@dataclass(slots=True)
class _MatchMomentState:
    home_score: int = 0
    away_score: int = 0


@dataclass(frozen=True, slots=True)
class _NormalizedMatchEvent:
    match_id: str
    source_event_id: str
    sequence_id: int | None
    event_type: str
    source_event_type: str
    minute: int
    clock: str | None
    team_id: str | None
    team: str | None
    player_id: str | None
    player: str | None
    home_score: int
    away_score: int
    metadata: dict[str, Any]

    @property
    def scoreline(self) -> str:
        return f"{self.home_score}-{self.away_score}"


@dataclass(slots=True)
class MomentsEngine:
    app: FastAPI
    highlight_generation_service: HighlightGenerationService
    event_publisher: EventPublisher | None = None
    viral_leaderboard_store: ViralLeaderboardStore | None = None
    session_factory: sessionmaker[Session] | None = None
    max_live_moments: int = 200
    _moments: deque[LiveMomentView] = field(default_factory=deque, init=False, repr=False)
    _match_state: dict[str, _MatchMomentState] = field(default_factory=dict, init=False, repr=False)
    _seen_source_events: set[str] = field(default_factory=set, init=False, repr=False)
    _seen_source_event_order: deque[str] = field(default_factory=deque, init=False, repr=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def handle_event(self, event: DomainEvent) -> None:
        if event.name != "match.events":
            return

        try:
            normalized = self._normalize_match_event(event)
        except Exception:
            return
        with self._lock:
            dedupe_id = normalized.source_event_id or (
                f"seq:{normalized.sequence_id}" if normalized.sequence_id is not None else event.event_id
            )
            source_key = f"{normalized.match_id}:{dedupe_id}"
            if source_key in self._seen_source_events:
                return
            match_state = self._match_state.setdefault(normalized.match_id, _MatchMomentState())
            detected_events = self._detect_key_events(normalized, match_state)
            match_state.home_score = normalized.home_score
            match_state.away_score = normalized.away_score
            if not detected_events:
                self._remember_source_event(source_key)
                return
            self._remember_source_event(source_key)

        moment = self._build_moment(normalized, detected_events=detected_events)
        variant_ids = self._trigger_variant_burst(moment)
        if variant_ids:
            moment.metadata["variant_ids"] = variant_ids
            moment.metadata["variant_count"] = len(variant_ids)

        with self._lock:
            self._moments.appendleft(moment)
            while len(self._moments) > self.max_live_moments:
                self._moments.pop()

        self._push_to_trending_feed(moment)
        self._dispatch_to_viral_engine(moment)
        self._broadcast_moment(moment)

    def live(self, *, limit: int = 20, match_id: str | None = None) -> LiveMomentsResponse:
        with self._lock:
            moments = list(self._moments)
        if match_id is not None:
            moments = [moment for moment in moments if moment.match_id == match_id]
        moments.sort(
            key=lambda item: (-item.boost.final_score, -item.minute, item.moment_id),
        )
        sliced = moments[: max(1, int(limit))]
        return LiveMomentsResponse(
            moments=sliced,
            generated_at=_utcnow(),
            total=len(sliced),
        )

    def _build_moment(
        self,
        event: _NormalizedMatchEvent,
        *,
        detected_events: list[str],
    ) -> LiveMomentView:
        initial_score = self._initial_score(event.event_type)
        priority_boost = 0.0
        reasons: list[str] = []
        if event.event_type == "goal":
            priority_boost += 0.3
            reasons.append("goal_priority_boost")
        if "last_minute_win" in detected_events:
            priority_boost += 0.5
            reasons.append("last_minute_win_bonus")
        hot_window_multiplier = 2.0 if event.minute <= 5 else 1.0
        if hot_window_multiplier > 1.0:
            reasons.append("hot_window_x2")
        final_score = round((initial_score + priority_boost) * hot_window_multiplier, 4)
        clip = self._queue_clip(event, detected_events=detected_events, final_score=final_score)
        moment_id = f"moment_{uuid4().hex}"
        created_at = _utcnow()
        metadata = {
            "priority_reasons": list(reasons),
            "source": "match.events",
            "source_metadata": dict(event.metadata),
        }
        return LiveMomentView(
            moment_id=moment_id,
            match_id=event.match_id,
            source_event_id=event.source_event_id,
            event_type=event.event_type,
            source_event_type=event.source_event_type,
            detected_events=detected_events,
            minute=event.minute,
            clock=event.clock,
            team_id=event.team_id,
            team=event.team,
            player_id=event.player_id,
            player=event.player,
            home_score=event.home_score,
            away_score=event.away_score,
            scoreline=event.scoreline,
            distribution_multiplier=hot_window_multiplier,
            clip=clip,
            boost=MomentBoostView(
                initial_score=initial_score,
                priority_boost=priority_boost,
                hot_window_multiplier=hot_window_multiplier,
                final_score=final_score,
                reasons=reasons,
            ),
            destinations=MomentDestinationView(),
            created_at=created_at,
            metadata=metadata,
        )

    def _queue_clip(
        self,
        event: _NormalizedMatchEvent,
        *,
        detected_events: list[str],
        final_score: float,
    ) -> MomentClipView:
        queue = self.highlight_generation_service.queue
        settings = self.highlight_generation_service.settings
        if queue is None:
            return MomentClipView(render_status="unavailable")

        match_key = _safe_segment(event.match_id, fallback="match")
        source_key = _safe_segment(event.source_event_id, fallback="event")
        storage_key = f"moments/live/{match_key}/{source_key}.mp4"
        title = self._clip_title(event, detected_events=detected_events)
        subtitle = self._clip_subtitle(event)
        event_second = max(0, event.minute * 60)
        source_path = self._optional_string(event.metadata.get("source_path"))
        source_storage_key = self._optional_string(event.metadata.get("source_storage_key"))
        source_status = self.highlight_generation_service.resolve_clip_source_status(
            source_path=source_path,
            source_storage_key=source_storage_key,
        )
        if source_status == "unavailable":
            return MomentClipView(
                storage_key=storage_key,
                render_status="unavailable",
            )
        job = HighlightRenderJob(
            kind="clip",
            match_id=event.match_id,
            highlight_id=event.source_event_id,
            output_storage_key=storage_key,
            title=title,
            subtitle=subtitle,
            duration_seconds=14,
            start_second=max(0, event_second - 8),
            end_second=event_second + 6,
            playback_speed=0.85 if "last_minute_win" in detected_events else 1.0,
            source_path=source_path,
            source_storage_key=source_storage_key,
            metadata={
                "source_event_type": event.source_event_type,
                "event_type": event.event_type,
                "detected_events": list(detected_events),
                "minute": event.minute,
                "team": event.team,
                "player": event.player,
                "home_score": event.home_score,
                "away_score": event.away_score,
                "priority_score": final_score,
            },
        )
        record = queue.enqueue(job)
        render_status = self.highlight_generation_service.render_status_for_record(record)
        if source_status == "pending":
            render_status = "pending"
        cdn_path = None
        if getattr(settings, "cdn_base_url", None):
            cdn_path = f"{str(settings.cdn_base_url).rstrip('/')}/{storage_key}"
        return MomentClipView(
            job_id=record.job_id,
            queue_name=record.queue_name,
            storage_key=storage_key,
            cdn_path=cdn_path,
            render_status=render_status,
        )

    def _dispatch_to_viral_engine(self, moment: LiveMomentView) -> None:
        payload = {
            "match_id": moment.match_id,
            "moment_id": moment.moment_id,
            "clip_id": moment.moment_id,
            "source_event_id": moment.source_event_id,
            "event_type": moment.event_type,
            "detected_events": list(moment.detected_events),
            "priority_score": moment.boost.final_score,
            "storage_key": moment.clip.storage_key,
            "render_status": moment.clip.render_status,
        }
        if self.session_factory is not None:
            try:
                with self.session_factory() as session:
                    enqueue_viral_dispatch(
                        session=session,
                        aggregate_id=moment.match_id,
                        aggregate_type="moment",
                        partition_key=moment.match_id,
                        producer="moments-engine",
                        payload=payload,
                    )
                    session.commit()
            except Exception:
                logger.exception(
                    "moments.dispatch.enqueue_failed match_id=%s moment_id=%s", moment.match_id, moment.moment_id
                )
        if self.event_publisher is None:
            return
        self.event_publisher.publish(
            DomainEvent(
                name="viral.clip.dispatch.requested",
                aggregate_id=moment.match_id,
                aggregate_type="moment",
                partition_key=moment.match_id,
                producer="moments-engine",
                payload=payload,
            )
        )

    def _trigger_variant_burst(self, moment: LiveMomentView) -> list[str]:
        if self.session_factory is None:
            return []
        try:
            with self.session_factory() as session:
                comparator = ViralVariantScoringComparator()
                variant_manager = ViralClipVariantManager(session=session, comparator=comparator)
                variants = variant_manager.generate_variants(self._moment_variant_payload(moment))
                if variants:
                    ViralClipPromotionService(session=session, comparator=comparator).refresh(moment.moment_id)
                session.commit()
        except Exception:
            return []
        return [variant.variant_id for variant in variants]

    def _moment_variant_payload(self, moment: LiveMomentView) -> dict[str, Any]:
        title = self._clip_title_from_moment(moment)
        return {
            "clip_id": moment.moment_id,
            "moment_id": moment.moment_id,
            "match_id": moment.match_id,
            "source_event_id": moment.source_event_id,
            "source_event_type": moment.source_event_type,
            "event_type": moment.event_type,
            "detected_events": list(moment.detected_events),
            "team": moment.team,
            "player": moment.player,
            "title": title,
            "overlay_text": title,
            "storage_key": moment.clip.storage_key,
            "cdn_path": moment.clip.cdn_path,
            "duration_seconds": 14,
            "priority_score": moment.boost.final_score,
            "created_at": moment.created_at,
        }

    def _push_to_trending_feed(self, moment: LiveMomentView) -> None:
        score = float(moment.boost.final_score)
        title = self._clip_title_from_moment(moment)
        caption = self._caption_from_moment(moment)
        breakdown = ViralScoreBreakdownView(
            base_event=int(round(moment.boost.initial_score * 100)),
            late_drama_bonus=50 if "last_minute_win" in moment.detected_events else 0,
            total=int(round(score * 100)),
        )
        trending_clip = ViralTrendingClipView(
            clip_id=moment.moment_id,
            match_id=moment.match_id,
            highlight_id=moment.source_event_id,
            title=title,
            team_name=moment.team,
            player_name=moment.player,
            event_type=moment.event_type,
            minute=moment.minute,
            scoreline_label=moment.scoreline,
            storage_key=moment.clip.storage_key,
            video_url=moment.clip.cdn_path,
            duration_seconds=14.0,
            render_status=moment.clip.render_status,
            viral_score=int(round(score * 100)),
            engagement=0.0,
            freshness=1.0,
            ranking_score=score,
            tags=list(moment.detected_events),
            share_channel="moments_engine",
            breakdown=breakdown,
            caption=ViralCaptionView(
                hook=title,
                caption=caption,
                hashtags=["#GTEX", "#LiveMoment", f"#{moment.event_type.title().replace('_', '')}"],
                source="moments_engine",
            ),
            distribution_accounts=[],
            editor=ViralEditPlanView(
                crop_filter="scale=1080:1920",
                overlay_text=title,
                transcode_command=[],
                overlay_command=[],
                share_targets=["trending_feed"],
            ),
            formats=[],
            analytics=ViralClipAnalyticsView(clip_id=moment.moment_id),
            feedback=ViralFeedbackLoopView(
                performance_tier="hot",
                recommendation="Push immediately while live attention is still concentrated.",
                increase_similar_clips=True,
                actions=["push_to_trending_feed", "broadcast_to_live_watchers"],
                viral_analysis="Live moment seeded directly from the match event stream.",
                analysis_source="moments_engine",
            ),
            metadata={
                "source": "moments_engine",
                "detected_events": list(moment.detected_events),
                "is_moment": True,
            },
            rank=1,
            trending_score=score,
            age_hours=0.0,
            recompute_bucket="hot",
            last_ranked_at=_utcnow(),
            trending_metrics=ViralTrendingMetricsView(
                velocity=score,
                views_last_10min=1,
                views_last_60min=1,
                velocity_boost_applied=moment.distribution_multiplier > 1.0,
                decay_multiplier=1.0,
            ),
        )
        ensure_moment_priority_cache(self.app).put(
            clip_id=trending_clip.clip_id,
            score=score,
            payload=trending_clip.model_dump(mode="json"),
        )
        if self.viral_leaderboard_store is None:
            return
        self.viral_leaderboard_store.upsert(
            [
                LeaderboardEnvelope(
                    clip_id=trending_clip.clip_id,
                    score=score,
                    payload=trending_clip.model_dump(mode="json"),
                )
            ]
        )

    def _broadcast_moment(self, moment: LiveMomentView) -> None:
        if self.event_publisher is None:
            return
        self.event_publisher.publish(
            DomainEvent(
                name="moments.live.created",
                aggregate_id=moment.match_id,
                aggregate_type="moment",
                partition_key=moment.match_id,
                producer="moments-engine",
                payload=moment.model_dump(mode="json"),
            )
        )

    def _detect_key_events(
        self,
        event: _NormalizedMatchEvent,
        match_state: _MatchMomentState,
    ) -> list[str]:
        detected: list[str] = []
        if event.event_type == "goal":
            detected.append("goal")
        if event.event_type == "red_card":
            detected.append("red_card")
        if event.source_event_type in {
            "penalty_awarded",
            "penalty_goal",
            "penalty_scored",
            "penalty_missed",
            "penalty_miss",
        }:
            detected.append("penalty")
        if self._is_last_minute_win(event, match_state):
            detected.append("last_minute_win")
        return detected

    def _is_last_minute_win(self, event: _NormalizedMatchEvent, match_state: _MatchMomentState) -> bool:
        if event.minute < 85 or event.event_type != "goal":
            return False
        home_delta = event.home_score - match_state.home_score
        away_delta = event.away_score - match_state.away_score
        if home_delta > 0 and event.home_score > event.away_score and match_state.home_score <= match_state.away_score:
            return True
        if away_delta > 0 and event.away_score > event.home_score and match_state.away_score <= match_state.home_score:
            return True
        return False

    @staticmethod
    def _normalize_match_event(event: DomainEvent) -> _NormalizedMatchEvent:
        payload = dict(event.payload or {})
        match_id = str(payload.get("match_id") or event.aggregate_id or "").strip()
        if not match_id:
            raise ValueError("match.events payload is missing match_id")
        source_event_id = str(payload.get("source_event_id") or payload.get("event_id") or event.event_id).strip()
        source_event_type = (
            str(payload.get("source_event_type") or payload.get("event_type") or "generic").strip().lower()
        )
        event_type = MomentsEngine._moment_event_type(source_event_type)
        return _NormalizedMatchEvent(
            match_id=match_id,
            source_event_id=source_event_id or event.event_id,
            sequence_id=int(payload.get("sequence_id") or payload.get("sequence") or 0) or None,
            event_type=event_type,
            source_event_type=source_event_type,
            minute=max(0, int(payload.get("minute") or 0)),
            clock=MomentsEngine._optional_string(payload.get("clock")),
            team_id=MomentsEngine._optional_string(payload.get("team_id")),
            team=MomentsEngine._optional_string(payload.get("team")),
            player_id=MomentsEngine._optional_string(payload.get("player_id")),
            player=MomentsEngine._optional_string(payload.get("player")),
            home_score=max(0, int(payload.get("home_score") or 0)),
            away_score=max(0, int(payload.get("away_score") or 0)),
            metadata=dict(payload.get("metadata") or {}),
        )

    @staticmethod
    def _moment_event_type(source_event_type: str) -> str:
        if source_event_type in {"goal", "penalty_goal", "penalty_scored"}:
            return "goal"
        if source_event_type in {"red_card", "red_cards"}:
            return "red_card"
        if source_event_type in {"penalty_awarded", "penalty_missed", "penalty_miss"}:
            return "penalty"
        return source_event_type or "generic"

    @staticmethod
    def _initial_score(event_type: str) -> float:
        return {
            "goal": 1.0,
            "penalty": 0.85,
            "red_card": 0.75,
            "last_minute_win": 1.25,
        }.get(event_type, 0.6)

    @staticmethod
    def _clip_title(event: _NormalizedMatchEvent, *, detected_events: Iterable[str]) -> str:
        if "last_minute_win" in detected_events:
            return f"Last-minute win swing {event.minute}'"
        if event.event_type == "goal":
            return f"Goal {event.minute}'"
        if event.event_type == "red_card":
            return f"Red card {event.minute}'"
        if event.event_type == "penalty":
            return f"Penalty moment {event.minute}'"
        return f"Live moment {event.minute}'"

    @staticmethod
    def _clip_title_from_moment(moment: LiveMomentView) -> str:
        if "last_minute_win" in moment.detected_events:
            return f"Last-minute winner for {moment.team or 'unknown side'}"
        if moment.event_type == "goal":
            return f"Goal for {moment.team or 'unknown side'}"
        if moment.event_type == "red_card":
            return f"Red card changes the match"
        if moment.event_type == "penalty":
            return f"Penalty drama for {moment.team or 'unknown side'}"
        return "Live match moment"

    @staticmethod
    def _clip_subtitle(event: _NormalizedMatchEvent) -> str | None:
        parts = [item for item in (event.team, event.player, event.scoreline) if item]
        if not parts:
            return None
        return " | ".join(parts)

    @staticmethod
    def _caption_from_moment(moment: LiveMomentView) -> str:
        subject = moment.player or moment.team or "The match"
        if "last_minute_win" in moment.detected_events:
            return f"{subject} just flipped the result late. Score now {moment.scoreline}."
        if moment.event_type == "goal":
            return f"{subject} found the net. Score now {moment.scoreline}."
        if moment.event_type == "red_card":
            return f"{subject} just saw red and the match state changed immediately."
        return f"Penalty moment at {moment.minute}' with the score at {moment.scoreline}."

    def _remember_source_event(self, source_key: str) -> None:
        self._seen_source_events.add(source_key)
        self._seen_source_event_order.append(source_key)
        while len(self._seen_source_event_order) > self.max_live_moments * 4:
            removed = self._seen_source_event_order.popleft()
            self._seen_source_events.discard(removed)

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        if value is None:
            return None
        resolved = str(value).strip()
        return resolved or None


def ensure_moments_engine(app: FastAPI) -> MomentsEngine:
    engine = getattr(app.state, "moments_engine", None)
    if isinstance(engine, MomentsEngine):
        return engine

    highlight_generation_service = getattr(app.state, "highlight_generation_service", None)
    if not isinstance(highlight_generation_service, HighlightGenerationService):
        settings = getattr(app.state, "settings", None)
        highlight_generation_service = HighlightGenerationService(settings=settings)
        app.state.highlight_generation_service = highlight_generation_service

    event_publisher = getattr(app.state, "event_publisher", None)
    engine = MomentsEngine(
        app=app,
        highlight_generation_service=highlight_generation_service,
        event_publisher=event_publisher,
        viral_leaderboard_store=ensure_viral_leaderboard_store(app, settings=getattr(app.state, "settings", None)),
        session_factory=getattr(app.state, "session_factory", None),
    )
    app.state.moments_engine = engine
    if event_publisher is not None:
        event_publisher.subscribe(engine.handle_event)
    return engine


def bind_moments_engine(app: FastAPI, _context) -> None:
    ensure_moments_engine(app)


def shutdown_moments_engine(app: FastAPI, _context) -> None:
    app.state.moments_engine = None


__all__ = [
    "MomentsEngine",
    "bind_moments_engine",
    "ensure_moments_engine",
    "shutdown_moments_engine",
]
