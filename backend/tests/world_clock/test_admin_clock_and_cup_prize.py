from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_admin, get_session
from app.models import Base
import app.models  # noqa: F401
from app.models.national_team import NationalTeamCompetition
from app.models.user import User, UserRole
from app.models.wallet import LedgerAccount
from app.national_team_engine.named_cup_prize import cup_prize_account_code, set_named_cup_prize
from app.national_team_engine.router import admin_router as national_admin_router
from app.world_simulation.router import admin_router as world_admin_router


def _db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()


def test_admin_can_pause_resume_and_change_clock_speed() -> None:
    session = _db()
    admin = User(
        id="admin-clock",
        email="clock@example.com",
        username="clockadmin",
        display_name="Clock Admin",
        password_hash="not-used",  # pragma: allowlist secret
        role=UserRole.ADMIN,
    )
    session.add(admin)
    session.commit()
    app = FastAPI()
    app.include_router(world_admin_router)

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_admin] = lambda: admin
    client = TestClient(app)

    paused = client.post("/admin/world/clock/pause")
    assert paused.status_code == 200, paused.text
    assert paused.json()["is_paused"] is True

    running = client.post("/admin/world/clock/resume")
    assert running.status_code == 200, running.text
    assert running.json()["is_paused"] is False

    faster = client.post("/admin/world/clock/speed", json={"progression_rate": 2})
    assert faster.status_code == 200, faster.text
    assert faster.json()["progression_rate"] == 2

    rejected = client.post("/admin/world/clock/speed", json={"progression_rate": 0})
    assert rejected.status_code == 422


def test_admin_puts_prize_coin_aside_for_a_named_cup() -> None:
    session = _db()
    admin = User(
        id="admin-prize",
        email="prize@example.com",
        username="prizeadmin",
        display_name="Prize Admin",
        password_hash="not-used",  # pragma: allowlist secret
        role=UserRole.ADMIN,
    )
    cup = NationalTeamCompetition(
        id="cup-afcon",
        key="afcon-2026",
        title="AFCON",
        season_label="2026",
        age_band="senior",
        metadata_json={},
    )
    session.add(admin)
    session.add(cup)
    session.commit()

    saved = set_named_cup_prize(
        session,
        competition_id="cup-afcon",
        actor=admin,
        first="1000",
        second="500",
        third="250",
    )
    session.commit()
    assert saved["first"] == "1000.0000"
    assert saved["held_coin"] == "1750.0000"
    account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == cup_prize_account_code("cup-afcon")))
    assert account is not None

    app = FastAPI()
    app.include_router(national_admin_router)

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_admin] = lambda: admin
    client = TestClient(app)
    listed = client.get("/admin/national-team-engine/cups")
    assert listed.status_code == 200, listed.text
    assert listed.json()[0]["title"] == "AFCON"
    updated = client.put(
        "/admin/national-team-engine/cups/cup-afcon/prize",
        json={"first": 2000, "second": 800, "third": 400},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["held_coin"] == "3200.0000"
