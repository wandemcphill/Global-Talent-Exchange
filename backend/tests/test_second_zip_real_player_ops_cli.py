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
        self.report_calls: list[str] = []

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

    def report_run(self, *, run_id: str):
        self.report_calls.append(run_id)
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
    assert service.report_calls == ["run-1"]


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
