from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.ingestion.models  # noqa: F401
import app.ingestion.real_player_import_models  # noqa: F401
import app.models  # noqa: F401
import app.players.read_models  # noqa: F401
import app.value_engine.read_models  # noqa: F401
from app.core.config import load_settings
from app.ingestion.models import ProviderSyncRun
from app.ingestion.real_player_import_models import (
    RealPlayerImportRun,
    RealPlayerImportStagingRecord,
)
from app.ingestion.real_player_import_service import RealPlayerImportService
from app.models.base import Base


def _session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _settings() -> object:
    return load_settings(
        environ={"DATABASE_URL": "sqlite+pysqlite:///:memory:"},
        config_root=(Path(__file__).resolve().parents[2] / "config"),
    )


def _write_csv(path: Path, rows: list[dict[str, object]]) -> Path:
    headers = list(rows[0])
    lines = [",".join(headers)]
    for row in rows:
        values = []
        for header in headers:
            raw_value = row.get(header)
            text = "" if raw_value is None else str(raw_value)
            if any(char in text for char in {",", "\"", "\n"}):
                text = "\"" + text.replace("\"", "\"\"") + "\""
            values.append(text)
        lines.append(",".join(values))
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_bulk_source_import_processes_csv_in_chunks(tmp_path: Path) -> None:
    engine, factory = _session_factory()
    try:
        csv_path = _write_csv(
            tmp_path / "chunked.csv",
            [
                {
                    "provider_player_id": "csv-001",
                    "full_name": "Victor Osimhen",
                    "display_position": "Striker",
                    "nationality_name": "Nigeria",
                    "nationality_code": "NG",
                    "date_of_birth": "1998-12-29",
                    "current_club_name": "Galatasaray",
                    "current_competition_name": "Super Lig",
                },
                {
                    "provider_player_id": "csv-002",
                    "full_name": "Alex Iwobi",
                    "display_position": "Winger",
                    "nationality_name": "Nigeria",
                    "nationality_code": "NG",
                    "date_of_birth": "1996-05-03",
                    "current_club_name": "Fulham",
                    "current_competition_name": "Premier League",
                },
                {
                    "provider_player_id": "csv-003",
                    "full_name": "Wilfred Ndidi",
                    "display_position": "Midfielder",
                    "nationality_name": "Nigeria",
                    "nationality_code": "NG",
                    "date_of_birth": "1996-12-16",
                    "current_club_name": "",
                    "current_competition_name": "",
                },
                {
                    "provider_player_id": "csv-004",
                    "full_name": "Victor Boniface",
                    "display_position": "Striker",
                    "nationality_name": "Nigeria",
                    "nationality_code": "NG",
                    "date_of_birth": "2000-12-23",
                    "current_club_name": "Bayer Leverkusen",
                    "current_competition_name": "Bundesliga",
                },
                {
                    "provider_player_id": "csv-005",
                    "full_name": "Calvin Bassey",
                    "display_position": "Centre-Back",
                    "nationality_name": "Nigeria",
                    "nationality_code": "NG",
                    "date_of_birth": "1999-12-31",
                    "current_club_name": "Fulham",
                    "current_competition_name": "Premier League",
                },
            ],
        )

        with factory() as session:
            service = RealPlayerImportService(session, settings=_settings())
            summary = service.import_source_file(
                source_path=csv_path,
                provider_name="csv-feed",
                batch_size=2,
                cursor_key="bulk-csv-chunked",
            )

            assert summary.status == "success"
            assert summary.records_seen == 5
            assert summary.processed_count == 5
            assert summary.inserted_count == 5
            assert summary.updated_count == 0
            assert summary.duplicate_skipped_count == 0
            assert summary.failed_count == 0
            assert summary.batches_processed == 3
            assert summary.exhausted is True

            staged_count = session.scalar(
                select(func.count()).select_from(RealPlayerImportStagingRecord).where(
                    RealPlayerImportStagingRecord.provider_name == "csv-feed"
                )
            )
            assert staged_count == 5

            import_run = session.get(RealPlayerImportRun, summary.import_run_id)
            assert import_run is not None
            assert import_run.status == "completed"
            assert import_run.total_rows_discovered == 5
            assert import_run.processed_rows == 5
            assert import_run.inserted_rows == 5
            assert import_run.duplicate_skipped_rows == 0
            assert import_run.last_successful_batch_marker == "batch:3"
    finally:
        engine.dispose()


