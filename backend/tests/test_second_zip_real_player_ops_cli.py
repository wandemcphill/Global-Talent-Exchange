from __future__ import annotations

import json

from app.ingestion.second_zip_real_player_ops_service import (
    SecondZipReferencePreloadCounts,
    SecondZipReferencePreloadReport,
    SecondZipReportCounts,
    SecondZipRunReport,
)
from backend.scripts.real_player_import_from_2nd_zip import main


class _FakeService:
    def __init__(self) -> None:
        self.preload_calls: list[str] = []
        self.import_calls: list[tuple[str, int, int | None]] = []
        self.publish_calls: list[tuple[str, int | None, str | None, int]] = []
        self.report_calls: list[tuple[str, bool]] = []

    def preload_references(self, *, archive_path: str):
        self.preload_calls.append(archive_path)
        return SecondZipReferencePreloadReport(
            archive_path=archive_path,
            archive_sha256="abc123",
            counts=SecondZipReferencePreloadCounts(
                inserted_countries=1,
                inserted_competitions=1,
                inserted_clubs=1,
            ),
        )

    def import_archive(self, *, archive_path: str, batch_size: int, limit: int | None):
        self.import_calls.append((archive_path, batch_size, limit))
        return SecondZipRunReport(
            run_id="run-1",
            batch_key="2nd-zip-test",
            status="completed",
            archive_path=archive_path,
            archive_sha256="abc123",
            batch_size=batch_size,
            limit=limit,
            read_exhausted=False,
            scope_complete=True,
            next_resume_row_number=None,
            counts=SecondZipReportCounts(total_rows_read=2000, eligible_rows=2000, publish_ready=2000),
        )

    def report_run(self, *, run_id: str, refresh_summary: bool = False):
        self.report_calls.append((run_id, refresh_summary))
        return SecondZipRunReport(
            run_id=run_id,
            batch_key="2nd-zip-test",
            status="completed",
            archive_path="C:/temp/2nd.zip",
            archive_sha256="abc123",
            batch_size=1000,
            limit=2000,
            read_exhausted=False,
            scope_complete=True,
            next_resume_row_number=None,
            counts=SecondZipReportCounts(total_rows_read=2000, eligible_rows=2000, publish_ready=2000),
        )

    def publish_run(self, *, run_id: str, limit: int | None, tier: str | None, batch_size: int):
        self.publish_calls.append((run_id, limit, tier, batch_size))
        return SecondZipRunReport(
            run_id=run_id,
            batch_key="2nd-zip-test",
            status="completed",
            archive_path="C:/temp/2nd.zip",
            archive_sha256="abc123",
            batch_size=1000,
            limit=limit,
            read_exhausted=False,
            scope_complete=True,
            next_resume_row_number=None,
            counts=SecondZipReportCounts(total_rows_read=2000, eligible_rows=2000, published=2000),
        )


def test_second_zip_cli_routes_import_and_report(monkeypatch, capsys) -> None:
    service = _FakeService()
    monkeypatch.setattr(
        "backend.scripts.real_player_import_from_2nd_zip.build_service",
        lambda database_url: service,
    )

    exit_code = main(
        [
            "--database-url",
            "sqlite+pysqlite:///tmp/test.db",
            "import",
            "--file",
            "C:/temp/2nd.zip",
            "--batch-size",
            "1000",
            "--limit",
            "2000",
        ]
    )
    assert exit_code == 0
    import_payload = json.loads(capsys.readouterr().out)
    assert import_payload["run_id"] == "run-1"
    assert service.import_calls == [("C:/temp/2nd.zip", 1000, 2000)]

    exit_code = main(
        [
            "--database-url",
            "sqlite+pysqlite:///tmp/test.db",
            "report",
            "--run-id",
            "run-1",
        ]
    )
    assert exit_code == 0
    report_payload = json.loads(capsys.readouterr().out)
    assert report_payload["run_id"] == "run-1"
    assert service.report_calls == [("run-1", False)]


def test_second_zip_cli_routes_preload(monkeypatch, capsys) -> None:
    service = _FakeService()
    monkeypatch.setattr(
        "backend.scripts.real_player_import_from_2nd_zip.build_service",
        lambda database_url: service,
    )

    exit_code = main(
        [
            "--database-url",
            "sqlite+pysqlite:///tmp/test.db",
            "preload",
            "--file",
            "C:/temp/2nd.zip",
        ]
    )

    assert exit_code == 0
    preload_payload = json.loads(capsys.readouterr().out)
    assert preload_payload["archive_path"] == "C:/temp/2nd.zip"
    assert service.preload_calls == ["C:/temp/2nd.zip"]


def test_second_zip_cli_accepts_database_url_after_wrapper_subcommand(monkeypatch, capsys) -> None:
    service = _FakeService()
    monkeypatch.setattr(
        "backend.scripts.real_player_import_from_2nd_zip.build_service",
        lambda database_url: service,
    )

    exit_code = main(
        [
            "import",
            "--database-url",
            "sqlite+pysqlite:///tmp/test.db",
            "--file",
            "C:/temp/2nd.zip",
            "--batch-size",
            "1000",
            "--limit",
            "2000",
        ]
    )

    assert exit_code == 0
    import_payload = json.loads(capsys.readouterr().out)
    assert import_payload["run_id"] == "run-1"
    assert service.import_calls == [("C:/temp/2nd.zip", 1000, 2000)]


def test_second_zip_cli_routes_publish_with_batch_size(monkeypatch, capsys) -> None:
    service = _FakeService()
    monkeypatch.setattr(
        "backend.scripts.real_player_import_from_2nd_zip.build_service",
        lambda database_url: service,
    )

    exit_code = main(
        [
            "--database-url",
            "sqlite+pysqlite:///tmp/test.db",
            "publish",
            "--run-id",
            "run-1",
            "--limit",
            "500",
            "--tier",
            "tier_1",
            "--batch-size",
            "100",
        ]
    )

    assert exit_code == 0
    publish_payload = json.loads(capsys.readouterr().out)
    assert publish_payload["run_id"] == "run-1"
    assert service.publish_calls == [("run-1", 500, "tier_1", 100)]


def test_second_zip_cli_routes_report_with_refresh_summary(monkeypatch, capsys) -> None:
    service = _FakeService()
    monkeypatch.setattr(
        "backend.scripts.real_player_import_from_2nd_zip.build_service",
        lambda database_url: service,
    )

    exit_code = main(
        [
            "--database-url",
            "sqlite+pysqlite:///tmp/test.db",
            "report",
            "--run-id",
            "run-1",
            "--refresh-summary",
        ]
    )

    assert exit_code == 0
    report_payload = json.loads(capsys.readouterr().out)
    assert report_payload["run_id"] == "run-1"
    assert service.report_calls == [("run-1", True)]


def test_second_zip_cli_routes_check_db(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "backend.scripts.real_player_import_from_2nd_zip.check_database",
        lambda database_url: {
            "status": "ready",
            "database_backend": "postgresql",
            "database_driver": "psycopg",
            "schema_heads": ["head"],
            "authoritative_large_publish_supported": True,
            "migration_check": True,
        },
    )

    exit_code = main(
        [
            "--database-url",
            "postgresql://db.example/gtex",
            "check-db",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ready"
    assert payload["database_backend"] == "postgresql"
