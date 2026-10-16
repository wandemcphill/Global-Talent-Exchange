from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.ingestion.models  # noqa: F401
import app.ingestion.real_player_import_models  # noqa: F401
from app.ingestion.models import ProviderSyncRun
from app.ingestion.real_player_import_models import (
    RealPlayerImportProcessingState,
    RealPlayerImportRunStatus,
    RealPlayerImportStagingRecord,
)
from app.ingestion.real_player_import_repository import RealPlayerImportRepository
from app.models.base import Base
from app.providers.import_models import RealPlayerSourceItem


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session
    engine.dispose()


def test_repository_tracks_processing_state_counters_for_import_runs(session) -> None:
    sync_run = ProviderSyncRun(
        id="sync-run-001",
        provider_name="mock",
        job_name="real_player_directory_import",
        entity_type="real_player_directory",
        status="running",
    )
    session.add(sync_run)
    session.flush()

    repository = RealPlayerImportRepository(session)
    import_run = repository.create_import_run(
        provider_name="mock",
        source_type="provider_feed",
        source_reference="C:/imports/players.csv",
        configured_batch_size=500,
        provider_sync_run_id=sync_run.id,
        resume_cursor="batch-0",
        metadata_json={"file_name": "players.csv"},
    )

    stats = repository.upsert_staging_records(
        provider_name="mock",
        items=[
            RealPlayerSourceItem(
                provider_player_id="p-osimhen",
                full_name="Victor Osimhen",
                display_position="Striker",
                nationality_name="Nigeria",
                nationality_code="NG",
                date_of_birth=date(1998, 12, 29),
                rough_market_value=60000000,
                rough_market_value_currency="EUR",
                raw_payload={"provider_player_id": "p-osimhen"},
            ),
            RealPlayerSourceItem(
                provider_player_id="p-iwobi",
                full_name="Alex Iwobi",
                display_position="Winger",
                nationality_name="Nigeria",
                nationality_code="NG",
                date_of_birth=date(1996, 5, 3),
                raw_payload={"provider_player_id": "p-iwobi"},
            ),
        ],
        source_version="v1",
        import_run_id=import_run.id,
        import_batch_key="batch-1",
        last_import_run_id=sync_run.id,
        last_import_cursor="batch-2",
    )
    repository.mark_import_run_progress(
        import_run,
        stats=stats,
        batch_marker="batch-1",
        resume_cursor="batch-2",
    )
    repository.refresh_run_state_counts(import_run)
    session.commit()

    stored_osimhen = repository.get_staging_record(provider_name="mock", provider_player_id="p-osimhen")
    assert stored_osimhen is not None
    assert stored_osimhen.import_run_id == import_run.id
    assert stored_osimhen.import_batch_key == "batch-1"
    assert stored_osimhen.normalized_name == "victor osimhen"
    assert stored_osimhen.age is not None
    assert stored_osimhen.rough_market_value == pytest.approx(60000000)
    assert stored_osimhen.processing_state == RealPlayerImportProcessingState.PENDING.value

    assert import_run.status == RealPlayerImportRunStatus.RUNNING.value
    assert import_run.total_rows_discovered == 2
    assert import_run.processed_rows == 2
    assert import_run.inserted_rows == 2
    assert import_run.updated_rows == 0
    assert import_run.duplicate_skipped_rows == 0
    assert import_run.unresolved_rows == 2
    assert import_run.publish_ready_rows == 0
    assert import_run.published_rows == 0
    assert import_run.failed_rows == 0

    repository.set_processing_state(
        provider_name="mock",
        provider_player_id="p-osimhen",
        processing_state=RealPlayerImportProcessingState.MAPPED_READY.value,
    )
    repository.set_processing_state(
        provider_name="mock",
        provider_player_id="p-iwobi",
        processing_state=RealPlayerImportProcessingState.REJECTED.value,
        rejection_reason="missing club mapping",
    )
    repository.set_processing_state(
        provider_name="mock",
        provider_player_id="p-osimhen",
        processing_state=RealPlayerImportProcessingState.PUBLISHED.value,
    )
    repository.finish_import_run(
        import_run,
        status=RealPlayerImportRunStatus.COMPLETED_WITH_ERRORS.value,
        resume_cursor=None,
    )
    session.commit()

    stored_iwobi = repository.get_staging_record(provider_name="mock", provider_player_id="p-iwobi")
    assert stored_iwobi is not None
    assert stored_iwobi.rejection_reason == "missing club mapping"

    assert import_run.status == RealPlayerImportRunStatus.COMPLETED_WITH_ERRORS.value
    assert import_run.unresolved_rows == 0
    assert import_run.publish_ready_rows == 0
    assert import_run.published_rows == 1
    assert import_run.failed_rows == 1
    assert import_run.completed_at is not None


def test_repository_reuses_existing_processing_state_when_payload_is_unchanged(session) -> None:
    sync_run = ProviderSyncRun(
        id="sync-run-002",
        provider_name="mock",
        job_name="real_player_directory_import",
        entity_type="real_player_directory",
        status="running",
    )
    session.add(sync_run)
    session.flush()

    repository = RealPlayerImportRepository(session)
    import_run = repository.create_import_run(
        provider_name="mock",
        source_type="provider_directory",
        source_reference="provider_directory:mock:test",
        configured_batch_size=2,
        provider_sync_run_id=sync_run.id,
    )

    repository.upsert_staging_records(
        provider_name="mock",
        items=[
            RealPlayerSourceItem(
                provider_player_id="p-saka",
                full_name="Bukayo Saka",
                raw_payload={"provider_player_id": "p-saka"},
            )
        ],
        source_version="v1",
        import_run_id=import_run.id,
        import_batch_key="page:1",
        last_import_run_id=sync_run.id,
        last_import_cursor="2",
    )
    repository.set_processing_state(
        provider_name="mock",
        provider_player_id="p-saka",
        processing_state=RealPlayerImportProcessingState.MAPPED_READY.value,
    )

    second_sync_run = ProviderSyncRun(
        id="sync-run-003",
        provider_name="mock",
        job_name="real_player_directory_import",
        entity_type="real_player_directory",
        status="running",
    )
    session.add(second_sync_run)
    session.flush()

    stats = repository.upsert_staging_records(
        provider_name="mock",
        items=[
            RealPlayerSourceItem(
                provider_player_id="p-saka",
                full_name="Bukayo Saka",
                raw_payload={"provider_player_id": "p-saka"},
            )
        ],
        source_version="v1",
        import_run_id=import_run.id,
        import_batch_key="page:2",
        last_import_run_id=second_sync_run.id,
        last_import_cursor=None,
    )

    stored_record = repository.get_staging_record(provider_name="mock", provider_player_id="p-saka")
    assert stored_record is not None
    assert stats.skipped_count == 1
    assert stored_record.processing_state == RealPlayerImportProcessingState.MAPPED_READY.value
    assert stored_record.import_batch_key == "page:2"
