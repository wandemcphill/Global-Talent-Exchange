from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import date

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import load_settings
from app.core.database import load_model_modules
from app.ingestion.models import Country, Player
from app.ingestion.real_player_ingestion_service import (
    RealPlayerBatchBlockedError,
    RealPlayerIngestionService,
)
from app.models.base import Base
from app.models.player_cards import PlayerMarketValueSnapshot
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_source_link import RealPlayerSourceLink
from app.players.read_models import PlayerSummaryReadModel
from app.schemas.real_player_ingestion import RealPlayerIngestionRequest
from app.value_engine.read_models import PlayerValueSnapshotRecord


def _session_factory():
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _settings():
    return load_settings(environ={**os.environ, "GTE_DATABASE_URL": "sqlite+pysqlite:///:memory:"})


def _batch_request(
    *,
    mode: str = "curated_seed",
    as_of: str = "2026-03-22T12:00:00+00:00",
    osimhen_club: str = "Launch Club A",
) -> RealPlayerIngestionRequest:
    return RealPlayerIngestionRequest.model_validate(
        {
            "mode": mode,
            "as_of": as_of,
            "ingestion_batch_id": "first-controlled-batch-test",
            "ingestion_source_version": "first-controlled-batch-v1",
            "players": [
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
                    "current_real_world_club": osimhen_club,
                    "current_real_world_league": "Launch League Elite",
                    "competition_level": "elite",
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
                    "current_real_world_club": "Launch Club B",
                    "current_real_world_league": "Launch League Premier",
                    "competition_level": "top_flight",
                    "appearances": 29,
                    "minutes_played": 2280,
                    "goals": 6,
                    "assists": 7,
                    "current_market_reference_value": 18000000,
                    "market_reference_currency": "EUR",
                },
            ],
        }
    )


def test_validate_dry_run_reports_counts_and_rolls_back() -> None:
    engine, session_factory = _session_factory()
    try:
        service = RealPlayerIngestionService(session_factory=session_factory, settings=_settings())

        report = service.validate(_batch_request())

        assert report.source_row_count == 2
        assert report.normalized_row_count == 2
        assert report.matched_existing_count == 0
        assert report.new_identity_count == 2
        assert report.ambiguous_match_count == 0
        assert report.missing_pricing_snapshot_count == 0
        assert report.hard_failure_count == 0
        assert len(report.staged_player_ids) == 2

        with session_factory() as session:
            assert session.scalar(select(func.count()).select_from(Player)) == 0
            assert session.scalar(select(func.count()).select_from(RealPlayerProfile)) == 0
            assert session.scalar(select(func.count()).select_from(RealPlayerSourceLink)) == 0
    finally:
        engine.dispose()


def test_validate_accumulates_ambiguous_matches_without_aborting() -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            nigeria = Country(
                source_provider="test-source",
                provider_external_id="NG",
                name="Nigeria",
                alpha2_code="NG",
            )
            session.add(nigeria)
            session.flush()
            session.add_all(
                [
                    Player(
                        source_provider="legacy-source",
                        provider_external_id="legacy-chukwueze-a",
                        full_name="Samuel Chukwueze",
                        canonical_display_name="Samuel Chukwueze",
                        country=nigeria,
                        position="Winger",
                        normalized_position="forward",
                        date_of_birth=date(1999, 5, 22),
                        is_real_player=True,
                    ),
                    Player(
                        source_provider="legacy-source",
                        provider_external_id="legacy-chukwueze-b",
                        full_name="Samuel Chukwueze",
                        canonical_display_name="Samuel Chukwueze",
                        country=nigeria,
                        position="Winger",
                        normalized_position="forward",
                        date_of_birth=date(1999, 5, 22),
                        is_real_player=True,
                    ),
                ]
            )
            session.commit()

        request = RealPlayerIngestionRequest.model_validate(
            {
                "mode": "curated_seed",
                "as_of": "2026-03-22T12:00:00+00:00",
                "players": [
                    {
                        "source_name": "curated-feed",
                        "source_player_key": "chukwueze-ambiguous-001",
                        "canonical_name": "Samuel Chukwueze",
                        "nationality": "Nigeria",
                        "nationality_code": "NG",
                        "date_of_birth": "1999-05-22",
                        "primary_position": "Winger",
                    },
                    {
                        "source_name": "curated-feed",
                        "source_player_key": "chukwueze-ambiguous-002",
                        "canonical_name": "Samuel Chukwueze",
                        "nationality": "Nigeria",
                        "nationality_code": "NG",
                        "date_of_birth": "1999-05-22",
                        "primary_position": "Winger",
                    },
                ],
            }
        )

        service = RealPlayerIngestionService(session_factory=session_factory, settings=_settings())
        report = service.validate(request)

        assert report.source_row_count == 2
        assert report.normalized_row_count == 2
        assert report.ambiguous_match_count == 2
        assert report.missing_pricing_snapshot_count == 0
        assert report.hard_failure_count == 0
        assert len(report.staged_player_ids) == 0
        assert [issue.issue_type for issue in report.issues] == ["ambiguous_match", "ambiguous_match"]
        assert all(len(issue.candidates) == 2 for issue in report.issues)

        with session_factory() as session:
            assert session.scalar(select(func.count()).select_from(Player)) == 2
    finally:
        engine.dispose()


