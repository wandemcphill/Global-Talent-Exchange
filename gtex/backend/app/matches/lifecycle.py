"""Match lifecycle state machine.

Phase B hardening: the match runtime previously mutated ``CompetitionMatch.status``
from several call sites with no notion of a legal transition. A duplicate or late
``StartMatchCommand`` could therefore reset an already-settled match back to
``queued`` — clearing its score, winner and ``completed_at`` while the competition
standings kept the points that had already been applied.

This module is the single source of truth for which transitions are legal. It is
intentionally dependency-free so it can be used from services, workers and the
orchestrator without import cycles.
"""

from __future__ import annotations

from types import MappingProxyType

from app.common.enums.match_status import MatchStatus

#: Statuses that end a match's life. Nothing may transition out of them.
TERMINAL_MATCH_STATUSES: frozenset[MatchStatus] = frozenset(
    {
        MatchStatus.COMPLETED,
        MatchStatus.CANCELLED,
        MatchStatus.ABANDONED,
    }
)

#: Statuses for which a settled result exists and may be read back.
SETTLED_MATCH_STATUSES: frozenset[MatchStatus] = frozenset({MatchStatus.COMPLETED})

#: Statuses that represent a match currently being played out.
LIVE_MATCH_STATUSES: frozenset[MatchStatus] = frozenset(
    {
        MatchStatus.IN_PROGRESS,
        MatchStatus.PAUSED,
    }
)

_TRANSITIONS: dict[MatchStatus, frozenset[MatchStatus]] = {
    MatchStatus.SCHEDULED: frozenset(
        {
            MatchStatus.QUEUED,
            MatchStatus.IN_PROGRESS,
            MatchStatus.POSTPONED,
            MatchStatus.CANCELLED,
            MatchStatus.FAILED,
            # The simulation worker produces the full 90 minutes in a single pass, so a
            # scheduled fixture can settle without first being observed as queued/live.
            MatchStatus.COMPLETED,
        }
    ),
    MatchStatus.QUEUED: frozenset(
        {
            MatchStatus.IN_PROGRESS,
            MatchStatus.POSTPONED,
            MatchStatus.CANCELLED,
            MatchStatus.FAILED,
            # A queued match may be settled directly by the simulation worker,
            # which produces the full 90 minutes in one pass.
            MatchStatus.COMPLETED,
        }
    ),
    MatchStatus.IN_PROGRESS: frozenset(
        {
            MatchStatus.PAUSED,
            MatchStatus.COMPLETED,
            MatchStatus.ABANDONED,
            MatchStatus.FAILED,
            # Operational recovery: a match left live by a crashed worker may be requeued.
            MatchStatus.QUEUED,
        }
    ),
    MatchStatus.PAUSED: frozenset(
        {
            MatchStatus.IN_PROGRESS,
            MatchStatus.COMPLETED,
            MatchStatus.ABANDONED,
            MatchStatus.FAILED,
            MatchStatus.QUEUED,
        }
    ),
    MatchStatus.POSTPONED: frozenset(
        {
            MatchStatus.SCHEDULED,
            MatchStatus.QUEUED,
            MatchStatus.CANCELLED,
        }
    ),
    # A failed simulation is recoverable: the match returns to the queue.
    MatchStatus.FAILED: frozenset(
        {
            MatchStatus.QUEUED,
            MatchStatus.SCHEDULED,
            MatchStatus.CANCELLED,
            MatchStatus.ABANDONED,
        }
    ),
    MatchStatus.COMPLETED: frozenset(),
    MatchStatus.CANCELLED: frozenset(),
    MatchStatus.ABANDONED: frozenset(),
}

MATCH_STATUS_TRANSITIONS = MappingProxyType({status: frozenset(targets) for status, targets in _TRANSITIONS.items()})


class MatchStateTransitionError(ValueError):
    """Raised when a caller attempts an illegal match lifecycle transition."""

    def __init__(self, current: MatchStatus | None, target: MatchStatus, *, match_id: str | None = None) -> None:
        self.current = current
        self.target = target
        self.match_id = match_id
        subject = f"Match {match_id}" if match_id else "Match"
        current_label = current.value if current is not None else "unknown"
        super().__init__(f"{subject} cannot transition from '{current_label}' to '{target.value}'.")


def is_terminal(status: MatchStatus | str | None) -> bool:
    resolved = MatchStatus.coerce(status)
    return resolved is not None and resolved in TERMINAL_MATCH_STATUSES


def is_settled(status: MatchStatus | str | None) -> bool:
    resolved = MatchStatus.coerce(status)
    return resolved is not None and resolved in SETTLED_MATCH_STATUSES


def is_live(status: MatchStatus | str | None) -> bool:
    resolved = MatchStatus.coerce(status)
    return resolved is not None and resolved in LIVE_MATCH_STATUSES


def can_transition(current: MatchStatus | str | None, target: MatchStatus | str) -> bool:
    """Return ``True`` when ``current -> target`` is a legal lifecycle move.

    A self-transition is always allowed so that idempotent replays of the same
    command do not trip the guard; callers remain responsible for verifying that the
    repeated command carries the same result payload.
    """
    resolved_target = MatchStatus.coerce(target)
    if resolved_target is None:
        return False
    resolved_current = MatchStatus.coerce(current)
    if resolved_current is None:
        # An unknown/unset status is treated as a fresh match so that rows written by
        # legacy paths remain drivable, but terminal states can still never be re-entered.
        return True
    if resolved_current is resolved_target:
        return True
    return resolved_target in MATCH_STATUS_TRANSITIONS.get(resolved_current, frozenset())


def assert_transition(
    current: MatchStatus | str | None,
    target: MatchStatus | str,
    *,
    match_id: str | None = None,
) -> MatchStatus:
    """Validate a transition and return the resolved target status."""
    resolved_target = MatchStatus.coerce(target)
    if resolved_target is None:
        raise MatchStateTransitionError(MatchStatus.coerce(current), MatchStatus.FAILED, match_id=match_id)
    if not can_transition(current, resolved_target):
        raise MatchStateTransitionError(MatchStatus.coerce(current), resolved_target, match_id=match_id)
    return resolved_target


__all__ = [
    "LIVE_MATCH_STATUSES",
    "MATCH_STATUS_TRANSITIONS",
    "MatchStateTransitionError",
    "SETTLED_MATCH_STATUSES",
    "TERMINAL_MATCH_STATUSES",
    "assert_transition",
    "can_transition",
    "is_live",
    "is_settled",
    "is_terminal",
]
