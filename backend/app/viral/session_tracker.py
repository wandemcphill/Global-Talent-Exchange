from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import json
import logging
from threading import Lock

from fastapi import FastAPI
from redis import Redis
from redis.exceptions import RedisError

from app.viral.ingestion_schemas import ClipEvent, ClipEventType
from app.viral.ranking import base_rank_score, rank_score
from app.viral.schemas import (
    ViralClipView,
    ViralFeedResponse,
    ViralSessionAffinityView,
    ViralSessionFeedContextView,
    ViralSessionStateView,
)

_FEED_REFRESH_MIN = 5
_FEED_REFRESH_MAX = 10
_FULL_WATCH_THRESHOLD = 0.92
_CONTENT_WEIGHT = 10.0
_FORMAT_WEIGHT = 12.0
_TEAM_WEIGHT = 6.0
_EVENT_WEIGHT = 8.0
_TAG_WEIGHT = 2.0
_SCORE_CLAMP = 4.0
_SESSION_TTL_SECONDS = 60 * 60 * 24 * 7
_SESSION_STATE_KEY_PATTERN = "session:{session_id}:state"
_SESSION_AFFINITY_VECTOR_KEY_PATTERN = "session:{session_id}:affinity_vector"
_INTERACTION_EVENTS = {
    ClipEventType.COMPLETE,
    ClipEventType.LOOP,
    ClipEventType.SHARE,
    ClipEventType.COMMENT,
    ClipEventType.LIKE,
}
_SEEN_EVENTS = {
    ClipEventType.VIEW,
    ClipEventType.WATCH_TIME,
    ClipEventType.COMPLETE,
    ClipEventType.SCROLL,
}

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ClipAffinityProfile:
    clip_id: str
    content_type: str | None = None
    format_key: str | None = None
    team_name: str | None = None
    clip_event_type: str | None = None
    tags: tuple[str, ...] = ()


@dataclass(slots=True)
class SessionState:
    session_id: str
    clips_seen: int = 0
    watch_time_ms: int = 0
    skips: int = 0
    interactions: int = 0
    refresh_after_clips: int = _FEED_REFRESH_MIN
    clips_since_refresh: int = 0
    refresh_count: int = 0
    content_affinity: dict[str, float] = field(default_factory=dict)
    format_affinity: dict[str, float] = field(default_factory=dict)
    team_affinity: dict[str, float] = field(default_factory=dict)
    clip_event_affinity: dict[str, float] = field(default_factory=dict)
    tag_affinity: dict[str, float] = field(default_factory=dict)
    skip_counts: dict[str, int] = field(default_factory=dict)
    clip_profiles: dict[str, ClipAffinityProfile] = field(default_factory=dict, repr=False)
    seen_clip_ids: set[str] = field(default_factory=set, repr=False)
    last_updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class SessionSnapshot:
    session_id: str
    refresh_after_clips: int
    clips_until_refresh: int
    pending_refresh: bool
    content_affinity: dict[str, float]
    format_affinity: dict[str, float]
    team_affinity: dict[str, float]
    clip_event_affinity: dict[str, float]
    tag_affinity: dict[str, float]
    override_dimensions: list[str]


