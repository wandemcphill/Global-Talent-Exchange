from __future__ import annotations

import os
from datetime import UTC, datetime

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import load_settings
from app.core.database import load_model_modules
from app.ingestion.models import Country
from app.ingestion.real_player_footballsquads_canonical_backfill import FootballsquadsCanonicalBackfillService
from app.models.base import Base
from app.models.real_player_reference_mapping import RealPlayerReferenceMapping, RealPlayerUnresolvedReference


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


def _seed_unresolved_country(
    session,
    *,
    reference_id: str,
    provider_reference_key: str,
    provider_external_id: str,
    raw_label: str,
    as_of: datetime,
) -> None:
    session.add(
        RealPlayerUnresolvedReference(
            id=reference_id,
            source_name="footballsquads",
            entity_type="country",
            provider_reference_key=provider_reference_key,
            provider_external_id=provider_external_id,
            raw_label=raw_label,
            normalized_label=raw_label,
            reason_code="country_not_found",
            status="open",
            occurrence_count=1,
            first_seen_at=as_of,
            last_seen_at=as_of,
            sample_payload_json={
                "nationality": raw_label,
                "nationality_code": provider_external_id,
            },
            metadata_json={
                "country_code": provider_external_id,
                "country_name": raw_label,
            },
        )
    )
    session.commit()


def test_footballsquads_country_backfill_resolves_provider_keyed_country_mapping() -> None:
    engine, session_factory = _session_factory()
    as_of = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    try:
        service = FootballsquadsCanonicalBackfillService(
            settings=_settings(),
            entity_types=("country",),
        )
        with session_factory() as session:
            _seed_unresolved_country(
                session,
                reference_id="unresolved-country-england",
                provider_reference_key="gb",
                provider_external_id="GB",
                raw_label="England",
                as_of=as_of,
            )

            report = service.run(session, as_of=as_of)

            country = session.scalar(
                select(Country).where(
                    Country.source_provider == "footballsquads",
                    Country.provider_external_id == "GB",
                )
            )
            mapping = session.scalar(
                select(RealPlayerReferenceMapping).where(
                    RealPlayerReferenceMapping.source_name == "footballsquads",
                    RealPlayerReferenceMapping.entity_type == "country",
                    RealPlayerReferenceMapping.provider_reference_key == "gb",
                )
            )
            unresolved = session.get(RealPlayerUnresolvedReference, "unresolved-country-england")

            assert tuple(item.label for item in report.resolved_countries) == ("England",)
            assert report.remaining_unresolved_items == ()
            assert country is not None
            assert country.name == "England"
            assert country.alpha2_code is None
            assert country.fifa_code == "ENG"
            assert mapping is not None
            assert mapping.mapping_status == "resolved"
            assert mapping.resolution_method == "provider_exact"
            assert mapping.canonical_country_id == country.id
            assert unresolved is not None
            assert unresolved.status == "resolved"
            assert unresolved.canonical_country_id == country.id
    finally:
        engine.dispose()


def test_footballsquads_country_backfill_is_idempotent_on_rerun() -> None:
    engine, session_factory = _session_factory()
    as_of = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    try:
        service = FootballsquadsCanonicalBackfillService(
            settings=_settings(),
            entity_types=("country",),
        )
        with session_factory() as session:
            _seed_unresolved_country(
                session,
                reference_id="unresolved-country-brazil",
                provider_reference_key="br",
                provider_external_id="BR",
                raw_label="Brazil",
                as_of=as_of,
            )

            first = service.run(session, as_of=as_of)
            country_count_after_first = session.scalar(select(func.count()).select_from(Country))
            mapping_count_after_first = session.scalar(select(func.count()).select_from(RealPlayerReferenceMapping))
            second = service.run(session, as_of=as_of)

            assert tuple(item.label for item in first.resolved_countries) == ("Brazil",)
            assert second.resolved_countries == ()
            assert second.remaining_unresolved_items == ()
            assert session.scalar(select(func.count()).select_from(Country)) == country_count_after_first == 1
            assert session.scalar(select(func.count()).select_from(RealPlayerReferenceMapping)) == mapping_count_after_first == 1
            unresolved = session.get(RealPlayerUnresolvedReference, "unresolved-country-brazil")
            assert unresolved is not None
            assert unresolved.status == "resolved"
    finally:
        engine.dispose()


def test_footballsquads_country_backfill_keeps_ambiguous_country_unresolved() -> None:
    engine, session_factory = _session_factory()
    as_of = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    try:
        service = FootballsquadsCanonicalBackfillService(
            settings=_settings(),
            entity_types=("country",),
        )
        with session_factory() as session:
            _seed_unresolved_country(
                session,
                reference_id="unresolved-country-congo",
                provider_reference_key="cg",
                provider_external_id="CG",
                raw_label="Congo",
                as_of=as_of,
            )

            report = service.run(session, as_of=as_of)

            assert report.resolved_countries == ()
            assert tuple(item.label for item in report.remaining_unresolved_items) == ("Congo",)
            assert session.scalar(select(func.count()).select_from(Country)) == 0
            assert session.scalar(select(func.count()).select_from(RealPlayerReferenceMapping)) == 0
            unresolved = session.get(RealPlayerUnresolvedReference, "unresolved-country-congo")
            assert unresolved is not None
            assert unresolved.status == "open"
    finally:
        engine.dispose()
