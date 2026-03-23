from __future__ import annotations

import os
from datetime import UTC, datetime

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import load_settings
from app.core.database import load_model_modules
from app.ingestion.models import Club, Competition
from app.ingestion.normalizers import slugify
from app.ingestion.real_player_canonical_mapping_service import RealPlayerCanonicalMappingService
from app.ingestion.real_player_footballsquads_canonical_backfill import (
    FootballsquadsCanonicalBackfillService,
)
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


def _settings():
    return load_settings(
        environ={
            **os.environ,
            "GTE_DATABASE_URL": "sqlite+pysqlite:///:memory:",
            "GTE_REAL_PLAYER_MAPPING_AUTO_CREATE_MISSING_ENTITIES": "0",
        }
    )


def _seed_unresolved_reference(
    session,
    *,
    entity_type: str,
    provider_external_id: str,
    raw_label: str,
    as_of: datetime,
    metadata_json: dict[str, object] | None = None,
    reason_code: str | None = None,
) -> RealPlayerUnresolvedReference:
    unresolved = RealPlayerUnresolvedReference(
        source_name="footballsquads",
        entity_type=entity_type,
        provider_external_id=provider_external_id,
        provider_reference_key=slugify(provider_external_id),
        raw_label=raw_label,
        normalized_label=raw_label,
        reason_code=reason_code or f"{entity_type}_not_found",
        status="open",
        occurrence_count=1,
        first_seen_at=as_of,
        last_seen_at=as_of,
        sample_payload_json={},
        metadata_json=metadata_json or {},
    )
    session.add(unresolved)
    session.flush()
    return unresolved


def test_footballsquads_backfill_resolves_provider_keyed_competition_mapping() -> None:
    engine, factory = _session_factory()
    as_of = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    try:
        with factory() as session:
            unresolved = _seed_unresolved_reference(
                session,
                entity_type="competition",
                provider_external_id="engprem-2023-2024",
                raw_label="English Premier League 2023/2024",
                as_of=as_of,
            )

            report = FootballsquadsCanonicalBackfillService(settings=_settings()).run(session, as_of=as_of)

            competition = session.scalar(select(Competition))
            mapping = session.scalar(select(RealPlayerReferenceMapping))
            resolution = RealPlayerCanonicalMappingService(settings=_settings()).resolve_competition(
                session,
                source_name="footballsquads",
                provider_external_id="engprem-2023-2024",
                name="English Premier League 2023/2024",
                as_of=as_of,
            )

            assert report.resolved_competitions[0].label == "English Premier League 2023/2024"
            assert report.remaining_unresolved_items == ()
            assert competition is not None
            assert competition.name == "Premier League"
            assert competition.slug == "premier-league"
            assert competition.source_provider == "footballsquads"
            assert competition.provider_external_id == "engprem-2023-2024"
            assert competition.current_season_external_id == "engprem-2023-2024"
            assert mapping is not None
            assert mapping.mapping_status == "resolved"
            assert mapping.provider_reference_key == "engprem-2023-2024"
            assert mapping.canonical_competition_id == competition.id
            assert resolution.status == "resolved"
            assert resolution.canonical_competition_id == competition.id
            assert unresolved.status == "resolved"
            assert unresolved.canonical_competition_id == competition.id
    finally:
        engine.dispose()


