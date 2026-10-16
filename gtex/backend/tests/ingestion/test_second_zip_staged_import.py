from __future__ import annotations

import csv
from datetime import date
from io import StringIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.ingestion.models  # noqa: F401
import app.ingestion.real_player_import_models  # noqa: F401
import app.models  # noqa: F401
import app.players.read_models  # noqa: F401
import app.value_engine.read_models  # noqa: F401
from app.ingestion.models import ProviderSyncRun
from app.ingestion.real_player_import_models import RealPlayerImportStagingRecord
from app.ingestion.second_zip_staged_ingest_service import (
    SECOND_ZIP_STAGED_IMPORT_DEFAULT_BATCH_SIZE,
    SecondZipStagedIngestService,
)
from app.ingestion.transfermarkt_second_zip import SECOND_ZIP_SOURCE_NAME
from app.models.base import Base


REFERENCE_DATE = date(2026, 3, 23)
PLAYER_FIELDNAMES = [
    "player_id",
    "first_name",
    "last_name",
    "name",
    "last_season",
    "current_club_id",
    "player_code",
    "country_of_birth",
    "city_of_birth",
    "country_of_citizenship",
    "date_of_birth",
    "sub_position",
    "position",
    "foot",
    "height_in_cm",
    "contract_expiration_date",
    "agent_name",
    "image_url",
    "international_caps",
    "international_goals",
    "current_national_team_id",
    "url",
    "current_club_domestic_competition_id",
    "current_club_name",
    "market_value_in_eur",
    "highest_market_value_in_eur",
]


def _session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _player_row(*, player_id: str, name: str, **overrides: str) -> dict[str, str]:
    row = {
        "player_id": player_id,
        "first_name": name.split(" ")[0],
        "last_name": name.split(" ")[-1],
        "name": name,
        "last_season": "2024",
        "current_club_id": "100",
        "player_code": name.casefold().replace(" ", "-"),
        "country_of_birth": "Nigeria",
        "city_of_birth": "Lagos",
        "country_of_citizenship": "Nigeria",
        "date_of_birth": "2000-01-02 00:00:00",
        "sub_position": "Centre-Forward",
        "position": "Attack",
        "foot": "right",
        "height_in_cm": "182",
        "contract_expiration_date": "",
        "agent_name": "",
        "image_url": "https://img.test/player.jpg",
        "international_caps": "",
        "international_goals": "",
        "current_national_team_id": "",
        "url": f"https://example.test/player/{player_id or 'missing'}",
        "current_club_domestic_competition_id": "NG1",
        "current_club_name": "Test FC",
        "market_value_in_eur": "250000",
        "highest_market_value_in_eur": "500000",
    }
    row.update(overrides)
    return row


def _csv_text(fieldnames: list[str], rows: list[dict[str, str]]) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def _write_second_zip_archive(archive_path: Path, *, player_rows: list[dict[str, str]]) -> None:
    files = {
        "players.csv": _csv_text(PLAYER_FIELDNAMES, player_rows),
        "clubs.csv": "club_id,name\n100,Test FC\n",
        "competitions.csv": "competition_id,name\nNG1,Nigeria Premier League\n",
        "countries.csv": "country_id,name\nNG,Nigeria\n",
        "national_teams.csv": "team_id,name\nNT1,Nigeria\n",
        "player_valuations.csv": "player_id,market_value\n1,250000\n",
        "transfers.csv": "transfer_id,player_id\n1,1\n",
        "club_games.csv": "game_id,club_id\n1,100\n",
    }
    with ZipFile(archive_path, mode="w", compression=ZIP_DEFLATED) as archive:
        for file_name, contents in files.items():
            archive.writestr(file_name, contents)


