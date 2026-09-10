from __future__ import annotations

from datetime import datetime, timezone

from app.common.enums.match_status import MatchStatus
from app.common.schemas.freshness import FreshnessInfo, FreshnessStatus


def evaluate_freshness(
    as_of: datetime | None,
    *,
    stale_threshold_seconds: float = 86400.0,
    reference_time: datetime | None = None,
) -> FreshnessInfo:
    """Evaluate timestamp age only.

    The generic evaluator never allows callers to assert LIVE or PENDING. Those
    states require domain-specific evidence and must be produced by a
    specialized evaluator or an explicit persisted status.
    """
    if as_of is None:
        return FreshnessInfo(
            status=FreshnessStatus.UNKNOWN,
            as_of=None,
            label="Unknown",
        )

    now = reference_time or datetime.now(timezone.utc)
    ts = as_of if as_of.tzinfo is not None else as_of.replace(tzinfo=timezone.utc)
    now_ts = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)

    age_seconds = (now_ts - ts).total_seconds()

    if age_seconds < 0:
        return FreshnessInfo(
            status=FreshnessStatus.RECENT,
            as_of=as_of,
            label="Recent",
        )

    if age_seconds > stale_threshold_seconds:
        hours = int(age_seconds // 3600)
        return FreshnessInfo(
            status=FreshnessStatus.STALE,
            as_of=as_of,
            label="Stale",
            stale_reason=f"Data is {hours} hours old",
        )

    return FreshnessInfo(
        status=FreshnessStatus.RECENT,
        as_of=as_of,
        label="Recent",
    )


def evaluate_match_freshness(
    as_of: datetime | None,
    *,
    match_status: MatchStatus | str | None,
    stale_threshold_seconds: float = 86400.0,
    reference_time: datetime | None = None,
) -> FreshnessInfo:
    """Evaluate freshness for a persisted match using its canonical status.

    LIVE is granted only from the match domain's IN_PROGRESS state plus a real
    timestamp. Missing timestamp evidence remains UNKNOWN even for IN_PROGRESS.
    """
    if as_of is None:
        return FreshnessInfo(
            status=FreshnessStatus.UNKNOWN,
            as_of=None,
            label="Unknown",
        )

    raw_status = match_status.value if isinstance(match_status, MatchStatus) else match_status
    if raw_status == MatchStatus.IN_PROGRESS.value:
        return FreshnessInfo(
            status=FreshnessStatus.LIVE,
            as_of=as_of,
            label="LIVE",
        )

    return evaluate_freshness(
        as_of,
        stale_threshold_seconds=stale_threshold_seconds,
        reference_time=reference_time,
    )


__all__ = ["evaluate_freshness", "evaluate_match_freshness"]
