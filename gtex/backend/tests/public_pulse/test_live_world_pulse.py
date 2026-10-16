from __future__ import annotations

from datetime import timedelta

import app.models  # noqa: F401
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base, utcnow
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.user import User
from app.public_pulse.service import PublicPulseService


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


def test_live_world_pulse_counts_clubs_and_recent_logins(session) -> None:
    now = utcnow()
    active = User(
        email="online@gtex.test",
        username="online_user",
        password_hash="x",
        last_login_at=now,
    )
    stale = User(
        email="stale@gtex.test",
        username="stale_user",
        password_hash="x",
        last_login_at=now - timedelta(minutes=30),
    )
    session.add_all([active, stale])
    session.flush()
    session.add(
        ClubProfile(
            owner_user_id=active.id,
            club_name="Pulse FC",
            short_name="PFC",
            slug="pulse-fc",
            country_code="NG",
            club_type=ClubType.COMMUNITY,
            lifecycle_status=ClubLifecycleStatus.ACTIVE,
            primary_color="#111111",
            secondary_color="#222222",
            accent_color="#333333",
        )
    )
    session.commit()

    pulse = PublicPulseService(session).live_world_pulse()
    assert pulse.clubs_on_gtex == 1
    assert pulse.users_online == 1
    assert pulse.players_online == 0
    assert pulse.labels["clubs_on_gtex"]
