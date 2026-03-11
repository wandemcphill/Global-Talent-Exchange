from __future__ import annotations

from backend.app.cache.redis_helpers import NullCacheBackend
from backend.app.ingestion.models import Club, Competition, Country, Player, PlayerClubTenure, ProviderRawPayload, ProviderSyncRun, Season
from backend.app.ingestion.service import IngestionService


def test_bootstrap_sync_happy_path_persists_canonical_records(session) -> None:
    service = IngestionService(session, cache_backend=NullCacheBackend())

    summary = service.bootstrap_sync(provider_name="mock")
    session.commit()

    assert summary.status == "success"
    assert summary.inserted_count > 0
    assert session.query(Country).count() == 2
    assert session.query(Competition).count() == 2
    assert session.query(Season).count() == 2
    assert session.query(Club).count() == 3
    assert session.query(Player).count() == 4
    assert session.query(PlayerClubTenure).count() == 6
    assert session.query(ProviderSyncRun).count() == 1
    assert session.query(ProviderRawPayload).count() > 0


def test_bootstrap_sync_is_idempotent_on_second_run(session) -> None:
    service = IngestionService(session, cache_backend=NullCacheBackend())

    first = service.bootstrap_sync(provider_name="mock")
    session.commit()
    second = service.bootstrap_sync(provider_name="mock")
    session.commit()

    assert first.inserted_count > 0
    assert second.inserted_count == 0
    assert second.skipped_count > 0
    assert session.query(Competition).count() == 2
    assert session.query(Season).count() == 2
    assert session.query(Club).count() == 3
    assert session.query(Player).count() == 4
    assert session.query(PlayerClubTenure).count() == 6
    assert session.query(ProviderSyncRun).count() == 2
    assert session.query(ProviderRawPayload).count() > 0
