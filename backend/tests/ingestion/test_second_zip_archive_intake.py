from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from app.ingestion.second_zip_archive_intake import (
    REQUIRED_SECOND_ZIP_DATASETS,
    SecondZipArchiveIntakeService,
    SecondZipArchiveMalformedError,
    SecondZipArchiveValidationError,
)


def _build_dataset_files() -> dict[str, str]:
    return {
        dataset_name: "id,name\n1,alpha\n2,beta\n"
        for dataset_name in REQUIRED_SECOND_ZIP_DATASETS
    }


def _write_archive(archive_path: Path, files: dict[str, str]) -> None:
    with ZipFile(archive_path, mode="w", compression=ZIP_DEFLATED) as archive:
        for file_name, contents in files.items():
            archive.writestr(file_name, contents)


def test_validate_archive_accepts_complete_2nd_zip_and_streams_rows(tmp_path: Path) -> None:
    archive_path = tmp_path / "2nd.zip"
    files = _build_dataset_files()
    files["README.txt"] = "metadata"
    _write_archive(archive_path, files)

    service = SecondZipArchiveIntakeService()

    inspection = service.validate_archive(archive_path)

    assert inspection.archive_path == archive_path.resolve()
    assert inspection.is_complete is True
    assert inspection.missing_files == ()
    assert inspection.unexpected_files == ("README.txt",)

    players_entry = inspection.get_entry("players.csv")
    assert players_entry is not None
    assert players_entry.column_names == ("id", "name")
    assert players_entry.row_count == 2

    with service.open_csv_rows(archive_path, "players.csv") as rows:
        first_row = next(rows)
        second_row = next(rows)

    assert first_row == {"id": "1", "name": "alpha"}
    assert second_row == {"id": "2", "name": "beta"}


def test_validate_archive_rejects_missing_required_file(tmp_path: Path) -> None:
    archive_path = tmp_path / "2nd.zip"
    files = _build_dataset_files()
    files.pop("transfers.csv")
    _write_archive(archive_path, files)

    service = SecondZipArchiveIntakeService()

    with pytest.raises(SecondZipArchiveValidationError, match="transfers\\.csv"):
        service.validate_archive(archive_path)


def test_validate_archive_rejects_malformed_zip(tmp_path: Path) -> None:
    archive_path = tmp_path / "2nd.zip"
    archive_path.write_bytes(b"not a zip archive")

    service = SecondZipArchiveIntakeService()

    with pytest.raises(SecondZipArchiveMalformedError, match="readable zip file"):
        service.validate_archive(archive_path)


def test_extract_archive_cleans_up_temp_workdir(tmp_path: Path) -> None:
    archive_path = tmp_path / "2nd.zip"
    _write_archive(archive_path, _build_dataset_files())

    temp_root = tmp_path / "extracted"
    service = SecondZipArchiveIntakeService(temp_root=temp_root)

    with service.extract_archive(archive_path) as extracted:
        workdir = extracted.workdir
        players_path = extracted.get_path("players.csv")

        assert workdir.exists()
        assert players_path.exists()
        assert players_path.parent == workdir
        assert players_path.read_text(encoding="utf-8") == "id,name\n1,alpha\n2,beta\n"

    assert not workdir.exists()
