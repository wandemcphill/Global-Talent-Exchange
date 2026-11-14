from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import load_model_modules
from app.ingestion.models import Country, Player
from app.models.base import Base
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_source_link import RealPlayerSourceLink
from app.players.read_models import PlayerSummaryReadModel
from app.players.real_player_service import RealPlayerUniverseQueryService
from app.players.traits_service import (
    CURATED_PLAYER_PROFILES,
    derive_playstyle_and_traits,
    resolve_player_traits_and_playstyle,
)


def _build_session() -> Session:
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return session_factory()


def test_curated_player_profiles_include_calibrated_and_icon_players() -> None:
    younes = CURATED_PLAYER_PROFILES["younes ebnoutalib"]
    assert younes[0] == "Target Man"
    assert "Power Header" in younes[1]
    assert "Plays With Back To Goal" in younes[1]

    said = CURATED_PLAYER_PROFILES["said el mala"]
    assert said[0] == "Inverted Winger"
    assert "Technical Dribbler" in said[1]

    sadiq = CURATED_PLAYER_PROFILES["sadiq saleh"]
    assert sadiq[0] == "Goal Poacher"
    assert "Tries To Beat Offside Trap" in sadiq[1]

    wael = CURATED_PLAYER_PROFILES["wael mohya"]
    assert wael[0] == "Advanced Playmaker"
    assert "Technical Dribbler" in wael[1]

    maldini = CURATED_PLAYER_PROFILES["paolo maldini"]
    assert any(t.startswith("Slides Into Tackles") for t in maldini[1])

    kante = CURATED_PLAYER_PROFILES["ngolo kante"]
    assert "Ball-Winning Midfielder" in kante[0]
    assert any(t.startswith("Slides Into Tackles") for t in kante[1])


def test_derive_playstyle_and_traits_covers_all_positions() -> None:
    positions = ["GK", "CB", "RB", "DM", "CM", "AM", "LW", "RW", "ST"]
    for pos in positions:
        playstyle, traits = derive_playstyle_and_traits(
            player_id=f"seed-{pos}",
            full_name=f"Test {pos} Player",
            position=pos,
            normalized_position=pos.lower(),
            preferred_foot="Right",
            height_cm=185 if pos in ("CB", "ST", "GK") else 178,
            gsi=80,
            dna={
                "attributes": {
                    "pace": 82,
                    "shooting": 79,
                    "passing": 78,
                    "dribbling": 80,
                    "defending": 81 if pos in ("CB", "RB", "DM", "CM") else 45,
                    "physical": 82,
                }
            },
        )
        assert playstyle
        assert len(traits) >= 4
        if pos in ("CB", "RB", "DM"):
            assert "Slides Into Tackles" in traits


def test_real_player_service_exposes_playstyle_traits_and_skills() -> None:
    session = _build_session()
    now = datetime.now(timezone.utc)
    country = Country(
        id="country-de",
        source_provider="curated-feed",
        provider_external_id="DE",
        name="Germany",
        alpha2_code="DE",
    )
    session.add(country)
    player = Player(
        id="player-wael-mohya",
        source_provider="curated-feed",
        provider_external_id="wael-mohya",
        country_id=country.id,
        full_name="Wael Mohya",
        first_name="Wael",
        last_name="Mohya",
        position="AM",
        normalized_position="am",
        date_of_birth=date(2008, 12, 31),
        height_cm=176,
        preferred_foot="Right",
        canonical_display_name="Wael Mohya",
        is_real_player=True,
        is_tradable=True,
        real_player_tier="wonderkid",
        dna_profile={"overall": 78, "potential": 86},
    )
    session.add(player)
    link = RealPlayerSourceLink(
        id="link-wael-mohya",
        gtex_player_id=player.id,
        source_name="curated-feed",
        source_player_key="wael-mohya",
        canonical_name="Wael Mohya",
        is_verified_real_player=True,
        verification_state="verified",
    )
    session.add(link)
    profile = RealPlayerProfile(
        id="profile-wael-mohya",
        gtex_player_id=player.id,
        source_link_id=link.id,
        source_name="curated-feed",
        source_player_key="wael-mohya",
        canonical_name="Wael Mohya",
        nationality="Germany",
        primary_position="AM",
        secondary_positions_json=["LM", "LW", "ST"],
        dominant_foot="Right",
        height_cm=176,
        current_club_name="Borussia M'gladbach",
        current_league_name="Bundesliga",
        competition_level="wonderkid",
        source_last_refreshed_at=now,
        metadata_json={"honors": ["U17 Standout"]},
    )
    session.add(profile)
    summary = PlayerSummaryReadModel(
        player_id=player.id,
        player_name="Wael Mohya",
        current_club_name="Borussia M'gladbach",
        current_competition_name="Bundesliga",
        last_snapshot_at=now,
        current_value_credits=185.0,
        previous_value_credits=175.0,
        movement_pct=5.7,
        average_rating=7.4,
        market_interest_score=84,
        summary_json={"gsi": 78, "potential": 86},
    )
    session.add(summary)
    session.commit()

    playstyle, traits, skills = resolve_player_traits_and_playstyle(player, profile, summary)
    assert playstyle == "Advanced Playmaker"
    assert "Technical Dribbler" in traits
    assert skills == traits

    svc = RealPlayerUniverseQueryService(session)
    detail = svc.get_player_detail(player.id)
    assert detail.playstyle == "Advanced Playmaker"
    assert "Technical Dribbler" in detail.traits
    assert detail.skills == detail.traits
    assert detail.metadata_json["playstyle"] == "Advanced Playmaker"
    assert detail.summary_json["playstyle"] == "Advanced Playmaker"
