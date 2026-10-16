from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
import json
import logging
from typing import Any, Protocol

from fastapi import FastAPI
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import Settings, get_settings
from app.models.user import User
from app.services.device_fingerprint_service import DeviceFingerprintService
from app.viral.anomaly_detector import ClipTrustAnomalyDetector
from app.viral.ingestion_schemas import ClipEvent, ClipEventTrust, ClipEventTrustFactors, ClipEventType

logger = logging.getLogger(__name__)

DEFAULT_USER_TRUST_SCORE = 0.55
DEFAULT_ANON_TRUST_SCORE = 0.45
SHADOW_BAN_THRESHOLD = 0.2
LOW_TRUST_THRESHOLD = 0.35
USER_TRUST_SCORE_KEY_PATTERN = "user:{user_id}:trust_score"
USER_TRUST_PROFILE_KEY_PATTERN = "user:{user_id}:trust_profile"
SESSION_BEHAVIOR_KEY_PATTERN = "session:{session_id}:behavior"
USER_DEVICE_KEY_PATTERN = "trust:user:{user_id}:devices"
PATTERN_ACTOR_KEY_PATTERN = "trust:pattern:{pattern_signature}:actors"
IP_CLUSTER_KEY_PATTERN = "trust:cluster:ip:{ip_hash}"
DEVICE_CLUSTER_KEY_PATTERN = "trust:cluster:device:{fingerprint}"
SESSION_LOOP_KEY_PATTERN = "trust:session:{session_id}:clip:{clip_id}:loops"
PROFILE_TTL_SECONDS = 60 * 60 * 24 * 30
SESSION_TTL_SECONDS = 60 * 60 * 24 * 7
PATTERN_TTL_SECONDS = 60 * 60 * 6
CLUSTER_TTL_SECONDS = 60 * 15
LOOP_TTL_SECONDS = 60 * 60 * 6


@dataclass(frozen=True, slots=True)
class TrustFactorBreakdown:
    account_age: float
    session_consistency: float
    device_fingerprint_stability: float
    engagement_authenticity: float
    anomaly_detection: float

    def as_dict(self) -> dict[str, float]:
        return {
            "account_age": round(self.account_age, 4),
            "session_consistency": round(self.session_consistency, 4),
            "device_fingerprint_stability": round(self.device_fingerprint_stability, 4),
            "engagement_authenticity": round(self.engagement_authenticity, 4),
            "anomaly_detection": round(self.anomaly_detection, 4),
        }


