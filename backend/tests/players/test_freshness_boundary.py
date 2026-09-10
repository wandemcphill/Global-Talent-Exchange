from datetime import datetime, timedelta, timezone

from app.common.freshness import evaluate_freshness
from app.common.schemas.freshness import FreshnessStatus
from app.players.schemas import PlayerSummaryView
from app.portfolio.schemas import PortfolioHoldingView


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
