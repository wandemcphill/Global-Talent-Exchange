from __future__ import annotations

import os
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import app.models.real_player_import_batch  # noqa: F401
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.core.config import load_settings
from app.core.database import load_model_modules
from app.ingestion.models import Player
from app.ingestion.real_player_batch_runner import (
    RealPlayerBatchExecutionRow,
    RealPlayerBatchPreflightRow,
    RealPlayerBatchRunReport,
)
from app.ingestion.real_player_import_ops_schemas import (
    RealPlayerImportBatchResumeRequest,
    RealPlayerImportBatchRunRequest,
)
from app.ingestion.real_player_import_ops_service import RealPlayerImportOpsService
from app.ingestion.second_zip_staged_import import SECOND_ZIP_SOURCE_TYPE
from app.models.base import Base
from app.models.real_player_import_batch import RealPlayerImportBatch, RealPlayerImportRow
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_source_link import RealPlayerSourceLink


def _database_url(database_path: Path) -> str:
    return f"sqlite+pysqlite:///{database_path.as_posix()}"


def _initialize_database(database_url: str):
    load_model_modules()
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


def _session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _settings(database_url: str):
    return load_settings(environ={**os.environ, "GTE_DATABASE_URL": database_url})


def _service(database_url: str, engine) -> RealPlayerImportOpsService:
    return RealPlayerImportOpsService(
        session_factory=_session_factory(engine),
        database_url=database_url,
        settings=_settings(database_url),
    )


