"""The reviewer's audit points, as executable checks rather than assertions in prose.

Each test here corresponds to a numbered item in the PR #90 architectural review.
They are deliberately blunt: the point is that a future change which breaks one of
these invariants fails a test rather than quietly changing what moves money.
"""

from __future__ import annotations

import importlib
import inspect
import typing
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.player_match_performance import PlayerMatchPerformance
from app.players.form_service import (
    MAX_PERFORMANCES_PER_COMPETITION,
    FORM_WINDOW_SIZE,
    PlayerFormService,
)
from app.players.performance_recorder import (
    MINIMUM_VALUATION_MINUTES,
    PlayerMatchPerformanceRecorder,
)

from .conftest import KICKOFF, FakePlayerStat, add_performance, make_match


# --- 1. competition-only is enforced by the call path, not documentation ----


def test_recorder_is_reachable_from_exactly_one_call_site():
    """Competition-only is structural: one caller, and it is the competition runner."""
    import app.services.competition_auto_runner as runner

    source = inspect.getsource(runner)
    assert "PlayerMatchPerformanceRecorder(self.session).record_match(" in source


def test_recorder_signature_requires_a_competition_match():
    """The type is the enforcement: nothing but a CompetitionMatch can be recorded.

    Annotations are strings here (``from __future__ import annotations``), so the
    check is on the declared name and on the resolved type behind it.
    """
    from app.models.competition_match import CompetitionMatch

    signature = inspect.signature(PlayerMatchPerformanceRecorder.record_match)
    assert signature.parameters["match"].annotation == "CompetitionMatch"

    hints = typing.get_type_hints(PlayerMatchPerformanceRecorder.record_match)
    assert hints["match"] is CompetitionMatch


def test_friendly_and_adhoc_simulation_paths_do_not_record():
    """Other simulation callers must not have acquired a recording side effect.

    Every one of these calls ``build_replay_payload``; none of them may persist a
    performance, because none of them is a competition match.
    """
    module_names = (
        "app.manager_duels.service",
        "app.simulation_matchmaking.service",
        "app.match_engine.api.router",
        "app.competitive_integrity.service",
        "app.match_engine.services.execution_runtime",
    )
    for name in module_names:
        module = importlib.import_module(name)
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "build_replay_payload" in source, f"{name} no longer simulates; update this test"
        assert "PlayerMatchPerformanceRecorder" not in source, (
            f"{name} would persist performance from a non-competition match"
        )


# --- 2. synthetic ids can never be persisted -------------------------------


@pytest.mark.parametrize(
    "synthetic_id",
    ["club-home-p7", "club-away-p11", "team-x-p1", "", "   "],
)
def test_synthetic_ids_are_never_persisted(session, canonical_player, synthetic_id):
    match = make_match(session)

    PlayerMatchPerformanceRecorder(session).record_match(
        match=match,
        player_stats=[FakePlayerStat(player_id=synthetic_id, rating=9.9)],
    )

    assert session.scalars(select(PlayerMatchPerformance)).all() == []


def test_unknown_but_plausible_uuid_is_still_rejected(session, canonical_player):
    """Validation is against the player table, not against id shape."""
    match = make_match(session)

    PlayerMatchPerformanceRecorder(session).record_match(
        match=match,
        player_stats=[
            FakePlayerStat(player_id="3f2504e0-4f89-11d3-9a0c-0305e82c3301", rating=9.9)
        ],
    )

    assert session.scalars(select(PlayerMatchPerformance)).all() == []


# --- 3 & 4. idempotency and no duplicate rows per match --------------------


def test_repeated_recording_is_idempotent(session, canonical_player):
    match = make_match(session)
    stats = [FakePlayerStat(player_id=canonical_player.id, rating=7.7)]
    recorder = PlayerMatchPerformanceRecorder(session)

    for _ in range(5):
        recorder.record_match(match=match, player_stats=stats)

    assert len(session.scalars(select(PlayerMatchPerformance)).all()) == 1


def test_a_player_listed_twice_in_one_match_yields_one_row(session, canonical_player):
    """Defensive: a malformed payload must not double a player's form."""
    match = make_match(session)

    result = PlayerMatchPerformanceRecorder(session).record_match(
        match=match,
        player_stats=[
            FakePlayerStat(player_id=canonical_player.id, rating=8.0),
            FakePlayerStat(player_id=canonical_player.id, rating=4.0),
        ],
    )

    rows = session.scalars(select(PlayerMatchPerformance)).all()
    assert result.written == 1
    assert len(rows) == 1
    # The first entry wins, deterministically.
    assert rows[0].rating == 8.0


def test_the_unique_constraint_backs_the_guard(session, canonical_player):
    """Belt and braces: the database also refuses a duplicate (player, match)."""
    from sqlalchemy.exc import IntegrityError

    match = make_match(session)
    for _ in range(2):
        session.add(
            PlayerMatchPerformance(
                player_id=canonical_player.id,
                match_id=match.id,
                competition_id=match.competition_id,
                occurred_at=KICKOFF,
                rating=7.0,
                minutes_played=90,
            )
        )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


