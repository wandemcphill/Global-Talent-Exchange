from __future__ import annotations

from contextlib import redirect_stdout
from datetime import UTC, date, datetime
from io import StringIO
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.ingestion.models  # noqa: F401
import app.ingestion.real_player_import_models  # noqa: F401
import app.models.player_import  # noqa: F401
import app.models.real_player_import_batch  # noqa: F401
import app.models.real_player_profile  # noqa: F401
import app.models.real_player_reference_mapping  # noqa: F401
import app.models.real_player_source_link  # noqa: F401
import app.players.read_models  # noqa: F401
import app.value_engine.read_models  # noqa: F401
from app.ingestion.models import Player, ProviderSyncRun
from app.ingestion.real_player_import_models import RealPlayerImportStagingRecord
from app.ingestion.real_player_import_repository import RealPlayerImportRepository
from app.ingestion.real_player_import_validation import RealPlayerImportValidationService
from app.ingestion.real_player_normalization_service import RealPlayerNormalizationService
from app.models.base import Base
from app.models.real_player_import_batch import RealPlayerImportBatch, RealPlayerImportRow
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_reference_mapping import RealPlayerUnresolvedReference
from app.models.real_player_source_link import RealPlayerSourceLink
from app.players.read_models import PlayerSummaryReadModel
from app.providers.import_models import RealPlayerSourceItem
from app.schemas.real_player_ingestion import RealPlayerSeedInput
from app.value_engine.read_models import PlayerValueSnapshotRecord
try:
    from backend.scripts.validate_real_player_import import main as validate_real_player_import_main
except ModuleNotFoundError:
    from scripts.validate_real_player_import import main as validate_real_player_import_main


def _session_factory(database_url: str = "sqlite+pysqlite:///:memory:"):
    engine_kwargs = {"connect_args": {"check_same_thread": False}}
    if database_url.endswith(":memory:"):
        engine_kwargs["poolclass"] = StaticPool
    engine = create_engine(database_url, **engine_kwargs)
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _seed_sync_run(session, *, run_id: str) -> ProviderSyncRun:
    run = ProviderSyncRun(
        id=run_id,
        provider_name="mock",
        job_name="real_player_directory_import",
        entity_type="real_player_directory",
        status="running",
    )
    session.add(run)
    session.flush()
    return run


