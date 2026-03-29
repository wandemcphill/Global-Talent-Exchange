from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_session
from app.global_memory.models import GlobalRegenEvolution, PlayerHistory, UserDynasty
from app.global_memory.router import router as global_memory_router
from app.ingestion.models import Competition, Country, Player
from app.models.base import Base
from app.models.club_hall_of_fame import ClubHallOfFameEntry
from app.models.club_profile import ClubProfile
from app.models.player_cards import PlayerCard, PlayerCardTier
from app.models.regen import RegenOnboardingFlag, RegenProfile
from app.models.user import KycStatus, User, UserRole


@pytest.fixture()
def global_memory_api():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    app = FastAPI()
    app.include_router(global_memory_router)

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    Base.metadata.create_all(engine)

    with TestClient(app) as client:
        yield client, session_factory

    engine.dispose()


def _seed_context(app_session_factory: sessionmaker) -> dict[str, object]:
    with app_session_factory() as session:
        user = User(
            id="user-global-memory",
            email="memory@example.com",
            username="memory-user",
            password_hash="hash",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
        )
        country = Country(
            id="country-ng",
            source_provider="seed",
            provider_external_id="ng",
            name="Nigeria",
            alpha2_code="NG",
        )
        club = ClubProfile(
            id="club-memory",
            owner_user_id=user.id,
            club_name="Memory FC",
            short_name="MFC",
            slug="memory-fc",
            primary_color="#112233",
            secondary_color="#ddeeff",
            accent_color="#ff9900",
            country_code="NG",
            region_name="Lagos",
            city_name="Lagos",
        )
        tier = PlayerCardTier(
            id="tier-unique",
            code="unique",
            name="Unique",
            rarity_rank=99,
        )
        competitions = [
            Competition(
                id="comp-u17",
                source_provider="seed",
                provider_external_id="comp-u17",
                country_id=country.id,
                name="Lagos U17 Cup",
                slug="lagos-u17-cup",
                competition_type="cup",
                age_bracket="u17",
                is_major=True,
            ),
            *[
                Competition(
                    id=f"comp-senior-{index}",
                    source_provider="seed",
                    provider_external_id=f"comp-senior-{index}",
                    country_id=country.id,
                    name=f"Senior Crown {index}",
                    slug=f"senior-crown-{index}",
                    competition_type="cup",
                    age_bracket="senior",
                    is_major=index <= 2,
                )
                for index in range(1, 6)
            ],
        ]
        regen_player = Player(
            id="player-regen",
            source_provider="seed",
            provider_external_id="player-regen",
            country_id=country.id,
            current_club_profile_id=club.id,
            current_competition_id="comp-u17",
            full_name="Ayo Future",
            normalized_position="ST",
            is_tradable=False,
        )
        national_pool_player = Player(
            id="player-pool",
            source_provider="seed",
            provider_external_id="player-pool",
            country_id=country.id,
            current_club_profile_id=club.id,
            current_competition_id="comp-senior-1",
            full_name="Bola Anchor",
            normalized_position="CM",
            is_tradable=True,
        )
        card = PlayerCard(
            id="card-regen",
            player_id=regen_player.id,
            tier_id=tier.id,
            edition_code="starter",
            display_name="Ayo Future Unique",
        )
        regen = RegenProfile(
            id="regen-profile",
            regen_id="regen-001",
            player_id=regen_player.id,
            linked_unique_card_id=card.id,
            generated_for_club_id=club.id,
            birth_country_code="NG",
            birth_region="Lagos",
            birth_city="Lagos",
            primary_position="ST",
            secondary_positions_json=["RW"],
            current_gsi=92,
            current_ability_range_json={"minimum": 88, "maximum": 92},
            potential_range_json={"minimum": 91, "maximum": 97},
            scout_confidence="high",
            generation_source="starter_bundle",
        )
        onboarding = RegenOnboardingFlag(
            id="onboarding-regen",
            regen_id=regen.id,
            club_id=club.id,
            onboarding_type="starter_bundle",
            squad_bucket="first_team",
            is_non_tradable=True,
            replacement_only=True,
        )
        session.add_all(
            [
                user,
                country,
                club,
                tier,
                *competitions,
                regen_player,
                national_pool_player,
                card,
                regen,
                onboarding,
            ]
        )
        session.commit()
    return {
        "user_id": user.id,
        "player_id": regen_player.id,
        "pool_player_id": national_pool_player.id,
        "competition_ids": [competition.id for competition in competitions],
    }


