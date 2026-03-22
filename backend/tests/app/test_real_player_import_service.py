from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.ingestion.models  # noqa: F401
import app.ingestion.real_player_import_models  # noqa: F401
import app.models  # noqa: F401
import app.players.read_models  # noqa: F401
import app.value_engine.read_models  # noqa: F401
from app.core.config import load_settings
from app.ingestion.real_player_import_models import RealPlayerImportStagingRecord
from app.ingestion.real_player_import_service import RealPlayerImportService
from app.models.base import Base


def test_real_player_import_is_resumable_and_idempotent() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    settings = load_settings(
        environ={"DATABASE_URL": "sqlite+pysqlite:///:memory:"},
        config_root=(Path(__file__).resolve().parents[2] / "config"),
    )

    try:
        with session_factory() as session:
            service = RealPlayerImportService(session, settings=settings)

            first = service.import_directory(
                provider_name="mock",
                batch_size=2,
                max_pages=1,
                cursor_key="test-real-player-import",
            )
            session.commit()

            assert first.status == "partial_success"
            assert first.records_seen == 2
            assert first.inserted_count == 2
            assert first.updated_count == 0
            assert first.skipped_count == 0
            assert first.pages_processed == 1
            assert first.exhausted is False
            assert first.next_cursor == "2"

            second = service.import_directory(
                provider_name="mock",
                batch_size=2,
                max_pages=10,
                cursor_key="test-real-player-import",
            )
            session.commit()

            assert second.status == "success"
            assert second.records_seen == 2
            assert second.inserted_count == 2
            assert second.updated_count == 0
            assert second.skipped_count == 0
            assert second.exhausted is True
            assert second.next_cursor is None

            third = service.import_directory(
                provider_name="mock",
                batch_size=2,
                max_pages=10,
                cursor_key="test-real-player-import",
            )
            session.commit()

            assert third.status == "success"
            assert third.records_seen == 4
            assert third.inserted_count == 0
            assert third.updated_count == 0
            assert third.skipped_count == 4
            assert third.exhausted is True

            staged_count = session.scalar(
                select(func.count()).select_from(RealPlayerImportStagingRecord).where(
                    RealPlayerImportStagingRecord.provider_name == "mock"
                )
            )
            assert staged_count == 4

            records = session.scalars(
                select(RealPlayerImportStagingRecord).where(
                    RealPlayerImportStagingRecord.provider_name == "mock"
                )
            ).all()
            assert {record.provider_player_id for record in records} == {
                "p-bellingham",
                "p-foden",
                "p-raya",
                "p-saka",
            }
            assert all(record.import_state == "staged" for record in records)

            status = service.get_status(
                provider_name="mock",
                cursor_key="test-real-player-import",
            )

            assert status.provider_name == "mock"
            assert status.cursor_key == "test-real-player-import"
            assert status.staged_player_count == 4
            assert status.cursor is not None
            assert status.cursor.cursor_value is None
            assert status.latest_run is not None
            assert status.latest_run.job_name == "real_player_directory_import"
            assert len(status.recent_runs) == 3
    finally:
        engine.dispose()