def _seed_validation_batch(session) -> RealPlayerImportBatch:
    as_of = datetime(2026, 3, 22, 12, 0, tzinfo=UTC)
    batch = RealPlayerImportBatch(
        batch_key="phase-a-batch-001",
        provider_name="curated-feed",
        provider_job_key="job-001",
        source_type="provider_feed",
        mode="batch_import",
        status="completed_with_errors",
        submitted_row_count=3,
        normalized_row_count=3,
        created_player_count=2,
        failed_row_count=1,
        authoritative_snapshot_count=1,
    )
    session.add(batch)
    session.flush()

    player_a = Player(
        id="player-real-a",
        source_provider="curated-feed",
        provider_external_id="osimhen-001",
        full_name="Victor Osimhen",
        canonical_display_name="Victor Osimhen",
        normalized_position="forward",
        is_real_player=True,
        is_tradable=True,
    )
    player_b = Player(
        id="player-real-b",
        source_provider="curated-feed",
        provider_external_id="osimhen-duplicate-001",
        full_name="Victor Osimhen",
        canonical_display_name="Victor Osimhen",
        normalized_position="forward",
        is_real_player=True,
        is_tradable=True,
    )
    session.add_all([player_a, player_b])
    session.flush()

    source_link_a = RealPlayerSourceLink(
        id="source-link-a",
        gtex_player_id=player_a.id,
        source_name="curated-feed",
        source_player_key="osimhen-001",
        canonical_name="Victor Osimhen",
        identity_confidence_score=0.98,
    )
    source_link_b = RealPlayerSourceLink(
        id="source-link-b",
        gtex_player_id=player_b.id,
        source_name="curated-feed",
        source_player_key="osimhen-duplicate-001",
        canonical_name="Victor Osimhen",
        identity_confidence_score=0.81,
    )
    session.add_all([source_link_a, source_link_b])
    session.flush()

    snapshot = PlayerValueSnapshotRecord(
        id="snapshot-a",
        player_id=player_a.id,
        player_name=player_a.full_name,
        as_of=as_of,
        snapshot_type="intraday",
        previous_credits=610.0,
        target_credits=620.0,
        movement_pct=1.64,
        football_truth_value_credits=615.0,
        market_signal_value_credits=5.0,
        scouting_signal_value_credits=0.0,
        egame_signal_value_credits=0.0,
        confidence_score=0.95,
        confidence_tier="high",
        liquidity_tier="default",
        market_integrity_score=0.98,
        signal_trust_score=0.97,
        trend_7d_pct=2.0,
        trend_30d_pct=4.0,
        trend_direction="up",
        trend_confidence=0.89,
        config_version="baseline-v1",
        breakdown_json={"published_card_value_credits": 620.0},
        drivers_json=["real_player_ingestion"],
        reason_codes_json=["authoritative_snapshot"],
    )
    session.add(snapshot)
    session.flush()

    profile_a = RealPlayerProfile(
        id="profile-a",
        gtex_player_id=player_a.id,
        source_link_id=source_link_a.id,
        source_name="curated-feed",
        source_player_key="osimhen-001",
        canonical_name="Victor Osimhen",
        ingestion_batch_id=batch.batch_key,
        pricing_snapshot_id=snapshot.id,
        normalized_signals_json={"seed": "a"},
        metadata_json={},
    )
    profile_b = RealPlayerProfile(
        id="profile-b",
        gtex_player_id=player_b.id,
        source_link_id=source_link_b.id,
        source_name="curated-feed",
        source_player_key="osimhen-duplicate-001",
        canonical_name="Victor Osimhen",
        ingestion_batch_id=batch.batch_key,
        pricing_snapshot_id=None,
        normalized_signals_json={"seed": "b"},
        metadata_json={},
    )
    session.add_all([profile_a, profile_b])
    session.flush()

    summary = PlayerSummaryReadModel(
        player_id=player_a.id,
        player_name=player_a.full_name,
        current_club_name="Galatasaray",
        last_snapshot_id=snapshot.id,
        last_snapshot_at=as_of,
        current_value_credits=620.0,
        previous_value_credits=610.0,
        movement_pct=1.64,
        average_rating=7.4,
        market_interest_score=10,
        summary_json={"real_player_profile": {"pricing_snapshot_id": snapshot.id}},
    )
    session.add(summary)
    session.flush()

    session.add_all(
        [
            RealPlayerImportRow(
                id="row-1",
                batch_id=batch.id,
                row_number=1,
                source_name="curated-feed",
                source_player_key="osimhen-001",
                canonical_name="Victor Osimhen",
                status="imported",
                match_action="create_new",
                import_action="created",
                identity_confidence_score=0.98,
                gtex_player_id=player_a.id,
                source_link_id=source_link_a.id,
                real_player_profile_id=profile_a.id,
                authoritative_snapshot_id=snapshot.id,
                normalized_full_name="victor osimhen",
                normalized_display_name="victor osimhen",
                exact_identity_key="victor_osimhen_1998_ng",
                name_birthyear_nationality_key="victor_osimhen_1998_ng",
                nationality_code="NG",
                normalized_nationality="nigeria",
                primary_position_key="striker",
                raw_payload_json={
                    "canonical_name": "Victor Osimhen",
                    "date_of_birth": "1998-12-29",
                    "nationality": "Nigeria",
                    "primary_position": "Striker",
                },
                normalized_payload_json={"birth_year": 1998},
                import_metadata_json={"ingestion_batch_id": batch.batch_key},
                validation_errors_json=[],
                audit_findings_json=[],
            ),
            RealPlayerImportRow(
                id="row-2",
                batch_id=batch.id,
                row_number=2,
                source_name="curated-feed",
                source_player_key="osimhen-duplicate-001",
                canonical_name="Victor Osimhen",
                status="imported",
                match_action="matched_existing",
                import_action="updated",
                identity_confidence_score=0.81,
                gtex_player_id=player_b.id,
                source_link_id=source_link_b.id,
                real_player_profile_id=profile_b.id,
                authoritative_snapshot_id=None,
                normalized_full_name="victor osimhen",
                normalized_display_name="victor osimhen",
                exact_identity_key="victor_osimhen_1998_ng",
                name_birthyear_nationality_key="victor_osimhen_1998_ng",
                nationality_code="NG",
                normalized_nationality="nigeria",
                primary_position_key="striker",
                raw_payload_json={
                    "canonical_name": "Victor Osimhen",
                    "date_of_birth": "1998-12-29",
                    "nationality": "Nigeria",
                    "primary_position": "Striker",
                },
                normalized_payload_json={"birth_year": 1998},
                import_metadata_json={"ingestion_batch_id": batch.batch_key},
                validation_errors_json=[],
                audit_findings_json=[],
            ),
            RealPlayerImportRow(
                id="row-3",
                batch_id=batch.id,
                row_number=3,
                source_name="curated-feed",
                source_player_key="mystery-001",
                canonical_name="Mystery Player",
                status="failed",
                match_action=None,
                import_action=None,
                identity_confidence_score=None,
                gtex_player_id=None,
                source_link_id=None,
                real_player_profile_id=None,
                authoritative_snapshot_id=None,
                normalized_full_name=None,
                normalized_display_name=None,
                exact_identity_key=None,
                name_birthyear_club_key=None,
                name_birthyear_nationality_key=None,
                nationality_code=None,
                normalized_nationality=None,
                primary_position_key=None,
                club_reference_key="mystery-fc",
                league_reference_key="unknown-super-league",
                raw_payload_json={"canonical_name": "Mystery Player"},
                normalized_payload_json={},
                import_metadata_json={"ingestion_batch_id": batch.batch_key},
                validation_errors_json=["missing birth year"],
                audit_findings_json=[],
            ),
            RealPlayerUnresolvedReference(
                id="unresolved-club",
                source_name="curated-feed",
                entity_type="club",
                provider_reference_key="mystery-fc",
                raw_label="Mystery FC",
                normalized_label="mystery fc",
                reason_code="club_not_mapped",
                status="open",
                occurrence_count=1,
                first_seen_at=as_of,
                last_seen_at=as_of,
                sample_payload_json={},
                metadata_json={},
            ),
            RealPlayerUnresolvedReference(
                id="unresolved-competition",
                source_name="curated-feed",
                entity_type="competition",
                provider_reference_key="unknown-super-league",
                raw_label="Unknown Super League",
                normalized_label="unknown super league",
                reason_code="competition_not_mapped",
                status="open",
                occurrence_count=1,
                first_seen_at=as_of,
                last_seen_at=as_of,
                sample_payload_json={},
                metadata_json={},
            ),
        ]
    )
    session.commit()
    return batch


