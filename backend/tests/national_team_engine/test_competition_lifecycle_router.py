from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.ingestion.models import Country
from app.models import Base
from app.models.competition import UserCompetition
from app.models.national_team import NationalTeamCompetition, NationalTeamCompetitionEntry
from app.models.user import User, UserRole
from app.national_team_engine.router import admin_router, router


def _build_app(database_path: Path) -> tuple[TestClient, sessionmaker, dict[str, User]]:
    engine = create_engine(f"sqlite:///{database_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            UserCompetition.__table__,
            Country.__table__,
            NationalTeamCompetition.__table__,
            NationalTeamCompetitionEntry.__table__,
        ],
    )

    with SessionLocal() as session:
        admin = User(
            email="admin@example.com",
            username="admin",
            display_name="Admin",
            password_hash="not-used",
            role=UserRole.ADMIN,
        )
        user_one = User(
            email="user1@example.com",
            username="user1",
            display_name="User One",
            password_hash="not-used",
        )
        user_two = User(
            email="user2@example.com",
            username="user2",
            display_name="User Two",
            password_hash="not-used",
        )
        session.add_all(
            [
                admin,
                user_one,
                user_two,
                Country(
                    source_provider="test",
                    provider_external_id="ng",
                    name="Nigeria",
                    alpha2_code="NG",
                    fifa_code="NGA",
                    confederation_code="CAF",
                ),
                Country(
                    source_provider="test",
                    provider_external_id="gh",
                    name="Ghana",
                    alpha2_code="GH",
                    fifa_code="GHA",
                    confederation_code="CAF",
                ),
            ]
        )
        session.flush()
        competition = NationalTeamCompetition(
            key="gtex-u17-afcon-router",
            title="GTEX U17 AFCON Router",
            season_label="2031",
            region_type="afcon",
            age_band="u17",
            format_type="cup",
            status="published",
            metadata_json={
                "competition_family": "afcon",
                "minimum_squad_size": 2,
                "maximum_squad_size": 3,
                "competition_engine": {
                    "tournament_slots": 2,
                    "group_size": 2,
                    "advance_per_group": 1,
                    "best_third_slots": 0,
                    "qualifier_group_size": 2,
                    "preferred_cycle_week": 1,
                    "schedule_label": "Week 1 -> U17 AFCON",
                },
            },
            created_by_user_id=admin.id,
        )
        session.add(competition)
        session.commit()

    current_user_holder = {"user": None}

    app = FastAPI()
    app.include_router(router)
    app.include_router(admin_router)

    def override_get_session():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def override_get_current_user():
        return current_user_holder["user"]

    def override_get_current_admin():
        return admin

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_admin] = override_get_current_admin
    client = TestClient(app)
    return client, SessionLocal, {
        "admin": admin,
        "user_one": user_one,
        "user_two": user_two,
        "competition": competition,
        "holder": current_user_holder,
    }


def test_lifecycle_routes_submit_lock_advance_and_read(tmp_path: Path) -> None:
    client, _session_factory, context = _build_app(tmp_path / "lifecycle-router.db")
    try:
        competition_id = context["competition"].id
        holder = context["holder"]

        holder["user"] = context["user_one"]
        invalid = client.post(
            f"/national-team-engine/competitions/{competition_id}/entries",
            json={
                "country_code": "NG",
                "country_name": "Nigeria",
                "squad": [
                    {"player_name": "Too Old", "age": 18, "overall_rating": 77},
                    {"player_name": "Valid", "age": 16, "overall_rating": 74},
                ],
            },
        )
        assert invalid.status_code == 409, invalid.text
        assert invalid.json()["detail"] == "invalid_squad_age"

        valid_payloads = [
            (
                context["user_one"],
                {
                    "country_code": "NG",
                    "country_name": "Nigeria",
                    "squad": [
                        {"player_name": "Nigeria One", "age": 17, "overall_rating": 80},
                        {"player_name": "Nigeria Two", "age": 16, "overall_rating": 78},
                    ],
                },
            ),
            (
                context["user_two"],
                {
                    "country_code": "GH",
                    "country_name": "Ghana",
                    "squad": [
                        {"player_name": "Ghana One", "age": 17, "overall_rating": 75},
                        {"player_name": "Ghana Two", "age": 16, "overall_rating": 74},
                    ],
                },
            ),
        ]
        for user, payload in valid_payloads:
            holder["user"] = user
            response = client.post(
                f"/national-team-engine/competitions/{competition_id}/entries",
                json=payload,
            )
            assert response.status_code == 200, response.text
            assert response.json()["locked"] is False

        locked = client.post(f"/admin/national-team-engine/competitions/{competition_id}/entries/lock")
        assert locked.status_code == 200, locked.text
        assert locked.json()["current_stage"] == "tournament"

        advanced = client.post(f"/admin/national-team-engine/competitions/{competition_id}/lifecycle/advance")
        assert advanced.status_code == 200, advanced.text
        assert advanced.json()["current_stage"] == "completed"
        assert advanced.json()["champion_entry_id"] is not None

        lifecycle = client.get(f"/national-team-engine/competitions/{competition_id}/lifecycle")
        assert lifecycle.status_code == 200, lifecycle.text
        body = lifecycle.json()
        assert body["current_stage"] == "completed"
        assert len(body["submitted_entries"]) == 2
        assert body["schedule_plan"][0]["week"] == 1
    finally:
        client.close()