@dataclass(slots=True)
class ViralSessionTracker:
    redis_url: str | None = None
    _state: dict[str, SessionState] = field(default_factory=dict, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)
    _redis_client: Redis | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.redis_url:
            return
        try:
            client = Redis.from_url(self.redis_url, decode_responses=True, health_check_interval=30)
            client.ping()
        except RedisError:
            logger.warning("viral.session_tracker.redis_unavailable")
            return
        self._redis_client = client

    def get_state(self, session_id: str) -> ViralSessionStateView:
        normalized_session_id = session_id.strip()
        with self._lock:
            state = self._state_for(normalized_session_id)
            return self._state_view(state)

    def observe_many(self, events: list[ClipEvent]) -> None:
        if not events:
            return
        touched_states: dict[str, SessionState] = {}
        with self._lock:
            for event in events:
                state = self._state_for(event.session_id)
                profile = _profile_from_event(event, state.clip_profiles.get(event.clip_id))
                if _counts_towards_seen(event) and event.clip_id not in state.seen_clip_ids:
                    state.seen_clip_ids.add(event.clip_id)
                    state.clips_seen += 1
                    state.clips_since_refresh += 1
                if event.watch_time_ms is not None:
                    state.watch_time_ms += max(int(event.watch_time_ms), 0)
                if event.event_type is ClipEventType.SCROLL:
                    state.skips += 1
                if event.event_type in _INTERACTION_EVENTS:
                    state.interactions += 1
                self._apply_affinity(state, event, profile)
                state.last_updated_at = _resolve_timestamp(event.timestamp)
                touched_states[state.session_id] = state
            for state in touched_states.values():
                self._persist_state(state)

    def personalize_feed(
        self,
        *,
        session_id: str,
        feed: ViralFeedResponse,
        favorite_team: str | None = None,
        favorite_event_types: list[str] | None = None,
    ) -> ViralFeedResponse:
        normalized_session_id = session_id.strip()
        with self._lock:
            state = self._state_for(normalized_session_id)
            for clip in feed.clips:
                state.clip_profiles[clip.clip_id] = _profile_from_clip(clip)
            refreshed = state.refresh_count == 0 or state.clips_since_refresh >= state.refresh_after_clips
            if refreshed:
                state.refresh_count += 1
                state.clips_since_refresh = 0
                state.refresh_after_clips = _refresh_window(normalized_session_id, state.refresh_count)
            snapshot = self._snapshot(state)
            state.last_updated_at = datetime.now(UTC)
            self._persist_state(state)

        normalized_favorite_team = _normalize(favorite_team)
        favorite_event_set = {_normalize(item) for item in (favorite_event_types or []) if _normalize(item)}
        team_override = "teams" in snapshot.override_dimensions
        event_override = "clip_event_types" in snapshot.override_dimensions

        personalized: list[ViralClipView] = []
        for clip in feed.clips:
            profile = _profile_from_clip(clip)
            session_delta = self._session_boost(profile, snapshot)

            favorite_team_match = bool(
                not team_override and normalized_favorite_team and profile.team_name == normalized_favorite_team
            )
            favorite_event_match = bool(
                not event_override and profile.clip_event_type and profile.clip_event_type in favorite_event_set
            )

            metadata = dict(clip.metadata)
            metadata.setdefault("content_type", profile.content_type or "highlight")
            metadata.setdefault("format_key", profile.format_key)
            base_score = base_rank_score(
                viral_score=clip.viral_score,
                engagement=clip.engagement,
                freshness=clip.freshness,
                favorite_team_match=favorite_team_match,
                favorite_event_match=favorite_event_match,
            )
            session_affinity = max(base_score + session_delta, 0.0)
            metadata["base_score"] = round(base_score, 2)
            metadata["session_affinity"] = round(session_affinity, 2)
            metadata["session_score_adjustment"] = round(session_delta, 2)
            metadata["session_affinity_applied"] = round(session_delta, 2) != 0.0

            personalized.append(
                clip.model_copy(
                    update={
                        "ranking_score": rank_score(
                            viral_score=clip.viral_score,
                            engagement=clip.engagement,
                            freshness=clip.freshness,
                            favorite_team_match=favorite_team_match,
                            favorite_event_match=favorite_event_match,
                            session_boost=session_delta,
                        ),
                        "metadata": metadata,
                    }
                )
            )

        personalized.sort(key=lambda item: (-item.ranking_score, -item.viral_score, item.minute, item.highlight_id))

        personalization = dict(feed.personalization)
        personalization["session_id"] = normalized_session_id

        return feed.model_copy(
            update={
                "clips": personalized,
                "personalization": personalization,
                "session": ViralSessionFeedContextView(
                    session_id=normalized_session_id,
                    refreshed=refreshed,
                    refresh_after_clips=snapshot.refresh_after_clips,
                    clips_until_refresh=snapshot.clips_until_refresh,
                    pending_refresh=snapshot.pending_refresh,
                    override_global_affinity=bool({"teams", "clip_event_types"} & set(snapshot.override_dimensions)),
                    affinity=self._affinity_view(snapshot),
                ),
            }
        )

    def _apply_affinity(self, state: SessionState, event: ClipEvent, profile: ClipAffinityProfile) -> None:
        is_full_watch = _is_full_watch(event)
        if profile.content_type:
            if event.event_type is ClipEventType.SCROLL:
                state.skip_counts[profile.content_type] = state.skip_counts.get(profile.content_type, 0) + 1
                self._adjust_score(state.content_affinity, profile.content_type, -0.45)
                if profile.content_type == "meme" and state.skip_counts[profile.content_type] >= 3:
                    self._adjust_score(state.content_affinity, profile.content_type, -1.0)
            elif is_full_watch:
                self._adjust_score(
                    state.content_affinity,
                    profile.content_type,
                    1.65 if profile.content_type == "tactical" else 0.55,
                )
            elif event.event_type in _INTERACTION_EVENTS:
                self._adjust_score(state.content_affinity, profile.content_type, 0.4)

        if profile.format_key:
            if event.event_type is ClipEventType.SCROLL:
                self._adjust_score(state.format_affinity, profile.format_key, -0.4)
            elif is_full_watch:
                self._adjust_score(state.format_affinity, profile.format_key, 0.8)
            elif event.event_type in _INTERACTION_EVENTS:
                self._adjust_score(state.format_affinity, profile.format_key, 0.25)

        if profile.clip_event_type:
            if event.event_type is ClipEventType.SCROLL:
                self._adjust_score(state.clip_event_affinity, profile.clip_event_type, -0.25)
            elif is_full_watch:
                self._adjust_score(state.clip_event_affinity, profile.clip_event_type, 0.75)
            elif event.event_type in _INTERACTION_EVENTS:
                self._adjust_score(state.clip_event_affinity, profile.clip_event_type, 0.3)

        if profile.team_name:
            if event.event_type is ClipEventType.SCROLL:
                self._adjust_score(state.team_affinity, profile.team_name, -0.2)
            elif is_full_watch:
                self._adjust_score(state.team_affinity, profile.team_name, 0.6)
            elif event.event_type in _INTERACTION_EVENTS:
                self._adjust_score(state.team_affinity, profile.team_name, 0.2)

        for tag in profile.tags:
            if event.event_type is ClipEventType.SCROLL:
                self._adjust_score(state.tag_affinity, tag, -0.1)
            elif is_full_watch:
                self._adjust_score(state.tag_affinity, tag, 0.2)
            elif event.event_type in _INTERACTION_EVENTS:
                self._adjust_score(state.tag_affinity, tag, 0.1)

    def _adjust_score(self, bucket: dict[str, float], key: str, delta: float) -> None:
        if not key or delta == 0.0:
            return
        current = bucket.get(key, 0.0)
        updated = max(-_SCORE_CLAMP, min(_SCORE_CLAMP, current + delta))
        if abs(updated) < 0.01:
            bucket.pop(key, None)
            return
        bucket[key] = round(updated, 4)

    def _session_boost(self, profile: ClipAffinityProfile, snapshot: SessionSnapshot) -> float:
        boost = 0.0
        if profile.content_type:
            boost += snapshot.content_affinity.get(profile.content_type, 0.0) * _CONTENT_WEIGHT
        if profile.format_key:
            boost += snapshot.format_affinity.get(profile.format_key, 0.0) * _FORMAT_WEIGHT
        if profile.team_name:
            boost += snapshot.team_affinity.get(profile.team_name, 0.0) * _TEAM_WEIGHT
        if profile.clip_event_type:
            boost += snapshot.clip_event_affinity.get(profile.clip_event_type, 0.0) * _EVENT_WEIGHT
        for tag in profile.tags:
            boost += snapshot.tag_affinity.get(tag, 0.0) * _TAG_WEIGHT
        return round(boost, 2)

    def _snapshot(self, state: SessionState) -> SessionSnapshot:
        return SessionSnapshot(
            session_id=state.session_id,
            refresh_after_clips=state.refresh_after_clips,
            clips_until_refresh=max(state.refresh_after_clips - state.clips_since_refresh, 0),
            pending_refresh=state.clips_since_refresh >= state.refresh_after_clips,
            content_affinity=dict(state.content_affinity),
            format_affinity=dict(state.format_affinity),
            team_affinity=dict(state.team_affinity),
            clip_event_affinity=dict(state.clip_event_affinity),
            tag_affinity=dict(state.tag_affinity),
            override_dimensions=_override_dimensions(state),
        )

    def _state_view(self, state: SessionState) -> ViralSessionStateView:
        snapshot = self._snapshot(state)
        return ViralSessionStateView(
            session_id=state.session_id,
            clips_seen=state.clips_seen,
            watch_time_ms=state.watch_time_ms,
            skips=state.skips,
            interactions=state.interactions,
            refresh_after_clips=snapshot.refresh_after_clips,
            clips_until_refresh=snapshot.clips_until_refresh,
            pending_refresh=snapshot.pending_refresh,
            affinity=self._affinity_view(snapshot),
            last_updated_at=state.last_updated_at,
        )

    def _affinity_view(self, snapshot: SessionSnapshot) -> ViralSessionAffinityView:
        return ViralSessionAffinityView(
            content_types=_sorted_scores(snapshot.content_affinity),
            formats=_sorted_scores(snapshot.format_affinity),
            teams=_sorted_scores(snapshot.team_affinity),
            clip_event_types=_sorted_scores(snapshot.clip_event_affinity),
            tags=_sorted_scores(snapshot.tag_affinity),
            override_dimensions=list(snapshot.override_dimensions),
        )

    def _persist_state(self, state: SessionState) -> None:
        if self._redis_client is None:
            return
        state_payload = {
            "session_id": state.session_id,
            "clips_seen": state.clips_seen,
            "watch_time_ms": state.watch_time_ms,
            "skips": state.skips,
            "interactions": state.interactions,
            "refresh_after_clips": state.refresh_after_clips,
            "clips_since_refresh": state.clips_since_refresh,
            "refresh_count": state.refresh_count,
            "skip_counts": dict(state.skip_counts),
            "clip_profiles": {
                clip_id: {
                    "clip_id": profile.clip_id,
                    "content_type": profile.content_type,
                    "format_key": profile.format_key,
                    "team_name": profile.team_name,
                    "clip_event_type": profile.clip_event_type,
                    "tags": list(profile.tags),
                }
                for clip_id, profile in state.clip_profiles.items()
            },
            "seen_clip_ids": sorted(state.seen_clip_ids),
            "last_updated_at": state.last_updated_at.astimezone(UTC).isoformat(),
        }
        affinity_payload = {
            "session_id": state.session_id,
            "content_types": _sorted_scores(state.content_affinity),
            "formats": _sorted_scores(state.format_affinity),
            "teams": _sorted_scores(state.team_affinity),
            "clip_event_types": _sorted_scores(state.clip_event_affinity),
            "tags": _sorted_scores(state.tag_affinity),
            "override_dimensions": _override_dimensions(state),
            "updated_at": state.last_updated_at.astimezone(UTC).isoformat(),
        }
        try:
            pipeline = self._redis_client.pipeline()
            pipeline.set(
                _SESSION_STATE_KEY_PATTERN.format(session_id=state.session_id),
                json.dumps(state_payload, ensure_ascii=True, default=str),
                ex=_SESSION_TTL_SECONDS,
            )
            pipeline.set(
                _SESSION_AFFINITY_VECTOR_KEY_PATTERN.format(session_id=state.session_id),
                json.dumps(affinity_payload, ensure_ascii=True, default=str),
                ex=_SESSION_TTL_SECONDS,
            )
            pipeline.execute()
        except RedisError:
            logger.warning("viral.session_tracker.persist_failed session_id=%s", state.session_id)

    def _load_persisted_state(self, session_id: str) -> SessionState | None:
        if self._redis_client is None:
            return None
        try:
            state_payload = self._redis_client.get(_SESSION_STATE_KEY_PATTERN.format(session_id=session_id))
            affinity_payload = self._redis_client.get(
                _SESSION_AFFINITY_VECTOR_KEY_PATTERN.format(session_id=session_id)
            )
        except RedisError:
            logger.warning("viral.session_tracker.load_failed session_id=%s", session_id)
            return None
        if not state_payload:
            return None
        try:
            parsed_state = json.loads(state_payload)
            parsed_affinity = json.loads(affinity_payload) if affinity_payload else {}
        except json.JSONDecodeError:
            return None
        last_updated_raw = parsed_state.get("last_updated_at")
        last_updated_at = datetime.now(UTC)
        if isinstance(last_updated_raw, str):
            try:
                last_updated_at = _resolve_timestamp(datetime.fromisoformat(last_updated_raw.replace("Z", "+00:00")))
            except ValueError:
                last_updated_at = datetime.now(UTC)
        clip_profiles_payload = parsed_state.get("clip_profiles")
        clip_profiles: dict[str, ClipAffinityProfile] = {}
        if isinstance(clip_profiles_payload, dict):
            for clip_id, raw_profile in clip_profiles_payload.items():
                if not isinstance(clip_id, str) or not isinstance(raw_profile, dict):
                    continue
                raw_tags = raw_profile.get("tags")
                clip_profiles[clip_id] = ClipAffinityProfile(
                    clip_id=clip_id,
                    content_type=_normalize(raw_profile.get("content_type")),
                    format_key=_normalize(raw_profile.get("format_key")),
                    team_name=_normalize(raw_profile.get("team_name")),
                    clip_event_type=_normalize(raw_profile.get("clip_event_type")),
                    tags=tuple(_normalize(tag) for tag in (raw_tags or []) if _normalize(tag)),
                )
        return SessionState(
            session_id=session_id,
            clips_seen=int(parsed_state.get("clips_seen", 0) or 0),
            watch_time_ms=int(parsed_state.get("watch_time_ms", 0) or 0),
            skips=int(parsed_state.get("skips", 0) or 0),
            interactions=int(parsed_state.get("interactions", 0) or 0),
            refresh_after_clips=max(
                int(parsed_state.get("refresh_after_clips", _refresh_window(session_id, 0)) or _refresh_window(session_id, 0)),
                1,
            ),
            clips_since_refresh=int(parsed_state.get("clips_since_refresh", 0) or 0),
            refresh_count=int(parsed_state.get("refresh_count", 0) or 0),
            content_affinity=_coerce_score_map(
                parsed_affinity.get("content_types", parsed_affinity.get("content_affinity"))
            ),
            format_affinity=_coerce_score_map(
                parsed_affinity.get("formats", parsed_affinity.get("format_affinity"))
            ),
            team_affinity=_coerce_score_map(parsed_affinity.get("teams", parsed_affinity.get("team_affinity"))),
            clip_event_affinity=_coerce_score_map(
                parsed_affinity.get("clip_event_types", parsed_affinity.get("clip_event_affinity"))
            ),
            tag_affinity=_coerce_score_map(parsed_affinity.get("tags", parsed_affinity.get("tag_affinity"))),
            skip_counts=_coerce_int_map(parsed_state.get("skip_counts")),
            clip_profiles=clip_profiles,
            seen_clip_ids=set(str(item) for item in parsed_state.get("seen_clip_ids", []) if str(item).strip()),
            last_updated_at=last_updated_at,
        )

    def _state_for(self, session_id: str) -> SessionState:
        state = self._state.get(session_id)
        if state is None:
            state = self._load_persisted_state(session_id)
            if state is None:
                state = SessionState(
                    session_id=session_id,
                    refresh_after_clips=_refresh_window(session_id, 0),
                )
            self._state[session_id] = state
        return state


