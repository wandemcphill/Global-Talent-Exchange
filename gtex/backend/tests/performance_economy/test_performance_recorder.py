"""The match -> performance link: ratings must survive the match that produced them."""

from __future__ import annotations

from sqlalchemy import select

from app.models.player_match_performance import PlayerMatchPerformance
from app.players.performance_recorder import (
    INELIGIBLE_NO_MINUTES,
    INELIGIBLE_SENT_OFF_EARLY,
    PlayerMatchPerformanceRecorder,
)

from .conftest import FakePlayerStat, make_match


def _records(session) -> list[PlayerMatchPerformance]:
    return list(session.scalars(select(PlayerMatchPerformance)).all())


def test_records_canonical_player_performance(session, canonical_player):
    match = make_match(session)

    result = PlayerMatchPerformanceRecorder(session).record_match(
        match=match,
        player_stats=[
            FakePlayerStat(player_id=canonical_player.id, rating=8.4, goals=2, team_id="club-home")
        ],
    )

    assert result.written == 1
    stored = _records(session)
    assert len(stored) == 1
    assert stored[0].rating == 8.4
    assert stored[0].goals == 2
    assert stored[0].competition_id == match.competition_id
    assert stored[0].club_id == "club-home"
    assert stored[0].eligible_for_valuation is True


def test_synthetic_squad_ids_are_never_recorded(session, canonical_player):
    """Simulations run without a database produce ids like ``club-home-p7``.

    Those cannot be joined to a tradable player, so letting them through would
    quietly corrupt form for a player who does not exist.
    """
    match = make_match(session)

    result = PlayerMatchPerformanceRecorder(session).record_match(
        match=match,
        player_stats=[
            FakePlayerStat(player_id="club-home-p7", rating=9.1),
            FakePlayerStat(player_id=canonical_player.id, rating=7.0),
        ],
    )

    assert result.written == 1
    assert result.skipped_non_canonical == 1
    assert [record.player_id for record in _records(session)] == [canonical_player.id]


def test_recording_is_idempotent(session, canonical_player):
    """Re-settling a fixture must not double-count a player's form."""
    match = make_match(session)
    stats = [FakePlayerStat(player_id=canonical_player.id, rating=7.7)]
    recorder = PlayerMatchPerformanceRecorder(session)

    first = recorder.record_match(match=match, player_stats=stats)
    second = recorder.record_match(match=match, player_stats=stats)

    assert first.written == 1
    assert second.written == 0
    assert second.already_recorded is True
    assert len(_records(session)) == 1


def test_cameo_appearance_is_recorded_but_not_valuation_eligible(session, canonical_player):
    match = make_match(session)

    PlayerMatchPerformanceRecorder(session).record_match(
        match=match,
        player_stats=[FakePlayerStat(player_id=canonical_player.id, rating=9.9, minutes_played=3)],
    )

    stored = _records(session)[0]
    assert stored.eligible_for_valuation is False
    assert stored.ineligibility_reason == INELIGIBLE_NO_MINUTES


def test_early_red_card_is_flagged_distinctly(session, canonical_player):
    match = make_match(session)

    PlayerMatchPerformanceRecorder(session).record_match(
        match=match,
        player_stats=[
            FakePlayerStat(player_id=canonical_player.id, rating=3.0, minutes_played=4, red_card=True)
        ],
    )

    stored = _records(session)[0]
    assert stored.eligible_for_valuation is False
    assert stored.ineligibility_reason == INELIGIBLE_SENT_OFF_EARLY


def test_unrated_players_are_skipped(session, canonical_player):
    match = make_match(session)

    result = PlayerMatchPerformanceRecorder(session).record_match(
        match=match,
        player_stats=[FakePlayerStat(player_id=canonical_player.id, rating=None)],
    )

    assert result.written == 0
    assert result.skipped_no_rating == 1
    assert _records(session) == []


def test_performance_carries_the_match_completion_time(session, canonical_player):
    """Form windows are ordered by when the football happened, not when it was written."""
    match = make_match(session)

    PlayerMatchPerformanceRecorder(session).record_match(
        match=match,
        player_stats=[FakePlayerStat(player_id=canonical_player.id, rating=7.0)],
    )

    assert _records(session)[0].occurred_at.replace(tzinfo=None) == match.completed_at.replace(tzinfo=None)
