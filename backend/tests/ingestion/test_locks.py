from __future__ import annotations

from app.ingestion.locks import IngestionLockManager


def test_duplicate_lock_prevention(session_factory) -> None:
    with session_factory() as first_session, session_factory() as second_session:
        first_manager = IngestionLockManager(first_session)
        second_manager = IngestionLockManager(second_session)

        first = first_manager.acquire("ingestion:test")
        second = second_manager.acquire("ingestion:test")

        assert first.acquired is True
        assert second.acquired is False

        first_manager.release(first)
        third = second_manager.acquire("ingestion:test")

        assert third.acquired is True