def ensure_viral_session_tracker(app: FastAPI) -> ViralSessionTracker:
    tracker = getattr(app.state, "viral_session_tracker", None)
    if tracker is None:
        settings = getattr(app.state, "settings", None)
        tracker = ViralSessionTracker(redis_url=getattr(settings, "redis_url", None) if settings is not None else None)
        app.state.viral_session_tracker = tracker
    return tracker


def _profile_from_clip(clip: ViralClipView) -> ClipAffinityProfile:
    metadata = dict(clip.metadata)
    tags = tuple(_normalize(tag) for tag in clip.tags if _normalize(tag))
    return ClipAffinityProfile(
        clip_id=clip.clip_id,
        content_type=_normalize(metadata.get("content_type")) or _infer_content_type(clip),
        format_key=_format_key_from_clip(clip),
        team_name=_normalize(clip.team_name),
        clip_event_type=_normalize(clip.event_type),
        tags=tags,
    )


def _profile_from_event(event: ClipEvent, known_profile: ClipAffinityProfile | None) -> ClipAffinityProfile:
    metadata = event.metadata
    tags = tuple(_normalize(tag) for tag in metadata.tags if _normalize(tag))
    return ClipAffinityProfile(
        clip_id=event.clip_id,
        content_type=_normalize(metadata.content_type) or (known_profile.content_type if known_profile is not None else None),
        format_key=_normalize(metadata.format_key) or (known_profile.format_key if known_profile is not None else None),
        team_name=_normalize(metadata.team_name) or (known_profile.team_name if known_profile is not None else None),
        clip_event_type=_normalize(metadata.clip_event_type)
        or (known_profile.clip_event_type if known_profile is not None else None),
        tags=tags or (known_profile.tags if known_profile is not None else ()),
    )


