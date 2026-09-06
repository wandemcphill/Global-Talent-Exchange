"""A holder is told when football moved a player he owns -- and only then.

A notification is a claim made unprompted, so this producer is tested for what it
refuses to say as much as for what it says:

* it fires only when the matchday overlay was actually applied, never on a
  valuation that moved for some other reason;
* it reports the overlay's own contribution, not the total valuation movement,
  because attributing the whole move to football would be causal overreach;
* it never states or implies a share price change, because matchday cannot cause
  one;
* it reaches holders only -- owning nothing means hearing nothing;
* and a re-run of the idempotent cron does not notify the same holder twice.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.ingestion.models  # noqa: F401
import app.ledger.models  # noqa: F401
import app.models  # noqa: F401
import app.orders.models  # noqa: F401
import app.players.read_models  # noqa: F401
import app.value_engine.read_models  # noqa: F401
from app.auth.service import AuthService
from app.ingestion.models import Player
from app.models.base import Base
from app.models.competition_match import CompetitionMatch
from app.models.notification_record import NotificationRecord
from app.models.player_token_market import PlayerShareHolding, PlayerShareMarket
from app.players.performance_recorder import PlayerMatchPerformanceRecorder
from app.value_engine.matchday_notifications import (
    TOPIC,
    MatchdayValueNotificationProducer,
)

from scripts.rebuild_value_snapshots import notify_holders, run_scheduled_rebuild

KICKOFF = datetime(2026, 9, 1, 15, 0, tzinfo=timezone.utc)
AS_OF = datetime(2026, 9, 2, tzinfo=timezone.utc)

STRONG_FORM = [8.6, 8.4, 8.8, 8.5, 8.7, 8.6]
POOR_FORM = [4.4, 4.6, 4.2, 4.5, 4.3, 4.4]
BASELINE_FORM = [6.5, 6.5, 6.5, 6.5, 6.5, 6.5]


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class _Stat:
    def __init__(self, player_id: str, rating: float) -> None:
        self.player_id = player_id
        self.player_name = "Canonical Footballer"
        self.team_id = "club-home"
        self.rating = rating
        self.minutes_played = 90
        self.goals = 1
        self.assists = 0
        self.saves = 0
        self.shots_on_target = 2
        self.key_passes = 1
        self.tackles_won = 0
        self.interceptions = 0
        self.yellow_cards = 0
        self.red_card = False
        self.started = True
        self.xg = 0.4


def _seed_player(session) -> Player:
    player = Player(
        source_provider="manual",
        provider_external_id="matchday-notifications",
        full_name="Canonical Footballer",
        is_tradable=True,
        market_value_eur=25_000_000.0,
    )
    session.add(player)
    session.flush()
    session.add(
        PlayerShareMarket(
            player_id=player.id,
            total_shares=1000,
            circulating_shares=100,
            share_price_coin=Decimal("250.0000"),
            status="active",
        )
    )
    session.commit()
    return player


def _play(session, player_id: str, ratings: list[float]) -> None:
    recorder = PlayerMatchPerformanceRecorder(session)
    for index, rating in enumerate(ratings):
        match = CompetitionMatch(
            id=f"notif-match-{index}",
            competition_id=f"notif-comp-{index // 2}",
            round_id=f"notif-round-{index}",
            round_number=1,
            home_club_id="club-home",
            away_club_id="club-away",
            completed_at=KICKOFF - timedelta(days=index),
        )
        session.add(match)
        session.flush()
        recorder.record_match(match=match, player_stats=[_Stat(player_id, rating)])
    session.commit()


def _register(session, *, email: str, username: str) -> str:
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password="SuperSecret1",
    )
    session.commit()
    return user.id


def _hold(session, *, user_id: str, player_id: str, shares: int = 10) -> None:
    session.add(
        PlayerShareHolding(
            user_id=user_id,
            player_id=player_id,
            share_count=shares,
            average_cost_coin=Decimal("200.0000"),
        )
    )
    session.commit()


def _setup(session_factory, ratings: list[float], *, with_holder: bool = True):
    """Seed a player, optionally give him a holder, play his matches, run the cron."""
    with session_factory() as session:
        player_id = _seed_player(session).id
        user_id = None
        if with_holder:
            user_id = _register(session, email="holder@example.com", username="holder")
            _hold(session, user_id=user_id, player_id=player_id)
    with session_factory() as session:
        _play(session, player_id, ratings)
    snapshots = run_scheduled_rebuild(session_factory, as_of=AS_OF)
    return player_id, user_id, snapshots


def _notifications(session_factory) -> list[NotificationRecord]:
    with session_factory() as session:
        return list(session.scalars(select(NotificationRecord).where(NotificationRecord.topic == TOPIC)).all())


def test_a_holder_is_told_when_form_raised_his_players_valuation(session_factory):
    player_id, user_id, snapshots = _setup(session_factory, STRONG_FORM)
    written = notify_holders(session_factory, snapshots)

    assert written == 1
    records = _notifications(session_factory)
    assert len(records) == 1
    record = records[0]
    assert record.user_id == user_id
    assert record.resource_id == player_id
    assert "raised" in record.message
    assert "valuation" in record.message


def test_a_holder_is_told_when_form_lowered_it_too(session_factory):
    """Bad news is news. A producer that only reports gains is a marketing tool."""
    _player_id, _user_id, snapshots = _setup(session_factory, POOR_FORM)
    notify_holders(session_factory, snapshots)

    records = _notifications(session_factory)
    assert len(records) == 1
    assert "lowered" in records[0].message


def test_the_message_never_claims_the_share_price_moved(session_factory):
    _player_id, _user_id, snapshots = _setup(session_factory, STRONG_FORM)
    notify_holders(session_factory, snapshots)

    record = _notifications(session_factory)[0]
    assert "not a share price change" in record.message
    assert record.metadata_json["moves_share_price"] is False


def test_the_reported_figure_is_matchdays_contribution_not_the_whole_movement(
    session_factory,
):
    """The audit is the only thing entitled to attribute a movement to football."""
    _player_id, _user_id, snapshots = _setup(session_factory, STRONG_FORM)
    notify_holders(session_factory, snapshots)

    snapshot = snapshots[0]
    record = _notifications(session_factory)[0]
    audit = snapshot.matchday_signal_audit
    expected = audit.get("applied_adjustment_pct", audit.get("adjustment_pct"))

    assert record.metadata_json["matchday_adjustment_pct"] == pytest.approx(round(expected, 6))
    # And the total movement is carried separately rather than being conflated
    # with it, so a client can show both without inventing either.
    assert record.metadata_json["target_credits"] == snapshot.target_credits
    assert record.metadata_json["previous_credits"] == snapshot.previous_credits


def test_baseline_form_moves_nothing_and_so_says_nothing(session_factory):
    """A player performing exactly at baseline is not news."""
    _player_id, _user_id, snapshots = _setup(session_factory, BASELINE_FORM)
    written = notify_holders(session_factory, snapshots)

    assert written == 0
    assert _notifications(session_factory) == []


def test_a_player_nobody_owns_generates_no_notifications(session_factory):
    _player_id, _user_id, snapshots = _setup(session_factory, STRONG_FORM, with_holder=False)
    written = notify_holders(session_factory, snapshots)

    assert written == 0
    assert _notifications(session_factory) == []


def test_a_non_holder_is_not_told(session_factory):
    """Owning nothing means hearing nothing, even while signed up."""
    player_id, _holder_id, snapshots = _setup(session_factory, STRONG_FORM)
    with session_factory() as session:
        bystander_id = _register(session, email="bystander@example.com", username="bystander")
    notify_holders(session_factory, snapshots)

    records = _notifications(session_factory)
    assert [record.user_id for record in records] != [bystander_id]
    assert all(record.resource_id == player_id for record in records)


def test_a_sold_out_position_is_not_notified(session_factory):
    """A zeroed holding is not a holding."""
    with session_factory() as session:
        player_id = _seed_player(session).id
        user_id = _register(session, email="seller@example.com", username="seller")
        _hold(session, user_id=user_id, player_id=player_id, shares=0)
    with session_factory() as session:
        _play(session, player_id, STRONG_FORM)
    snapshots = run_scheduled_rebuild(session_factory, as_of=AS_OF)

    assert notify_holders(session_factory, snapshots) == 0


def test_rerunning_the_cron_does_not_notify_the_same_holder_twice(session_factory):
    """The snapshot job is idempotent; its notifications must be too."""
    _player_id, _user_id, snapshots = _setup(session_factory, STRONG_FORM)

    assert notify_holders(session_factory, snapshots) == 1
    assert notify_holders(session_factory, snapshots) == 0
    assert len(_notifications(session_factory)) == 1


def test_a_later_snapshot_instant_is_a_new_event(session_factory):
    """Dedupe is per as_of, not forever: tomorrow's move is tomorrow's news."""
    _player_id, _user_id, snapshots = _setup(session_factory, STRONG_FORM)
    assert notify_holders(session_factory, snapshots) == 1

    later = run_scheduled_rebuild(session_factory, as_of=AS_OF + timedelta(days=1))
    assert notify_holders(session_factory, later) == 1
    assert len(_notifications(session_factory)) == 2


def test_a_movement_below_the_threshold_is_not_worth_interrupting_anyone(
    session_factory,
):
    player_id, user_id, snapshots = _setup(session_factory, STRONG_FORM)
    del player_id, user_id

    with session_factory() as session:
        # A threshold above the overlay's own hard bound can never be cleared.
        producer = MatchdayValueNotificationProducer(session, minimum_adjustment_pct=0.99)
        assert producer.publish(snapshots) == 0
        session.commit()

    assert _notifications(session_factory) == []


def test_holders_are_resolved_in_one_read_not_one_per_player(session_factory):
    """Guards the production shape: this runs over every player, every night."""
    with session_factory() as session:
        players = [_seed_player_named(session, index) for index in range(3)]
        user_id = _register(session, email="multi@example.com", username="multi")
        for player in players:
            _hold(session, user_id=user_id, player_id=player.id)
        player_ids = [player.id for player in players]

    with session_factory() as session:
        producer = MatchdayValueNotificationProducer(session)
        statements: list[str] = []
        original = session.execute

        def _record(statement, *args, **kwargs):
            statements.append(str(statement))
            return original(statement, *args, **kwargs)

        session.execute = _record  # type: ignore[method-assign]
        holders = producer._holders(player_ids)
        session.execute = original  # type: ignore[method-assign]

    assert set(holders) == set(player_ids)
    assert len(statements) == 1


def _seed_player_named(session, index: int) -> Player:
    player = Player(
        source_provider="manual",
        provider_external_id=f"matchday-notifications-{index}",
        full_name=f"Footballer {index}",
        is_tradable=True,
        market_value_eur=25_000_000.0,
    )
    session.add(player)
    session.commit()
    return player
