from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path

import app.models.real_player_import_batch  # noqa: F401
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.core.config import load_settings
from app.core.database import load_model_modules
from app.ingestion.models import Country, Player
from app.ingestion.real_player_import_ops_schemas import (
    RealPlayerImportBatchResumeRequest,
    RealPlayerImportBatchRunRequest,
)
from app.ingestion.real_player_import_ops_service import RealPlayerImportOpsService
from app.models.base import Base
from app.models.real_player_import_batch import RealPlayerImportBatch, RealPlayerImportRow
from app.models.real_player_profile import RealPlayerProfile


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


def _write_manifest(tmp_path: Path, batch_key: str, players: list[dict[str, object]]) -> Path:
    manifest_path = tmp_path / f"{batch_key}.json"
    manifest_path.write_text(
        json.dumps(
            {
                "mode": "curated_seed",
                "ingestion_batch_id": batch_key,
                "ingestion_source_version": "ops-test-v1",
                "as_of": "2026-03-22T12:00:00+00:00",
                "players": players,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return manifest_path


def _sample_players() -> list[dict[str, object]]:
    return [
        {
            "source_name": "curated-feed",
            "source_player_key": "osimhen-001",
            "canonical_name": "Victor Osimhen",
            "known_aliases": ["V. Osimhen"],
            "nationality": "Nigeria",
            "nationality_code": "NG",
            "date_of_birth": "1998-12-29",
            "dominant_foot": "right",
            "primary_position": "Striker",
            "secondary_positions": ["Winger"],
            "current_real_world_club": "Galatasaray",
            "current_real_world_league": "Super Lig",
            "competition_level": "top_flight",
            "appearances": 31,
            "minutes_played": 2410,
            "goals": 19,
            "assists": 4,
            "current_market_reference_value": 60000000,
            "market_reference_currency": "EUR",
        },
        {
            "source_name": "curated-feed",
            "source_player_key": "iwobi-001",
            "canonical_name": "Alex Iwobi",
            "nationality": "Nigeria",
            "nationality_code": "NG",
            "date_of_birth": "1996-05-03",
            "dominant_foot": "right",
            "primary_position": "Winger",
            "secondary_positions": ["Attacking Midfielder"],
            "current_real_world_club": "Fulham",
            "current_real_world_league": "Premier League",
            "competition_level": "elite",
            "appearances": 29,
            "minutes_played": 2280,
            "goals": 6,
            "assists": 7,
            "current_market_reference_value": 18000000,
            "market_reference_currency": "EUR",
        },
    ]


def test_run_batch_tracks_ambiguous_rows_for_manual_review(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path / "ops-ambiguous.db")
    engine = _initialize_database(database_url)
    service = _service(database_url, engine)
    try:
        with _session_factory(engine)() as session:
            country = Country(
                source_provider="test-source",
                provider_external_id="NG",
                name="Nigeria",
                alpha2_code="NG",
            )
            session.add(country)
            session.flush()
            session.add_all(
                [
                    Player(
                        source_provider="legacy-a",
                        provider_external_id="bassey-a",
                        full_name="Calvin Bassey",
                        country=country,
                        position="Centre-Back",
                        normalized_position="defender",
                        date_of_birth=date(1999, 12, 31),
                    ),
                    Player(
                        source_provider="legacy-b",
                        provider_external_id="bassey-b",
                        full_name="Calvin Bassey",
                        country=country,
                        position="Centre-Back",
                        normalized_position="defender",
                        date_of_birth=date(1999, 12, 31),
                    ),
                ]
            )
            session.commit()

        manifest_path = _write_manifest(
            tmp_path,
            "ops-ambiguous-batch",
            [
                {
                    "source_name": "curated-feed",
                    "source_player_key": "bassey-001",
                    "canonical_name": "Calvin Bassey",
                    "nationality": "Nigeria",
                    "nationality_code": "NG",
                    "date_of_birth": "1999-12-31",
                    "primary_position": "Centre-Back",
                    "current_real_world_club": "Fulham",
                    "current_real_world_league": "Premier League",
                    "competition_level": "elite",
                    "appearances": 30,
                    "minutes_played": 2550,
                    "goals": 1,
                    "assists": 2,
                    "clean_sheets": 11,
                    "current_market_reference_value": 22000000,
                    "market_reference_currency": "EUR",
                }
            ],
        )

        batch = service.run_batch(
            actor_user_id=None,
            payload=RealPlayerImportBatchRunRequest(
                manifest_path=str(manifest_path),
                mode="write",
            ),
        )

        assert batch.status == "completed_with_errors"
        assert batch.failed_row_count == 1
        issues = service.list_unresolved_issues(batch_id=batch.id)
        assert [issue.issue_type for issue in issues] == ["ambiguous_match"]
        assert issues[0].source_player_key == "bassey-001"
    finally:
        engine.dispose()


def test_resume_batch_reuses_stored_rows_after_ambiguity_is_resolved(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path / "ops-resume.db")
    engine = _initialize_database(database_url)
    service = _service(database_url, engine)
    try:
        with _session_factory(engine)() as session:
            country = Country(
                source_provider="test-source",
                provider_external_id="NG",
                name="Nigeria",
                alpha2_code="NG",
            )
            session.add(country)
            session.flush()
            first = Player(
                source_provider="legacy-a",
                provider_external_id="bassey-a",
                full_name="Calvin Bassey",
                country=country,
                position="Centre-Back",
                normalized_position="defender",
                date_of_birth=date(1999, 12, 31),
            )
            second = Player(
                source_provider="legacy-b",
                provider_external_id="bassey-b",
                full_name="Calvin Bassey",
                country=country,
                position="Centre-Back",
                normalized_position="defender",
                date_of_birth=date(1999, 12, 31),
            )
            session.add_all([first, second])
            session.commit()
            duplicate_id = second.id

        manifest_path = _write_manifest(
            tmp_path,
            "ops-resume-batch",
            [
                {
                    "source_name": "curated-feed",
                    "source_player_key": "bassey-001",
                    "canonical_name": "Calvin Bassey",
                    "nationality": "Nigeria",
                    "nationality_code": "NG",
                    "date_of_birth": "1999-12-31",
                    "primary_position": "Centre-Back",
                    "current_real_world_club": "Fulham",
                    "current_real_world_league": "Premier League",
                    "competition_level": "elite",
                    "appearances": 30,
                    "minutes_played": 2550,
                    "goals": 1,
                    "assists": 2,
                    "clean_sheets": 11,
                    "current_market_reference_value": 22000000,
                    "market_reference_currency": "EUR",
                }
            ],
        )

        blocked_batch = service.run_batch(
            actor_user_id=None,
            payload=RealPlayerImportBatchRunRequest(
                manifest_path=str(manifest_path),
                mode="write",
            ),
        )
        assert blocked_batch.status == "completed_with_errors"

        with _session_factory(engine)() as session:
            session.delete(session.get(Player, duplicate_id))
            session.commit()

        resumed_batch = service.resume_batch(
            batch_id=blocked_batch.id,
            actor_user_id=None,
            payload=RealPlayerImportBatchResumeRequest(mode="write"),
        )

        assert resumed_batch.status == "completed"
        assert resumed_batch.authoritative_snapshot_count == 1
        with _session_factory(engine)() as session:
            assert session.scalar(select(func.count()).select_from(RealPlayerImportBatch)) == 1
            assert session.scalar(select(func.count()).select_from(RealPlayerImportRow)) == 1
            assert session.scalar(select(func.count()).select_from(RealPlayerProfile)) == 1
    finally:
        engine.dispose()


def test_valuation_status_reports_clean_write_batches(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path / "ops-valuation.db")
    engine = _initialize_database(database_url)
    service = _service(database_url, engine)
    try:
        manifest_path = _write_manifest(tmp_path, "ops-valuation-batch", _sample_players())

        batch = service.run_batch(
            actor_user_id=None,
            payload=RealPlayerImportBatchRunRequest(
                manifest_path=str(manifest_path),
                mode="write",
            ),
        )
        valuation_status = service.get_valuation_status(batch_id=batch.id)

        assert batch.status == "completed"
        assert valuation_status.total_rows == 2
        assert valuation_status.imported_row_count == 2
        assert valuation_status.tracked_authoritative_snapshot_count == 2
        assert valuation_status.persisted_pricing_issue_count == 0
        assert valuation_status.audit_clean is True
    finally:
        engine.dispose()