def test_real_player_import_repository_is_idempotent_for_identical_payloads() -> None:
    engine, factory = _session_factory()
    try:
        with factory() as session:
            _seed_sync_run(session, run_id="run-001")
            repository = RealPlayerImportRepository(session)
            items = [
                RealPlayerSourceItem(
                    provider_player_id="p-osimhen",
                    full_name="Victor Osimhen",
                    short_name="V. Osimhen",
                    display_position="Striker",
                    nationality_name="Nigeria",
                    nationality_code="NG",
                    current_club_name="Galatasaray",
                    current_competition_name="Super Lig",
                    raw_payload={"provider_player_id": "p-osimhen", "club": "Galatasaray"},
                ),
                RealPlayerSourceItem(
                    provider_player_id="p-iwobi",
                    full_name="Alex Iwobi",
                    short_name="A. Iwobi",
                    display_position="Winger",
                    nationality_name="Nigeria",
                    nationality_code="NG",
                    current_club_name="Fulham",
                    current_competition_name="Premier League",
                    raw_payload={"provider_player_id": "p-iwobi", "club": "Fulham"},
                ),
            ]

            first = repository.upsert_staging_records(
                provider_name="mock",
                items=items,
                source_version="v1",
                last_import_run_id="run-001",
                last_import_cursor="2",
            )
            second = repository.upsert_staging_records(
                provider_name="mock",
                items=items,
                source_version="v1",
                last_import_run_id="run-001",
                last_import_cursor="2",
            )
            third = repository.upsert_staging_records(
                provider_name="mock",
                items=[
                    RealPlayerSourceItem(
                        provider_player_id="p-osimhen",
                        full_name="Victor Osimhen",
                        short_name="V. Osimhen",
                        display_position="Striker",
                        nationality_name="Nigeria",
                        nationality_code="NG",
                        current_club_name="Galatasaray Updated",
                        current_competition_name="Super Lig",
                        raw_payload={"provider_player_id": "p-osimhen", "club": "Galatasaray Updated"},
                    )
                ],
                source_version="v2",
                last_import_run_id="run-001",
                last_import_cursor="3",
            )

            assert first.inserted_count == 2
            assert first.updated_count == 0
            assert first.skipped_count == 0
            assert second.inserted_count == 0
            assert second.updated_count == 0
            assert second.skipped_count == 2
            assert third.inserted_count == 0
            assert third.updated_count == 1
            assert third.skipped_count == 0

            assert session.scalar(select(func.count()).select_from(RealPlayerImportStagingRecord)) == 2
    finally:
        engine.dispose()