def test_enter_competition_unlocks_preseeded_regen_and_records_memory(global_memory_api) -> None:
    client, app_session_factory = global_memory_api
    seeded = _seed_context(app_session_factory)

    competitions_response = client.get("/competitions")
    assert competitions_response.status_code == 200
    assert any(item["id"] == "comp-u17" for item in competitions_response.json())

    entry_response = client.post(
        "/enter",
        json={
            "user_id": seeded["user_id"],
            "competition_id": "comp-u17",
            "player_id": seeded["player_id"],
            "performance_score": 88,
            "won_title": True,
        },
    )
    assert entry_response.status_code == 200
    entry_payload = entry_response.json()
    assert entry_payload["status"] == "champion"
    assert entry_payload["dynasty"]["total_titles"] == 1
    assert entry_payload["dynasty"]["youth_titles"] == 1
    assert entry_payload["evolution"]["regen_type"] == "preseeded"
    assert entry_payload["evolution"]["tradable"] is True
    assert entry_payload["evolution"]["unique"] is True

    history_response = client.get("/player-history", params={"player_id": seeded["player_id"]})
    assert history_response.status_code == 200
    events = [item["event"] for item in history_response.json()["history"]]
    assert any("Entered Lagos U17 Cup" in event for event in events)
    assert any("Won Lagos U17 Cup" in event for event in events)
    assert any("tradable unique asset" in event for event in events)

    with app_session_factory() as session:
        evolution = session.scalar(
            select(GlobalRegenEvolution).where(GlobalRegenEvolution.player_id == seeded["player_id"])
        )
        assert evolution is not None
        assert evolution.is_tradable is True
        assert evolution.is_unique is True

        dynasty = session.scalar(select(UserDynasty).where(UserDynasty.user_id == seeded["user_id"]))
        assert dynasty is not None
        assert dynasty.total_titles == 1
        assert dynasty.youth_titles == 1

        history_count = session.scalar(
            select(func.count()).select_from(PlayerHistory).where(PlayerHistory.player_id == seeded["player_id"])
        )
        assert history_count == 3


def test_rent_and_hall_of_fame_flow_updates_national_pool_and_dynasty(global_memory_api) -> None:
    client, app_session_factory = global_memory_api
    seeded = _seed_context(app_session_factory)

    rent_response = client.post(
        "/rent",
        json={
            "user_id": seeded["user_id"],
            "competition_id": "comp-senior-1",
            "player_id": seeded["pool_player_id"],
            "rental_fee_minor": 25000,
            "performance_score": 64,
        },
    )
    assert rent_response.status_code == 200
    assert rent_response.json()["rental_fee_minor"] == 25000

    for competition_id in seeded["competition_ids"]:
        response = client.post(
            "/enter",
            json={
                "user_id": seeded["user_id"],
                "competition_id": competition_id,
                "player_id": seeded["player_id"],
                "performance_score": 91,
                "won_title": True,
            },
        )
        assert response.status_code == 200

    dynasty_response = client.get("/dynasty", params={"user_id": seeded["user_id"]})
    assert dynasty_response.status_code == 200
    dynasty_payload = dynasty_response.json()
    assert dynasty_payload["total_titles"] == 6
    assert dynasty_payload["youth_titles"] == 1
    assert dynasty_payload["senior_titles"] == 5
    assert dynasty_payload["dynasty_label"] == "Established Dynasty"

    history_response = client.get("/player-history", params={"player_id": seeded["player_id"]})
    assert history_response.status_code == 200
    evolution_payload = history_response.json()["evolution"]
    assert evolution_payload["titles"] == 6
    assert evolution_payload["hall_of_fame"] is True

    national_pool_response = client.get("/national-pool", params={"country_code": "NG"})
    assert national_pool_response.status_code == 200
    pool_payload = national_pool_response.json()
    regen_row = next(item for item in pool_payload if item["player_id"] == seeded["player_id"])
    assert regen_row["tradable"] is True
    assert regen_row["unique"] is True
    assert regen_row["hall_of_fame"] is True

    with app_session_factory() as session:
        hall_of_fame_entry = session.scalar(
            select(ClubHallOfFameEntry).where(ClubHallOfFameEntry.regen_id == "regen-profile")
        )
        assert hall_of_fame_entry is not None
        assert hall_of_fame_entry.entry_category == "Legends"

