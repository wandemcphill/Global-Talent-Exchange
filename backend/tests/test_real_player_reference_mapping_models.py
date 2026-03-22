from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.ingestion.models  # noqa: F401
import app.models  # noqa: F401
from app.models.base import Base
from app.models.real_player_reference_mapping import RealPlayerReferenceMapping, RealPlayerUnresolvedReference


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session
    engine.dispose()


def test_real_player_reference_mapping_models_persist_resolution_states(session) -> None:
    mapping = RealPlayerReferenceMapping(
        source_name="mock",
        entity_type="club",
        provider_external_id="club-arsenal",
        provider_reference_key="mock:club:arsenal",
        provider_label="Arsenal FC",
        normalized_label="arsenal fc",
        mapping_status="resolved",
        resolution_method="name_match",
        confidence_score=0.94,
        metadata_json={"import_state": "staged"},
    )
    unresolved = RealPlayerUnresolvedReference(
        source_name="mock",
        entity_type="competition",
        provider_external_id="comp-ucl",
        provider_reference_key="mock:competition:ucl",
        raw_label="UEFA Champions League",
        normalized_label="uefa champions league",
        reason_code="missing_competition_mapping",
        status="open",
        occurrence_count=2,
        first_seen_at=datetime(2026, 3, 22, 12, 0, tzinfo=timezone.utc),
        last_seen_at=datetime(2026, 3, 22, 12, 30, tzinfo=timezone.utc),
        sample_payload_json={"provider_competition_name": "UEFA Champions League"},
        metadata_json={"provider_name": "mock"},
    )

    session.add_all([mapping, unresolved])
    session.commit()

    stored_mapping = session.get(RealPlayerReferenceMapping, mapping.id)
    stored_unresolved = session.get(RealPlayerUnresolvedReference, unresolved.id)

    assert stored_mapping is not None
    assert stored_mapping.provider_reference_key == "mock:club:arsenal"
    assert stored_mapping.mapping_status == "resolved"
    assert stored_mapping.confidence_score == pytest.approx(0.94)

    assert stored_unresolved is not None
    assert stored_unresolved.provider_reference_key == "mock:competition:ucl"
    assert stored_unresolved.reason_code == "missing_competition_mapping"
    assert stored_unresolved.occurrence_count == 2


def test_real_player_reference_mapping_enforces_source_entity_reference_uniqueness(session) -> None:
    session.add(
        RealPlayerReferenceMapping(
            source_name="mock",
            entity_type="club",
            provider_reference_key="mock:club:arsenal",
            mapping_status="resolved",
            resolution_method="manual",
            confidence_score=1.0,
        )
    )
    session.commit()

    session.add(
        RealPlayerReferenceMapping(
            source_name="mock",
            entity_type="club",
            provider_reference_key="mock:club:arsenal",
            mapping_status="resolved",
            resolution_method="manual",
            confidence_score=1.0,
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
