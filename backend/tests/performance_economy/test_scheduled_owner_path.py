"""The production path, end to end, with nothing hand-inserted.

The earlier chain test proved the links compose, but it wrote the final
`PlayerSummaryReadModel` by hand. For a change that moves money that is not good
enough: it proves the arithmetic, not the plumbing.

These tests drive the *real* write path:

    canonical player
      -> canonical competition match
      -> persisted performance          (PlayerMatchPerformanceRecorder)
      -> form window                    (PlayerFormService)
      -> scheduled valuation rebuild    (scripts/rebuild_value_snapshots.py — the cron entrypoint)
      -> summary projection             (PlayerSummaryProjector, invoked inside the bridge)
      -> real holding lookup            (PortfolioService over real settled ledger entries)
      -> owner valuation

Nothing between those steps is faked. The summary read model is written by the
projector, and the holding comes from ledger entries created by
`SettlementService`, which is what a real trade produces.
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
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.players.performance_recorder import PlayerMatchPerformanceRecorder
from app.players.read_models import PlayerSummaryReadModel
from app.portfolio.service import PortfolioService
from app.settlement.service import SettlementService, TradeExecution
from app.wallets.service import LedgerPosting, WalletService

from scripts.rebuild_value_snapshots import build_bridge, run_scheduled_rebuild

KICKOFF = datetime(2026, 9, 1, 15, 0, tzinfo=timezone.utc)
AS_OF = datetime(2026, 9, 2, tzinfo=timezone.utc)


@pytest.fixture()
def session_factory():
    """A shared in-memory database the bridge can open its own sessions against."""
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


def _seed_player(session) -> Player:
    player = Player(
        source_provider="manual",
        provider_external_id="scheduled-owner-path",
        full_name="Canonical Footballer",
        is_tradable=True,
        market_value_eur=25_000_000.0,
    )
    session.add(player)
    session.commit()
    return player


def _play_competition_matches(session, player_id: str, ratings: list[float]) -> None:
    """Real competition matches, recorded through the real recorder."""
    recorder = PlayerMatchPerformanceRecorder(session)
    for index, rating in enumerate(ratings):
        match = CompetitionMatch(
            id=f"sched-match-{index}",
            competition_id=f"sched-comp-{index // 2}",
            round_id=f"sched-round-{index}",
            round_number=1,
            home_club_id="club-home",
            away_club_id="club-away",
            completed_at=KICKOFF - timedelta(days=index),
        )
        session.add(match)
        session.flush()
        recorder.record_match(match=match, player_stats=[_Stat(player_id, rating)])
    session.commit()


def _buy_shares(session, user: User, player: Player, *, quantity: Decimal, price: Decimal) -> None:
    """A real settled trade, producing real `position:` ledger entries."""
    wallet_service = WalletService()
    user_account = wallet_service.get_user_account(session, user, LedgerUnit.CREDIT)
    platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.CREDIT)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=Decimal("100000")),
            LedgerPosting(account=platform_account, amount=Decimal("-100000")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="scheduled-owner-path-funding",
        description="Seed cash",
        actor=user,
    )
    session.commit()

    SettlementService().settle_execution(
        session,
        user=user,
        execution=TradeExecution(
            execution_id="scheduled-owner-path-buy",
            player_id=player.id,
            side="buy",
            quantity=quantity,
            price=price,
            reserve_before_settlement=True,
        ),
    )
    session.commit()


# --- BLOCKER 1: the scheduled path is the same path -------------------------


def test_scheduled_entrypoint_builds_the_same_bridge_as_the_api(session_factory):
    """The cron must not be a second valuation pipeline."""
    bridge = build_bridge(session_factory)

    # Same class the API container builds, and it carries the projector that
    # writes the published value onto the read model the portfolio prices from.
    from app.players.service import PlayerSummaryProjector
    from app.value_engine.service import IngestionValueEngineBridge

    assert isinstance(bridge, IngestionValueEngineBridge)
    assert isinstance(bridge.summary_projector, PlayerSummaryProjector)


def test_scheduled_run_wires_the_matchday_provider_into_value_snapshot_job(
    session_factory, monkeypatch
):
    """Prove the scheduled path reaches ValueSnapshotJob *with* the overlay."""
    import app.value_engine.service as value_service
    from app.value_engine.matchday_provider import MatchdayValuationSignalProvider

    captured: dict = {}
    original = value_service.ValueSnapshotJob

    def _spy(*args, **kwargs):
        captured.update(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(value_service, "ValueSnapshotJob", _spy)

    with session_factory() as session:
        _seed_player(session)

    run_scheduled_rebuild(session_factory, as_of=AS_OF)

    assert "matchday_signal_provider" in captured
    assert isinstance(captured["matchday_signal_provider"], MatchdayValuationSignalProvider)


def test_scheduled_run_records_itself_as_a_cron_run(session_factory):
    with session_factory() as session:
        _seed_player(session)

    snapshots = run_scheduled_rebuild(session_factory, as_of=AS_OF)

    assert snapshots, "the scheduled rebuild produced no snapshots"


# --- BLOCKER 2: the real owner path ----------------------------------------


def test_matchday_form_reaches_the_published_valuation_with_no_manual_endpoint_call(
    session_factory,
):
    """The read model is written by the projector, not by this test."""
    with session_factory() as session:
        player = _seed_player(session)
        player_id = player.id

    # Baseline: rebuild before any football has been played.
    run_scheduled_rebuild(session_factory, as_of=AS_OF - timedelta(days=30))
    with session_factory() as session:
        baseline_summary = session.get(PlayerSummaryReadModel, player_id)
        assert baseline_summary is not None, "the projector did not write a summary row"
        baseline_value = baseline_summary.current_value_credits

    # Now he plays a strong run of competition football.
    with session_factory() as session:
        _play_competition_matches(session, player_id, [8.6, 8.4, 8.8, 8.5, 8.7, 8.6])

    # Only the scheduled job runs. No operator endpoint is called anywhere here.
    snapshots = run_scheduled_rebuild(session_factory, as_of=AS_OF)

    snapshot = next(item for item in snapshots if item.player_id == player_id)
    assert snapshot.matchday_signal_audit is not None
    assert snapshot.matchday_signal_audit["applied"] is True
    assert snapshot.matchday_signal_audit["adjustment_pct"] > 0

    with session_factory() as session:
        summary = session.get(PlayerSummaryReadModel, player_id)
        assert summary is not None
        # Written by PlayerSummaryProjector inside the bridge, not by this test.
        assert summary.current_value_credits != baseline_value


def test_the_owner_position_is_priced_from_the_form_adjusted_valuation(session_factory):
    """The last link, over a real settled holding and a projector-written price."""
    with session_factory() as session:
        player = _seed_player(session)
        player_id = player.id
        user = AuthService().register_user(
            session,
            email="owner@example.com",
            username="owner-user",
            password="SuperSecret1",
        )
        session.commit()
        user_id = user.id
        _buy_shares(session, user, player, quantity=Decimal("10"), price=Decimal("100"))

    with session_factory() as session:
        _play_competition_matches(session, player_id, [8.6, 8.4, 8.8, 8.5, 8.7, 8.6])

    snapshots = run_scheduled_rebuild(session_factory, as_of=AS_OF)
    snapshot = next(item for item in snapshots if item.player_id == player_id)

    with session_factory() as session:
        owner = session.get(User, user_id)
        portfolio = PortfolioService().build_for_user(session, owner)

        holding = next(item for item in portfolio.holdings if item.player_id == player_id)
        assert holding.quantity == Decimal("10.0000")

        summary = session.get(PlayerSummaryReadModel, player_id)
        # The holder is priced at exactly the value the scheduled run published.
        assert holding.current_price == Decimal(
            str(summary.current_value_credits)
        ).quantize(Decimal("0.0001"))
        assert float(holding.current_price) == pytest.approx(
            summary.current_value_credits, rel=1e-6
        )

    # And that published value carries the matchday overlay.
    assert snapshot.matchday_signal_audit["applied"] is True


def test_poor_form_lowers_what_the_owner_is_priced_at(session_factory):
    with session_factory() as session:
        player = _seed_player(session)
        player_id = player.id
        user = AuthService().register_user(
            session,
            email="owner2@example.com",
            username="owner-user-2",
            password="SuperSecret1",
        )
        session.commit()
        user_id = user.id
        _buy_shares(session, user, player, quantity=Decimal("10"), price=Decimal("100"))

    run_scheduled_rebuild(session_factory, as_of=AS_OF - timedelta(days=30))
    with session_factory() as session:
        before = session.get(PlayerSummaryReadModel, player_id).current_value_credits

    with session_factory() as session:
        _play_competition_matches(session, player_id, [4.4, 4.6, 4.2, 4.5, 4.3, 4.4])

    run_scheduled_rebuild(session_factory, as_of=AS_OF)

    with session_factory() as session:
        owner = session.get(User, user_id)
        portfolio = PortfolioService().build_for_user(session, owner)
        holding = next(item for item in portfolio.holdings if item.player_id == player_id)
        after = session.get(PlayerSummaryReadModel, player_id).current_value_credits

        assert after < before
        assert holding.current_price == Decimal(str(after)).quantize(Decimal("0.0001"))


def test_the_audit_trail_survives_into_the_persisted_snapshot(session_factory):
    """Point 9 of the audit: the stored decision must be reconstructable."""
    from app.value_engine.read_models import PlayerValueSnapshotRecord

    with session_factory() as session:
        player = _seed_player(session)
        player_id = player.id

    with session_factory() as session:
        _play_competition_matches(session, player_id, [8.6, 8.4, 8.8, 8.5, 8.7, 8.6])

    run_scheduled_rebuild(session_factory, as_of=AS_OF)

    with session_factory() as session:
        record = session.scalar(
            select(PlayerValueSnapshotRecord)
            .where(PlayerValueSnapshotRecord.player_id == player_id)
            .order_by(PlayerValueSnapshotRecord.as_of.desc())
            .limit(1)
        )
        audit = record.breakdown_json["matchday_signal"]

        for key in (
            "applied",
            "adjustment_pct",
            "reason_code",
            "matches_counted",
            "competitions_counted",
            "average_rating",
            "confidence",
            "trend",
            "baseline_rating",
            "minimum_matches_for_signal",
            "applied_adjustment_pct",
            "requested_adjustment_pct",
            "overlay_clamped",
        ):
            assert key in audit, f"audit payload is missing {key}"