class ScriptedRealPlayerImportOpsService(RealPlayerImportOpsService):
    def __init__(self, *args, scripted_reports: list[RealPlayerBatchRunReport], **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.scripted_reports = iter(scripted_reports)
        self.captured_requests: list[list[str]] = []

    def _run_report(self, *, request, runner_mode):  # type: ignore[override]
        self.captured_requests.append([player.source_player_key for player in request.players])
        return next(self.scripted_reports)


def _player_csv_row(
    *,
    player_id: str,
    name: str,
    first_name: str,
    last_name: str,
    date_of_birth: str,
    club_id: str,
    club_name: str,
    competition_id: str,
    player_code: str | None = None,
    market_value_in_eur: int = 1_000_000,
    highest_market_value_in_eur: int = 2_000_000,
    last_season: int = 2024,
) -> str:
    return ",".join(
        [
            player_id,
            player_code or f"{player_id}-{last_name.casefold()}",
            name,
            first_name,
            last_name,
            f"{date_of_birth} 00:00:00",
            "Nigeria",
            "Nigeria",
            "Lagos",
            "right",
            "185",
            "Attack",
            "Centre-Forward",
            club_id,
            club_name,
            competition_id,
            str(market_value_in_eur),
            str(highest_market_value_in_eur),
            f"https://img.test/{player_id}.jpg",
            f"https://example.test/player/{player_id}",
            str(last_season),
        ]
    )


def _write_second_zip(tmp_path: Path, player_rows: list[str], *, archive_name: str = "2nd.zip") -> Path:
    archive_path = tmp_path / archive_name
    players_csv = "\n".join(
        [
            (
                "player_id,player_code,name,first_name,last_name,date_of_birth,country_of_citizenship,"
                "country_of_birth,city_of_birth,foot,height_in_cm,position,sub_position,current_club_id,"
                "current_club_name,current_club_domestic_competition_id,market_value_in_eur,"
                "highest_market_value_in_eur,image_url,url,last_season"
            ),
            *player_rows,
        ]
    ) + "\n"
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("players.csv", players_csv)
        archive.writestr("clubs.csv", "club_id,club_code,name\n100,test-fc,Test FC\n101,alt-fc,Alt FC\n")
        archive.writestr(
            "competitions.csv",
            "competition_id,competition_code,name\nNG1,nigeria-premier-league,Nigeria Premier League\n",
        )
        archive.writestr("countries.csv", "country_id,country_name\nNG,Nigeria\n")
        archive.writestr("national_teams.csv", "national_team_id,name\nNG,Nigeria\n")
        archive.writestr("player_valuations.csv", "player_id,market_value_in_eur\n")
        archive.writestr("transfers.csv", "player_id,from_club_id,to_club_id\n")
        archive.writestr("club_games.csv", "game_id,club_id\n")
    return archive_path


def _run_request(archive_path: Path) -> RealPlayerImportBatchRunRequest:
    return RealPlayerImportBatchRunRequest(
        manifest_path=str(archive_path),
        mode="write",
        source_type=SECOND_ZIP_SOURCE_TYPE,
    )


def _partial_report(*, source_keys: list[str], executed_source_keys: list[str], error_message: str | None) -> RealPlayerBatchRunReport:
    return RealPlayerBatchRunReport(
        runner_mode="write",
        request_mode="curated_seed",
        database_url="sqlite+pysqlite:///synthetic.db",
        batch_path="synthetic-2nd.zip",
        ingestion_batch_id="synthetic-batch",
        preflight_rows=tuple(
            RealPlayerBatchPreflightRow(
                source_name=SECOND_ZIP_SOURCE_TYPE,
                source_player_key=source_key,
                canonical_name=f"Player {source_key}",
                resolved_action="matched_existing",
                gtex_player_id=f"player-{source_key}",
                confidence_score=1.0,
                audit_status="pass",
            )
            for source_key in source_keys
        ),
        execution_rows=tuple(
            RealPlayerBatchExecutionRow(
                source_name=SECOND_ZIP_SOURCE_TYPE,
                source_player_key=source_key,
                canonical_name=f"Player {source_key}",
                resolved_action="created",
                gtex_player_id=f"player-{source_key}",
                confidence_score=1.0,
                pricing_snapshot_id=f"snapshot-{source_key}",
                pricing_status="resolved",
                audit_status="pass",
                commit_status="committed",
            )
            for source_key in executed_source_keys
        ),
        error_message=error_message,
    )


def test_second_zip_rerun_is_idempotent_for_staged_and_live_rows(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path / "second-zip-idempotent.db")
    engine = _initialize_database(database_url)
    service = _service(database_url, engine)
    try:
        archive_path = _write_second_zip(
            tmp_path,
            [
                _player_csv_row(
                    player_id="10",
                    name="Victor Osimhen",
                    first_name="Victor",
                    last_name="Osimhen",
                    date_of_birth="1998-12-29",
                    club_id="100",
                    club_name="Test FC",
                    competition_id="NG1",
                ),
                _player_csv_row(
                    player_id="11",
                    name="Alex Iwobi",
                    first_name="Alex",
                    last_name="Iwobi",
                    date_of_birth="1996-05-03",
                    club_id="101",
                    club_name="Alt FC",
                    competition_id="NG1",
                ),
            ],
        )

        first_batch = service.run_batch(actor_user_id=None, payload=_run_request(archive_path))
        rerun_batch = service.run_batch(actor_user_id=None, payload=_run_request(archive_path))

        assert first_batch.status == "completed"
        assert rerun_batch.id == first_batch.id
        assert rerun_batch.status == "completed"
        assert rerun_batch.summary_json["noop_reason"] == "idempotent_rerun"
        assert rerun_batch.summary_json["duplicate_skipped_count"] == 2
        assert rerun_batch.skipped_row_count == 2
        with _session_factory(engine)() as session:
            assert session.scalar(select(func.count()).select_from(RealPlayerImportBatch)) == 1
            assert session.scalar(select(func.count()).select_from(RealPlayerImportRow)) == 2
            assert session.scalar(select(func.count()).select_from(Player)) == 2
            assert session.scalar(select(func.count()).select_from(RealPlayerSourceLink)) == 2
            assert session.scalar(select(func.count()).select_from(RealPlayerProfile)) == 2
    finally:
        engine.dispose()


def test_second_zip_duplicate_source_ids_are_skipped_and_counted(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path / "second-zip-duplicates.db")
    engine = _initialize_database(database_url)
    service = _service(database_url, engine)
    try:
        archive_path = _write_second_zip(
            tmp_path,
            [
                _player_csv_row(
                    player_id="10",
                    name="Victor Osimhen",
                    first_name="Victor",
                    last_name="Osimhen",
                    date_of_birth="1998-12-29",
                    club_id="100",
                    club_name="Test FC",
                    competition_id="NG1",
                ),
                _player_csv_row(
                    player_id="10",
                    name="Victor Osimhen Duplicate",
                    first_name="Victor",
                    last_name="Osimhen",
                    date_of_birth="1998-12-29",
                    club_id="100",
                    club_name="Test FC",
                    competition_id="NG1",
                    player_code="duplicate-osimhen",
                ),
            ],
        )

        batch = service.run_batch(actor_user_id=None, payload=_run_request(archive_path))

        assert batch.status == "completed"
        assert batch.submitted_row_count == 1
        assert batch.skipped_row_count == 1
        assert batch.metadata_json["source_anchor_field"] == "external_player_id"
        assert batch.metadata_json["source_row_count"] == 2
        assert batch.metadata_json["source_duplicate_skipped_count"] == 1
        assert batch.summary_json["duplicate_skipped_count"] == 1
        assert batch.summary_json["source_duplicate_skipped_count"] == 1
        with _session_factory(engine)() as session:
            assert session.scalar(select(func.count()).select_from(RealPlayerImportRow)) == 1
            assert session.scalar(select(func.count()).select_from(Player)) == 1
            assert session.scalar(select(func.count()).select_from(RealPlayerSourceLink)) == 1
            assert session.scalar(select(func.count()).select_from(RealPlayerProfile)) == 1
    finally:
        engine.dispose()


def test_second_zip_interrupted_run_marks_resume_from_first_pending_row(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path / "second-zip-interrupted.db")
    engine = _initialize_database(database_url)
    service = ScriptedRealPlayerImportOpsService(
        session_factory=_session_factory(engine),
        database_url=database_url,
        settings=_settings(database_url),
        scripted_reports=[
            _partial_report(
                source_keys=["21", "22", "23"],
                executed_source_keys=["21"],
                error_message="interrupted after first commit",
            )
        ],
    )
    try:
        archive_path = _write_second_zip(
            tmp_path,
            [
                _player_csv_row(
                    player_id="21",
                    name="Player Twenty One",
                    first_name="Player",
                    last_name="Twentyone",
                    date_of_birth="2000-01-01",
                    club_id="100",
                    club_name="Test FC",
                    competition_id="NG1",
                ),
                _player_csv_row(
                    player_id="22",
                    name="Player Twenty Two",
                    first_name="Player",
                    last_name="Twentytwo",
                    date_of_birth="2000-01-02",
                    club_id="101",
                    club_name="Alt FC",
                    competition_id="NG1",
                ),
                _player_csv_row(
                    player_id="23",
                    name="Player Twenty Three",
                    first_name="Player",
                    last_name="Twentythree",
                    date_of_birth="2000-01-03",
                    club_id="101",
                    club_name="Alt FC",
                    competition_id="NG1",
                ),
            ],
        )

        batch = service.run_batch(actor_user_id=None, payload=_run_request(archive_path))

        assert service.captured_requests == [["21", "22", "23"]]
        assert batch.status == "completed_with_errors"
        assert batch.summary_json["resume_from_row_number"] == 2
        assert batch.summary_json["last_successful_row_number"] == 1
        with _session_factory(engine)() as session:
            rows = list(
                session.scalars(
                    select(RealPlayerImportRow)
                    .join(RealPlayerImportBatch, RealPlayerImportBatch.id == RealPlayerImportRow.batch_id)
                    .where(RealPlayerImportBatch.id == batch.id)
                    .order_by(RealPlayerImportRow.row_number.asc())
                )
            )
            assert [row.status for row in rows] == ["imported", "pending", "pending"]
    finally:
        engine.dispose()


def test_second_zip_resume_after_partial_success_only_reprocesses_pending_rows(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path / "second-zip-resume.db")
    engine = _initialize_database(database_url)
    service = ScriptedRealPlayerImportOpsService(
        session_factory=_session_factory(engine),
        database_url=database_url,
        settings=_settings(database_url),
        scripted_reports=[
            _partial_report(
                source_keys=["31", "32", "33"],
                executed_source_keys=["31"],
                error_message="interrupted after first commit",
            ),
            _partial_report(
                source_keys=["32", "33"],
                executed_source_keys=["32", "33"],
                error_message=None,
            ),
        ],
    )
    try:
        archive_path = _write_second_zip(
            tmp_path,
            [
                _player_csv_row(
                    player_id="31",
                    name="Player Thirty One",
                    first_name="Player",
                    last_name="Thirtyone",
                    date_of_birth="2001-01-01",
                    club_id="100",
                    club_name="Test FC",
                    competition_id="NG1",
                ),
                _player_csv_row(
                    player_id="32",
                    name="Player Thirty Two",
                    first_name="Player",
                    last_name="Thirtytwo",
                    date_of_birth="2001-01-02",
                    club_id="101",
                    club_name="Alt FC",
                    competition_id="NG1",
                ),
                _player_csv_row(
                    player_id="33",
                    name="Player Thirty Three",
                    first_name="Player",
                    last_name="Thirtythree",
                    date_of_birth="2001-01-03",
                    club_id="101",
                    club_name="Alt FC",
                    competition_id="NG1",
                ),
            ],
        )

        partial_batch = service.run_batch(actor_user_id=None, payload=_run_request(archive_path))
        resumed_batch = service.resume_batch(
            batch_id=partial_batch.id,
            actor_user_id=None,
            payload=RealPlayerImportBatchResumeRequest(mode="write"),
        )

        assert service.captured_requests == [["31", "32", "33"], ["32", "33"]]
        assert resumed_batch.status == "completed"
        assert resumed_batch.skipped_row_count == 1
        assert resumed_batch.summary_json["duplicate_skipped_count"] == 1
        assert resumed_batch.summary_json["last_successful_row_number"] == 3
        with _session_factory(engine)() as session:
            assert session.scalar(select(func.count()).select_from(RealPlayerImportBatch)) == 1
            rows = list(
                session.scalars(
                    select(RealPlayerImportRow)
                    .join(RealPlayerImportBatch, RealPlayerImportBatch.id == RealPlayerImportRow.batch_id)
                    .where(RealPlayerImportBatch.id == resumed_batch.id)
                    .order_by(RealPlayerImportRow.row_number.asc())
                )
            )
            assert [row.status for row in rows] == ["imported", "imported", "imported"]
    finally:
        engine.dispose()