def test_bulk_source_import_is_idempotent_for_json_provider_dump(tmp_path: Path) -> None:
    engine, factory = _session_factory()
    try:
        json_path = _write_json(
            tmp_path / "provider-dump.json",
            {
                "source_version": "provider-dump-v1",
                "players": [
                    {
                        "id": "json-001",
                        "name": "Victor Osimhen",
                        "position": "Striker",
                        "nationality": "Nigeria",
                        "nationality_code": "NG",
                        "dateOfBirth": "1998-12-29",
                        "currentClub": {"id": "GAL", "name": "Galatasaray"},
                        "currentCompetition": {"id": "TR1", "name": "Super Lig"},
                    },
                    {
                        "name": "Victor Boniface",
                        "position": "Striker",
                        "nationality": "Nigeria",
                        "nationality_code": "NG",
                        "dateOfBirth": "2000-12-23",
                        "currentClub": {"id": "LEV", "name": "Bayer Leverkusen"},
                        "currentCompetition": {"id": "BL1", "name": "Bundesliga"},
                    },
                    {
                        "id": "json-003",
                        "name": "Alex Iwobi",
                        "position": "Winger",
                        "nationality": "Nigeria",
                        "nationality_code": "NG",
                        "dateOfBirth": "1996-05-03",
                        "currentClub": {"id": "FUL", "name": "Fulham"},
                        "currentCompetition": {"id": "PL", "name": "Premier League"},
                    },
                    {
                        "id": "json-004",
                        "name": "Calvin Bassey",
                        "position": "Centre-Back",
                        "nationality": "Nigeria",
                        "nationality_code": "NG",
                        "dateOfBirth": "1999-12-31",
                        "currentClub": {"id": "FUL", "name": "Fulham"},
                        "currentCompetition": {"id": "PL", "name": "Premier League"},
                    },
                ],
            },
        )

        with factory() as session:
            service = RealPlayerImportService(session, settings=_settings())
            first = service.import_source_file(
                source_path=json_path,
                provider_name="json-feed",
                batch_size=2,
                cursor_key="bulk-json-idempotent",
            )
            second = service.import_source_file(
                source_path=json_path,
                provider_name="json-feed",
                batch_size=2,
                cursor_key="bulk-json-idempotent",
            )

            assert first.inserted_count == 4
            assert first.duplicate_skipped_count == 0
            assert second.inserted_count == 0
            assert second.duplicate_skipped_count == 4

            records = session.scalars(
                select(RealPlayerImportStagingRecord).where(
                    RealPlayerImportStagingRecord.provider_name == "json-feed"
                )
            ).all()
            assert len(records) == 4
            fallback_records = [record for record in records if record.provider_player_id.startswith("fallback:")]
            assert len(fallback_records) == 1
            assert fallback_records[0].metadata_json["fallback_provider_identity_kind"] == "exact_identity_key"
    finally:
        engine.dispose()