def _infer_content_type(clip: ViralClipView) -> str:
    normalized_event = _normalize(clip.event_type)
    tags = {_normalize(tag) for tag in clip.tags if _normalize(tag)}
    if normalized_event == "tactical_swing" or "tactical" in tags or "breakdown" in tags:
        return "tactical"
    if normalized_event in {"red_card", "missed_big_chance", "penalty_miss", "penalty_missed", "woodwork"}:
        return "meme"
    if {"chaos", "meme"} & tags:
        return "meme"
    return "highlight"


def _sorted_scores(values: dict[str, float]) -> dict[str, float]:
    return {
        key: round(score, 4)
        for key, score in sorted(values.items(), key=lambda item: (-abs(item[1]), item[0]))
    }


def _coerce_score_map(value: object) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, float] = {}
    for key, item in value.items():
        try:
            score = round(float(item), 4)
        except (TypeError, ValueError):
            continue
        if abs(score) < 0.01:
            continue
        normalized[str(key)] = max(-_SCORE_CLAMP, min(_SCORE_CLAMP, score))
    return normalized


def _coerce_int_map(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, int] = {}
    for key, item in value.items():
        try:
            normalized[str(key)] = int(item)
        except (TypeError, ValueError):
            continue
    return normalized


def _override_dimensions(state: SessionState) -> list[str]:
    dimensions: list[str] = []
    if any(abs(score) >= 0.45 for score in state.team_affinity.values()):
        dimensions.append("teams")
    if any(abs(score) >= 0.45 for score in state.clip_event_affinity.values()):
        dimensions.append("clip_event_types")
    if any(abs(score) >= 0.75 for score in state.content_affinity.values()):
        dimensions.append("content_types")
    if any(abs(score) >= 0.45 for score in state.format_affinity.values()):
        dimensions.append("formats")
    return dimensions


def _refresh_window(session_id: str, refresh_count: int) -> int:
    digest = hashlib.sha256(f"{session_id}:{refresh_count}".encode("utf-8")).digest()
    return _FEED_REFRESH_MIN + (digest[0] % (_FEED_REFRESH_MAX - _FEED_REFRESH_MIN + 1))


def _resolve_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _normalize(value: object | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    return normalized or None


def _format_key_from_clip(clip: ViralClipView) -> str | None:
    metadata = dict(clip.metadata or {})
    if normalized := _normalize(metadata.get("format_key")):
        return normalized
    if normalized := _normalize(getattr(clip.editor, "format_key", None)):
        return normalized
    formats = getattr(clip, "formats", None) or []
    if formats:
        return _normalize(getattr(formats[0], "format_key", None))
    return None


def _counts_towards_seen(event: ClipEvent) -> bool:
    return event.event_type in _SEEN_EVENTS


def _is_full_watch(event: ClipEvent) -> bool:
    if event.event_type is ClipEventType.COMPLETE:
        return True
    if event.watch_time_ms is None or event.video_length_ms is None or event.video_length_ms <= 0:
        return False
    return (event.watch_time_ms / event.video_length_ms) >= _FULL_WATCH_THRESHOLD
