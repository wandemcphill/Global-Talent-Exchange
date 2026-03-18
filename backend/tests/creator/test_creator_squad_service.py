from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.club_identity.models.reputation  # noqa: F401
import backend.app.ingestion.models  # noqa: F401
import backend.app.models  # noqa: F401
from backend.app.common.enums.creator_profile_status import CreatorProfileStatus
from backend.app.models.base import Base
from backend.app.models.club_profile import ClubProfile
from backend.app.models.creator_profile import CreatorProfile
from backend.app.models.creator_provisioning import CreatorSquad
from backend.app.models.user import User
from backend.app.services.creator_squad_service import CreatorSquadLimitError, CreatorSquadService


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


def test_creator_squad_limit_enforcement(session) -> None:
    user = User(id="creator-user", email="creator@example.com", username="creator", password_hash="hashed")
    session.add(user)
    session.flush()
    creator_profile = CreatorProfile(
        id="creator-profile",
        user_id=user.id,
        handle="creator",
        display_name="Creator",
        tier="emerging",
        status=CreatorProfileStatus.ACTIVE,
    )
    club = ClubProfile(
        id="club-1",
        owner_user_id=user.id,
        club_name="Creator FC",
        short_name="CRTR",
        slug="creator-fc",
        primary_color="#112233",
        secondary_color="#223344",
        accent_color="#334455",
        visibility="public",
    )
    squad = CreatorSquad(
        id="squad-1",
        club_id=club.id,
        creator_profile_id=creator_profile.id,
        first_team_limit=25,
        academy_limit=30,
        total_limit=55,
        first_team_json=[],
        academy_json=[],
        metadata_json={},
    )
    session.add_all([creator_profile, club, squad])
    session.flush()

    service = CreatorSquadService(session=session)
    for index in range(25):
        service.add_player_payload(
            squad=squad,
            squad_bucket="first_team",
            payload={"regen_id": f"ft-{index}", "player_name": f"First Team {index}"},
        )
    for index in range(30):
        service.add_player_payload(
            squad=squad,
            squad_bucket="academy",
            payload={"regen_id": f"ac-{index}", "player_name": f"Academy {index}"},
        )

    assert len(squad.first_team_json) == 25
    assert len(squad.academy_json) == 30

    with pytest.raises(CreatorSquadLimitError):
        service.add_player_payload(
            squad=squad,
            squad_bucket="academy",
            payload={"regen_id": "overflow", "player_name": "Overflow Academy"},
        )