def test_real_player_seed_input_dedupes_aliases_and_normalization_is_stable() -> None:
    payload = RealPlayerSeedInput.model_validate(
        {
            "source_name": "curated-feed",
            "source_player_key": "osimhen-001",
            "canonical_name": "Victor Osimhen",
            "known_aliases": [" V. Osimhen ", "v. osimhen", "Victor Osimhen"],
            "nationality": "Nigeria",
            "date_of_birth": "1998-12-29",
            "primary_position": "centre forward",
            "secondary_positions": ["Winger", "winger", " Striker "],
            "competition_level": "Champions League",
            "minutes_played": 2410,
            "goals": 19,
            "assists": 4,
            "current_market_reference_value": 60000000,
            "market_reference_currency": "eur",
        }
    )

    normalized = RealPlayerNormalizationService().normalize(
        payload,
        as_of=datetime(2026, 3, 22, 12, 0, tzinfo=UTC),
    )

    assert payload.known_aliases == ["V. Osimhen", "Victor Osimhen"]
    assert payload.secondary_positions == ["Winger", "Striker"]
    assert normalized.primary_position == "Striker"
    assert normalized.secondary_positions == ("Winger",)
    assert normalized.normalized_position == "forward"
    assert normalized.competition_level == "elite"
    assert normalized.market_reference_currency == "EUR"
    assert normalized.reference_market_value_eur == 60000000.0


def test_validation_service_summarizes_duplicate_mapping_and_valuation_gaps() -> None:
    engine, factory = _session_factory()
    try:
        with factory() as session:
            batch = _seed_validation_batch(session)

        report = RealPlayerImportValidationService(session_factory=factory).run(batch_key=batch.batch_key)

        assert report.batch_key == "phase-a-batch-001"
        assert report.imported_row_count == 2
        assert report.unique_player_count == 2
        assert report.rows_by_status == {"failed": 1, "imported": 2}
        assert report.verdict == "fail"

        assert len(report.duplicate_candidates) == 2
        assert report.duplicate_candidates[0].identity_key == "victor_osimhen_1998_ng"
        assert report.duplicate_candidates[0].row_count == 2

        unresolved = {(item.entity_type, item.provider_reference_key): item.reason_code for item in report.unresolved_references}
        assert unresolved == {
            ("club", "mystery-fc"): "club_not_mapped",
            ("competition", "unknown-super-league"): "competition_not_mapped",
        }

        assert len(report.missing_required_fields) == 1
        assert report.missing_required_fields[0].source_player_key == "mystery-001"
        assert set(report.missing_required_fields[0].missing_fields) == {
            "normalized_name",
            "birth_reference",
            "nationality",
            "primary_position",
        }

        assert report.valuation_coverage.imported_row_count == 2
        assert report.valuation_coverage.rows_with_snapshot_id == 1
        assert report.valuation_coverage.rows_with_persisted_snapshot == 1
        assert report.valuation_coverage.profiles_with_snapshot_id == 1
        assert report.valuation_coverage.profiles_with_matching_snapshot == 1
        assert report.valuation_coverage.summaries_with_current_value == 1
        assert report.valuation_coverage.rows_missing_valuation == ("curated-feed:osimhen-duplicate-001",)
    finally:
        engine.dispose()


