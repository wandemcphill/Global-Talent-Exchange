from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import md5
from typing import Any


@dataclass(frozen=True, slots=True)
class AdAnalyticsRecord:
    user_id: str
    ad_id: str
    action: str
    match_id: str | None
    timestamp: datetime
    metadata: dict[str, Any]


def build_tracking_token(
    *,
    match_id: str,
    ad_id: str,
    action: str,
    user_id: str | None = None,
) -> str:
    seed = "|".join((match_id, ad_id, action, user_id or "anonymous"))
    return md5(seed.encode("utf-8")).hexdigest()[:16]


def track_event(
    *,
    user_id: str,
    ad_id: str,
    action: str,
    match_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = AdAnalyticsRecord(
        user_id=user_id,
        ad_id=ad_id,
        action=action,
        match_id=match_id,
        timestamp=datetime.now(UTC),
        metadata=dict(metadata or {}),
    )
    return {
        "user": record.user_id,
        "ad": record.ad_id,
        "action": record.action,
        "match_id": record.match_id,
        "timestamp": record.timestamp.isoformat(),
        "metadata": record.metadata,
    }


def impression_metadata(
    *,
    match_id: str,
    ad_id: str,
    placement: str,
) -> dict[str, Any]:
    return {
        "tracking_token": build_tracking_token(
            match_id=match_id,
            ad_id=ad_id,
            action="impression",
        ),
        "placement": placement,
        "match_id": match_id,
    }


__all__ = [
    "AdAnalyticsRecord",
    "build_tracking_token",
    "impression_metadata",
    "track_event",
]