def test_write_batch_aborts_before_commit_when_pricing_preview_is_missing() -> None:
    engine, session_factory = _session_factory()
    try:
        class _MissingPreviewBridge:
            def preview_player(self, _session, **_kwargs):
                return None

        service = RealPlayerIngestionService(
            session_factory=session_factory,
            value_engine_bridge=_MissingPreviewBridge(),
            settings=_settings(),
        )

        report = service.validate(_batch_request())
        assert report.missing_pricing_snapshot_count == 2
        assert report.hard_failure_count == 0

        with pytest.raises(RealPlayerBatchBlockedError) as exc:
            service.write_batch(_batch_request())

        assert exc.value.report.missing_pricing_snapshot_count == 2

        with session_factory() as session:
            assert session.scalar(select(func.count()).select_from(Player).where(Player.is_real_player.is_(True))) == 0
            assert session.scalar(select(func.count()).select_from(PlayerValueSnapshotRecord)) == 0
    finally:
        engine.dispose()


def test_write_batch_persists_authoritative_snapshots_and_passes_audit() -> None:
    engine, session_factory = _session_factory()
    try:
        service = RealPlayerIngestionService(session_factory=session_factory, settings=_settings())

        report = service.write_batch(_batch_request())

        assert report.players_processed == 2
        assert report.players_created == 2
        assert report.players_updated == 0
        assert report.identities_linked == 2
        assert report.duplicates_prevented == 0
        assert report.pricing_snapshots_resolved == 2
        assert report.avatars_assigned == 2
        assert report.agency_profiles_created_or_attached == 0
        assert report.audit is not None
        assert report.audit.all_checks_passed is True
        assert report.audit.duplicate_canonical_identity_count == 0
        assert report.audit.players_missing_authoritative_price_count == 0
        assert report.audit.players_missing_market_snapshot_count == 0
        assert report.audit.players_missing_avatar_seed_count == 0
        assert report.audit.agency_linkage_required_count == 0
        assert report.audit.agency_linkage_missing_count == 0

        with session_factory() as session:
            assert session.scalar(select(func.count()).select_from(Player).where(Player.is_real_player.is_(True))) == 2
            assert session.scalar(select(func.count()).select_from(PlayerValueSnapshotRecord)) == 2
            assert session.scalar(select(func.count()).select_from(PlayerMarketValueSnapshot)) == 2
            summary = session.scalar(
                select(PlayerSummaryReadModel)
                .join(Player, Player.id == PlayerSummaryReadModel.player_id)
                .where(Player.full_name == "Victor Osimhen")
            )
            assert summary is not None
            assert summary.summary_json["avatar_seed_token"]
            assert summary.summary_json["avatar_dna_seed"]
    finally:
        engine.dispose()


def test_write_batch_prevents_duplicates_on_refresh_existing() -> None:
    engine, session_factory = _session_factory()
    try:
        service = RealPlayerIngestionService(session_factory=session_factory, settings=_settings())

        first = service.write_batch(_batch_request())
        second = service.write_batch(
            _batch_request(
                mode="refresh_existing",
                as_of="2026-03-23T12:00:00+00:00",
                osimhen_club="Launch Club Z",
            )
        )

        assert set(first.player_ids) == set(second.player_ids)
        assert second.players_created == 0
        assert second.players_updated == 2
        assert second.duplicates_prevented == 2
        assert second.audit is not None
        assert second.audit.all_checks_passed is True
    finally:
        engine.dispose()


def test_first_controlled_batch_manifest_is_locked_to_150_players() -> None:
    manifest_path = Path("backend/data/real_player_batches/first_controlled_batch_v1.json")
    review_path = Path("backend/data/real_player_batches/first_controlled_batch_v1.review.json")

    manifest = RealPlayerIngestionRequest.model_validate(json.loads(manifest_path.read_text(encoding="utf-8")))
    review = json.loads(review_path.read_text(encoding="utf-8"))

    assert manifest.mode == "curated_seed"
    assert len(manifest.players) == 150
    assert review["batch_id"] == "first-controlled-batch-v1"
    assert review["counts"]["global_stars"] == 18
    assert review["counts"]["nigerian_core"] == 24
    assert review["counts"]["prospects"] == 45
    assert review["counts"]["fillers_total"] == 63
    assert review["counts"]["fillers_gk"] == 12
    assert review["counts"]["fillers_def"] == 18
    assert review["counts"]["fillers_mid"] == 18
    assert review["counts"]["fillers_fwd"] == 15
