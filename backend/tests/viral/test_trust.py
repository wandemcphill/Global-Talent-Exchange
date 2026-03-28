from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models.user import User, UserRole
from app.viral.ingestion_schemas import ClipEvent, ClipEventMetadata, ClipEventType
from app.viral.trust import InMemoryTrustStateStore, TrustScoreService


def _event(*, event_id: str, event_type: ClipEventType, session_id: str, user_id: str) -> ClipEvent:
    return ClipEvent(
        event_id=event_id,
        clip_id="clip-trust-unit",
        user_id=user_id,
        session_id=session_id,
        timestamp=datetime(2026, 3, 28, 12, 0, tzinfo=UTC),
        event_type=event_type,
        watch_time_ms=12_000 if event_type is not ClipEventType.SCROLL else 50,
        video_length_ms=12_000,
        metadata=ClipEventMetadata(
            device="ios",
            country="NG",
            referrer="feed",
        ),
    )


def test_trust_service_decays_on_loop_abuse_and_persists_state() -> None:
    store = InMemoryTrustStateStore()
    service = TrustScoreService(store=store)
    user = User(
        id="trust-user-1",
        email="trust@example.com",
        username="trust-user",
        password_hash="hashed",
        role=UserRole.USER,
        created_at=datetime.now(UTC) - timedelta(days=120),
        updated_at=datetime.now(UTC) - timedelta(days=1),
    )

    trust_scores: list[float] = []
    last_evaluation = None
    for index in range(1, 6):
        last_evaluation = service.evaluate_event(
            _event(
                event_id=f"4fe03dba-7b62-4fd5-a7fd-{index:012d}",
                event_type=ClipEventType.LOOP,
                session_id="session-unit-trust",
                user_id=user.id,
            ),
            headers={"x-device-id": "device-1", "user-agent": "pytest"},
            ip_address="203.0.113.7",
            user=user,
        )
        trust_scores.append(last_evaluation.trust.trust_score)

    assert last_evaluation is not None
    assert trust_scores[-1] < trust_scores[0]
    assert last_evaluation.trust.loop_discount_factor == 0.0
    assert "repeated_loop_session" in last_evaluation.trust.suspicious_flags

    persisted_state = store.load_trust_state(user.id)
    persisted_session = store.load_session_behavior("session-unit-trust")
    assert persisted_state is not None
    assert persisted_state.trust_score == trust_scores[-1]
    assert persisted_state.suspicious_event_count >= 1
    assert persisted_session is not None
    assert persisted_session.total_loops == 5
    assert persisted_session.event_count == 5
