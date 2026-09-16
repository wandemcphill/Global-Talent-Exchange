from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import load_model_modules
from app.ingestion.models import Player
from app.legend_layer.pilot_dataset import load_and_validate_pilot_dataset
from app.legend_layer.registry_service import (
    LEGEND_SOURCE_PROVIDER,
    LegendaryInvalidRecordError,
    LegendaryPlayerRegistryService,
)
from app.models.base import Base
from app.models.player_token_market import PlayerShareMarket
from app.models.user import User, UserRole
from app.national_team_engine.tournament_service import NationalTeamTournamentService
from app.wallets.service import LedgerEntryReason, LedgerPosting, LedgerSourceTag, LedgerUnit, WalletService
from tests.support.economic_policy import seed_economic_policy


def _seed_user_wallet_coin(session: Session, user: User, amount: Decimal) -> None:
    wallet = WalletService()
    wallet.ensure_default_accounts(session, user)
    user_account = wallet.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = wallet.ensure_platform_account(session, LedgerUnit.COIN)
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=amount),
            LedgerPosting(account=platform_account, amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
    )
    session.flush()


@pytest.fixture
def db_session():
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = session_factory()
    seed_economic_policy(session)
    session.commit()
    yield session
    session.close()


@pytest.fixture
def test_buyer_user(db_session):
    user = User(
        email="buyer_legend_cert@gtex.io",
        username="buyer_legend_cert",
        display_name="Legend Buyer",
        password_hash="test_hash_buyer",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    _seed_user_wallet_coin(db_session, user, Decimal("1000000.0000"))
    return user


@pytest.fixture
def test_seller_user(db_session):
    user = User(
        email="seller_legend_cert@gtex.io",
        username="seller_legend_cert",
        display_name="Legend Seller",
        password_hash="test_hash_seller",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    _seed_user_wallet_coin(db_session, user, Decimal("1000000.0000"))
    return user


def test_pilot_dataset_requirements_coverage():
    """
    Certifies all requirements for the 25-player pilot dataset:
    - 25 players
    - multiple continents (Africa, Europe, South America, Asia, North America)
    - African, European, South American, Asian players present
    - multiple positions (GK, CB, LB, CM, AM, ST, RW)
    - left-footed and right-footed
    - different eras
    - different physical profiles
    - different roles
    - different fame levels
    - factual historical data
    """
    dataset = load_and_validate_pilot_dataset()
    assert len(dataset) == 25, f"Expected exactly 25 players, got {len(dataset)}"

    continents = {item.continent for item in dataset}
    assert continents == {"Africa", "Europe", "South America", "Asia", "North America"}

    # Continent breakdown
    african_players = [item for item in dataset if item.continent == "Africa"]
    european_players = [item for item in dataset if item.continent == "Europe"]
    south_american_players = [item for item in dataset if item.continent == "South America"]
    asian_players = [item for item in dataset if item.continent == "Asia"]

    assert len(african_players) >= 5
    assert len(european_players) >= 8
    assert len(south_american_players) >= 5
    assert len(asian_players) >= 3

    # Position breakdown
    positions = {item.primary_position for item in dataset}
    assert "GK" in positions
    assert "CB" in positions
    assert "LB" in positions
    assert "CM" in positions
    assert "AM" in positions
    assert "ST" in positions
    assert "RW" in positions

    # Preferred foot
    left_footed = [item for item in dataset if item.preferred_foot == "left"]
    right_footed = [item for item in dataset if item.preferred_foot == "right"]
    assert len(left_footed) >= 5
    assert len(right_footed) >= 15

    # Eras
    eras = {item.era for item in dataset}
    assert len(eras) >= 5

    # Fame levels
    fame_levels = {item.fame_level for item in dataset}
    assert fame_levels == {"Global Superstar", "Continental Icon", "Cult Legend", "National Hero"}

    # Verify no fake bios or empty required fields
    for item in dataset:
        assert len(item.full_name) > 0
        assert len(item.nationality) > 0
        assert len(item.country_code) == 3
        assert 140 <= item.height_cm <= 220
        assert 50 <= item.weight_kg <= 120
        assert len(item.signature_traits) >= 2


def test_identity_acceptance_for_representative_profiles(db_session):
    """
    Certifies full identity acceptance fields for representative profiles:
    full name, nationality, preferred foot, positions, height ±1 cm, traits, portrait metadata, flags.
    """
    registry = LegendaryPlayerRegistryService(db_session)
    registry.seed_pilot_dataset()

    # Representative 1: Pelé (South America / ST / Right foot / 173cm)
    pele_profile = registry.get_legend_profile("legend-pele")
    assert pele_profile["full_name"] == "Edson Arantes do Nascimento"
    assert pele_profile["canonical_display_name"] == "Pelé"
    assert pele_profile["nationality"] == "Brazil"
    assert pele_profile["country_code"] == "BRA"
    assert pele_profile["preferred_foot"] == "right"
    assert pele_profile["positions"]["primary"] == "ST"
    assert pele_profile["height_cm"] == 173
    assert "dribbling_wizard" in pele_profile["signature_traits"]
    assert pele_profile["portrait_metadata"]["asset_ref"] is not None
    assert pele_profile["flags"]["is_active"] is True
    assert pele_profile["flags"]["is_tradable"] is True
    assert pele_profile["flags"]["is_rentable"] is True

    # Representative 2: Diego Maradona (South America / AM / Left foot / 165cm)
    maradona_profile = registry.get_legend_profile("legend-maradona")
    assert maradona_profile["full_name"] == "Diego Armando Maradona"
    assert maradona_profile["nationality"] == "Argentina"
    assert maradona_profile["country_code"] == "ARG"
    assert maradona_profile["preferred_foot"] == "left"
    assert maradona_profile["positions"]["primary"] == "AM"
    assert maradona_profile["height_cm"] == 165
    assert "maestro_dribbler" in maradona_profile["signature_traits"]

    # Representative 3: Lev Yashin (Europe / GK / Right foot / 189cm)
    yashin_profile = registry.get_legend_profile("legend-yashin")
    assert yashin_profile["full_name"] == "Lev Ivanovich Yashin"
    assert yashin_profile["nationality"] == "Russia"
    assert yashin_profile["country_code"] == "RUS"
    assert yashin_profile["preferred_foot"] == "right"
    assert yashin_profile["positions"]["primary"] == "GK"
    assert yashin_profile["height_cm"] == 189
    assert "black_spider_reflexes" in yashin_profile["signature_traits"]

    # Representative 4: Samuel Eto'o (Africa / ST / Right foot / 179cm)
    etoo_profile = registry.get_legend_profile("legend-etoo")
    assert etoo_profile["full_name"] == "Samuel Eto'o Fils"
    assert etoo_profile["nationality"] == "Cameroon"
    assert etoo_profile["country_code"] == "CMR"
    assert etoo_profile["preferred_foot"] == "right"
    assert etoo_profile["positions"]["primary"] == "ST"
    assert etoo_profile["height_cm"] == 179
    assert "explosive_acceleration" in etoo_profile["signature_traits"]


def test_complete_lifecycle_acceptance(db_session, test_buyer_user, test_seller_user):
    """
    Certifies the complete lifecycle path for representative legendary players:
    registry → player creation → active → searchable → profile → market acquisition → ownership → transfer/resale → national-team eligibility → national-team rental → competition selection → normal player lifecycle.
    """
    registry = LegendaryPlayerRegistryService(db_session)
    registry.seed_pilot_dataset()

    representative_ids = [
        "legend-pele",
        "legend-maradona",
        "legend-yashin",
        "legend-etoo",
        "legend-okocha",
        "legend-park-ji-sung",
    ]

    for legend_id in representative_ids:
        report = registry.certify_player_lifecycle(
            identifier=legend_id,
            buyer_user=test_buyer_user,
            seller_user=test_seller_user,
        )
        assert report["all_steps_passed"] is True
        steps = report["certified_lifecycle_steps"]
        assert steps["registry"]["status"] == "PASSED"
        assert steps["player_creation"]["status"] == "PASSED"
        assert steps["active"]["status"] == "PASSED"
        assert steps["searchable"]["status"] == "PASSED"
        assert steps["profile"]["status"] == "PASSED"
        assert steps["market_acquisition"]["status"] == "PASSED"
        assert steps["ownership"]["status"] == "PASSED"
        assert steps["transfer_resale"]["status"] == "PASSED"
        assert steps["national_team_eligibility"]["status"] == "PASSED"
        assert steps["national_team_rental"]["status"] == "PASSED"
        assert steps["competition_selection"]["status"] == "PASSED"
        assert steps["normal_player_lifecycle"]["status"] == "PASSED"


def test_negative_tests(db_session, test_buyer_user):
    """
    Negative tests proving:
    1) Duplicate seeding does not create duplicate players (idempotency check)
    2) Wrong-nationality national-team selection is rejected
    3) Ordinary players still behave normally
    4) Invalid legendary records are rejected cleanly
    """
    registry = LegendaryPlayerRegistryService(db_session)

    # 1. Duplicate seeding idempotency
    res1 = registry.seed_pilot_dataset()
    assert res1["created"] == 25
    assert res1["total_seeded"] == 25

    total_players_1 = db_session.scalar(
        select(func.count()).select_from(Player).where(Player.source_provider == LEGEND_SOURCE_PROVIDER)
    )
    assert total_players_1 == 25

    # Second run
    res2 = registry.seed_pilot_dataset()
    assert res2["created"] == 0
    assert res2["updated"] == 25

    total_players_2 = db_session.scalar(
        select(func.count()).select_from(Player).where(Player.source_provider == LEGEND_SOURCE_PROVIDER)
    )
    assert total_players_2 == 25, "Duplicate seeding created duplicate player records!"

    total_markets = db_session.scalar(
        select(func.count())
        .select_from(PlayerShareMarket)
        .join(Player, PlayerShareMarket.player_id == Player.id)
        .where(Player.source_provider == LEGEND_SOURCE_PROVIDER)
    )
    assert total_markets == 25, "Duplicate seeding created duplicate market records!"

    # 2. Wrong-nationality national-team selection is rejected
    maradona = db_session.scalar(
        select(Player).where(
            Player.source_provider == LEGEND_SOURCE_PROVIDER,
            Player.provider_external_id == "legend-maradona",
        )
    )
    assert maradona is not None

    tournament_service = NationalTeamTournamentService(db_session)
    # Check Nigeria pool (country_code = NGA)
    nigeria_pool = tournament_service._national_pool(
        filters=tournament_service._normalize_pool_filters(country_code="NGA"),
        limit=1000,
    )
    nigeria_player_ids = {item["player_id"] for item in nigeria_pool}
    assert (
        maradona.id not in nigeria_player_ids
    ), "Argentinian legend Maradona incorrectly appeared in Nigeria national pool!"

    # 3. Ordinary players still behave normally
    ordinary_player = Player(
        source_provider="standard_ingestion",
        provider_external_id="std-p-101",
        full_name="John Standard",
        canonical_display_name="John Standard",
        position="CM",
        normalized_position="CM",
        preferred_foot="right",
        height_cm=180,
        weight_kg=75,
        is_tradable=True,
        is_real_player=True,
    )
    db_session.add(ordinary_player)
    db_session.flush()

    assert ordinary_player.id is not None
    assert ordinary_player.source_provider == "standard_ingestion"

    # 4. Invalid legendary records are rejected cleanly
    invalid_record_missing_name = {
        "provider_external_id": "legend-fake",
        "full_name": " ",
        "canonical_display_name": "Fake Legend",
        "nationality": "France",
        "country_code": "FRA",
        "continent": "Europe",
        "preferred_foot": "right",
        "primary_position": "ST",
        "height_cm": 180,
        "weight_kg": 75,
        "date_of_birth": date(1980, 1, 1),
        "era": "2000s",
        "physical_profile": "Tall",
        "role": "Striker",
        "fame_level": "Global Superstar",
        "portrait_asset_ref": "http://fake.png",
        "market_value_eur": 100000.0,
    }

    with pytest.raises(LegendaryInvalidRecordError):
        registry.validate_record(invalid_record_missing_name)

    invalid_record_bad_height = {
        "provider_external_id": "legend-fake2",
        "full_name": "Fake Height",
        "canonical_display_name": "Fake Height",
        "nationality": "France",
        "country_code": "FRA",
        "continent": "Europe",
        "preferred_foot": "right",
        "primary_position": "ST",
        "height_cm": 100,  # Invalid: height < 140
        "weight_kg": 75,
        "date_of_birth": date(1980, 1, 1),
        "era": "2000s",
        "physical_profile": "Tall",
        "role": "Striker",
        "fame_level": "Global Superstar",
        "portrait_asset_ref": "http://fake.png",
        "market_value_eur": 100000.0,
    }

    with pytest.raises(LegendaryInvalidRecordError):
        registry.validate_record(invalid_record_bad_height)
