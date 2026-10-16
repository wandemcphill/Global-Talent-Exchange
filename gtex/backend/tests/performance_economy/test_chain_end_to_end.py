"""The whole relationship, end to end.

    match -> performance -> form -> valuation signal -> market -> ownership

Each test below walks one more link of that chain, and the final tests walk all of
it, because the value of this feature is precisely that the links connect.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.players.form_service import PlayerFormService
from app.players.performance_recorder import PlayerMatchPerformanceRecorder
from app.players.read_models import PlayerSummaryReadModel
from app.portfolio.service import PortfolioService
from app.value_engine.jobs import InMemoryValueSnapshotRepository, ValueSnapshotJob
from app.value_engine.matchday_provider import MatchdayValuationSignalProvider
from app.value_engine.models import PlayerValueInput
from app.value_engine.read_models import PlayerValueSnapshotRecord

from .conftest import KICKOFF, FakePlayerStat, make_match

AS_OF = datetime(2026, 9, 2, tzinfo=timezone.utc)


def _play_matches(session, player_id: str, ratings: list[float]) -> None:
    """Play a run of competition matches, spread across competitions."""
    recorder = PlayerMatchPerformanceRecorder(session)
    for index, rating in enumerate(ratings):
        match = make_match(
            session,
            match_id=f"match-{index}",
            competition_id=f"comp-{index // 2}",
        )
        match.completed_at = KICKOFF - timedelta(days=index)
        recorder.record_match(
            match=match,
            player_stats=[FakePlayerStat(player_id=player_id, rating=rating, team_id="club-home")],
        )


def _value_input(player_id: str) -> PlayerValueInput:
    return PlayerValueInput(
        player_id=player_id,
        player_name="Canonical Footballer",
        as_of=AS_OF,
        reference_market_value_eur=70_000_000,
        current_credits=710.0,
    )


def _snapshot_for(session, player_id: str, *, with_form: bool):
    repository = InMemoryValueSnapshotRepository(inputs={player_id: _value_input(player_id)})
    provider = MatchdayValuationSignalProvider(session=session, as_of=AS_OF) if with_form else None
    return ValueSnapshotJob(matchday_signal_provider=provider).run(repository, AS_OF)[0]


def test_match_produces_persisted_performance(session, canonical_player):
    _play_matches(session, canonical_player.id, [8.5])

    performances = PlayerFormService(session).list_recent_performances(canonical_player.id)

    assert len(performances) == 1
    assert performances[0].rating == 8.5


def test_performance_produces_form(session, canonical_player):
    _play_matches(session, canonical_player.id, [8.5, 8.3, 8.7])

    window = PlayerFormService(session).build_window(canonical_player.id)

    assert window.matches_counted == 3
    assert window.average_rating == pytest.approx(8.5)


def test_form_produces_a_valuation_signal(session, canonical_player):
    _play_matches(session, canonical_player.id, [8.5, 8.3, 8.7, 8.6])

    signal = MatchdayValuationSignalProvider(session=session, as_of=AS_OF)(canonical_player.id)

    assert signal is not None
    assert signal.applied is True
    assert signal.adjustment_pct > 0


def test_a_player_who_has_never_played_carries_no_signal(session, canonical_player):
    signal = MatchdayValuationSignalProvider(session=session, as_of=AS_OF)(canonical_player.id)

    assert signal is None


def test_strong_form_raises_the_published_valuation(session, canonical_player):
    baseline = _snapshot_for(session, canonical_player.id, with_form=False)
    _play_matches(session, canonical_player.id, [8.5, 8.3, 8.7, 8.6, 8.4, 8.5])

    adjusted = _snapshot_for(session, canonical_player.id, with_form=True)

    assert adjusted.target_credits > baseline.target_credits
    assert adjusted.matchday_signal_audit["applied"] is True


def test_poor_form_lowers_the_published_valuation(session, canonical_player):
    baseline = _snapshot_for(session, canonical_player.id, with_form=False)
    _play_matches(session, canonical_player.id, [4.5, 4.3, 4.7, 4.6, 4.4, 4.5])

    adjusted = _snapshot_for(session, canonical_player.id, with_form=True)

    assert adjusted.target_credits < baseline.target_credits


def test_one_good_match_does_not_move_the_valuation(session, canonical_player):
    """A player with a single good game is not a player whose value should move."""
    baseline = _snapshot_for(session, canonical_player.id, with_form=False)
    _play_matches(session, canonical_player.id, [9.8])

    adjusted = _snapshot_for(session, canonical_player.id, with_form=True)

    assert adjusted.target_credits == baseline.target_credits
    assert adjusted.matchday_signal_audit["applied"] is False


def test_farming_one_competition_is_heavily_blunted(session, canonical_player):
    """Six perfect matches in a single competition must not pay like six elsewhere."""
    recorder = PlayerMatchPerformanceRecorder(session)
    for index in range(6):
        match = make_match(session, match_id=f"farm-{index}", competition_id="farmed-comp")
        match.completed_at = KICKOFF - timedelta(days=index)
        recorder.record_match(
            match=match,
            player_stats=[FakePlayerStat(player_id=canonical_player.id, rating=9.9)],
        )

    farmed = _snapshot_for(session, canonical_player.id, with_form=True)
    audit = farmed.matchday_signal_audit

    # Only the per-competition cap survives into the window, so the run of six
    # cannot buy six matches worth of influence.
    assert audit["matches_counted"] == 3
    assert audit["confidence"] < 1.0
    assert audit["adjustment_pct"] < 0.015


def test_valuation_change_reaches_the_owner(session, canonical_player):
    """The final link: a valuation that moved must be what a holder is priced at."""
    _play_matches(session, canonical_player.id, [8.5, 8.3, 8.7, 8.6, 8.4, 8.5])
    adjusted = _snapshot_for(session, canonical_player.id, with_form=True)

    # The projector writes the published value onto the player summary read model,
    # which is the first thing the portfolio consults when pricing a holding.
    session.add(
        PlayerSummaryReadModel(
            player_id=canonical_player.id,
            player_name=adjusted.player_name,
            last_snapshot_at=adjusted.as_of,
            current_value_credits=adjusted.target_credits,
            previous_value_credits=adjusted.previous_credits,
            movement_pct=adjusted.movement_pct,
            summary_json={},
        )
    )
    session.flush()

    price = PortfolioService()._resolve_current_price(session, canonical_player.id)

    assert price == Decimal(str(adjusted.target_credits)).quantize(Decimal("0.0001"))


def test_valuation_falls_back_to_the_snapshot_record_for_the_owner(session, canonical_player):
    """Even without a summary row, the snapshot the overlay produced prices a holding."""
    _play_matches(session, canonical_player.id, [8.5, 8.3, 8.7, 8.6, 8.4, 8.5])
    adjusted = _snapshot_for(session, canonical_player.id, with_form=True)

    session.add(
        PlayerValueSnapshotRecord(
            player_id=canonical_player.id,
            player_name=adjusted.player_name,
            as_of=adjusted.as_of,
            snapshot_type=adjusted.snapshot_type,
            previous_credits=adjusted.previous_credits,
            target_credits=adjusted.target_credits,
            movement_pct=adjusted.movement_pct,
        )
    )
    session.flush()

    price = PortfolioService()._resolve_current_price(session, canonical_player.id)

    assert price > 0
