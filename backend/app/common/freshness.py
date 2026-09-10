from __future__ import annotations

from datetime import datetime, timezone

from app.common.schemas.freshness import FreshnessInfo, FreshnessStatus


def evaluate_freshness(
    as_of: datetime | None,
    *,
    is_live: bool = False,
    is_pending: bool = False,
    pending_reason: str | None = None,
    stale_threshold_seconds: float = 86400.0,
    reference_time: datetime | None = None,
) -> FreshnessInfo:
    """Evaluate source timestamp and state flags into a canonical FreshnessInfo model."""
    if is_live:
        return FreshnessInfo(
            status=FreshnessStatus.LIVE,
            as_of=as_of,
            label="LIVE",
        )

    if is_pending:
        return FreshnessInfo(
            status=FreshnessStatus.PENDING_RECALCULATION,
            as_of=as_of,
            label="Pending Recalculation",
            pending_reason=pending_reason or "Recalculation queued",
        )

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
        # Future timestamp safeguard
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
