from __future__ import annotations

import json
import os
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import load_settings
from app.core.database import load_model_modules
from app.ingestion.models import Club, Competition, Country, Player
from app.ingestion.real_player_bulk_ops_service import RealPlayerBulkImportOpsService
from app.ingestion.real_player_import_models import (
    RealPlayerImportProcessingState,
    RealPlayerImportRun,
    RealPlayerImportStagingRecord,
)
from app.models.base import Base
from app.models.real_player_reference_mapping import RealPlayerUnresolvedReference


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "real_player_bulk_import_sample.json"


def _database_url() -> str:
    return "sqlite+pysqlite:///:memory:"


def _session_factory():
    load_model_modules()
    engine = create_engine(
        _database_url(),
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _settings():
    return load_settings(
        environ={
            **os.environ,
            "GTE_DATABASE_URL": _database_url(),
            "GTE_REAL_PLAYER_MAPPING_AUTO_CREATE_MISSING_ENTITIES": "0",
        }
    )


def _service(session_factory) -> RealPlayerBulkImportOpsService:
    return RealPlayerBulkImportOpsService(
        session_factory=session_factory,
        settings=_settings(),
    )


def _seed_canonical_entities(session) -> None:
    nigeria = Country(
        source_provider="seed",
        provider_external_id="NG",
        name="Nigeria",
        alpha2_code="NG",
        confederation_code="CAF",
        market_region="africa",
    )
    england = Country(
        source_provider="seed",
        provider_external_id="ENG",
        name="England",
        alpha2_code="GB",
        alpha3_code="ENG",
        fifa_code="ENG",
        confederation_code="UEFA",
        market_region="europe",
    )
    turkey = Country(
        source_provider="seed",
        provider_external_id="TR",
        name="Turkey",
        alpha2_code="TR",
        confederation_code="UEFA",
        market_region="europe",
    )
    germany = Country(
        source_provider="seed",
        provider_external_id="DE",
        name="Germany",
        alpha2_code="DE",
        confederation_code="UEFA",
        market_region="europe",
    )
    premier_league = Competition(
        source_provider="seed",
        provider_external_id="premier-league",
        country=england,
        name="Premier League",
        slug="premier-league",
        competition_type="league",
        format_type="real_world",
        is_major=True,
        is_tradable=True,
    )
    super_lig = Competition(
        source_provider="seed",
        provider_external_id="super-lig",
        country=turkey,
        name="Super Lig",
        slug="super-lig",
        competition_type="league",
        format_type="real_world",
        is_major=True,
        is_tradable=True,
    )
    bundesliga = Competition(
        source_provider="seed",
        provider_external_id="bundesliga",
        country=germany,
        name="Bundesliga",
        slug="bundesliga",
        competition_type="league",
        format_type="real_world",
        is_major=True,
        is_tradable=True,
    )
    session.add_all([nigeria, england, turkey, germany, premier_league, super_lig, bundesliga])
    session.flush()
    session.add_all(
        [
            Club(
                source_provider="seed",
                provider_external_id="fulham",
                country=england,
                current_competition=premier_league,
                name="Fulham",
                slug="fulham",
                short_name="Fulham",
                is_tradable=True,
            ),
            Club(
                source_provider="seed",
                provider_external_id="galatasaray",
                country=turkey,
                current_competition=super_lig,
                name="Galatasaray",
                slug="galatasaray",
                short_name="Galatasaray",
                is_tradable=True,
            ),
            Club(
                source_provider="seed",
                provider_external_id="hoffenheim",
                country=germany,
                current_competition=bundesliga,
                name="TSG Hoffenheim",
                slug="tsg-hoffenheim",
                short_name="Hoffenheim",
                is_tradable=True,
            ),
        ]
    )
    session.commit()


def _write_fixture_copy(tmp_path: Path) -> Path:
    target = tmp_path / "bulk-import.json"
    target.write_text(FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def _write_rows(tmp_path: Path, name: str, rows: list[dict[str, object]]) -> Path:
    target = tmp_path / name
    target.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return target


def test_bulk_ops_end_to_end_sample_run_in_batches(tmp_path: Path) -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            _seed_canonical_entities(session)

        service = _service(session_factory)
        import_path = _write_fixture_copy(tmp_path)
        imported = service.import_file(
            file_path=str(import_path),
            provider_name="bulk-fixture",
            batch_size=2,
        )

        assert imported.run is not None
        assert imported.run.status == "completed"
        assert imported.run.inserted_rows == 4
        assert imported.run.mapped_ready_rows == 4
        assert imported.run.mapped_partial_rows == 0
        assert imported.run.publish_ready_rows == 4
        assert imported.details_json["batch_count"] == 2

        dry_run = service.publish_ready_players(
            run_id=imported.run.id,
            limit=2,
            priority_bucket="high",
            dry_run=True,
        )
        assert dry_run.run is not None
        assert dry_run.details_json["would_publish_rows"] == 2

        published = service.publish_ready_players(
            run_id=imported.run.id,
            limit=2,
            priority_bucket="high",
        )
        assert published.run is not None
        assert published.details_json["published_now"] == 2
        assert published.run.published_rows == 2
        assert published.run.publish_ready_rows == 2

        report = service.report_run(run_id=imported.run.id)
        assert report.run is not None
        assert report.run.processing_state_distribution["published"] == 2
        assert report.run.processing_state_distribution["mapped_ready"] == 2
        assert report.run.mapped_ready_rows == 2
        assert report.run.mapped_partial_rows == 0
    finally:
        engine.dispose()


def test_bulk_ops_resume_after_interruption_keeps_completed_batches(tmp_path: Path) -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            _seed_canonical_entities(session)

        import_path = _write_fixture_copy(tmp_path)
        broken_rows = json.loads(import_path.read_text(encoding="utf-8"))
        del broken_rows[2]["provider_player_id"]
        import_path.write_text(json.dumps(broken_rows, indent=2), encoding="utf-8")

        service = _service(session_factory)
        first = service.import_file(
            file_path=str(import_path),
            provider_name="bulk-fixture",
            batch_size=2,
        )
        assert first.run is not None
        assert first.run.status == "partial"
        assert first.run.processed_rows == 2
        assert first.run.resume_cursor == "2"

        with session_factory() as session:
            staged_count = session.query(RealPlayerImportStagingRecord).count()
            assert staged_count == 2

        fixed_rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        import_path.write_text(json.dumps(fixed_rows, indent=2), encoding="utf-8")

        resumed = service.resume_import(
            run_id=first.run.id,
            batch_size=2,
        )
        assert resumed.run is not None
        assert resumed.run.status == "completed"
        assert resumed.run.processed_rows == 4
        assert resumed.run.inserted_rows == 4

        with session_factory() as session:
            staged_count = session.query(RealPlayerImportStagingRecord).count()
            assert staged_count == 4
    finally:
        engine.dispose()


def test_bulk_ops_publish_excludes_partial_rows(tmp_path: Path) -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            _seed_canonical_entities(session)

        import_path = _write_fixture_copy(tmp_path)
        rows = json.loads(import_path.read_text(encoding="utf-8"))
        rows[1]["current_real_world_club"] = "Unknown FC"
        rows[1]["current_real_world_club_key"] = "unknown-fc"
        rows[1]["current_real_world_league"] = "Unknown League"
        rows[1]["current_real_world_league_key"] = "unknown-league"
        import_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

        service = _service(session_factory)
        imported = service.import_file(
            file_path=str(import_path),
            provider_name="bulk-fixture",
            batch_size=4,
        )
        assert imported.run is not None
        assert imported.run.status == "completed_with_errors"
        assert imported.run.mapped_partial_rows == 1
        assert imported.run.publish_ready_rows == 3
        assert imported.run.unresolved_rows == 1

        published = service.publish_ready_players(
            run_id=imported.run.id,
            limit=10,
            priority_bucket="high",
        )
        assert published.run is not None
        assert published.details_json["published_now"] == 1

        report = service.report_run(run_id=imported.run.id)
        assert report.run is not None
        assert report.run.published_rows == 1
        assert report.run.unresolved_rows == 1
        assert report.run.mapped_partial_rows == 1
        assert report.run.processing_state_distribution["mapped_partial"] == 1
        with session_factory() as session:
            unresolved = list(
                session.scalars(
                    select(RealPlayerUnresolvedReference).where(
                        RealPlayerUnresolvedReference.source_name == "bulk-fixture"
                    )
                )
            )
            assert any(item.entity_type == "club" for item in unresolved)
    finally:
        engine.dispose()


def test_bulk_ops_second_run_is_idempotent(tmp_path: Path) -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            _seed_canonical_entities(session)

        service = _service(session_factory)
        import_path = _write_fixture_copy(tmp_path)
        first = service.import_file(
            file_path=str(import_path),
            provider_name="bulk-fixture",
            batch_size=3,
        )
        second = service.import_file(
            file_path=str(import_path),
            provider_name="bulk-fixture",
            batch_size=3,
        )

        assert first.run is not None
        assert second.run is not None
        assert first.run.inserted_rows == 4
        assert second.run.inserted_rows == 0
        assert second.run.updated_rows == 0
        assert second.run.duplicate_skipped_rows == 4
    finally:
        engine.dispose()


def test_bulk_ops_reporting_counts_stay_consistent(tmp_path: Path) -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            _seed_canonical_entities(session)

        service = _service(session_factory)
        import_path = _write_fixture_copy(tmp_path)
        imported = service.import_file(
            file_path=str(import_path),
            provider_name="bulk-fixture",
            batch_size=2,
        )
        assert imported.run is not None
        service.publish_ready_players(
            run_id=imported.run.id,
            limit=2,
            priority_bucket="high",
        )
        report = service.report_run(run_id=imported.run.id)
        assert report.run is not None

        distribution = report.run.processing_state_distribution
        unresolved_total = sum(
            distribution.get(state, 0)
            for state in (
                RealPlayerImportProcessingState.PENDING.value,
                RealPlayerImportProcessingState.NORMALIZED.value,
                RealPlayerImportProcessingState.MAPPED_PARTIAL.value,
            )
        )
        failed_total = sum(
            distribution.get(state, 0)
            for state in (
                RealPlayerImportProcessingState.ERROR.value,
                RealPlayerImportProcessingState.REJECTED.value,
            )
        )

        assert report.run.inserted_rows + report.run.updated_rows + report.run.duplicate_skipped_rows == report.run.processed_rows
        assert report.run.mapped_rows == report.run.publish_ready_rows + report.run.published_rows
        assert report.run.unresolved_rows == unresolved_total
        assert report.run.failed_rows == failed_total
        assert report.run.mapped_partial_rows == distribution.get(RealPlayerImportProcessingState.MAPPED_PARTIAL.value, 0)
        assert report.run.mapped_ready_rows == report.run.publish_ready_rows
    finally:
        engine.dispose()


def test_bulk_ops_applies_fallback_valuation_when_source_value_is_missing(tmp_path: Path) -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            _seed_canonical_entities(session)

        rows = [
            {
                "provider_player_id": "fallback-001",
                "canonical_name": "Fallback Forward",
                "nationality": "Nigeria",
                "nationality_code": "NG",
                "date_of_birth": "2005-04-10",
                "primary_position": "Striker",
                "current_real_world_club": "Fulham",
                "current_real_world_club_key": "fulham",
                "current_real_world_league": "Premier League",
                "current_real_world_league_key": "premier-league",
                "competition_level": "elite",
                "appearances": 18,
                "minutes_played": 1220,
                "goals": 9,
                "assists": 2,
                "priority_bucket": "default",
            }
        ]
        import_path = _write_rows(tmp_path, "fallback.json", rows)

        service = _service(session_factory)
        imported = service.import_file(
            file_path=str(import_path),
            provider_name="bulk-fixture",
            batch_size=1,
        )

        assert imported.run is not None
        assert imported.run.status == "completed"
        assert imported.run.publish_ready_rows == 1
        assert imported.run.mapped_ready_rows == 1

        with session_factory() as session:
            record = session.scalar(
                select(RealPlayerImportStagingRecord).where(
                    RealPlayerImportStagingRecord.provider_player_id == "fallback-001"
                )
            )
            assert record is not None
            assert record.processing_state == RealPlayerImportProcessingState.MAPPED_READY.value
            valuation = dict((record.metadata_json or {}).get("valuation") or {})
            assert valuation["source"] == "fallback"
            assert valuation["fallback_used"] is True
            assert float(valuation["market_value_eur"]) > 0
    finally:
        engine.dispose()


def test_bulk_ops_repair_mappings_can_promote_partial_rows_to_publish_ready(tmp_path: Path) -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            _seed_canonical_entities(session)

        import_path = _write_fixture_copy(tmp_path)
        rows = json.loads(import_path.read_text(encoding="utf-8"))
        rows[1]["current_real_world_club"] = "Unknown FC"
        rows[1]["current_real_world_club_key"] = "unknown-fc"
        rows[1]["current_real_world_league"] = "Unknown League"
        rows[1]["current_real_world_league_key"] = "unknown-league"
        import_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

        service = _service(session_factory)
        imported = service.import_file(
            file_path=str(import_path),
            provider_name="bulk-fixture",
            batch_size=4,
        )

        assert imported.run is not None
        assert imported.run.unresolved_rows == 1
        assert imported.run.publish_ready_rows == 3

        with session_factory() as session:
            england = session.scalar(select(Country).where(Country.name == "England"))
            assert england is not None
            unknown_league = Competition(
                source_provider="bulk-fixture",
                provider_external_id="unknown-league",
                country=england,
                name="Unknown League",
                slug="unknown-league",
                competition_type="league",
                format_type="real_world",
                is_tradable=True,
            )
            session.add(unknown_league)
            session.flush()
            session.add(
                Club(
                    source_provider="bulk-fixture",
                    provider_external_id="unknown-fc",
                    country=england,
                    current_competition=unknown_league,
                    name="Unknown FC",
                    slug="unknown-fc",
                    short_name="Unknown FC",
                    is_tradable=True,
                )
            )
            session.commit()

        repaired = service.repair_mappings(run_id=imported.run.id)
        report = service.report_run(run_id=imported.run.id)

        assert repaired.details_json["transitioned_ready_rows"] == 1
        assert repaired.details_json["remaining_unresolved_rows"] == 0
        assert report.run is not None
        assert report.run.publish_ready_rows == 4
        assert report.run.mapped_partial_rows == 0
        assert report.run.unresolved_rows == 0
    finally:
        engine.dispose()


def test_bulk_ops_priority_selector_supports_reason_based_publish_filters(tmp_path: Path) -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            _seed_canonical_entities(session)

        rows = [
            {
                "provider_player_id": "wonderkid-001",
                "canonical_name": "Wonderkid One",
                "nationality": "Nigeria",
                "nationality_code": "NG",
                "date_of_birth": "2007-01-14",
                "primary_position": "Striker",
                "current_real_world_club": "Fulham",
                "current_real_world_club_key": "fulham",
                "current_real_world_league": "Premier League",
                "current_real_world_league_key": "premier-league",
                "competition_level": "elite",
                "appearances": 14,
                "minutes_played": 940,
                "goals": 7,
                "current_market_reference_value": 8000000,
                "market_reference_currency": "EUR",
                "priority_bucket": "default",
            },
            {
                "provider_player_id": "veteran-001",
                "canonical_name": "Veteran Two",
                "nationality": "Nigeria",
                "nationality_code": "NG",
                "date_of_birth": "1996-03-20",
                "primary_position": "Midfielder",
                "current_real_world_club": "Fulham",
                "current_real_world_club_key": "fulham",
                "current_real_world_league": "Premier League",
                "current_real_world_league_key": "premier-league",
                "competition_level": "elite",
                "appearances": 29,
                "minutes_played": 2240,
                "goals": 4,
                "assists": 8,
                "current_market_reference_value": 15000000,
                "market_reference_currency": "EUR",
                "priority_bucket": "default",
            },
        ]
        import_path = _write_rows(tmp_path, "priority.json", rows)

        service = _service(session_factory)
        imported = service.import_file(
            file_path=str(import_path),
            provider_name="bulk-fixture",
            batch_size=2,
        )
        assert imported.run is not None
        assert imported.run.publish_ready_rows == 2

        dry_run = service.publish_ready_players(
            run_id=imported.run.id,
            limit=10,
            priority_bucket="wonderkid",
            dry_run=True,
        )

        assert dry_run.details_json["selected_rows"] == 1
        assert dry_run.details_json["selected_source_keys"] == ["bulk-fixture:wonderkid-001"]
        assert dry_run.details_json["would_publish_rows"] == 1

        with session_factory() as session:
            record = session.scalar(
                select(RealPlayerImportStagingRecord).where(
                    RealPlayerImportStagingRecord.provider_player_id == "wonderkid-001"
                )
            )
            assert record is not None
            priority = dict((record.metadata_json or {}).get("publish_priority") or {})
            assert "wonderkid" in set(priority.get("reasons") or [])
            assert "nigeria_priority" in set(priority.get("reasons") or [])
    finally:
        engine.dispose()