@dataclass(frozen=True, slots=True)
class TrustState:
    user_id: str
    trust_score: float
    suspicious_event_count: int
    healthy_event_count: int
    shadow_banned: bool
    monetization_eligible: bool
    ranking_eligible: bool
    suspicious_flags: tuple[str, ...]
    factors: TrustFactorBreakdown
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "trust_score": round(self.trust_score, 4),
            "suspicious_event_count": int(self.suspicious_event_count),
            "healthy_event_count": int(self.healthy_event_count),
            "shadow_banned": bool(self.shadow_banned),
            "monetization_eligible": bool(self.monetization_eligible),
            "ranking_eligible": bool(self.ranking_eligible),
            "suspicious_flags": list(self.suspicious_flags),
            "factors": self.factors.as_dict(),
            "updated_at": self.updated_at.astimezone(UTC).isoformat(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrustState":
        factors_payload = payload.get("factors") if isinstance(payload.get("factors"), Mapping) else {}
        return cls(
            user_id=str(payload.get("user_id") or ""),
            trust_score=_coerce_float(payload.get("trust_score"), default=DEFAULT_USER_TRUST_SCORE),
            suspicious_event_count=_coerce_int(payload.get("suspicious_event_count"), default=0),
            healthy_event_count=_coerce_int(payload.get("healthy_event_count"), default=0),
            shadow_banned=bool(payload.get("shadow_banned", False)),
            monetization_eligible=bool(payload.get("monetization_eligible", True)),
            ranking_eligible=bool(payload.get("ranking_eligible", True)),
            suspicious_flags=tuple(str(item) for item in payload.get("suspicious_flags", []) if str(item).strip()),
            factors=TrustFactorBreakdown(
                account_age=_coerce_float(factors_payload.get("account_age"), default=0.5),
                session_consistency=_coerce_float(factors_payload.get("session_consistency"), default=0.75),
                device_fingerprint_stability=_coerce_float(
                    factors_payload.get("device_fingerprint_stability"),
                    default=0.75,
                ),
                engagement_authenticity=_coerce_float(
                    factors_payload.get("engagement_authenticity"),
                    default=0.75,
                ),
                anomaly_detection=_coerce_float(factors_payload.get("anomaly_detection"), default=0.75),
            ),
            updated_at=_parse_datetime(payload.get("updated_at")),
        )


@dataclass(frozen=True, slots=True)
class SessionBehaviorState:
    session_id: str
    event_count: int = 0
    unique_clip_count: int = 0
    suspicious_event_count: int = 0
    healthy_event_count: int = 0
    total_loops: int = 0
    fast_scroll_count: int = 0
    countries: tuple[str, ...] = ()
    referrers: tuple[str, ...] = ()
    device_fingerprints: tuple[str, ...] = ()
    ip_hashes: tuple[str, ...] = ()
    recent_clip_ids: tuple[str, ...] = ()
    last_pattern_signature: str | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "event_count": int(self.event_count),
            "unique_clip_count": int(self.unique_clip_count),
            "suspicious_event_count": int(self.suspicious_event_count),
            "healthy_event_count": int(self.healthy_event_count),
            "total_loops": int(self.total_loops),
            "fast_scroll_count": int(self.fast_scroll_count),
            "countries": list(self.countries),
            "referrers": list(self.referrers),
            "device_fingerprints": list(self.device_fingerprints),
            "ip_hashes": list(self.ip_hashes),
            "recent_clip_ids": list(self.recent_clip_ids),
            "last_pattern_signature": self.last_pattern_signature,
            "updated_at": self.updated_at.astimezone(UTC).isoformat(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SessionBehaviorState":
        return cls(
            session_id=str(payload.get("session_id") or ""),
            event_count=_coerce_int(payload.get("event_count"), default=0),
            unique_clip_count=_coerce_int(payload.get("unique_clip_count"), default=0),
            suspicious_event_count=_coerce_int(payload.get("suspicious_event_count"), default=0),
            healthy_event_count=_coerce_int(payload.get("healthy_event_count"), default=0),
            total_loops=_coerce_int(payload.get("total_loops"), default=0),
            fast_scroll_count=_coerce_int(payload.get("fast_scroll_count"), default=0),
            countries=_normalized_tuple(payload.get("countries")),
            referrers=_normalized_tuple(payload.get("referrers")),
            device_fingerprints=_normalized_tuple(payload.get("device_fingerprints")),
            ip_hashes=_normalized_tuple(payload.get("ip_hashes")),
            recent_clip_ids=_normalized_tuple(payload.get("recent_clip_ids"), preserve_case=True),
            last_pattern_signature=_normalized_string(payload.get("last_pattern_signature"), preserve_case=True),
            updated_at=_parse_datetime(payload.get("updated_at")),
        )


class TrustStateStore(Protocol):
    def ping(self) -> bool:
        ...

    def load_trust_state(self, user_id: str) -> TrustState | None:
        ...

    def save_trust_state(self, state: TrustState) -> None:
        ...

    def load_session_behavior(self, session_id: str) -> SessionBehaviorState | None:
        ...

    def save_session_behavior(self, state: SessionBehaviorState) -> None:
        ...

    def register_user_device(self, user_id: str, fingerprint: str) -> int:
        ...

    def register_pattern_actor(self, pattern_signature: str, actor_key: str) -> int:
        ...

    def record_cluster_activity(self, *, ip_hash: str | None, fingerprint: str) -> tuple[int, int]:
        ...

    def record_session_loop(self, *, session_id: str, clip_id: str) -> int:
        ...


@dataclass(slots=True)
class InMemoryTrustStateStore:
    _trust_profiles: dict[str, TrustState] = field(default_factory=dict, init=False, repr=False)
    _session_profiles: dict[str, SessionBehaviorState] = field(default_factory=dict, init=False, repr=False)
    _user_devices: dict[str, set[str]] = field(default_factory=dict, init=False, repr=False)
    _pattern_actors: dict[str, set[str]] = field(default_factory=dict, init=False, repr=False)
    _ip_clusters: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _device_clusters: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _session_loops: dict[str, int] = field(default_factory=dict, init=False, repr=False)

    def ping(self) -> bool:
        return True

    def load_trust_state(self, user_id: str) -> TrustState | None:
        return self._trust_profiles.get(user_id)

    def save_trust_state(self, state: TrustState) -> None:
        self._trust_profiles[state.user_id] = state

    def load_session_behavior(self, session_id: str) -> SessionBehaviorState | None:
        return self._session_profiles.get(session_id)

    def save_session_behavior(self, state: SessionBehaviorState) -> None:
        self._session_profiles[state.session_id] = state

    def register_user_device(self, user_id: str, fingerprint: str) -> int:
        bucket = self._user_devices.setdefault(user_id, set())
        bucket.add(fingerprint)
        return len(bucket)

    def register_pattern_actor(self, pattern_signature: str, actor_key: str) -> int:
        bucket = self._pattern_actors.setdefault(pattern_signature, set())
        bucket.add(actor_key)
        return len(bucket)

    def record_cluster_activity(self, *, ip_hash: str | None, fingerprint: str) -> tuple[int, int]:
        ip_count = 0
        if ip_hash:
            self._ip_clusters[ip_hash] = self._ip_clusters.get(ip_hash, 0) + 1
            ip_count = self._ip_clusters[ip_hash]
        self._device_clusters[fingerprint] = self._device_clusters.get(fingerprint, 0) + 1
        return ip_count, self._device_clusters[fingerprint]

    def record_session_loop(self, *, session_id: str, clip_id: str) -> int:
        key = f"{session_id}:{clip_id}"
        self._session_loops[key] = self._session_loops.get(key, 0) + 1
        return self._session_loops[key]


@dataclass(slots=True)
class RedisTrustStateStore:
    redis_url: str
    _client: Redis = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = Redis.from_url(self.redis_url, decode_responses=True, health_check_interval=30)

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except RedisError:
            logger.warning("viral.trust.redis.ping_failed")
            return False

    def load_trust_state(self, user_id: str) -> TrustState | None:
        try:
            payload = self._client.get(USER_TRUST_PROFILE_KEY_PATTERN.format(user_id=user_id))
        except RedisError:
            logger.warning("viral.trust.redis.load_user_failed user_id=%s", user_id)
            return None
        if not payload:
            return None
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return None
        return TrustState.from_dict(parsed)

    def save_trust_state(self, state: TrustState) -> None:
        payload = json.dumps(state.to_dict(), ensure_ascii=True, default=str)
        score_key = USER_TRUST_SCORE_KEY_PATTERN.format(user_id=state.user_id)
        profile_key = USER_TRUST_PROFILE_KEY_PATTERN.format(user_id=state.user_id)
        try:
            pipeline = self._client.pipeline()
            pipeline.set(score_key, f"{state.trust_score:.4f}", ex=PROFILE_TTL_SECONDS)
            pipeline.set(profile_key, payload, ex=PROFILE_TTL_SECONDS)
            pipeline.execute()
        except RedisError:
            logger.warning("viral.trust.redis.save_user_failed user_id=%s", state.user_id)

    def load_session_behavior(self, session_id: str) -> SessionBehaviorState | None:
        try:
            payload = self._client.get(SESSION_BEHAVIOR_KEY_PATTERN.format(session_id=session_id))
        except RedisError:
            logger.warning("viral.trust.redis.load_session_failed session_id=%s", session_id)
            return None
        if not payload:
            return None
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return None
        return SessionBehaviorState.from_dict(parsed)

    def save_session_behavior(self, state: SessionBehaviorState) -> None:
        payload = json.dumps(state.to_dict(), ensure_ascii=True, default=str)
        try:
            self._client.set(
                SESSION_BEHAVIOR_KEY_PATTERN.format(session_id=state.session_id),
                payload,
                ex=SESSION_TTL_SECONDS,
            )
        except RedisError:
            logger.warning("viral.trust.redis.save_session_failed session_id=%s", state.session_id)

    def register_user_device(self, user_id: str, fingerprint: str) -> int:
        key = USER_DEVICE_KEY_PATTERN.format(user_id=user_id)
        try:
            pipeline = self._client.pipeline()
            pipeline.sadd(key, fingerprint)
            pipeline.expire(key, PROFILE_TTL_SECONDS)
            pipeline.scard(key)
            response = pipeline.execute()
            return _coerce_int(response[-1], default=1)
        except RedisError:
            logger.warning("viral.trust.redis.register_device_failed user_id=%s", user_id)
            return 1

    def register_pattern_actor(self, pattern_signature: str, actor_key: str) -> int:
        key = PATTERN_ACTOR_KEY_PATTERN.format(pattern_signature=pattern_signature)
        try:
            pipeline = self._client.pipeline()
            pipeline.sadd(key, actor_key)
            pipeline.expire(key, PATTERN_TTL_SECONDS)
            pipeline.scard(key)
            response = pipeline.execute()
            return _coerce_int(response[-1], default=1)
        except RedisError:
            logger.warning("viral.trust.redis.register_pattern_failed pattern=%s", pattern_signature)
            return 1

    def record_cluster_activity(self, *, ip_hash: str | None, fingerprint: str) -> tuple[int, int]:
        ip_count = 0
        device_count = 1
        try:
            pipeline = self._client.pipeline()
            if ip_hash:
                ip_key = IP_CLUSTER_KEY_PATTERN.format(ip_hash=ip_hash)
                pipeline.incr(ip_key)
                pipeline.expire(ip_key, CLUSTER_TTL_SECONDS)
            device_key = DEVICE_CLUSTER_KEY_PATTERN.format(fingerprint=fingerprint)
            pipeline.incr(device_key)
            pipeline.expire(device_key, CLUSTER_TTL_SECONDS)
            response = pipeline.execute()
            if ip_hash:
                ip_count = _coerce_int(response[0], default=0)
                device_count = _coerce_int(response[2], default=1)
            else:
                device_count = _coerce_int(response[0], default=1)
        except RedisError:
            logger.warning("viral.trust.redis.cluster_activity_failed")
        return ip_count, device_count

    def record_session_loop(self, *, session_id: str, clip_id: str) -> int:
        key = SESSION_LOOP_KEY_PATTERN.format(session_id=session_id, clip_id=clip_id)
        try:
            pipeline = self._client.pipeline()
            pipeline.incr(key)
            pipeline.expire(key, LOOP_TTL_SECONDS)
            response = pipeline.execute()
            return _coerce_int(response[0], default=1)
        except RedisError:
            logger.warning("viral.trust.redis.loop_record_failed session_id=%s clip_id=%s", session_id, clip_id)
            return 1


@dataclass(slots=True)
class TrustEvaluation:
    state: TrustState | None
    session_behavior: SessionBehaviorState
    trust: ClipEventTrust


@dataclass(slots=True)
class TrustScoreService:
    store: TrustStateStore = field(default_factory=InMemoryTrustStateStore)
    anomaly_detector: ClipTrustAnomalyDetector = field(default_factory=ClipTrustAnomalyDetector)
    fingerprint_service: DeviceFingerprintService = field(default_factory=DeviceFingerprintService)

    def evaluate_event(
        self,
        event: ClipEvent,
        *,
        headers: Mapping[str, str],
        ip_address: str | None,
        user: User | None,
    ) -> TrustEvaluation:
        now = _resolve_timestamp(event.timestamp)
        actor_user_id = (event.user_id or (user.id if user is not None else None) or "").strip() or None
        session_behavior = self.store.load_session_behavior(event.session_id) or SessionBehaviorState(session_id=event.session_id)
        previous_state = self.store.load_trust_state(actor_user_id) if actor_user_id else None

        fingerprint_result = self.fingerprint_service.build(headers=headers)
        fingerprint = fingerprint_result.fingerprint
        ip_hash = _hash_value(ip_address) if ip_address else None
        pattern_signature = self._pattern_signature(event)

        distinct_user_devices = (
            self.store.register_user_device(actor_user_id, fingerprint)
            if actor_user_id is not None
            else 0
        )
        actor_key = actor_user_id or f"anon:{event.session_id}"
        pattern_actor_count = self.store.register_pattern_actor(pattern_signature, actor_key)
        ip_cluster_count, device_cluster_count = self.store.record_cluster_activity(
            ip_hash=ip_hash,
            fingerprint=fingerprint,
        )
        loop_count = 0
        if event.event_type is ClipEventType.LOOP:
            loop_count = self.store.record_session_loop(session_id=event.session_id, clip_id=event.clip_id)

        anomaly = self.anomaly_detector.assess(
            event,
            loop_count=loop_count,
            pattern_actor_count=pattern_actor_count,
            ip_cluster_count=ip_cluster_count,
            device_cluster_count=device_cluster_count,
        )

        factors = TrustFactorBreakdown(
            account_age=self._account_age_factor(user.created_at if user is not None else None),
            session_consistency=self._session_consistency_factor(
                session_behavior=session_behavior,
                event=event,
                fingerprint=fingerprint,
                ip_hash=ip_hash,
            ),
            device_fingerprint_stability=self._device_stability_factor(
                actor_user_id=actor_user_id,
                session_behavior=session_behavior,
                fingerprint=fingerprint,
                distinct_user_devices=distinct_user_devices,
            ),
            engagement_authenticity=self._engagement_authenticity_factor(event=event, loop_count=loop_count),
            anomaly_detection=anomaly.anomaly_factor,
        )
        base_score = self._base_score(factors)
        previous_score = previous_state.trust_score if previous_state is not None else (
            DEFAULT_USER_TRUST_SCORE if actor_user_id else DEFAULT_ANON_TRUST_SCORE
        )
        trust_score = self._blend_score(
            previous_score=previous_score,
            base_score=base_score,
            suspicious=len(anomaly.flags),
        )
        shadow_banned = trust_score < SHADOW_BAN_THRESHOLD
        velocity_weight = 0.0 if shadow_banned else trust_score
        if trust_score < LOW_TRUST_THRESHOLD or "abnormal_device_ip_cluster_spike" in anomaly.flags:
            velocity_weight = round(velocity_weight * 0.35, 6)
        loop_discount_factor = self._loop_discount_factor(loop_count)

        session_behavior = self._updated_session_behavior(
            current=session_behavior,
            event=event,
            fingerprint=fingerprint,
            ip_hash=ip_hash,
            suspicious=anomaly.suspicious,
            pattern_signature=pattern_signature,
            updated_at=now,
        )
        self.store.save_session_behavior(session_behavior)

        trust = ClipEventTrust(
            trust_score=round(trust_score, 4),
            weighted_event_value=0.0 if shadow_banned else round(trust_score, 6),
            velocity_weight=round(velocity_weight, 6),
            loop_discount_factor=round(loop_discount_factor, 4),
            shadow_banned=shadow_banned,
            monetization_eligible=not shadow_banned,
            ranking_eligible=not shadow_banned,
            device_fingerprint=fingerprint,
            device_fingerprint_sources=list(fingerprint_result.source_signals),
            ip_hash=ip_hash,
            pattern_signature=pattern_signature,
            suspicious_flags=list(anomaly.flags),
            factors=ClipEventTrustFactors(**factors.as_dict()),
        )

        trust_state: TrustState | None = None
        if actor_user_id is not None:
            trust_state = TrustState(
                user_id=actor_user_id,
                trust_score=round(trust_score, 4),
                suspicious_event_count=(previous_state.suspicious_event_count if previous_state is not None else 0)
                + (1 if anomaly.suspicious else 0),
                healthy_event_count=(previous_state.healthy_event_count if previous_state is not None else 0)
                + (0 if anomaly.suspicious else 1),
                shadow_banned=shadow_banned,
                monetization_eligible=not shadow_banned,
                ranking_eligible=not shadow_banned,
                suspicious_flags=tuple(anomaly.flags),
                factors=factors,
                updated_at=now,
            )
            self.store.save_trust_state(trust_state)

        return TrustEvaluation(
            state=trust_state,
            session_behavior=session_behavior,
            trust=trust,
        )

    def get_user_trust(self, *, user: User) -> TrustState:
        existing = self.store.load_trust_state(user.id)
        if existing is not None:
            return existing
        factors = TrustFactorBreakdown(
            account_age=self._account_age_factor(user.created_at),
            session_consistency=0.75,
            device_fingerprint_stability=0.75,
            engagement_authenticity=0.75,
            anomaly_detection=0.8,
        )
        baseline = TrustState(
            user_id=user.id,
            trust_score=round(self._base_score(factors), 4),
            suspicious_event_count=0,
            healthy_event_count=0,
            shadow_banned=False,
            monetization_eligible=True,
            ranking_eligible=True,
            suspicious_flags=(),
            factors=factors,
            updated_at=datetime.now(UTC),
        )
        self.store.save_trust_state(baseline)
        return baseline

    @staticmethod
    def _base_score(factors: TrustFactorBreakdown) -> float:
        return round(
            (
                (0.20 * factors.account_age)
                + (0.20 * factors.session_consistency)
                + (0.20 * factors.device_fingerprint_stability)
                + (0.20 * factors.engagement_authenticity)
                + (0.20 * factors.anomaly_detection)
            ),
            6,
        )

    @staticmethod
    def _account_age_factor(created_at: datetime | None) -> float:
        if created_at is None:
            return 0.35
        age_days = max((_resolve_timestamp(datetime.now(UTC)) - _resolve_timestamp(created_at)).total_seconds() / 86400.0, 0.0)
        if age_days < 1:
            return 0.25
        if age_days < 7:
            return 0.45
        if age_days < 30:
            return 0.65
        if age_days < 90:
            return 0.82
        return 1.0

    @staticmethod
    def _session_consistency_factor(
        *,
        session_behavior: SessionBehaviorState,
        event: ClipEvent,
        fingerprint: str,
        ip_hash: str | None,
    ) -> float:
        score = 1.0
        country = _normalized_string(event.metadata.country) or ""
        referrer = _normalized_string(event.metadata.referrer) or ""
        if session_behavior.device_fingerprints and fingerprint not in set(session_behavior.device_fingerprints):
            score -= 0.25
        if session_behavior.countries and country and country not in set(session_behavior.countries):
            score -= 0.15
        if session_behavior.referrers and referrer and referrer not in set(session_behavior.referrers):
            score -= 0.10
        if session_behavior.ip_hashes and ip_hash and ip_hash not in set(session_behavior.ip_hashes):
            score -= 0.10
        if session_behavior.event_count >= 8 and session_behavior.suspicious_event_count > session_behavior.healthy_event_count:
            score -= 0.15
        return round(max(0.05, min(score, 1.0)), 4)

    @staticmethod
    def _device_stability_factor(
        *,
        actor_user_id: str | None,
        session_behavior: SessionBehaviorState,
        fingerprint: str,
        distinct_user_devices: int,
    ) -> float:
        if actor_user_id is None:
            return 0.55 if fingerprint else 0.35
        if distinct_user_devices <= 1:
            score = 1.0
        elif distinct_user_devices == 2:
            score = 0.75
        elif distinct_user_devices == 3:
            score = 0.55
        else:
            score = 0.35
        if session_behavior.device_fingerprints and fingerprint not in set(session_behavior.device_fingerprints):
            score -= 0.10
        return round(max(0.05, min(score, 1.0)), 4)

    @staticmethod
    def _engagement_authenticity_factor(*, event: ClipEvent, loop_count: int) -> float:
        watch_ratio = _watch_ratio(event)
        if event.event_type is ClipEventType.COMPLETE:
            return 1.0
        if event.event_type is ClipEventType.SCROLL:
            if watch_ratio <= 0.03:
                return 0.05
            if watch_ratio <= 0.08:
                return 0.18
            return 0.35
        if event.event_type is ClipEventType.LOOP:
            score = 0.85 if watch_ratio >= 0.9 else 0.55
            if loop_count > 3:
                score -= 0.35
            return round(max(0.05, min(score, 1.0)), 4)
        if event.event_type is ClipEventType.WATCH_TIME:
            if watch_ratio >= 0.85:
                return 0.92
            if watch_ratio >= 0.40:
                return 0.78
            if watch_ratio >= 0.15:
                return 0.62
            return 0.40
        if event.event_type is ClipEventType.VIEW:
            if watch_ratio >= 0.50:
                return 0.84
            if watch_ratio >= 0.15:
                return 0.68
            return 0.42
        if event.event_type in {ClipEventType.SHARE, ClipEventType.COMMENT, ClipEventType.LIKE}:
            return 0.72 if watch_ratio >= 0.10 else 0.58
        return 0.60

    @staticmethod
    def _blend_score(*, previous_score: float, base_score: float, suspicious: int) -> float:
        if suspicious > 0:
            blended = min(previous_score, base_score) - (0.12 * suspicious)
        else:
            blended = (previous_score * 0.82) + (base_score * 0.18) + 0.02
        return round(max(0.0, min(blended, 1.0)), 4)

    @staticmethod
    def _loop_discount_factor(loop_count: int) -> float:
        if loop_count <= 3:
            return 1.0
        excess = loop_count - 3
        return round(max(0.0, 1.0 - (0.5 * excess)), 4)

    @staticmethod
    def _pattern_signature(event: ClipEvent) -> str:
        watch_band = "na"
        if event.watch_time_ms is not None and event.video_length_ms:
            ratio = _watch_ratio(event)
            watch_band = f"{int(ratio * 10):02d}"
        base = "|".join(
            (
                event.clip_id,
                event.event_type.value,
                watch_band,
                _normalized_string(event.metadata.device) or "device",
                _normalized_string(event.metadata.referrer) or "referrer",
            )
        )
        return sha256(base.encode("utf-8")).hexdigest()

    @staticmethod
    def _updated_session_behavior(
        *,
        current: SessionBehaviorState,
        event: ClipEvent,
        fingerprint: str,
        ip_hash: str | None,
        suspicious: bool,
        pattern_signature: str,
        updated_at: datetime,
    ) -> SessionBehaviorState:
        recent_clip_ids = list(current.recent_clip_ids)
        if event.clip_id not in recent_clip_ids:
            recent_clip_ids.append(event.clip_id)
        recent_clip_ids = recent_clip_ids[-25:]

        countries = _append_unique(current.countries, event.metadata.country)
        referrers = _append_unique(current.referrers, event.metadata.referrer)
        device_fingerprints = _append_unique(current.device_fingerprints, fingerprint, preserve_case=True)
        ip_hashes = current.ip_hashes
        if ip_hash:
            ip_hashes = _append_unique(ip_hashes, ip_hash, preserve_case=True)

        return SessionBehaviorState(
            session_id=current.session_id,
            event_count=current.event_count + 1,
            unique_clip_count=len(recent_clip_ids),
            suspicious_event_count=current.suspicious_event_count + (1 if suspicious else 0),
            healthy_event_count=current.healthy_event_count + (0 if suspicious else 1),
            total_loops=current.total_loops + (1 if event.event_type is ClipEventType.LOOP else 0),
            fast_scroll_count=current.fast_scroll_count + (
                1 if event.event_type is ClipEventType.SCROLL and _watch_ratio(event) <= 0.03 else 0
            ),
            countries=countries,
            referrers=referrers,
            device_fingerprints=device_fingerprints,
            ip_hashes=ip_hashes,
            recent_clip_ids=tuple(recent_clip_ids),
            last_pattern_signature=pattern_signature,
            updated_at=updated_at,
        )


def build_trust_score_service(*, settings: Settings | None = None) -> TrustScoreService:
    resolved_settings = settings
    if resolved_settings is None:
        try:
            resolved_settings = get_settings()
        except Exception:
            resolved_settings = None
    if resolved_settings is not None and resolved_settings.redis_url:
        store = RedisTrustStateStore(resolved_settings.redis_url)
        if store.ping():
            return TrustScoreService(store=store)
    return TrustScoreService()


def ensure_trust_score_service(app: FastAPI, *, settings: Settings | None = None) -> TrustScoreService:
    service = getattr(app.state, "trust_score_service", None)
    if service is None:
        service = build_trust_score_service(settings=settings or getattr(app.state, "settings", None))
        app.state.trust_score_service = service
    return service


def _resolve_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return _resolve_timestamp(value)
    if isinstance(value, str):
        try:
            return _resolve_timestamp(datetime.fromisoformat(value.replace("Z", "+00:00")))
        except ValueError:
            return datetime.now(UTC)
    return datetime.now(UTC)


def _coerce_float(value: object, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value: object, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalized_string(value: object | None, *, preserve_case: bool = False) -> str | None:
    if value is None:
        return None
    candidate = str(value).strip()
    if not candidate:
        return None
    return candidate if preserve_case else candidate.lower()


def _normalized_tuple(values: object, *, preserve_case: bool = False) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        return ()
    normalized: list[str] = []
    for value in values:
        item = _normalized_string(value, preserve_case=preserve_case)
        if item:
            normalized.append(item)
    return tuple(normalized)


def _append_unique(values: tuple[str, ...], item: object | None, *, preserve_case: bool = False) -> tuple[str, ...]:
    normalized = _normalized_string(item, preserve_case=preserve_case)
    if normalized is None:
        return values
    existing = list(values)
    if normalized not in existing:
        existing.append(normalized)
    return tuple(existing[-8:])


def _hash_value(value: str) -> str:
    return sha256(value.strip().lower().encode("utf-8")).hexdigest()


def _watch_ratio(event: ClipEvent) -> float:
    if event.watch_time_ms is None or event.video_length_ms is None or event.video_length_ms <= 0:
        return 0.0
    return max(0.0, min(float(event.watch_time_ms) / float(event.video_length_ms), 1.5))


__all__ = [
    "DEFAULT_ANON_TRUST_SCORE",
    "DEFAULT_USER_TRUST_SCORE",
    "LOW_TRUST_THRESHOLD",
    "SHADOW_BAN_THRESHOLD",
    "SESSION_BEHAVIOR_KEY_PATTERN",
    "SessionBehaviorState",
    "TrustEvaluation",
    "TrustFactorBreakdown",
    "TrustScoreService",
    "TrustState",
    "USER_TRUST_SCORE_KEY_PATTERN",
    "build_trust_score_service",
    "ensure_trust_score_service",
]