def test_validation_service_matches_provider_keyed_unresolved_references() -> None:
    engine, factory = _session_factory()
    as_of = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    try:
        with factory() as session:
            batch = RealPlayerImportBatch(
                batch_key="phase-a-footballsquads-validation",
                provider_name="footballsquads",
                provider_job_key="job-footballsquads-001",
                source_type="provider_feed",
                mode="batch_import",
                status="completed_with_errors",
                submitted_row_count=1,
                normalized_row_count=1,
                failed_row_count=1,
                authoritative_snapshot_count=0,
            )
            session.add(batch)
            session.flush()
            session.add(
                RealPlayerImportRow(
                    id="row-footballsquads-1",
                    batch_id=batch.id,
                    row_number=1,
                    source_name="footballsquads",
                    source_player_key="engprem-2023-2024-arsenal-aaron-ramsdale-1998-05-14",
                    canonical_name="Aaron Ramsdale",
                    status="failed",
                    match_action=None,
                    import_action=None,
                    identity_confidence_score=None,
                    gtex_player_id=None,
                    source_link_id=None,
                    real_player_profile_id=None,
                    authoritative_snapshot_id=None,
                    normalized_full_name="aaron ramsdale",
                    normalized_display_name="aaron ramsdale",
                    exact_identity_key=None,
                    name_birthyear_club_key=None,
                    name_birthyear_nationality_key=None,
                    nationality_code="GB",
                    normalized_nationality="england",
                    primary_position_key="goalkeeper",
                    club_reference_key="arsenal",
                    league_reference_key="english-premier-league-2023-2024",
                    raw_payload_json={
                        "canonical_name": "Aaron Ramsdale",
                        "current_real_world_club": "Arsenal",
                        "current_real_world_club_key": "engprem:arsenal",
                        "current_real_world_league": "English Premier League 2023/2024",
                        "current_real_world_league_key": "engprem-2023-2024",
                    },
                    normalized_payload_json={},
                    import_metadata_json={"ingestion_batch_id": batch.batch_key},
                    validation_errors_json=["unresolved canonical references"],
                    audit_findings_json=[],
                )
            )
            session.add_all(
                [
                    RealPlayerUnresolvedReference(
                        id="unresolved-footballsquads-club",
                        source_name="footballsquads",
                        entity_type="club",
                        provider_reference_key="engprem-arsenal",
                        provider_external_id="engprem:arsenal",
                        raw_label="Arsenal",
                        normalized_label="arsenal",
                        reason_code="club_not_found",
                        status="open",
                        occurrence_count=1,
                        first_seen_at=as_of,
                        last_seen_at=as_of,
                        sample_payload_json={},
                        metadata_json={},
                    ),
                    RealPlayerUnresolvedReference(
                        id="unresolved-footballsquads-competition",
                        source_name="footballsquads",
                        entity_type="competition",
                        provider_reference_key="engprem-2023-2024",
                        provider_external_id="engprem-2023-2024",
                        raw_label="English Premier League 2023/2024",
                        normalized_label="english premier league 2023/2024",
                        reason_code="competition_not_found",
                        status="open",
                        occurrence_count=1,
                        first_seen_at=as_of,
                        last_seen_at=as_of,
                        sample_payload_json={},
                        metadata_json={},
                    ),
                ]
            )
            session.commit()

        report = RealPlayerImportValidationService(session_factory=factory).run(batch_key=batch.batch_key)

        unresolved = {
            (item.entity_type, item.provider_reference_key): (item.reason_code, item.state, item.raw_label)
            for item in report.unresolved_references
        }
        assert unresolved == {
            ("club", "arsenal"): ("club_not_found", "tracked", "Arsenal"),
            (
                "competition",
                "english-premier-league-2023-2024",
            ): ("competition_not_found", "tracked", "English Premier League 2023/2024"),
        }
        assert all(item.state == "tracked" for item in report.unresolved_references)
    finally:
        engine.dispose()


def test_validation_cli_emits_json_and_nonzero_exit_code_for_gaps(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'validation-report.db').as_posix()}"
    engine, factory = _session_factory(database_url)
    try:
        with factory() as session:
            _seed_validation_batch(session)
    finally:
        engine.dispose()

    stdout = StringIO()
    with redirect_stdout(stdout):
        exit_code = validate_real_player_import_main(
            [
                "--database-url",
                database_url,
                "--batch-key",
                "phase-a-batch-001",
                "--json",
            ]
        )

    rendered = stdout.getvalue()
    assert exit_code == 2
    assert '"batch_key": "phase-a-batch-001"' in rendered
    assert '"verdict": "fail"' in rendered
    assert '"rows_with_persisted_snapshot": 1' in rendered
