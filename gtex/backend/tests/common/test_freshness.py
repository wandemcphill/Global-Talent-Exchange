from datetime import datetime, timedelta, timezone

from app.common.freshness import evaluate_freshness
from app.common.schemas.freshness import FreshnessStatus


def test_evaluate_freshness_live():
    info = evaluate_freshness(datetime.now(timezone.utc), is_live=True)
    assert info.status == FreshnessStatus.LIVE
    assert info.label == "LIVE"


def test_evaluate_freshness_pending():
    info = evaluate_freshness(
        datetime.now(timezone.utc),
        is_pending=True,
        pending_reason="Match finished, pending recalculation",
    )
    assert info.status == FreshnessStatus.PENDING_RECALCULATION
    assert info.pending_reason == "Match finished, pending recalculation"


def test_evaluate_freshness_unknown():
    info = evaluate_freshness(None)
    assert info.status == FreshnessStatus.UNKNOWN
    assert info.as_of is None


def test_evaluate_freshness_missing_timestamp_safeguard():
    # Attempting to declare LIVE or PENDING without as_of timestamp evidence MUST result in UNKNOWN
    live_without_ts = evaluate_freshness(None, is_live=True)
    assert live_without_ts.status == FreshnessStatus.UNKNOWN
    assert live_without_ts.as_of is None

    pending_without_ts = evaluate_freshness(None, is_pending=True)
    assert pending_without_ts.status == FreshnessStatus.UNKNOWN
    assert pending_without_ts.as_of is None


def test_evaluate_freshness_recent_and_stale():
    now = datetime(2026, 3, 30, 12, 0, 0, tzinfo=timezone.utc)

    # 1 hour old -> RECENT
    recent_ts = now - timedelta(hours=1)
    recent_info = evaluate_freshness(recent_ts, reference_time=now, stale_threshold_seconds=86400)
    assert recent_info.status == FreshnessStatus.RECENT

    # 48 hours old -> STALE
    stale_ts = now - timedelta(hours=48)
    stale_info = evaluate_freshness(stale_ts, reference_time=now, stale_threshold_seconds=86400)
    assert stale_info.status == FreshnessStatus.STALE
    assert stale_info.stale_reason == "Data is 48 hours old"


def test_evaluate_freshness_future_safeguard():
    now = datetime(2026, 3, 30, 12, 0, 0, tzinfo=timezone.utc)
    future_ts = now + timedelta(minutes=10)
    info = evaluate_freshness(future_ts, reference_time=now)
    assert info.status == FreshnessStatus.RECENT
