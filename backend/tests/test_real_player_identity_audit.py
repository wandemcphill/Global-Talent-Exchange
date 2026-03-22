from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import load_model_modules
from app.ingestion.models import Country, Player
from app.ingestion.real_player_identity_audit import RealPlayerIdentityAuditService
from app.models.base import Base
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_source_link import RealPlayerSourceLink


def _session_factory():
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def test_audit_batch_reports_global_normalization_collisions() -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            brazil = Country(
                source_provider="test-source",
                provider_external_id="BR",
                name="Brazil",
                alpha2_code="BR",
            )
            existing = Player(
                source_provider="legacy-source",
                provider_external_id="vinicius-existing",
                full_name="Vinícius Júnior",
                canonical_display_name="Vinícius Júnior",
                country=brazil,
                position="Winger",
                normalized_position="forward",
                date_of_birth=date(2000, 7, 12),
                is_real_player=True,
            )
            duplicate = Player(
                source_provider="legacy-source",
                provider_external_id="vinicius-duplicate",
                full_name="Vinicius Junior",
                canonical_display_name="Vinicius Junior",
                country=brazil,
                position="Winger",
                normalized_position="forward",
                date_of_birth=None,
                is_real_player=True,
            )
            session.add_all([brazil, existing, duplicate])
            session.flush()

            existing_link = RealPlayerSourceLink(
                gtex_player_id=existing.id,
                source_name="curated-feed",
                source_player_key="vinicius-001",
                canonical_name="Vinícius Júnior",
                nationality="Brazil",
                date_of_birth=date(2000, 7, 12),
                birth_year=2000,
                primary_position="Winger",
                identity_confidence_score=0.99,
            )
            duplicate_link = RealPlayerSourceLink(
                gtex_player_id=duplicate.id,
                source_name="curated-feed",
                source_player_key="vinicius-junior-001",
                canonical_name="Vinicius Junior",
                nationality="Brazil",
                birth_year=2000,
                primary_position="Winger",
                identity_confidence_score=0.99,
            )
            session.add_all([existing_link, duplicate_link])
            session.flush()

            session.add_all(
                [
                    RealPlayerProfile(
                        gtex_player_id=existing.id,
                        source_link_id=existing_link.id,
                        source_name="curated-feed",
                        source_player_key="vinicius-001",
                        canonical_name="Vinícius Júnior",
                        nationality="Brazil",
                        birth_year=2000,
                        date_of_birth=date(2000, 7, 12),
                        primary_position="Winger",
                        ingestion_batch_id="legacy-batch",
                    ),
                    RealPlayerProfile(
                        gtex_player_id=duplicate.id,
                        source_link_id=duplicate_link.id,
                        source_name="curated-feed",
                        source_player_key="vinicius-junior-001",
                        canonical_name="Vinicius Junior",
                        nationality="Brazil",
                        birth_year=2000,
                        primary_position="Winger",
                        ingestion_batch_id="target-batch",
                    ),
                ]
            )
            session.commit()

        with session_factory() as session:
            report = RealPlayerIdentityAuditService().audit_batch(
                session,
                ingestion_batch_id="target-batch",
            )

        assert any(finding.finding_type == "normalization_collision" for finding in report.duplicate_findings)
        assert any(
            "curated-feed:vinicius-001" in finding.source_keys
            and "curated-feed:vinicius-junior-001" in finding.source_keys
            for finding in report.duplicate_findings
        )
    finally:
        engine.dispose()
