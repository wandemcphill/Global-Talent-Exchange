from __future__ import annotations

import json
from pathlib import Path
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import load_model_modules
from app.ingestion.models import Player
from app.market.service import derive_player_attributes
from app.models.base import Base
from app.schemas.real_player_ingestion import RealPlayerIngestionRequest

BATCHES_DIR = Path(__file__).resolve().parents[2] / "data" / "real_player_batches"
FIRST_BATCH_PATH = BATCHES_DIR / "first_batch.json"
TOP_EIGHT_BATCH_PATH = BATCHES_DIR / "top_eight_leagues_batch_v1.json"
FIRST_CONTROLLED_PATH = BATCHES_DIR / "first_controlled_batch_v1.json"


def test_bukayo_saka_adequate_rating_and_independent_potential() -> None:
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with Session() as session:
        # Create Bukayo Saka with current rating 87 and potential 90
        saka = Player(
            id="player-bukayo-saka",
            source_provider="curated-feed",
            provider_external_id="saka-001",
            full_name="Bukayo Saka",
            canonical_display_name="Bukayo Saka",
            date_of_birth=date(2001, 9, 5),
            position="Right Winger",
            normalized_position="forward",
            preferred_foot="left",
            height_cm=178,
            weight_kg=72,
            is_real_player=True,
            is_tradable=True,
            potential=90,
            dna_profile={
                "overall": 87,
                "current_rating": 87,
                "potential": 90,
            },
        )
        session.add(saka)
        session.commit()

        attributes = derive_player_attributes(saka, overall=87)

        # Ratings must be adequate and independent
        assert attributes.overall == 87
        assert attributes.potential == 90
        assert attributes.overall < attributes.potential
        assert saka.preferred_foot == "left"
        assert saka.date_of_birth == date(2001, 9, 5)


def test_first_batch_includes_saka_and_top_league_players() -> None:
    data = json.loads(FIRST_BATCH_PATH.read_text(encoding="utf-8"))
    players = {p["source_player_key"]: p for p in data["players"]}

    # Verify Bukayo Saka
    assert "saka-001" in players
    saka = players["saka-001"]
    assert saka["canonical_name"] == "Bukayo Saka"
    assert saka["overall_rating"] == 87
    assert saka["potential"] == 90
    assert saka["dominant_foot"] == "left"
    assert saka["primary_position"] in {"Winger", "Right Winger"}
    assert saka["current_real_world_club"] == "Arsenal"
    assert saka["current_real_world_league"] == "Premier League"

    # Verify players from top 8 leagues exist in first_batch
    leagues = {p["current_real_world_league"] for p in data["players"]}
    assert "Premier League" in leagues
    assert "La Liga" in leagues
    assert "Serie A" in leagues
    assert "Bundesliga" in leagues
    assert "Ligue 1" in leagues
    assert "Primeira Liga" in leagues
    assert "Eredivisie" in leagues
    assert any("Super Lig" in l or "Belgian" in l for l in leagues)


def test_top_eight_leagues_batch_manifest_valid() -> None:
    request = RealPlayerIngestionRequest.model_validate(json.loads(TOP_EIGHT_BATCH_PATH.read_text(encoding="utf-8")))
    assert request.mode == "curated_seed"
    assert len(request.players) >= 30

    leagues = {p.current_real_world_league for p in request.players}
    expected_top_leagues = {
        "Premier League",
        "La Liga",
        "Serie A",
        "Bundesliga",
        "Ligue 1",
        "Primeira Liga",
        "Eredivisie",
    }
    for expected in expected_top_leagues:
        assert expected in leagues, f"Missing expected league: {expected}"

    # Verify ratings and potential are set for top players
    for p in request.players:
        assert p.overall_rating is not None, f"Missing overall_rating for {p.canonical_name}"
        assert p.potential is not None, f"Missing potential for {p.canonical_name}"
        assert p.overall_rating <= p.potential, f"Rating cannot exceed potential for {p.canonical_name}"
        assert p.dominant_foot in {"left", "right", "both"}
        assert p.date_of_birth is not None


def test_first_controlled_batch_saka_has_adequate_ratings() -> None:
    data = json.loads(FIRST_CONTROLLED_PATH.read_text(encoding="utf-8"))
    saka = next((p for p in data["players"] if p.get("source_player_key") == "saka-001"), None)
    assert saka is not None
    assert saka["canonical_name"] == "Bukayo Saka"
    assert saka["overall_rating"] == 87
    assert saka["potential"] == 90
