from __future__ import annotations

from decimal import Decimal
import uuid
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import get_current_user, get_session
from app.models import Base
from app.models.club_profile import ClubProfile
from app.models.user import User, UserRole
from app.owner_console.models import OwnerClubState
from app.owner_console.router import router as owner_router
from app.owner_console import ledger
from app.live_matches.service import ensure_live_match_hub


def _build_test_app(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'gifting_test.db'}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    app = FastAPI()
    app.state.session_factory = SessionLocal
    # Ensure LiveMatchHub is initialized on app
    hub = ensure_live_match_hub(app)

    with SessionLocal() as session:
        user = User(
            id=str(uuid.uuid4()),
            email="fan@gtex.test",
            username="superfan99",
            display_name="Super Fan 99",
            full_name="Super Fan 99",
            role=UserRole.USER,
            is_active=True,
            password_hash="pw_mock",
        )
        session.add(user)
        session.flush()

        club = ClubProfile(
            id=str(uuid.uuid4()),
            owner_user_id=user.id,
            club_name="Arsenal London",
            short_name="ARS",
            slug=f"arsenal-{uuid.uuid4().hex[:6]}",
            country_code="GB",
            primary_color="#EE0000",
            secondary_color="#FFFFFF",
            accent_color="#FFD700",
        )
        session.add(club)
        session.flush()

        state = OwnerClubState(
            club_id=club.id,
            owner_user_id=user.id,
            club_name=club.club_name,
            stage="active",
            fans=1000,
        )
        session.add(state)
        session.flush()

        # Fund user with Fan Coin
        ledger.record(
            session,
            event_type="credit_funding",
            source=ledger.PLATFORM_GRANTS,
            destination=ledger.user_account(user.id),
            currency=ledger.FAN,
            gross=Decimal("5000"),
            fee_bps=0,
            user_id=user.id,
            memo="Test Fan Coin grant",
        )
        session.commit()

        user_id = user.id
        club_id = club.id

    def override_get_user():
        with SessionLocal() as session:
            return session.get(User, user_id)

    def override_get_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_current_user] = override_get_user
    app.dependency_overrides[get_session] = override_get_session
    app.include_router(owner_router)

    return app, user_id, club_id, hub


def test_react_match_center_gifting_broadcasts_live_event(tmp_path):
    app, user_id, club_id, hub = _build_test_app(tmp_path)
    client = TestClient(app)
    match_id = f"match-{uuid.uuid4().hex[:8]}"

    # Send 'stadium_roar' gift
    res = client.post(
        "/owner/gifts/send",
        json={
            "club_id": club_id,
            "gift_code": "stadium_roar",
            "match_id": match_id,
        },
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["sender"] == "superfan99"
    assert data["gift"]["name"] == "Stadium Roar"
    assert "broadcast" in data
    broadcast = data["broadcast"]
    assert broadcast["match_id"] == match_id
    assert broadcast["club_id"] == club_id
    assert broadcast["gift_code"] == "stadium_roar"
    assert broadcast["animation_key"] == "fan_chant"
    assert broadcast["sound_key"] == "crowd_roar"

    # Verify LiveMatchHub recorded the gift for spectators and live match center
    recent = hub.get_recent_gifts(match_id)
    assert len(recent) == 1
    assert recent[0]["sender"] == "superfan99"
    assert recent[0]["gift_name"] == "Stadium Roar"
    assert recent[0]["cost"] == 10
