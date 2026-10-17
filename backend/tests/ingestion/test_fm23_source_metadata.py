from __future__ import annotations

from sqlalchemy import select

from app.ingestion.real_player_ingestion_service import RealPlayerIngestionService
from app.models.real_player_profile import RealPlayerProfile
from backend.tests.test_real_player_batch import (
    _batch_request,
    _session_factory,
    _settings,
)


def test_source_metadata_is_preserved_on_published_real_player_profile() -> None:
    engine, session_factory = _session_factory()
    try:
        request = _batch_request()
        request.players[0].source_metadata = {
            "kind": "fm23_founding_universe_snapshot",
            "fm23_age": 24,
            "fm23_value": 260283380,
            "semantics": {
                "age": "FM-universe age; not canonical real-world age",
                "value": "FM game value; not authoritative real-world market reference",
            },
        }

        service = RealPlayerIngestionService(
            session_factory=session_factory,
            settings=_settings(),
        )
        report = service.write_batch(request)

        assert report.players_processed == 2

        with session_factory() as session:
            profile = session.scalar(
                select(RealPlayerProfile).where(RealPlayerProfile.canonical_name == "Victor Osimhen")
            )
            assert profile is not None
            assert profile.metadata_json["source_metadata"]["kind"] == "fm23_founding_universe_snapshot"
            assert profile.metadata_json["source_metadata"]["fm23_age"] == 24
            assert profile.metadata_json["source_metadata"]["fm23_value"] == 260283380
    finally:
        engine.dispose()
