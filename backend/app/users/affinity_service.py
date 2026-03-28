from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_affinity_profile import UserAffinityProfile

CLIP_AFFINITY_EVENTS = frozenset(
    {
        "clip.view",
        "clip.complete",
        "clip.like",
        "clip.share",
        "clip.scroll",
    }
)
EVENT_SIGNAL_WEIGHTS = {
    "clip.view": 1.0,
    "clip.complete": 2.5,
    "clip.like": 2.0,
    "clip.share": 3.0,
    "clip.scroll": -1.25,
}
AFFINITY_WEIGHTS = {
    "format_match": 0.40,
    "creator_match": 0.35,
    "engagement_history": 0.25,
}
WATCH_TIME_BASELINE_SECONDS = 60.0
DEFAULT_EVENT_COUNTS = {
    "view": 0,
    "complete": 0,
    "like": 0,
    "share": 0,
    "scroll": 0,
}


def _clamp(value: float, *, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _default_state() -> dict[str, Any]:
    return {
        "event_counts": deepcopy(DEFAULT_EVENT_COUNTS),
        "format_scores": {},
        "creator_scores": {},
        "total_watch_time": 0.0,
        "watch_samples": 0,
        "anonymous_session_total": 0.0,
        "anonymous_session_count": 0,
        "named_session_durations": {},
    }


@dataclass(slots=True)
class UserAffinityService:
    session: Session

    def get_profile(
        self,
        user: User,
        *,
        format_key: str | None = None,
        creator_id: str | None = None,
    ) -> dict[str, Any]:
        profile = self._get_or_create_profile(user_id=user.id)
        affinity = None
        if format_key is not None or creator_id is not None:
            affinity = self.calculate_affinity(profile, format_key=format_key, creator_id=creator_id)
        return self.serialize_profile(profile, affinity=affinity)

    def track_event(
        self,
        *,
        user_id: str | None,
        name: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> UserAffinityProfile | None:
        if not user_id or name not in CLIP_AFFINITY_EVENTS:
            return None
        if self.session.get(User, user_id) is None:
            return None

        profile = self._get_or_create_profile(user_id=user_id)
        state = self._state(profile)
        event_key = name.rsplit(".", maxsplit=1)[-1]
        state["event_counts"][event_key] = int(state["event_counts"].get(event_key, 0)) + 1

        payload = metadata or {}
        watch_time = self._extract_float(
            payload,
            "watch_time",
            "watch_time_seconds",
            "watch_duration",
            "watch_duration_seconds",
        )
        if watch_time > 0:
            state["total_watch_time"] = float(state.get("total_watch_time", 0.0)) + watch_time
            state["watch_samples"] = int(state.get("watch_samples", 0)) + 1

        self._update_session_metrics(state, payload)

        signal_weight = EVENT_SIGNAL_WEIGHTS[name]
        format_key = self._extract_text(payload, "format", "format_type", "clip_format", "content_format")
        creator_key = self._extract_text(payload, "creator_id", "creator", "author_id", "creator_handle")
        self._apply_signal(state["format_scores"], format_key, signal_weight)
        self._apply_signal(state["creator_scores"], creator_key, signal_weight)

        self._refresh_profile(profile, state)
        self.session.flush()
        return profile

    def boost_creator_affinity(
        self,
        *,
        user_id: str,
        creator_id: str,
        delta: float = 4.0,
    ) -> UserAffinityProfile | None:
        if not user_id or not creator_id:
            return None
        if self.session.get(User, user_id) is None:
            return None

        profile = self._get_or_create_profile(user_id=user_id)
        state = self._state(profile)
        self._apply_signal(state["creator_scores"], creator_id, delta)
        self._refresh_profile(profile, state)
        self.session.flush()
        return profile

    def serialize_profile(
        self,
        profile: UserAffinityProfile,
        *,
        affinity: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "profile_key": f"user:{profile.user_id}:profile",
            "user_id": profile.user_id,
            "favorite_formats": dict(profile.favorite_formats_json or {}),
            "favorite_creators": dict(profile.favorite_creators_json or {}),
            "avg_watch_time": round(float(profile.avg_watch_time or 0.0), 4),
            "skip_rate": round(float(profile.skip_rate or 0.0), 4),
            "session_duration": round(float(profile.session_duration or 0.0), 4),
            "engagement_score": round(float(profile.engagement_score or 0.0), 4),
            "affinity_vector": dict(profile.affinity_vector_json or {}),
            "affinity": affinity,
            "updated_at": profile.updated_at,
        }

    def calculate_affinity(
        self,
        profile: UserAffinityProfile,
        *,
        format_key: str | None = None,
        creator_id: str | None = None,
    ) -> dict[str, Any]:
        format_match = float((profile.favorite_formats_json or {}).get(format_key or "", 0.0))
        creator_match = float((profile.favorite_creators_json or {}).get(creator_id or "", 0.0))
        engagement_history = _clamp(
            (float(profile.engagement_score or 0.0) * 0.65)
            + (_clamp(float(profile.avg_watch_time or 0.0) / WATCH_TIME_BASELINE_SECONDS) * 0.20)
            + ((1.0 - float(profile.skip_rate or 0.0)) * 0.15)
        )
        score = _clamp(
            (AFFINITY_WEIGHTS["format_match"] * format_match)
            + (AFFINITY_WEIGHTS["creator_match"] * creator_match)
            + (AFFINITY_WEIGHTS["engagement_history"] * engagement_history)
        )
        return {
            "format": format_key,
            "creator_id": creator_id,
            "format_match": round(format_match, 4),
            "creator_match": round(creator_match, 4),
            "engagement_history": round(engagement_history, 4),
            "score": round(score, 4),
        }

    def _get_or_create_profile(self, *, user_id: str) -> UserAffinityProfile:
        profile = self.session.scalar(select(UserAffinityProfile).where(UserAffinityProfile.user_id == user_id))
        if profile is None:
            profile = UserAffinityProfile(
                user_id=user_id,
                favorite_formats_json={},
                favorite_creators_json={},
                affinity_vector_json={},
                avg_watch_time=0.0,
                skip_rate=0.0,
                session_duration=0.0,
                engagement_score=0.0,
                state_json=_default_state(),
            )
            self.session.add(profile)
            self.session.flush()
        return profile

    def _refresh_profile(self, profile: UserAffinityProfile, state: dict[str, Any]) -> None:
        event_counts = state["event_counts"]
        view_count = int(event_counts.get("view", 0))
        complete_count = int(event_counts.get("complete", 0))
        like_count = int(event_counts.get("like", 0))
        share_count = int(event_counts.get("share", 0))
        scroll_count = int(event_counts.get("scroll", 0))

        watch_denominator = max(view_count, int(state.get("watch_samples", 0)), 1)
        avg_watch_time = float(state.get("total_watch_time", 0.0)) / watch_denominator
        skip_rate = _clamp(scroll_count / max(view_count, 1))
        session_duration = self._resolve_session_duration(state)
        engagement_score = self._compute_engagement_score(
            view_count=view_count,
            complete_count=complete_count,
            like_count=like_count,
            share_count=share_count,
            avg_watch_time=avg_watch_time,
            skip_rate=skip_rate,
        )

        favorite_formats = self._normalize_scores(state["format_scores"], limit=12)
        favorite_creators = self._normalize_scores(state["creator_scores"], limit=12)

        affinity_vector: dict[str, float] = {}
        for key, value in favorite_formats.items():
            affinity_vector[f"format:{key}"] = value
        for key, value in favorite_creators.items():
            affinity_vector[f"creator:{key}"] = value
        affinity_vector = dict(
            sorted(
                affinity_vector.items(),
                key=lambda item: (-item[1], item[0]),
            )[:24]
        )

        profile.favorite_formats_json = favorite_formats
        profile.favorite_creators_json = favorite_creators
        profile.affinity_vector_json = affinity_vector
        profile.avg_watch_time = round(avg_watch_time, 4)
        profile.skip_rate = round(skip_rate, 4)
        profile.session_duration = round(session_duration, 4)
        profile.engagement_score = round(engagement_score, 4)
        profile.state_json = state

    def _state(self, profile: UserAffinityProfile) -> dict[str, Any]:
        state = _default_state()
        stored = deepcopy(profile.state_json or {})

        event_counts = stored.get("event_counts")
        if isinstance(event_counts, dict):
            for key in DEFAULT_EVENT_COUNTS:
                state["event_counts"][key] = int(event_counts.get(key, 0) or 0)

        for key in ("format_scores", "creator_scores", "named_session_durations"):
            source = stored.get(key)
            if isinstance(source, dict):
                state[key] = {str(item_key): float(item_value or 0.0) for item_key, item_value in source.items()}

        # Preserve existing affinity snapshots when the mutable state payload
        # is absent or partially backfilled.
        if not state["format_scores"] and isinstance(profile.favorite_formats_json, dict):
            state["format_scores"] = {
                str(item_key): float(item_value or 0.0)
                for item_key, item_value in profile.favorite_formats_json.items()
            }
        if not state["creator_scores"] and isinstance(profile.favorite_creators_json, dict):
            state["creator_scores"] = {
                str(item_key): float(item_value or 0.0)
                for item_key, item_value in profile.favorite_creators_json.items()
            }

        for key in ("total_watch_time", "anonymous_session_total"):
            state[key] = float(stored.get(key, 0.0) or 0.0)
        for key in ("watch_samples", "anonymous_session_count"):
            state[key] = int(stored.get(key, 0) or 0)

        return state

    @staticmethod
    def _extract_text(metadata: Mapping[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = metadata.get(key)
            if value is None:
                continue
            candidate = str(value).strip()
            if candidate:
                return candidate
        return None

    @staticmethod
    def _extract_float(metadata: Mapping[str, Any], *keys: str) -> float:
        for key in keys:
            value = metadata.get(key)
            if value is None:
                continue
            try:
                candidate = float(value)
            except (TypeError, ValueError):
                continue
            if candidate > 0:
                return candidate
        return 0.0

    @staticmethod
    def _apply_signal(scores: dict[str, float], key: str | None, delta: float) -> None:
        if not key:
            return
        updated = max(float(scores.get(key, 0.0)) + delta, 0.0)
        if updated <= 0:
            scores.pop(key, None)
            return
        scores[key] = round(updated, 4)

    @staticmethod
    def _normalize_scores(scores: Mapping[str, float], *, limit: int) -> dict[str, float]:
        positive_scores = [(key, float(value)) for key, value in scores.items() if key and float(value) > 0]
        if not positive_scores:
            return {}
        positive_scores.sort(key=lambda item: (-item[1], item[0]))
        positive_scores = positive_scores[:limit]
        max_score = max(value for _, value in positive_scores)
        if max_score <= 0:
            return {}
        return {key: round(_clamp(value / max_score), 4) for key, value in positive_scores}

    @staticmethod
    def _update_session_metrics(state: dict[str, Any], metadata: Mapping[str, Any]) -> None:
        session_duration = UserAffinityService._extract_float(
            metadata,
            "session_duration",
            "session_duration_seconds",
        )
        if session_duration <= 0:
            return
        session_id = UserAffinityService._extract_text(metadata, "session_id")
        if session_id:
            existing = float(state["named_session_durations"].get(session_id, 0.0) or 0.0)
            state["named_session_durations"][session_id] = max(existing, session_duration)
            return
        state["anonymous_session_total"] = float(state.get("anonymous_session_total", 0.0)) + session_duration
        state["anonymous_session_count"] = int(state.get("anonymous_session_count", 0)) + 1

    @staticmethod
    def _resolve_session_duration(state: Mapping[str, Any]) -> float:
        named_sessions = state.get("named_session_durations")
        if isinstance(named_sessions, dict) and named_sessions:
            durations = [float(value or 0.0) for value in named_sessions.values() if float(value or 0.0) > 0]
            if durations:
                return sum(durations) / len(durations)
        anonymous_count = int(state.get("anonymous_session_count", 0) or 0)
        if anonymous_count <= 0:
            return 0.0
        return float(state.get("anonymous_session_total", 0.0) or 0.0) / anonymous_count

    @staticmethod
    def _compute_engagement_score(
        *,
        view_count: int,
        complete_count: int,
        like_count: int,
        share_count: int,
        avg_watch_time: float,
        skip_rate: float,
    ) -> float:
        denominator = max(view_count, 1)
        completion_rate = _clamp(complete_count / denominator)
        like_rate = _clamp(like_count / denominator)
        share_rate = _clamp(share_count / denominator)
        watch_quality = _clamp(avg_watch_time / WATCH_TIME_BASELINE_SECONDS)
        return _clamp(
            (completion_rate * 0.35)
            + (like_rate * 0.20)
            + (share_rate * 0.20)
            + (watch_quality * 0.15)
            + ((1.0 - skip_rate) * 0.10)
        )


__all__ = ["CLIP_AFFINITY_EVENTS", "UserAffinityService"]
