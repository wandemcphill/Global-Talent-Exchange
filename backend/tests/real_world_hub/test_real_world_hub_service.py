from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import ensure_database_schema_current
from app.ingestion.models import Country, Player
from app.models.real_world_hub import RealDataProvider, RealityMode
from app.real_world_hub.schemas import RealClubSeedRequest, RealCompetitionSeedRequest, RealWorldSyncRequest
from app.real_world_hub.service import RealWorldHubService
from app.schemas.real_player_ingestion import RealPlayerSeedInput


def test_real_world_hub_sync_and_hybrid_modes_respect_optional_layer(tmp_path) -> None:
    database_path = Path(tmp_path) / "real-world-hub.db"
    engine = create_engine(
        f"sqlite+pysqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    ensure_database_schema_current(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        nigeria = Country(
            source_provider="test",
            provider_external_id="ng-real-world",
            name="Nigeria",
            alpha2_code="NG",
            alpha3_code="NGA",
            fifa_code="NGA",
        )
        spain = Country(
            source_provider="test",
            provider_external_id="es-real-world",
            name="Spain",
            alpha2_code="ES",
            alpha3_code="ESP",
            fifa_code="ESP",
        )
        session.add_all([nigeria, spain])
        session.flush()

        regen_player = Player(
            source_provider="seed",
            provider_external_id="regen-hybrid-1",
            full_name="Ayo Regen",
            position="CM",
            normalized_position="cm",
            country_id=nigeria.id,
            is_real_player=False,
        )
        real_player = Player(
            source_provider="seed",
            provider_external_id="real-hybrid-1",
            full_name="Real Ace",
            position="ST",
            normalized_position="st",
            country_id=spain.id,
            is_real_player=True,
        )
        session.add_all([regen_player, real_player])
        session.commit()

        service = RealWorldHubService(session=session)
        provider = service.upsert_provider(
            name="Opta Mirror",
            api_endpoint="https://provider.invalid/api",
            refresh_interval=3600,
            normalization_profile_version="real_player_v1",
            is_active=True,
            metadata_json={"mode": "optional"},
        )
        session.commit()

        job = service.sync_provider(
            provider_id=provider.id,
            payload=RealWorldSyncRequest(
                competitions=[
                    RealCompetitionSeedRequest(
                        external_key="la-liga",
                        name="La Liga",
                        country_name="Spain",
                    )
                ],
                clubs=[
                    RealClubSeedRequest(
                        external_key="madrid",
                        competition_external_key="la-liga",
                        name="Madrid FC",
                        country_name="Spain",
                    )
                ],
                players=[
                    RealPlayerSeedInput(
                        source_name="Opta Mirror",
                        source_player_key="real-ace",
                        canonical_name="Real Ace",
                        display_name="Real Ace",
                        nationality="Spain",
                        primary_position="Striker",
                        current_real_world_club="Madrid FC",
                        current_real_world_club_key="madrid",
                        current_real_world_league="La Liga",
                        current_real_world_league_key="la-liga",
                        appearances=30,
                        minutes_played=2500,
                        goals=20,
                        assists=7,
                        injury_status="fit",
                        current_market_reference_value=120000000,
                    )
                ],
                use_existing_profiles=False,
                as_of=datetime.now(UTC),
            ),
        )
        session.commit()
        session.expire_all()

        provider_row = session.get(RealDataProvider, provider.id)
        assert provider_row is not None
        provider_row.last_sync_at = datetime(2020, 1, 1, 0, 0, 0)
        session.commit()

        assert service.sync_due_providers() == 1
        session.commit()

        projected = service.list_real_players(limit=5)
        hybrid_players = service.list_hybrid_players(mode=RealityMode.HYBRID, limit=10)
        regen_only_players = service.list_hybrid_players(mode=RealityMode.PURE_REGEN, limit=10)
        real_only_players = service.list_hybrid_players(mode=RealityMode.REAL_ONLY, limit=10)

        assert job.status == "completed"
        assert projected[0].gtex_player_id == real_player.id
        assert 35.0 <= projected[0].normalized_rating <= 92.0
        assert {item["player_origin"] for item in hybrid_players} == {"real_player", "regen_player"}
        assert [item["player_id"] for item in regen_only_players] == [regen_player.id]
        assert [item["player_id"] for item in real_only_players] == [real_player.id]
    finally:
        session.close()
        engine.dispose()