def test_bulk_source_import_resumes_after_mid_run_failure(tmp_path: Path) -> None:
    engine, factory = _session_factory()
    try:
        csv_path = _write_csv(
            tmp_path / "resume.csv",
            [
                {"provider_player_id": "resume-001", "full_name": "Player One", "date_of_birth": "2001-01-01"},
                {"provider_player_id": "resume-002", "full_name": "Player Two", "date_of_birth": "2001-01-02"},
                {"provider_player_id": "resume-003", "full_name": "Player Three", "date_of_birth": "2001-01-03"},
                {"provider_player_id": "resume-004", "full_name": "Player Four", "date_of_birth": "2001-01-04"},
                {"provider_player_id": "resume-005", "full_name": "Player Five", "date_of_birth": "2001-01-05"},
            ],
        )

        with factory() as session:
            service = RealPlayerImportService(session, settings=_settings())
            original_upsert = service.staging_repository.upsert_staging_records
            calls = {"count": 0}

            def failing_upsert(**kwargs):
                calls["count"] += 1
                if calls["count"] == 2:
                    raise RuntimeError("simulated batch failure")
                return original_upsert(**kwargs)

            service.staging_repository.upsert_staging_records = failing_upsert  # type: ignore[method-assign]
            with pytest.raises(RuntimeError, match="simulated batch failure"):
                service.import_source_file(
                    source_path=csv_path,
                    provider_name="resume-feed",
                    batch_size=2,
                    cursor_key="bulk-resume",
                )

            service.staging_repository.upsert_staging_records = original_upsert  # type: ignore[assignment]
            failed_run = session.scalar(
                select(RealPlayerImportRun)
                .where(RealPlayerImportRun.provider_name == "resume-feed")
                .order_by(RealPlayerImportRun.started_at.desc())
            )
            assert failed_run is not None
            assert failed_run.status == "failed"
            assert failed_run.processed_rows == 2
            assert failed_run.metadata_json["last_failed_batch"]["batch_marker"] == "batch:2"

            status = service.get_status(provider_name="resume-feed", cursor_key="bulk-resume")
            assert status.cursor is not None
            assert status.cursor.cursor_value == "2"
            assert status.staged_player_count == 2

            resumed = service.import_source_file(
                source_path=csv_path,
                provider_name="resume-feed",
                batch_size=2,
                cursor_key="bulk-resume",
            )

            assert resumed.import_run_id == failed_run.id
            assert resumed.records_seen == 3
            assert resumed.inserted_count == 3
            assert resumed.batches_processed == 2

            refreshed_run = session.get(RealPlayerImportRun, failed_run.id)
            assert refreshed_run is not None
            assert refreshed_run.status == "completed"
            assert refreshed_run.processed_rows == 5
            assert refreshed_run.inserted_rows == 5
            assert refreshed_run.last_successful_batch_marker == "batch:3"
    finally:
        engine.dispose()


def test_bulk_source_import_tracks_duplicate_skips(tmp_path: Path) -> None:
    engine, factory = _session_factory()
    try:
        csv_path = _write_csv(
            tmp_path / "duplicates.csv",
            [
                {"provider_player_id": "dup-001", "full_name": "Victor Osimhen", "date_of_birth": "1998-12-29"},
                {"provider_player_id": "dup-001", "full_name": "Victor Osimhen", "date_of_birth": "1998-12-29"},
                {"provider_player_id": "dup-002", "full_name": "Alex Iwobi", "date_of_birth": "1996-05-03"},
            ],
        )

        with factory() as session:
            service = RealPlayerImportService(session, settings=_settings())
            summary = service.import_source_file(
                source_path=csv_path,
                provider_name="dup-feed",
                batch_size=1000,
                cursor_key="bulk-duplicates",
            )

            assert summary.inserted_count == 2
            assert summary.duplicate_skipped_count == 1
            assert summary.failed_count == 0
            assert session.scalar(
                select(func.count()).select_from(RealPlayerImportStagingRecord).where(
                    RealPlayerImportStagingRecord.provider_name == "dup-feed"
                )
            ) == 2
    finally:
        engine.dispose()


def test_bulk_source_import_supports_dry_run_without_writing(tmp_path: Path) -> None:
    engine, factory = _session_factory()
    try:
        csv_path = _write_csv(
            tmp_path / "dry-run.csv",
            [
                {"provider_player_id": "dry-001", "full_name": "Dry Run One", "date_of_birth": "2002-01-01"},
                {"provider_player_id": "dry-002", "full_name": "Dry Run Two", "date_of_birth": "2002-01-02"},
            ],
        )

        with factory() as session:
            service = RealPlayerImportService(session, settings=_settings())
            summary = service.import_source_file(
                source_path=csv_path,
                provider_name="dry-feed",
                batch_size=2,
                dry_run=True,
            )

            assert summary.status == "dry_run"
            assert summary.inserted_count == 2
            assert summary.run_id is None
            assert session.scalar(select(func.count()).select_from(RealPlayerImportStagingRecord)) == 0
            assert session.scalar(select(func.count()).select_from(RealPlayerImportRun)) == 0
            assert session.scalar(select(func.count()).select_from(ProviderSyncRun)) == 0
    finally:
        engine.dispose()
