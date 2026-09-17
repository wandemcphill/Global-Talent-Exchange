from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.schemas.legendary_player import (
    LegendaryPlayerProfileCreate,
    LegendarySeedImportItem,
    LegendarySeedImportRequest,
)
from app.services.legendary_player_service import LegendaryPlayerRegistryService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_legendary_player_schema_validation():
    # Height offset must be -1, 0, or +1 cm
    with pytest.raises(ValidationError):
        LegendaryPlayerProfileCreate(
            slug="legend-test-1",
            full_name="Test Legend",
            country_code="BRA",
            primary_position="ST",
            preferred_foot="right",
            historical_height_cm=180,
            gtex_height_cm=185,  # Invalid offset (+5)
            era="1990s",
        )

    # Valid schema with valid GTEX height offset (+1 cm)
    profile_in = LegendaryPlayerProfileCreate(
        slug="legend-test-1",
        full_name="Test Legend",
        country_code="bra",
        primary_position="ST",
        preferred_foot="right",
        historical_height_cm=180,
        gtex_height_cm=181,
        era="1990s",
    )
    assert profile_in.slug == "legend-test-1"
    assert profile_in.country_code == "BRA"
    assert profile_in.gtex_height_cm == 181


def test_height_calculation_and_portrait_generation(db_session: Session):
    service = LegendaryPlayerRegistryService(db_session)

    # Height offset calculation is deterministic and strictly -1, 0, or +1
    h1 = service.calculate_gtex_height("pel-10", 173)
    assert abs(h1 - 173) <= 1

    h2 = service.calculate_gtex_height("maradona-10", 165)
    assert abs(h2 - 165) <= 1

    # Non-replicative fictional avatar metadata generation
    portrait = service.generate_fictional_portrait_metadata("pel-10", "BRA")
    assert portrait["avatar_system"] == "gtex_fictional_avatar_v1"
    assert portrait["is_fictional_non_replicative"] is True
    assert portrait["configured_nationality"] == "BRA"
    assert "dna_seed" in portrait


def test_upsert_legendary_profile_idempotency(db_session: Session):
    service = LegendaryPlayerRegistryService(db_session)

    item = LegendaryPlayerProfileCreate(
        slug="legend-pele-10",
        full_name="Edson Arantes do Nascimento (Pelé)",
        country_code="BRA",
        primary_position="ST",
        secondary_positions=["CAM", "CF"],
        preferred_foot="right",
        historical_height_cm=173,
        signature_traits=["Bicycle Kick", "Acrobatic Finishing"],
        signature_role="Attacking Free Role",
        technical_profile={"finishing": 99, "dribbling": 97},
        physical_profile={"pace": 93, "acceleration": 95},
        mental_profile={"vision": 96, "flair": 99},
        era="1958-1970",
        legendary_classification="immortal",
    )

    # First insert
    profile, created = service.upsert_legendary_profile(item)
    assert created is True
    assert profile.slug == "legend-pele-10"
    assert profile.full_name == "Edson Arantes do Nascimento (Pelé)"
    assert abs(profile.gtex_height_cm - 173) <= 1
    assert profile.portrait_metadata_json["avatar_system"] == "gtex_fictional_avatar_v1"

    original_id = profile.id
    original_gtex_height = profile.gtex_height_cm

    # Re-upserting same item (idempotency check)
    profile_updated, created_2 = service.upsert_legendary_profile(item)
    assert created_2 is False
    assert profile_updated.id == original_id
    assert profile_updated.gtex_height_cm == original_gtex_height


def test_instantiate_gtex_player(db_session: Session):
    service = LegendaryPlayerRegistryService(db_session)

    item = LegendaryPlayerProfileCreate(
        slug="legend-cruyff-14",
        full_name="Johan Cruyff",
        country_code="NLD",
        primary_position="CAM",
        secondary_positions=["CF", "LW"],
        preferred_foot="right",
        historical_height_cm=178,
        signature_traits=["Cruyff Turn", "Total Football Mastermind"],
        signature_role="Playmaker",
        technical_profile={"dribbling": 98, "passing": 96},
        physical_profile={"pace": 89, "stamina": 91},
        mental_profile={"vision": 99, "composure": 97},
        era="1970s",
        legendary_classification="immortal",
        is_tradable=True,
        is_rentable=True,
        is_national_team_eligible=True,
    )

    profile, _ = service.upsert_legendary_profile(item)
    player = service.instantiate_gtex_player(profile)

    # Verify ordinary GTEX player creation
    assert player.legendary_profile_id == profile.id
    assert player.source_provider == "gtex_legend"
    assert player.provider_external_id == "legend:legend-cruyff-14"
    assert player.full_name == "Johan Cruyff"
    assert player.first_name == "Johan"
    assert player.last_name == "Cruyff"
    assert player.position == "CAM"
    assert player.height_cm == profile.gtex_height_cm
    assert player.is_real_player is True
    assert player.is_tradable is True
    assert player.real_player_tier == "immortal"
    assert player.dna_profile["era"] == "1970s"
    assert player.dna_profile["is_national_team_eligible"] is True

    # Check country relationship
    assert player.country is not None
    assert player.country.name == "NLD"

    # Re-instantiate to check replay safety
    player_retry = service.instantiate_gtex_player(profile)
    assert player_retry.id == player.id


def test_bulk_import_contract(db_session: Session):
    service = LegendaryPlayerRegistryService(db_session)

    req = LegendarySeedImportRequest(
        profiles=[
            LegendarySeedImportItem(
                slug="legend-zico-10",
                full_name="Zico",
                country_code="BRA",
                primary_position="CAM",
                historical_height_cm=172,
                era="1980s",
                legendary_classification="icon",
                instantiate_gtex_player=True,
            ),
            LegendarySeedImportItem(
                slug="legend-platini-10",
                full_name="Michel Platini",
                country_code="FRA",
                primary_position="CAM",
                historical_height_cm=179,
                era="1980s",
                legendary_classification="icon",
                instantiate_gtex_player=True,
            ),
        ],
        instantiate_all=True,
    )

    res1 = service.bulk_import(req)
    assert res1.processed_count == 2
    assert res1.created_count == 2
    assert res1.updated_count == 0
    assert res1.instantiated_player_count == 2

    # Run again to ensure idempotency
    res2 = service.bulk_import(req)
    assert res2.processed_count == 2
    assert res2.created_count == 0
    assert res2.updated_count == 2
    assert res2.instantiated_player_count == 2

    # Query profiles
    profiles = service.search_profiles(country_code="BRA")
    assert len(profiles) == 1
    assert profiles[0].slug == "legend-zico-10"
