"""Tests for the price/value separation in the matchday economy.

Matchday form updates ValueSnapshot (canonical player valuation).
It does NOT update:
* PlayerShareMarket.share_price_coin (tradable share price)
* Player.market_value_eur (valuation input)
* Player.current_market_reference_value (valuation reference)

Portfolio holdings for PlayerShareHolding are valued at quantity x share_price_coin,
so Portfolio holding market value remains tied to share price, independent of Matchday form.
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
from app.models.player_token_market import PlayerShareHolding, PlayerShareMarket
from app.models.user import User
from app.players.performance_recorder import PlayerMatchPerformanceRecorder
from app.portfolio.service import PortfolioService

from scripts.rebuild_value_snapshots import run_scheduled_rebuild

KICKOFF = datetime(2026, 9, 1, 15, 0, tzinfo=timezone.utc)
AS_OF = datetime(2026, 9, 2, tzinfo=timezone.utc)

SHARE_PRICE_COIN = Decimal("250.0000")
MARKET_VALUE_EUR = 25_000_000.0
REFERENCE_VALUE_EUR = 24_000_000.0

STRONG_FORM = [8.6, 8.4, 8.8, 8.5, 8.7, 8.6]
POOR_FORM = [4.4, 4.6, 4.2, 4.5, 4.3, 4.4]


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
    """Shaped like the match engine's MatchPlayerStatsView."""

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


def _seed_player_with_market(session) -> Player:
    """A tradable player with both a published valuation input and a share market."""
    player = Player(
        source_provider="manual",
        provider_external_id="price-value-separation",
        full_name="Canonical Footballer",
        is_tradable=True,
        market_value_eur=MARKET_VALUE_EUR,
        current_market_reference_value=REFERENCE_VALUE_EUR,
    )
    session.add(player)
    session.flush()
    session.add(
        PlayerShareMarket(
            player_id=player.id,
            total_shares=1000,
            circulating_shares=100,
            share_price_coin=SHARE_PRICE_COIN,
            status="active",
        )
    )
    session.commit()
    return player


def _play_competition_matches(session, player_id: str, ratings: list[float]) -> None:
    recorder = PlayerMatchPerformanceRecorder(session)
    for index, rating in enumerate(ratings):
        match = CompetitionMatch(
            id=f"sep-match-{index}",
            competition_id=f"sep-comp-{index // 2}",
            round_id=f"sep-round-{index}",
            round_number=1,
            home_club_id="club-home",
            away_club_id="club-away",
            completed_at=KICKOFF - timedelta(days=index),
        )
        session.add(match)
        session.flush()
        recorder.record_match(match=match, player_stats=[_Stat(player_id, rating)])
    session.commit()


def _load_market(session, player_id: str) -> PlayerShareMarket:
    return session.scalar(select(PlayerShareMarket).where(PlayerShareMarket.player_id == player_id))


def _run(session_factory, ratings: list[float]):
    """Seed a player, play his matches, run the real scheduled rebuild."""
    with session_factory() as session:
        player_id = _seed_player_with_market(session).id
    with session_factory() as session:
        _play_competition_matches(session, player_id, ratings)
    snapshots = run_scheduled_rebuild(session_factory, as_of=AS_OF)
    snapshot = next(item for item in snapshots if item.player_id == player_id)
    return player_id, snapshot


def test_the_run_under_test_actually_applies_a_matchday_signal(session_factory):
    _player_id, snapshot = _run(session_factory, STRONG_FORM)

    assert snapshot.matchday_signal_audit is not None
    assert snapshot.matchday_signal_audit["applied"] is True
    assert snapshot.matchday_signal_audit["adjustment_pct"] > 0


def test_matchday_does_not_move_the_tradable_share_price(session_factory):
    player_id, snapshot = _run(session_factory, STRONG_FORM)
    assert snapshot.matchday_signal_audit["applied"] is True

    with session_factory() as session:
        market = _load_market(session, player_id)
        assert Decimal(str(market.share_price_coin)) == SHARE_PRICE_COIN


def test_matchday_does_not_rewrite_the_valuation_input(session_factory):
    player_id, snapshot = _run(session_factory, STRONG_FORM)
    assert snapshot.matchday_signal_audit["applied"] is True

    with session_factory() as session:
        player = session.get(Player, player_id)
        assert player.market_value_eur == MARKET_VALUE_EUR


def test_matchday_does_not_rewrite_the_market_reference_value(session_factory):
    player_id, snapshot = _run(session_factory, STRONG_FORM)
    assert snapshot.matchday_signal_audit["applied"] is True

    with session_factory() as session:
        player = session.get(Player, player_id)
        assert player.current_market_reference_value == REFERENCE_VALUE_EUR


def test_poor_form_is_equally_forbidden_from_touching_price(session_factory):
    player_id, snapshot = _run(session_factory, POOR_FORM)

    assert snapshot.matchday_signal_audit["applied"] is True
    assert snapshot.matchday_signal_audit["adjustment_pct"] < 0

    with session_factory() as session:
        market = _load_market(session, player_id)
        player = session.get(Player, player_id)
        assert Decimal(str(market.share_price_coin)) == SHARE_PRICE_COIN
        assert player.market_value_eur == MARKET_VALUE_EUR
        assert player.current_market_reference_value == REFERENCE_VALUE_EUR


def test_the_canonical_holding_is_still_priced_at_the_untouched_share_price(session_factory):
    with session_factory() as session:
        player_id = _seed_player_with_market(session).id
        owner = AuthService().register_user(
            session,
            email="sep-owner@example.com",
            username="sep-owner",
            password="SuperSecret1",  # pragma: allowlist secret
        )
        session.commit()
        owner_id = owner.id
        session.add(
            PlayerShareHolding(
                user_id=owner_id,
                player_id=player_id,
                share_count=10,
                average_cost_coin=Decimal("200.0000"),
            )
        )
        session.commit()

    with session_factory() as session:
        _play_competition_matches(session, player_id, STRONG_FORM)

    snapshots = run_scheduled_rebuild(session_factory, as_of=AS_OF)
    snapshot = next(item for item in snapshots if item.player_id == player_id)
    assert snapshot.matchday_signal_audit["applied"] is True

    with session_factory() as session:
        portfolio = PortfolioService().build_for_user(session, session.get(User, owner_id))
        holding = next(item for item in portfolio.holdings if item.player_id == player_id)

        assert holding.quantity == Decimal("10.0000")
        assert holding.current_price == SHARE_PRICE_COIN
        assert holding.market_value == Decimal("2500.0000")
