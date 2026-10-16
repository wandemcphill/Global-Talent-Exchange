"""Regression tests for the match lifecycle state machine (Phase B).

Before this guard existed, a duplicate or late ``StartMatchCommand`` reset an already
settled match back to ``queued`` — clearing its score, winner and ``completed_at``
while the competition standings kept the points that had already been applied.
"""

from __future__ import annotations

import pytest

from app.common.enums.match_status import MatchStatus
from app.matches.lifecycle import (
    MATCH_STATUS_TRANSITIONS,
    MatchStateTransitionError,
    assert_transition,
    can_transition,
    is_live,
    is_settled,
    is_terminal,
)


@pytest.mark.parametrize(
    "terminal",
    [MatchStatus.COMPLETED, MatchStatus.CANCELLED, MatchStatus.ABANDONED],
)
def test_terminal_statuses_have_no_outgoing_transitions(terminal: MatchStatus) -> None:
    assert is_terminal(terminal)
    assert MATCH_STATUS_TRANSITIONS[terminal] == frozenset()
    for target in MatchStatus:
        if target is terminal:
            continue
        assert not can_transition(terminal, target), f"{terminal} -> {target} must be illegal"


def test_completed_match_cannot_be_requeued() -> None:
    with pytest.raises(MatchStateTransitionError) as excinfo:
        assert_transition(MatchStatus.COMPLETED, MatchStatus.QUEUED, match_id="match-1")
    assert "match-1" in str(excinfo.value)
    assert excinfo.value.current is MatchStatus.COMPLETED
    assert excinfo.value.target is MatchStatus.QUEUED


def test_abandoned_match_cannot_be_completed() -> None:
    with pytest.raises(MatchStateTransitionError):
        assert_transition(MatchStatus.ABANDONED, MatchStatus.COMPLETED)


def test_cancelled_match_cannot_be_completed() -> None:
    with pytest.raises(MatchStateTransitionError):
        assert_transition(MatchStatus.CANCELLED, MatchStatus.COMPLETED)


def test_a_scheduled_fixture_can_be_settled_in_one_simulation_pass() -> None:
    assert can_transition(MatchStatus.SCHEDULED, MatchStatus.COMPLETED)
    assert can_transition(MatchStatus.QUEUED, MatchStatus.COMPLETED)
    # A postponed fixture must be re-scheduled before it can produce a result.
    assert not can_transition(MatchStatus.POSTPONED, MatchStatus.COMPLETED)


def test_happy_path_transitions_are_legal() -> None:
    assert can_transition(MatchStatus.SCHEDULED, MatchStatus.QUEUED)
    assert can_transition(MatchStatus.QUEUED, MatchStatus.IN_PROGRESS)
    assert can_transition(MatchStatus.IN_PROGRESS, MatchStatus.PAUSED)
    assert can_transition(MatchStatus.PAUSED, MatchStatus.IN_PROGRESS)
    assert can_transition(MatchStatus.IN_PROGRESS, MatchStatus.COMPLETED)
    # The simulation worker settles a queued fixture in a single pass.
    assert can_transition(MatchStatus.QUEUED, MatchStatus.COMPLETED)


def test_failed_simulation_is_recoverable_but_abandonment_is_not() -> None:
    assert can_transition(MatchStatus.IN_PROGRESS, MatchStatus.FAILED)
    assert can_transition(MatchStatus.FAILED, MatchStatus.QUEUED)
    assert not can_transition(MatchStatus.ABANDONED, MatchStatus.QUEUED)


def test_self_transition_is_idempotent() -> None:
    for status in MatchStatus:
        assert can_transition(status, status)


def test_unknown_persisted_status_degrades_instead_of_raising() -> None:
    assert MatchStatus.coerce("not_a_status") is None
    assert MatchStatus.coerce(None) is None
    assert MatchStatus.coerce("  COMPLETED ") is MatchStatus.COMPLETED
    assert MatchStatus.coerce(MatchStatus.QUEUED) is MatchStatus.QUEUED
    # A row written by a legacy path stays drivable rather than crashing the runtime.
    assert can_transition("not_a_status", MatchStatus.QUEUED)


def test_status_classification_helpers() -> None:
    assert is_settled(MatchStatus.COMPLETED)
    assert not is_settled(MatchStatus.ABANDONED)
    assert is_live(MatchStatus.IN_PROGRESS)
    assert is_live(MatchStatus.PAUSED)
    assert not is_live(MatchStatus.QUEUED)


def test_every_status_is_covered_by_the_transition_table() -> None:
    assert set(MATCH_STATUS_TRANSITIONS) == set(MatchStatus)
