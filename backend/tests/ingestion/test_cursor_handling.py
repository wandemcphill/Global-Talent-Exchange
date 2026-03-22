from __future__ import annotations

from app.cache.redis_helpers import NullCacheBackend
from app.ingestion.models import ProviderSyncCursor
from app.ingestion.service import IngestionService


def test_incremental_sync_updates_cursor_and_can_resume(session) -> None:
    service = IngestionService(session, cache_backend=NullCacheBackend())

    service.bootstrap_sync(provider_name="mock")
    session.commit()
    first = service.sync_incremental(provider_name="mock")
    session.commit()
    second = service.sync_incremental(provider_name="mock")
    session.commit()

    cursor = session.query(ProviderSyncCursor).one()

    assert first.cursor_value == "2026-03-11T00:00:00Z"
    assert cursor.cursor_value == "2026-03-11T00:00:00Z"
    assert second.failed_count == 0
