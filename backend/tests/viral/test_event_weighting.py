from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.viral.event_weighting import ClipEventWeightingMiddleware
from app.viral.ingestion_schemas import ClipEvent, ClipEventMetadata, ClipEventTrust, ClipEventType


class _TrustService:
    def evaluate_event(self, event, *, headers, ip_address, user):  # noqa: ANN001, ARG002
        return type(
            "TrustEvaluation",
            (),
            {"trust": ClipEventTrust(trust_score=0.6, weighted_event_value=0.6)},
        )()


def _event(*, event_type: ClipEventType, watch_time_ms: int, video_length_ms: int) -> ClipEvent:
    return ClipEvent(
        event_id=uuid4(),
        clip_id="clip-weighting",
        user_id=None,
        session_id="session-weighting",
        timestamp=datetime.now(UTC),
        event_type=event_type,
        watch_time_ms=watch_time_ms,
        video_length_ms=video_length_ms,
        metadata=ClipEventMetadata(
            device="ios",
            country="NG",
            referrer="feed",
        ),
    )


def test_event_weighting_applies_fast_skip_penalty_and_full_watch_boost() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    middleware = ClipEventWeightingMiddleware(trust_service=_TrustService())

    with session_factory() as session:
        weighted = middleware.validate_and_weight(
            events=[
                _event(event_type=ClipEventType.SCROLL, watch_time_ms=500, video_length_ms=12_000),
                _event(event_type=ClipEventType.COMPLETE, watch_time_ms=12_000, video_length_ms=12_000),
            ],
            headers={},
            ip_address=None,
            session=session,
        )

    assert weighted[0].trust.weighted_event_value == 0.9
    assert weighted[1].trust.weighted_event_value == 1.0
