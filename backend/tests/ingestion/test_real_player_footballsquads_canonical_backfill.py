from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import load_settings
from app.core.database import load_model_modules
from app.ingestion.models import Club, Competition
from app.ingestion.real_player_footballsquads_canonical_backfill import FootballsquadsCanonicalBackfillService
from app.models.base import Base
from app.models.real_player_reference_mapping import (
    RealPlayerReferenceMapping,
    RealPlayerUnresolvedReference,
)


def _session_factory():
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _seed_open_footballsquads_references(session, *, as_of: datetime) -> None:
    session.add_all(
        [
            RealPlayerUnresolvedReference(
                id="fs-competition-open",
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
            RealPlayerUnresolvedReference(
                id="fs-club-open",
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
        ]
    )
    session.commit()


def _service() -> FootballsquadsCanonicalBackfillService:
    return FootballsquadsCanonicalBackfillService(
        settings=load_settings(environ={"DATABASE_URL": "sqlite+pysqlite:///:memory:"})
    )


def test_footballsquads_backfill_is_idempotent_and_reports_resolution_counts() -> None:
    engine, session_factory = _session_factory()
    as_of = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    try:
        with session_factory() as session:
            _seed_open_footballsquads_references(session, as_of=as_of)

        service = _service()
        with session_factory() as session:
            first = service.run(session, as_of=as_of)
            session.commit()

        assert first.resolved_count == 2
        assert first.remaining_unresolved_count == 0
        assert first.resolved_counts_by_entity_type == {"club": 1, "competition": 1}
        assert first.remaining_unresolved_counts_by_entity_type == {}
        assert first.remaining_unresolved_categories == {}
        assert first.to_dict()["resolved_count"] == 2

        with session_factory() as session:
            assert session.scalar(
                select(func.count()).select_from(Competition).where(Competition.source_provider == "footballsquads")
            ) == 1
            assert session.scalar(
                select(func.count()).select_from(Club).where(Club.source_provider == "footballsquads")
            ) == 1
            assert session.scalar(
                select(func.count()).select_from(RealPlayerReferenceMapping).where(
                    RealPlayerReferenceMapping.source_name == "footballsquads"
                )
            ) == 2
            assert session.scalar(
                select(func.count()).select_from(RealPlayerUnresolvedReference).where(
                    RealPlayerUnresolvedReference.source_name == "footballsquads",
                    RealPlayerUnresolvedReference.status == "resolved",
                )
            ) == 2

        with session_factory() as session:
            second = service.run(session, as_of=as_of)
            session.commit()

        assert second.resolved_count == 0
        assert second.remaining_unresolved_count == 0
        assert second.resolved_counts_by_entity_type == {}
        assert second.remaining_unresolved_counts_by_entity_type == {}
        assert second.remaining_unresolved_categories == {}

        with session_factory() as session:
            assert session.scalar(
                select(func.count()).select_from(Competition).where(Competition.source_provider == "footballsquads")
            ) == 1
            assert session.scalar(
                select(func.count()).select_from(Club).where(Club.source_provider == "footballsquads")
            ) == 1
            assert session.scalar(
                select(func.count()).select_from(RealPlayerReferenceMapping).where(
                    RealPlayerReferenceMapping.source_name == "footballsquads"
                )
            ) == 2
    finally:
        engine.dispose()
