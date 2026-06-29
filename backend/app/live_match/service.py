"""Real-time, tick-based live-match session engine (additive).

Increment 1 of the real-time rewrite. Unlike the one-shot
`match_simulation_service` (which pre-computes the whole match), this advances a
match ONE MINUTE AT A TIME and re-reads each team's CURRENT tactics every tick —
so a tactical/formation change made mid-match genuinely affects the rest of play
for that team only, without pausing the match. Halftime pauses with a countdown;
both managers pressing Done resumes early.

NOTE: session state is in-process (per-worker). Production with multiple workers
must back this with Redis/DB (the broadcast layer already uses Redis) — a wiring
follow-up. The engine logic here is store-agnostic.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from math import ceil
from random import Random
from typing import Any

HALFTIME_SECONDS = 60
FULL_TIME_MINUTE = 90
HALFTIME_MINUTE = 45

_MENTALITY_ATTACK = {"attacking": 1.25, "balanced": 1.0, "defensive": 0.78}
_MENTALITY_CONCEDE = {"attacking": 1.22, "balanced": 1.0, "defensive": 0.82}


class LiveMatchError(ValueError):
    """Raised on invalid live-match operations."""


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class LiveTeamTactics:
    formation: str = "4-3-3"
    mentality: str = "balanced"
    pressing: int = 50
    tempo: int = 50

    def attack_multiplier(self) -> float:
        base = _MENTALITY_ATTACK.get(self.mentality, 1.0)
        return base * (0.9 + (self.tempo / 250.0))

    def concede_multiplier(self) -> float:
        base = _MENTALITY_CONCEDE.get(self.mentality, 1.0)
        return base * (0.92 + (self.pressing / 400.0))


@dataclass
class LiveMatchSession:
    match_id: str
    home_id: str
    away_id: str
    home_name: str
    away_name: str
    home_overall: int
    away_overall: int
    rng_seed: int
    home_tactics: LiveTeamTactics = field(default_factory=LiveTeamTactics)
    away_tactics: LiveTeamTactics = field(default_factory=LiveTeamTactics)
    minute: int = 0
    phase: str = "pre_match"  # pre_match | first_half | half_time | second_half | full_time
    home_score: int = 0
    away_score: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)
    halftime_ready: set[str] = field(default_factory=set)
    halftime_deadline: datetime | None = None
    # Controlling users — only the owner of a side may change its tactics / mark ready.
    home_user_id: str | None = None
    away_user_id: str | None = None

    def tactics_for(self, side: str) -> LiveTeamTactics:
        return self.home_tactics if side == "home" else self.away_tactics

    def side_for_user(self, user_id: str | None) -> str | None:
        if user_id is None:
            return None
        if self.home_user_id is not None and user_id == self.home_user_id:
            return "home"
        if self.away_user_id is not None and user_id == self.away_user_id:
            return "away"
        return None


class LiveMatchEngine:
    """Pure logic over a session; no I/O. The store/transport layer drives it."""

    def __init__(self, store: "LiveMatchStore") -> None:
        self.store = store

    def create(
        self,
        *,
        match_id: str,
        home_id: str,
        away_id: str,
        home_name: str,
        away_name: str,
        home_overall: int,
        away_overall: int,
        home_formation: str = "4-3-3",
        away_formation: str = "4-3-3",
        home_user_id: str | None = None,
        away_user_id: str | None = None,
    ) -> LiveMatchSession:
        seed = abs(hash((match_id, home_id, away_id))) % (2**31)
        session = LiveMatchSession(
            match_id=match_id,
            home_id=home_id,
            away_id=away_id,
            home_name=home_name,
            away_name=away_name,
            home_overall=max(1, min(99, home_overall)),
            away_overall=max(1, min(99, away_overall)),
            rng_seed=seed,
            home_tactics=LiveTeamTactics(formation=home_formation),
            away_tactics=LiveTeamTactics(formation=away_formation),
            home_user_id=home_user_id,
            away_user_id=away_user_id,
        )
        self.store.put(session)
        self.store.mark_active(match_id)
        return session

    def resolve_owned_side(self, *, match_id: str, user_id: str | None, side: str | None = None) -> str:
        """Map a user to the side they control, enforcing ownership when owners are set.

        If the session has no owners recorded (e.g. local/dev sessions created
        without users), fall back to the explicit `side` argument.
        """
        session = self.get(match_id)
        if session.home_user_id is None and session.away_user_id is None:
            if side not in {"home", "away"}:
                raise LiveMatchError("side must be 'home' or 'away'.")
            return side
        owned = session.side_for_user(user_id)
        if owned is None:
            raise LiveMatchError("You do not control a team in this match.")
        if side is not None and side != owned:
            raise LiveMatchError("You can only change tactics for your own team.")
        return owned

    def get(self, match_id: str) -> LiveMatchSession:
        session = self.store.get(match_id)
        if session is None:
            raise LiveMatchError("Live match session not found.")
        return session

    def set_tactics(
        self,
        *,
        match_id: str,
        side: str,
        formation: str | None = None,
        mentality: str | None = None,
        pressing: int | None = None,
        tempo: int | None = None,
    ) -> LiveMatchSession:
        if side not in {"home", "away"}:
            raise LiveMatchError("side must be 'home' or 'away'.")
        with self.store.lock(match_id):
            session = self.get(match_id)
            return self._apply_tactics(
                session,
                side=side,
                formation=formation,
                mentality=mentality,
                pressing=pressing,
                tempo=tempo,
            )

    def _apply_tactics(
        self,
        session: LiveMatchSession,
        *,
        side: str,
        formation: str | None,
        mentality: str | None,
        pressing: int | None,
        tempo: int | None,
    ) -> LiveMatchSession:
        tactics = session.tactics_for(side)
        if formation is not None:
            tactics.formation = formation
        if mentality is not None:
            if mentality not in _MENTALITY_ATTACK:
                raise LiveMatchError("Unknown mentality.")
            tactics.mentality = mentality
        if pressing is not None:
            tactics.pressing = max(0, min(100, pressing))
        if tempo is not None:
            tactics.tempo = max(0, min(100, tempo))
        # Recorded as an event so the OTHER user's stream is never interrupted —
        # the change just shapes subsequent ticks for this side.
        session.events.append(
            {
                "minute": session.minute,
                "type": "tactical_change",
                "side": side,
                "formation": tactics.formation,
                "mentality": tactics.mentality,
            }
        )
        self.store.put(session)
        return session

    def mark_halftime_ready(self, *, match_id: str, side: str) -> LiveMatchSession:
        if side not in {"home", "away"}:
            raise LiveMatchError("side must be 'home' or 'away'.")
        with self.store.lock(match_id):
            session = self.get(match_id)
            if session.phase != "half_time":
                return session
            session.halftime_ready.add(side)
            if {"home", "away"}.issubset(session.halftime_ready):
                self._resume_second_half(session)
            self.store.put(session)
            return session

    def tick(self, match_id: str) -> LiveMatchSession:
        """Advance the match by one minute (driver: the server ticker, or a poll)."""
        with self.store.lock(match_id):
            session = self.get(match_id)
            if session.phase == "full_time":
                return session
            if session.phase == "pre_match":
                session.phase = "first_half"
            if session.phase == "half_time":
                # Auto-resume when the countdown elapses; otherwise wait.
                if session.halftime_deadline is not None and _utcnow() >= session.halftime_deadline:
                    self._resume_second_half(session)
                self.store.put(session)
                return session

            session.minute += 1
            self._simulate_minute(session)

            if session.minute >= HALFTIME_MINUTE and session.phase == "first_half":
                session.phase = "half_time"
                session.halftime_ready.clear()
                session.halftime_deadline = _utcnow() + timedelta(seconds=HALFTIME_SECONDS)
                session.events.append({"minute": session.minute, "type": "half_time"})
            elif session.minute >= FULL_TIME_MINUTE:
                session.phase = "full_time"
                session.events.append({"minute": session.minute, "type": "full_time"})

            self.store.put(session)
            if session.phase == "full_time":
                self.store.mark_finished(match_id)
            return session

    # ---- internals --------------------------------------------------------

    def _resume_second_half(self, session: LiveMatchSession) -> None:
        session.phase = "second_half"
        session.halftime_deadline = None
        if session.minute < HALFTIME_MINUTE + 1:
            session.minute = HALFTIME_MINUTE + 1
        session.events.append({"minute": session.minute, "type": "second_half"})

    def _simulate_minute(self, session: LiveMatchSession) -> None:
        rng = Random(session.rng_seed + session.minute)
        self._maybe_goal(session, "home", session.home_tactics, session.away_tactics, rng)
        self._maybe_goal(session, "away", session.away_tactics, session.home_tactics, rng)

    def _maybe_goal(
        self,
        session: LiveMatchSession,
        side: str,
        attacker: LiveTeamTactics,
        defender: LiveTeamTactics,
        rng: Random,
    ) -> None:
        atk = session.home_overall if side == "home" else session.away_overall
        dfn = session.away_overall if side == "home" else session.home_overall
        # Base ~ per-minute goal probability scaled by strength + live tactics.
        edge = (atk - dfn) / 200.0
        prob = 0.012 * (1.0 + edge)
        prob *= attacker.attack_multiplier() * defender.concede_multiplier()
        prob = max(0.001, min(0.08, prob))
        if rng.random() < prob:
            if side == "home":
                session.home_score += 1
            else:
                session.away_score += 1
            team_name = session.home_name if side == "home" else session.away_name
            session.events.append(
                {
                    "minute": session.minute,
                    "type": "goal",
                    "side": side,
                    "team": team_name,
                    "score": f"{session.home_score}-{session.away_score}",
                }
            )


def session_public_state(session: LiveMatchSession) -> dict[str, Any]:
    """Json-safe read-model used by both the REST view and the ticker broadcast."""
    remaining: int | None = None
    if session.phase == "half_time" and session.halftime_deadline is not None:
        delta = (session.halftime_deadline - _utcnow()).total_seconds()
        remaining = max(0, ceil(delta))
    return {
        "match_id": session.match_id,
        "minute": session.minute,
        "phase": session.phase,
        "home_name": session.home_name,
        "away_name": session.away_name,
        "home_score": session.home_score,
        "away_score": session.away_score,
        "home_tactics": _tactics_state(session.home_tactics),
        "away_tactics": _tactics_state(session.away_tactics),
        "halftime_seconds_remaining": remaining,
        "halftime_ready": sorted(session.halftime_ready),
        "events": list(session.events[-40:]),
    }


def _tactics_state(tactics: LiveTeamTactics) -> dict[str, Any]:
    return {
        "formation": tactics.formation,
        "mentality": tactics.mentality,
        "pressing": tactics.pressing,
        "tempo": tactics.tempo,
    }


class LiveMatchStore:
    """In-process session store. Swap for a Redis/DB-backed store in production.

    The store also owns the *active session registry* (which matches the server
    ticker should advance) and a per-match lock so concurrent tick/tactics
    mutations don't clobber each other. The in-process variant runs single-worker,
    so the lock is a no-op and the registry is a plain set.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, LiveMatchSession] = {}
        self._active: set[str] = set()

    def get(self, match_id: str) -> LiveMatchSession | None:
        return self._sessions.get(match_id)

    def put(self, session: LiveMatchSession) -> None:
        self._sessions[session.match_id] = session

    def mark_active(self, match_id: str) -> None:
        self._active.add(match_id)

    def mark_finished(self, match_id: str) -> None:
        self._active.discard(match_id)

    def active_ids(self) -> list[str]:
        return list(self._active)

    @contextlib.contextmanager
    def lock(self, match_id: str) -> Iterator[None]:
        yield


# Lazily-built per-process singleton, picked from settings (Redis vs in-process).
_ENGINE: LiveMatchEngine | None = None


def build_live_match_store() -> LiveMatchStore:
    """Pick a Redis-backed shared store when configured, else in-process."""
    try:
        from app.core.config import get_settings

        settings = get_settings()
        redis_url = settings.redis_url if settings.redis_enabled else None
    except Exception:  # pragma: no cover - settings unavailable (standalone use)
        redis_url = None
    if redis_url:
        try:
            from app.live_match.store import RedisLiveMatchStore

            return RedisLiveMatchStore(redis_url)
        except Exception:  # pragma: no cover - redis import/connect failure
            pass
    return LiveMatchStore()


def get_live_match_engine() -> LiveMatchEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = LiveMatchEngine(build_live_match_store())
    return _ENGINE
