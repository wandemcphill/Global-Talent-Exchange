from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.events import DomainEvent
from app.infrastructure.outbox import OutboxEvent, write_event


ADS_FEED_REFRESH_REQUESTED = "ads.feed.refresh.requested"
CREATOR_EARNINGS_RECOMPUTE_REQUESTED = "creator.earnings.recompute.requested"
FEED_CACHE_REFRESH_REQUESTED = "feed.cache.refresh.requested"
VIRAL_CLIP_DISPATCH_REQUESTED = "viral.clip.dispatch.requested"


def enqueue_feed_cache_refresh(
    *,
    session: Session,
    user_id: str,
    session_id: str | None = None,
    limit: int = 20,
    refresh_following: bool = True,
    reason: str | None = None,
    producer: str = "feed-api",
) -> OutboxEvent:
    return write_event(
        DomainEvent(
            name=FEED_CACHE_REFRESH_REQUESTED,
            aggregate_id=user_id,
            aggregate_type="personalized_feed",
            partition_key=user_id,
            producer=producer,
            payload={
                "user_id": user_id,
                "session_id": session_id,
                "limit": max(int(limit), 1),
                "refresh_following": bool(refresh_following),
                "reason": reason,
            },
        ),
        session=session,
    )


def enqueue_ads_feed_refresh(
    *,
    session: Session,
    ad_id: str,
    advertiser_id: str | None = None,
    producer: str = "ads-engine",
) -> OutboxEvent:
    return write_event(
        DomainEvent(
            name=ADS_FEED_REFRESH_REQUESTED,
            aggregate_id=ad_id,
            aggregate_type="sponsored_clip",
            partition_key=advertiser_id or ad_id,
            producer=producer,
            payload={
                "ad_id": ad_id,
                "advertiser_id": advertiser_id,
            },
        ),
        session=session,
    )


def enqueue_creator_earnings_recompute(
    *,
    session: Session,
    creator_user_id: str,
    export_id: str | None = None,
    match_key: str | None = None,
    producer: str = "creator-monetization",
) -> OutboxEvent:
    return write_event(
        DomainEvent(
            name=CREATOR_EARNINGS_RECOMPUTE_REQUESTED,
            aggregate_id=creator_user_id,
            aggregate_type="creator_earnings",
            partition_key=creator_user_id,
            producer=producer,
            payload={
                "creator_user_id": creator_user_id,
                "export_id": export_id,
                "match_key": match_key,
            },
        ),
        session=session,
    )


def enqueue_viral_dispatch(
    *,
    session: Session,
    aggregate_id: str,
    aggregate_type: str,
    partition_key: str,
    producer: str,
    payload: dict[str, Any],
) -> OutboxEvent:
    return write_event(
        DomainEvent(
            name=VIRAL_CLIP_DISPATCH_REQUESTED,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            partition_key=partition_key,
            producer=producer,
            payload=dict(payload or {}),
        ),
        session=session,
    )


__all__ = [
    "ADS_FEED_REFRESH_REQUESTED",
    "CREATOR_EARNINGS_RECOMPUTE_REQUESTED",
    "FEED_CACHE_REFRESH_REQUESTED",
    "VIRAL_CLIP_DISPATCH_REQUESTED",
    "enqueue_ads_feed_refresh",
    "enqueue_creator_earnings_recompute",
    "enqueue_feed_cache_refresh",
    "enqueue_viral_dispatch",
]
