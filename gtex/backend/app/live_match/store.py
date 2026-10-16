"""Redis-backed shared store for live-match sessions (Increment 2).

The in-process `LiveMatchStore` (in `service.py`) only works single-worker: each
process has its own dict, so two web workers can't see the same match. This
backs the same interface with Redis so every worker — and the standalone ticker
— reads/writes one shared session, with a short-lived per-match lock to keep
concurrent tick/tactics mutations from clobbering each other.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from datetime import datetime, timezone
import json
import time
from typing import Any
from uuid import uuid4

from redis import Redis
from redis.exceptions import RedisError

from app.live_match.service import LiveMatchSession, LiveTeamTactics

_SESSION_PREFIX = "live-match:session:"
_ACTIVE_KEY = "live-match:active"
_LOCK_PREFIX = "live-match:lock:"
_SESSION_TTL_SECONDS = 6 * 60 * 60  # matches finish well within 6h; auto-reap stragglers
_LOCK_TTL_MS = 5_000
_LOCK_WAIT_SECONDS = 5.0


def session_to_dict(session: LiveMatchSession) -> dict[str, Any]:
    return {
        "match_id": session.match_id,
        "home_id": session.home_id,
        "away_id": session.away_id,
        "home_name": session.home_name,
        "away_name": session.away_name,
        "home_overall": session.home_overall,
        "away_overall": session.away_overall,
        "rng_seed": session.rng_seed,
        "home_tactics": _tactics_to_dict(session.home_tactics),
        "away_tactics": _tactics_to_dict(session.away_tactics),
        "minute": session.minute,
        "phase": session.phase,
        "home_score": session.home_score,
        "away_score": session.away_score,
        "events": session.events,
        "halftime_ready": sorted(session.halftime_ready),
        "halftime_deadline": (
            session.halftime_deadline.isoformat() if session.halftime_deadline is not None else None
        ),
        "home_user_id": session.home_user_id,
        "away_user_id": session.away_user_id,
    }


def session_from_dict(data: dict[str, Any]) -> LiveMatchSession:
    deadline_raw = data.get("halftime_deadline")
    deadline = None
    if deadline_raw:
        deadline = datetime.fromisoformat(deadline_raw)
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
    return LiveMatchSession(
        match_id=data["match_id"],
        home_id=data["home_id"],
        away_id=data["away_id"],
        home_name=data["home_name"],
        away_name=data["away_name"],
        home_overall=int(data["home_overall"]),
        away_overall=int(data["away_overall"]),
        rng_seed=int(data["rng_seed"]),
        home_tactics=_tactics_from_dict(data.get("home_tactics", {})),
        away_tactics=_tactics_from_dict(data.get("away_tactics", {})),
        minute=int(data.get("minute", 0)),
        phase=data.get("phase", "pre_match"),
        home_score=int(data.get("home_score", 0)),
        away_score=int(data.get("away_score", 0)),
        events=list(data.get("events", [])),
        halftime_ready=set(data.get("halftime_ready", [])),
        halftime_deadline=deadline,
        home_user_id=data.get("home_user_id"),
        away_user_id=data.get("away_user_id"),
    )


def _tactics_to_dict(tactics: LiveTeamTactics) -> dict[str, Any]:
    return {
        "formation": tactics.formation,
        "mentality": tactics.mentality,
        "pressing": tactics.pressing,
        "tempo": tactics.tempo,
    }


def _tactics_from_dict(data: dict[str, Any]) -> LiveTeamTactics:
    return LiveTeamTactics(
        formation=data.get("formation", "4-3-3"),
        mentality=data.get("mentality", "balanced"),
        pressing=int(data.get("pressing", 50)),
        tempo=int(data.get("tempo", 50)),
    )


class RedisLiveMatchStore:
    """Shared session store + active registry + per-match lock, backed by Redis."""

    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self.client: Redis = Redis.from_url(redis_url, decode_responses=True)

    def get(self, match_id: str) -> LiveMatchSession | None:
        raw = self.client.get(_SESSION_PREFIX + match_id)
        if not raw:
            return None
        try:
            return session_from_dict(json.loads(raw))
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def put(self, session: LiveMatchSession) -> None:
        self.client.set(
            _SESSION_PREFIX + session.match_id,
            json.dumps(session_to_dict(session)),
            ex=_SESSION_TTL_SECONDS,
        )

    def mark_active(self, match_id: str) -> None:
        self.client.sadd(_ACTIVE_KEY, match_id)

    def mark_finished(self, match_id: str) -> None:
        self.client.srem(_ACTIVE_KEY, match_id)

    def active_ids(self) -> list[str]:
        try:
            return list(self.client.smembers(_ACTIVE_KEY))
        except RedisError:
            return []

    @contextlib.contextmanager
    def lock(self, match_id: str) -> Iterator[None]:
        key = _LOCK_PREFIX + match_id
        token = uuid4().hex
        deadline = time.monotonic() + _LOCK_WAIT_SECONDS
        acquired = False
        while time.monotonic() < deadline:
            if self.client.set(key, token, nx=True, px=_LOCK_TTL_MS):
                acquired = True
                break
            time.sleep(0.05)
        try:
            yield
        finally:
            if acquired:
                # Best-effort release; only delete if we still own the lock.
                try:
                    if self.client.get(key) == token:
                        self.client.delete(key)
                except RedisError:
                    pass
