from __future__ import annotations

from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_session
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.regen import RegenLegacyRecord
from app.models.regen_ecosystem import RegenBloodlineLink
from app.models.user import KycStatus, User, UserRole
from app.regen_ecosystem.router import router as regen_ecosystem_router
from app.regen_universe.models import RegenAward, RegenSeason


@pytest.fixture()
def regen_api():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    app = FastAPI()
    app.include_router(regen_ecosystem_router)

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session

    with TestClient(app) as client:
        yield client, session_factory

    engine.dispose()


def _seed_regen_context(app_session_factory: sessionmaker) -> dict[str, str]:
    with app_session_factory() as session:
        user = User(
            id="user-regen-owner",
            email="regen-owner@example.com",
            username="regen-owner",
            password_hash="hash",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
        )
        club = ClubProfile(
            id="club-regen",
            owner_user_id=user.id,
            club_name="Regen FC",
            short_name="RFC",
            slug="regen-fc",
            primary_color="#112233",
            secondary_color="#ddeeff",
            accent_color="#ff9900",
            country_code="NG",
            region_name="Lagos",
            city_name="Lagos",
        )
        season = RegenSeason(
            id="season-regen",
            season_number=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_active=True,
            metadata_json={},
        )
        award = RegenAward(
            id="award-future-star",
            code="future_star",
            name="Future Star",
            description="Best emerging regen",
            category="seasonal",
            ranking_category="overall",
            eligibility_rules_json={},
            is_regen_only=True,
            sort_order=1,
            metadata_json={},
        )
        session.add_all([user, club, season, award])
        session.commit()
    return {"user_id": user.id, "club_id": club.id, "season_id": season.id, "award_id": award.id}


def test_regen_ecosystem_end_to_end(regen_api) -> None:
    client, app_session_factory = regen_api
    seeded = _seed_regen_context(app_session_factory)

    academy_response = client.post(
        "/academy",
        json={
            "club_user_id": seeded["user_id"],
            "club_id": seeded["club_id"],
            "level": 4,
            "scouting_regions": ["Lagos", "Nigeria"],
            "capacity": 2,
            "upgrade_cost": 250000,
        },
    )
    assert academy_response.status_code == 201
    assert academy_response.json()["capacity"] == 2

    generate_response = client.post(
        "/academy/generate",
        json={
            "club_user_id": seeded["user_id"],
            "club_id": seeded["club_id"],
            "season_label": "2026/2027",
        },
    )
    assert generate_response.status_code == 200
    generated_payload = generate_response.json()
    assert generated_payload["generated_count"] == 2
    generated_players = generated_payload["generated_players"]
    assert all(player["rarity_tier"] in {"common", "rare", "elite", "generational"} for player in generated_players)

    scout_response = client.post(
        "/scouts",
        json={
            "club_user_id": seeded["user_id"],
            "club_id": seeded["club_id"],
            "region": "Lagos",
            "skill_rating": 86,
            "specialty": "youth",
        },
    )
    assert scout_response.status_code == 201
    scout_id = scout_response.json()["id"]

    discover_response = client.post(f"/scouts/{scout_id}/discover?limit=5")
    assert discover_response.status_code == 200
    assert discover_response.json()["discovery_probability"] > 0

    player_id = generated_players[0]["player_id"]
    candidate_id = generated_players[0]["academy_candidate_id"]
    report_response = client.get(f"/scout/report/{player_id}?scout_id={scout_id}")
    assert report_response.status_code == 200
    report_payload = report_response.json()
    assert report_payload["accuracy"] == 86
    assert set(report_payload["visible_stats"].keys()) == {"technical", "physical", "mental", "tactical"}
    assert set(report_payload["hidden_stats"].keys()) == {"consistency", "injury_proneness", "clutch_factor", "growth_variance"}

    promote_response = client.post(f"/academy/promote/{candidate_id}")
    assert promote_response.status_code == 200
    assert promote_response.json()["promoted"] is True
    assert promote_response.json()["contract_id"] is not None

    agent_response = client.post(
        "/agents",
        json={
            "name": "Momentum Sports",
            "negotiation_skill": 78,
            "player_ids": [player_id],
        },
    )
    assert agent_response.status_code == 201
    assert agent_response.json()["player_ids"] == [player_id]

    career_event_response = client.post(f"/players/{player_id}/career-events?event_type=injury")
    assert career_event_response.status_code == 200
    assert career_event_response.json()["type"] == "injury"

    second_regen_profile_id = generated_players[1]["regen_profile_id"]
    parent_regen_profile_id = generated_players[0]["regen_profile_id"]
    with app_session_factory() as session:
        legacy = RegenLegacyRecord(
            regen_id=parent_regen_profile_id,
            player_id=player_id,
            club_id=seeded["club_id"],
            legacy_score=150.0,
            legacy_tier="legend",
            is_legend=True,
            metadata_json={},
        )
        session.add(legacy)
        session.flush()
        session.add(
            RegenBloodlineLink(
                regen_profile_id=second_regen_profile_id,
                parent_legacy_id=legacy.id,
                lineage_depth=1,
                metadata_json={},
            )
        )
        session.commit()

    lineage_response = client.get(f"/regens/{second_regen_profile_id}/lineage")
    assert lineage_response.status_code == 200
    chain = lineage_response.json()["chain"]
    assert chain[0]["regen_profile_id"] == second_regen_profile_id
    assert chain[0]["parent_legacy_id"] is not None

    awards_response = client.get("/regens/awards")
    assert awards_response.status_code == 200
    assert awards_response.json()[0]["award_code"] == "future_star"

    vote_response = client.post(
        f"/regens/awards/{seeded['award_id']}/vote",
        json={
            "user_id": seeded["user_id"],
            "player_id": player_id,
            "season_id": seeded["season_id"],
        },
    )
    assert vote_response.status_code == 201
    assert vote_response.json()["award_id"] == seeded["award_id"]

    potential_job_response = client.post("/regens/jobs/potential-updates")
    academy_job_response = client.post("/regens/jobs/academy-weekly")

    assert potential_job_response.status_code == 200
    assert academy_job_response.status_code == 200
    assert "updated_count" in potential_job_response.json()["result"]
    assert "academies_processed" in academy_job_response.json()["result"]

    feed_response = client.get("/regens/feed?limit=10")
    top_response = client.get("/regens/top?limit=10")
    rising_response = client.get("/regens/rising?limit=10")

    assert feed_response.status_code == 200
    assert top_response.status_code == 200
    assert rising_response.status_code == 200
    assert any(item["event_type"] == "new_generation" for item in feed_response.json())
    assert len(top_response.json()) >= 1
    assert len(rising_response.json()) >= 1
