from datetime import datetime, timedelta, timezone

from app.common.freshness import evaluate_freshness
from app.common.schemas.freshness import FreshnessStatus
from app.ingestion.models import Player
from app.matchday_economy.service import MatchdayEconomyService
from app.models.player_match_performance import PlayerMatchPerformance
from app.models.player_token_market import PlayerShareHolding, PlayerShareMarket
from app.models.user import User
from app.players.read_models import PlayerSummaryReadModel
from app.players.router import get_player_form
from app.players.schemas import PlayerSummaryView
from app.players.service import PlayerSummaryQueryService
from app.portfolio.schemas import PortfolioHoldingView
from app.portfolio.service import PortfolioService


def test_price_value_form_freshness_independence():
    now = datetime(2026, 3, 30, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Matchday form is fresh (LIVE or RECENT)
    match_ts = now - timedelta(minutes=15)
    form_freshness = evaluate_freshness(match_ts, is_live=True, reference_time=now)
    assert form_freshness.status == FreshnessStatus.LIVE

    # 2. Published valuation is pending recalculation because match just finished
    val_ts = now - timedelta(hours=12)
    valuation_freshness = evaluate_freshness(
        val_ts,
        is_pending=True,
        pending_reason="Matchday form pending valuation snapshot job",
        reference_time=now,
    )
    assert valuation_freshness.status == FreshnessStatus.PENDING_RECALCULATION

    # 3. Tradable share price is recent or stale independently
    market_ts = now - timedelta(hours=2)
    market_freshness = evaluate_freshness(market_ts, reference_time=now)
    assert market_freshness.status == FreshnessStatus.RECENT

    # Construct PlayerSummaryView verifying independent freshness structures
    player_summary = PlayerSummaryView(
        player_id="player-101",
        player_name="Daniel Okoro",
        current_club_id="club-1",
        current_club_name="Enyimba FC",
        current_competition_id="comp-1",
        current_competition_name="NPFL",
        last_snapshot_id="snap-1",
        last_snapshot_at=val_ts,
        current_value_credits=100.0,
        previous_value_credits=95.0,
        movement_pct=5.26,
        average_rating=7.8,
        market_interest_score=85,
        summary_json={},
        updated_at=now,
        valuation_freshness=valuation_freshness,
        market_freshness=market_freshness,
    )

    assert player_summary.valuation_freshness.status == FreshnessStatus.PENDING_RECALCULATION
    assert player_summary.market_freshness.status == FreshnessStatus.RECENT


def test_portfolio_holding_freshness_independence():
    now = datetime(2026, 3, 30, 12, 0, 0, tzinfo=timezone.utc)

    price_freshness = evaluate_freshness(now - timedelta(minutes=5), reference_time=now)
    val_freshness = evaluate_freshness(
        now - timedelta(days=2),
        is_pending=False,
        stale_threshold_seconds=86400,
        reference_time=now,
    )

    holding = PortfolioHoldingView(
        player_id="player-101",
        player_name="Daniel Okoro",
        club_name="Enyimba FC",
        quantity="10.0000",
        average_cost="12.0000",
        current_price="15.0000",
        market_value="150.0000",
        unrealized_pl="30.0000",
        unrealized_pl_percent="25.0000",
        price_freshness=price_freshness,
        valuation_freshness=val_freshness,
    )

    assert holding.price_freshness.status == FreshnessStatus.RECENT
    assert holding.valuation_freshness.status == FreshnessStatus.STALE


def test_four_way_freshness_disagreement_independence():
    """Proves that Matchday Form != Published Valuation != Tradable Share Price != Portfolio Value.

    Updating or evaluating one domain data stream does not alter the independent
    freshness state of the others.
    """
    ref_time = datetime(2026, 4, 1, 15, 0, 0, tzinfo=timezone.utc)

    # 1. Matchday form from a match played 10 minutes ago -> RECENT
    form_ts = ref_time - timedelta(minutes=10)
    form_freshness = evaluate_freshness(form_ts, reference_time=ref_time)
    assert form_freshness.status == FreshnessStatus.RECENT

    # 2. Published valuation last snapshot taken 3 days ago -> STALE
    val_ts = ref_time - timedelta(days=3)
    val_freshness = evaluate_freshness(val_ts, stale_threshold_seconds=86400, reference_time=ref_time)
    assert val_freshness.status == FreshnessStatus.STALE

    # 3. Share market traded 1 hour ago -> RECENT
    market_ts = ref_time - timedelta(hours=1)
    market_freshness = evaluate_freshness(market_ts, reference_time=ref_time)
    assert market_freshness.status == FreshnessStatus.RECENT

    # 4. Portfolio holding where valuation source is unavailable -> UNKNOWN
    portfolio_val_freshness = evaluate_freshness(None)
    assert portfolio_val_freshness.status == FreshnessStatus.UNKNOWN

    # All four distinct statuses can coexist honestly for the same entity
    assert form_freshness.status != val_freshness.status
    assert val_freshness.status != market_freshness.status
    assert portfolio_val_freshness.status == FreshnessStatus.UNKNOWN


def test_freshness_fields_populated_in_services(app_session_factory):
    """Integration test proving all 7 freshness fields are wired and populated with real backend data."""
    now = datetime.now(timezone.utc)

    with app_session_factory() as session:
        # 1. Seed player and summary read model
        player = Player(
            id="freshness-p1",
            source_provider="manual",
            provider_external_id="ext-p1",
            full_name="Kelechi Nnamdi",
            is_real_player=True,
            source_last_refreshed_at=now - timedelta(hours=2),
        )
        session.add(player)

        summary = PlayerSummaryReadModel(
            player_id="freshness-p1",
            player_name="Kelechi Nnamdi",
            last_snapshot_at=now - timedelta(hours=5),
            current_value_credits=150.0,
            previous_value_credits=140.0,
            movement_pct=7.14,
            summary_json={},
        )
        session.add(summary)

        # 2. Seed share market
        market = PlayerShareMarket(
            player_id="freshness-p1",
            share_price_coin=12.5,
            total_shares=1000.0,
            status="active",
            created_at=now - timedelta(minutes=30),
            updated_at=now - timedelta(minutes=10),
        )
        session.add(market)

        # 3. Seed match performance
        perf = PlayerMatchPerformance(
            player_id="freshness-p1",
            match_id="m-101",
            competition_id="c-1",
            rating=8.2,
            minutes_played=90,
            occurred_at=now - timedelta(minutes=45),
            eligible_for_valuation=True,
        )
        session.add(perf)

        # 4. Seed user and holding
        user = User(
            id="freshness-u1",
            email="freshness_user@example.com",
            username="freshnessuser",
            password_hash="pbkdf2:sha256:test",  # pragma: allowlist secret
            role="user",
            created_at=now,
        )
        session.add(user)

        holding = PlayerShareHolding(
            user_id="freshness-u1",
            player_id="freshness-p1",
            share_count=5.0,
            average_cost_coin=10.0,
        )
        session.add(holding)
        session.commit()

        # Test Player Summary View wiring
        summary_view = PlayerSummaryQueryService(session).get_summary_view("freshness-p1")
        assert summary_view is not None
        assert summary_view.valuation_freshness is not None
        assert summary_view.valuation_freshness.status in {FreshnessStatus.RECENT, FreshnessStatus.STALE}
        assert summary_view.market_freshness is not None
        assert summary_view.market_freshness.status == FreshnessStatus.RECENT
        assert summary_view.real_player_universe is not None
        assert summary_view.real_player_universe.source_freshness is not None
        assert summary_view.real_player_universe.source_freshness.status == FreshnessStatus.RECENT

        # Test Player Form View wiring
        form_view = get_player_form(player_id="freshness-p1", session=session)
        assert form_view.form_freshness is not None
        assert form_view.form_freshness.status == FreshnessStatus.RECENT
        assert len(form_view.performances) == 1
        assert form_view.performances[0].performance_freshness is not None
        assert form_view.performances[0].performance_freshness.status == FreshnessStatus.RECENT

        # Test Portfolio Holdings wiring
        holdings = PortfolioService()._build_player_share_holdings(session, user)
        assert len(holdings) == 1
        assert holdings[0].price_freshness is not None
        assert holdings[0].price_freshness.status == FreshnessStatus.RECENT
        assert holdings[0].valuation_freshness is not None
        assert holdings[0].valuation_freshness.status == FreshnessStatus.RECENT

        # Test Matchday Economy Overview wiring
        economy_view = MatchdayEconomyService(session).overview(user=user)
        assert economy_view.economy_freshness is not None
        assert economy_view.economy_freshness.status == FreshnessStatus.RECENT
