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

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
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

    def tactics_for(self, side: str) -> LiveTeamTactics:
        return self.home_tactics if side == "home" else self.away_tactics


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
        )
        self.store.put(session)
        return session

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
        session = self.get(match_id)
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
        session = self.get(match_id)
        if session.phase != "half_time":
            return session
        session.halftime_ready.add(side)
        if {"home", "away"}.issubset(session.halftime_ready):
            self._resume_second_half(session)
        self.store.put(session)
        return session

    def tick(self, match_id: str) -> LiveMatchSession:
        """Advance the match by one minute (driver: a worker on an interval, or poll)."""
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


class LiveMatchStore:
    """In-process session store. Swap for a Redis/DB-backed store in production."""

    def __init__(self) -> None:
        self._sessions: dict[str, LiveMatchSession] = {}

    def get(self, match_id: str) -> LiveMatchSession | None:
        return self._sessions.get(match_id)

    def put(self, session: LiveMatchSession) -> None:
        self._sessions[session.match_id] = session


# Module-level singletons (per worker process).
_STORE = LiveMatchStore()
_ENGINE = LiveMatchEngine(_STORE)


def get_live_match_engine() -> LiveMatchEngine:
    return _ENGINE