def test_second_zip_staged_import_chunks_with_default_batch_size(tmp_path: Path) -> None:
    archive_path = tmp_path / "2nd.zip"
    player_rows = [
        _player_row(player_id=str(index), name=f"Player {index}")
        for index in range(1, SECOND_ZIP_STAGED_IMPORT_DEFAULT_BATCH_SIZE + 2)
    ]
    _write_second_zip_archive(archive_path, player_rows=player_rows)

    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            service = SecondZipStagedIngestService(session)

            summary = service.import_players_csv(
                archive_path,
                reference_date=REFERENCE_DATE,
            )

            staged_count = session.scalar(
                select(func.count()).select_from(RealPlayerImportStagingRecord).where(
                    RealPlayerImportStagingRecord.provider_name == SECOND_ZIP_SOURCE_NAME
                )
            )
            run = session.get(ProviderSyncRun, summary.run_id)

            assert summary.batch_size == SECOND_ZIP_STAGED_IMPORT_DEFAULT_BATCH_SIZE
            assert summary.batches_processed == 2
            assert summary.total_rows_read == 1001
            assert summary.eligible_rows == 1001
            assert summary.inserted_count == 1001
            assert summary.updated_count == 0
            assert summary.duplicate_skipped_count == 0
            assert summary.failed_count == 0
            assert summary.processed_count == 1001
            assert staged_count == 1001
            assert run is not None
            assert run.metadata_json["batches_processed"] == 2
            assert run.metadata_json["batch_size"] == SECOND_ZIP_STAGED_IMPORT_DEFAULT_BATCH_SIZE
    finally:
        engine.dispose()


def test_second_zip_staged_import_updates_counters_for_insert_update_skip_and_fail(tmp_path: Path) -> None:
    archive_path = tmp_path / "2nd.zip"
    player_rows = [
        _player_row(player_id="100", name="Alpha One", market_value_in_eur="100000"),
        _player_row(player_id="100", name="Alpha One", market_value_in_eur="100000"),
        _player_row(player_id="100", name="Alpha One", market_value_in_eur="200000"),
        _player_row(player_id="", name="Broken Source"),
        _player_row(player_id="200", name="Ineligible Player", last_season="2023"),
    ]
    _write_second_zip_archive(archive_path, player_rows=player_rows)

    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            service = SecondZipStagedIngestService(session)

            summary = service.import_players_csv(
                archive_path,
                batch_size=2,
                reference_date=REFERENCE_DATE,
            )

            staged = session.scalar(
                select(RealPlayerImportStagingRecord).where(
                    RealPlayerImportStagingRecord.provider_name == SECOND_ZIP_SOURCE_NAME,
                    RealPlayerImportStagingRecord.provider_player_id == "100",
                )
            )
            run = session.get(ProviderSyncRun, summary.run_id)

            assert summary.status == "partial_success"
            assert summary.total_rows_read == 5
            assert summary.eligible_rows == 4
            assert summary.inserted_count == 1
            assert summary.updated_count == 1
            assert summary.duplicate_skipped_count == 1
            assert summary.failed_count == 1
            assert summary.processed_count == 4
            assert staged is not None
            assert staged.latest_payload_json["market_value_in_eur"] == "200000"
            assert run is not None
            assert run.records_seen == 4
            assert run.failed_count == 1
            assert run.metadata_json["eligible_rows"] == 4
            assert run.metadata_json["duplicate_skipped_count"] == 1
    finally:
        engine.dispose()


def test_second_zip_staged_import_keeps_imported_rows_in_staged_state(tmp_path: Path) -> None:
    archive_path = tmp_path / "2nd.zip"
    player_rows = [
        _player_row(
            player_id="501",
            name="Mapped Later",
            current_club_id="999",
            current_club_name="Unknown Club",
            current_club_domestic_competition_id="UNMAPPED-COMP",
            position="Midfield",
            sub_position="Central Midfield",
        )
    ]
    _write_second_zip_archive(archive_path, player_rows=player_rows)

    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            service = SecondZipStagedIngestService(session)

            summary = service.import_players_csv(
                archive_path,
                batch_size=1,
                reference_date=REFERENCE_DATE,
            )

            staged = session.scalar(
                select(RealPlayerImportStagingRecord).where(
                    RealPlayerImportStagingRecord.provider_name == SECOND_ZIP_SOURCE_NAME,
                    RealPlayerImportStagingRecord.provider_player_id == "501",
                )
            )

            assert summary.status == "success"
            assert summary.inserted_count == 1
            assert summary.failed_count == 0
            assert staged is not None
            assert staged.import_state == "staged"
            assert staged.provider_player_id == "501"
            assert staged.provider_club_id == "999"
            assert staged.provider_competition_id == "UNMAPPED-COMP"
            assert staged.provider_competition_name is None
            assert staged.metadata_json["source_row_number"] == 1
    finally:
        engine.dispose()