def test_footballsquads_backfill_resolves_provider_keyed_club_mapping() -> None:
    engine, factory = _session_factory()
    as_of = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    try:
        with factory() as session:
            _seed_unresolved_reference(
                session,
                entity_type="competition",
                provider_external_id="engprem-2023-2024",
                raw_label="English Premier League 2023/2024",
                as_of=as_of,
            )
            unresolved = _seed_unresolved_reference(
                session,
                entity_type="club",
                provider_external_id="engprem:arsenal",
                raw_label="Arsenal",
                as_of=as_of,
                metadata_json={
                    "competition_external_id": "engprem-2023-2024",
                    "competition_display_name": "English Premier League 2023/2024",
                },
            )

            report = FootballsquadsCanonicalBackfillService(settings=_settings()).run(session, as_of=as_of)

            club = session.scalar(select(Club).where(Club.provider_external_id == "engprem:arsenal"))
            mapping = session.scalar(
                select(RealPlayerReferenceMapping).where(
                    RealPlayerReferenceMapping.entity_type == "club",
                    RealPlayerReferenceMapping.provider_reference_key == "engprem-arsenal",
                )
            )
            resolution = RealPlayerCanonicalMappingService(settings=_settings()).resolve_club(
                session,
                source_name="footballsquads",
                provider_external_id="engprem:arsenal",
                name="Arsenal",
                competition_external_id="engprem-2023-2024",
                competition_name="English Premier League 2023/2024",
                as_of=as_of,
            )

            assert [item.label for item in report.resolved_clubs] == ["Arsenal"]
            assert club is not None
            assert club.name == "Arsenal"
            assert club.slug == "arsenal"
            assert club.current_competition is not None
            assert club.current_competition.provider_external_id == "engprem-2023-2024"
            assert mapping is not None
            assert mapping.mapping_status == "resolved"
            assert mapping.provider_reference_key == "engprem-arsenal"
            assert mapping.canonical_club_id == club.id
            assert resolution.status == "resolved"
            assert resolution.canonical_club_id == club.id
            assert unresolved.status == "resolved"
            assert unresolved.canonical_club_id == club.id
    finally:
        engine.dispose()


def test_footballsquads_backfill_is_idempotent_on_rerun() -> None:
    engine, factory = _session_factory()
    as_of = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    try:
        with factory() as session:
            _seed_unresolved_reference(
                session,
                entity_type="competition",
                provider_external_id="engprem-2023-2024",
                raw_label="English Premier League 2023/2024",
                as_of=as_of,
            )
            _seed_unresolved_reference(
                session,
                entity_type="club",
                provider_external_id="engprem:arsenal",
                raw_label="Arsenal",
                as_of=as_of,
                metadata_json={
                    "competition_external_id": "engprem-2023-2024",
                    "competition_display_name": "English Premier League 2023/2024",
                },
            )
            _seed_unresolved_reference(
                session,
                entity_type="club",
                provider_external_id="engprem:chelsea",
                raw_label="Chelsea",
                as_of=as_of,
                metadata_json={
                    "competition_external_id": "engprem-2023-2024",
                    "competition_display_name": "English Premier League 2023/2024",
                },
            )

            service = FootballsquadsCanonicalBackfillService(settings=_settings())
            first = service.run(session, as_of=as_of)
            session.commit()
            second = service.run(session, as_of=as_of)
            session.commit()

            assert len(first.resolved_items) == 3
            assert second.resolved_items == ()
            assert session.scalar(select(func.count()).select_from(Competition)) == 1
            assert session.scalar(select(func.count()).select_from(Club)) == 2
            assert session.scalar(select(func.count()).select_from(RealPlayerReferenceMapping)) == 3
            assert session.scalar(
                select(func.count()).select_from(RealPlayerUnresolvedReference).where(
                    RealPlayerUnresolvedReference.status != "resolved"
                )
            ) == 0
    finally:
        engine.dispose()


def test_footballsquads_backfill_leaves_unknown_mapping_unresolved() -> None:
    engine, factory = _session_factory()
    as_of = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    try:
        with factory() as session:
            _seed_unresolved_reference(
                session,
                entity_type="competition",
                provider_external_id="engprem-2023-2024",
                raw_label="English Premier League 2023/2024",
                as_of=as_of,
            )
            unknown = _seed_unresolved_reference(
                session,
                entity_type="club",
                provider_external_id="engprem:mysteryfc",
                raw_label="Mystery FC",
                as_of=as_of,
                metadata_json={
                    "competition_external_id": "engprem-2023-2024",
                    "competition_display_name": "English Premier League 2023/2024",
                },
            )

            report = FootballsquadsCanonicalBackfillService(settings=_settings()).run(session, as_of=as_of)

            assert [item.label for item in report.resolved_competitions] == ["English Premier League 2023/2024"]
            assert [item.label for item in report.remaining_unresolved_items] == ["Mystery FC"]
            assert session.scalar(select(func.count()).select_from(Competition)) == 1
            assert session.scalar(select(func.count()).select_from(Club)) == 0
            assert session.scalar(select(func.count()).select_from(RealPlayerReferenceMapping)) == 1
            assert unknown.status == "open"
            assert unknown.canonical_club_id is None
            assert session.scalar(
                select(RealPlayerReferenceMapping).where(
                    RealPlayerReferenceMapping.provider_reference_key == "engprem-mysteryfc"
                )
            ) is None
    finally:
        engine.dispose()