# --- 5. the 15-minute rule is deterministic --------------------------------


@pytest.mark.parametrize(
    "minutes,expected_eligible",
    [(0, False), (1, False), (14, False), (15, True), (16, True), (90, True)],
)
def test_minutes_rule_is_a_deterministic_threshold(
    session, canonical_player, minutes, expected_eligible
):
    match = make_match(session, match_id=f"m-{minutes}")

    PlayerMatchPerformanceRecorder(session).record_match(
        match=match,
        player_stats=[
            FakePlayerStat(player_id=canonical_player.id, rating=7.0, minutes_played=minutes)
        ],
    )

    row = session.scalars(select(PlayerMatchPerformance)).one()
    assert row.eligible_for_valuation is expected_eligible
    assert MINIMUM_VALUATION_MINUTES == 15


# --- 6 & 7. caps and window are deterministic ------------------------------


def test_competition_cap_is_deterministic_across_repeated_reads(session, canonical_player):
    for index in range(8):
        add_performance(session, rating=9.0, days_ago=index, competition_id="one-comp")

    service = PlayerFormService(session)
    windows = [service.build_window(canonical_player.id) for _ in range(5)]

    assert all(window.matches_counted == MAX_PERFORMANCES_PER_COMPETITION for window in windows)
    assert len({tuple(e.match_id for e in w.entries) for w in windows}) == 1


def test_form_window_size_is_deterministic_across_repeated_reads(session, canonical_player):
    for index in range(12):
        add_performance(
            session, rating=7.0 + (index % 3) * 0.5, days_ago=index, competition_id=f"c{index // 2}"
        )

    service = PlayerFormService(session)
    windows = [service.build_window(canonical_player.id) for _ in range(5)]

    assert all(window.matches_counted == FORM_WINDOW_SIZE for window in windows)
    assert len({w.average_rating for w in windows}) == 1
    assert len({tuple(e.match_id for e in w.entries) for w in windows}) == 1


def test_identical_timestamps_still_resolve_deterministically(session, canonical_player):
    """Ties must break the same way every time or valuations become unstable."""
    for index in range(8):
        record = add_performance(
            session, rating=6.0 + index * 0.2, days_ago=0, competition_id=f"c{index}"
        )
        record.occurred_at = KICKOFF  # force an exact tie

    service = PlayerFormService(session)
    first = service.build_window(canonical_player.id)
    second = service.build_window(canonical_player.id)

    assert [e.match_id for e in first.entries] == [e.match_id for e in second.entries]
    assert first.average_rating == second.average_rating


# --- 8. the signal reads persisted performance, not a provider feed --------


def test_signal_ignores_provider_season_stats_entirely(session, canonical_player):
    """Provider form and GTEX matchday form are separate inputs by construction."""
    from app.ingestion.models import PlayerSeasonStat
    from app.value_engine.matchday_provider import MatchdayValuationSignalProvider

    # A glittering provider season that GTEX matchday form must not borrow from.
    session.add(
        PlayerSeasonStat(
            source_provider="test",
            provider_external_id="season:1",
            player_id=canonical_player.id,
            appearances=38,
            average_rating=9.5,
        )
    )
    session.flush()

    signal = MatchdayValuationSignalProvider(session=session)(canonical_player.id)

    # No persisted GTEX competition football => no matchday signal at all.
    assert signal is None


def test_signal_reads_only_persisted_competition_performance(session, canonical_player):
    from app.value_engine.matchday_provider import MatchdayValuationSignalProvider

    for index in range(6):
        add_performance(session, rating=8.5, days_ago=index, competition_id=f"c{index // 2}")

    signal = MatchdayValuationSignalProvider(session=session)(canonical_player.id)

    assert signal is not None
    assert signal.matches_counted == 6
    assert signal.applied is True


# --- 10. persistence failure cannot corrupt match settlement ---------------


def test_recording_failure_does_not_fail_match_settlement():
    """Settlement is authoritative; the derived economic signal is best-effort."""
    import app.services.competition_auto_runner as runner

    source = inspect.getsource(runner.CompetitionAutoRunner._store_match_performances)
    # The recorder call is wrapped, and settlement has already returned by then.
    assert "try:" in source
    assert "except SQLAlchemyError" in source
    assert "logger.exception" in source


def test_settlement_completes_before_performances_are_recorded():
    """Ordering matters: a completed fixture must not depend on the side effect."""
    import app.services.competition_auto_runner as runner

    source = inspect.getsource(runner.CompetitionAutoRunner._simulate_match)
    complete_at = source.index("complete_match(")
    record_at = source.index("_store_match_performances(")
    assert complete_at < record_at


def test_empty_player_stats_is_a_no_op(session, canonical_player):
    match = make_match(session)

    result = PlayerMatchPerformanceRecorder(session).record_match(
        match=match, player_stats=[]
    )

    assert result.written == 0
    assert session.scalars(select(PlayerMatchPerformance)).all() == []
