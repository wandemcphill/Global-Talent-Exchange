from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.common.enums.injury_severity import InjurySeverity
from app.models.club_profile import ClubProfile
from app.models.player_contract import PlayerContract
from app.models.player_injury_case import PlayerInjuryCase
from app.models.user import User, UserRole
from app.routes.player_lifecycle import router
from tests.players.test_player_lifecycle import seed_base_context


def _client(session: Session, *, user_id: str) -> TestClient:
    app = FastAPI()
    app.include_router(router)

    def _session_override():
        yield session

    def _current_user_override() -> User:
        user = session.get(User, user_id)
        assert user is not None
        return user

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[get_current_user] = _current_user_override
    return TestClient(app)


def _add_user_and_club(session: Session, *, user_id: str, club_id: str) -> ClubProfile:
    user = User(
        id=user_id,
        email=f"{user_id}@example.com",
        username=user_id,
        display_name=user_id.title(),
        password_hash="x",
        role=UserRole.USER,
    )
    club = ClubProfile(
        id=club_id,
        owner_user_id=user.id,
        club_name=club_id.title(),
        short_name=club_id[:3].upper(),
        slug=club_id,
        primary_color="#111111",
        secondary_color="#222222",
        accent_color="#333333",
    )
    session.add_all([user, club])
    session.commit()
    return club


def test_contract_creation_requires_club_owner(lifecycle_session: Session) -> None:
    context = seed_base_context(lifecycle_session)
    _add_user_and_club(lifecycle_session, user_id="contract-attacker", club_id="contract-attacker-club")

    payload = {
        "club_id": context["club_profile_id"],
        "wage_amount": "1000.00",
        "signed_on": "2026-03-12",
        "starts_on": "2026-03-12",
        "ends_on": "2027-03-11",
    }

    with _client(lifecycle_session, user_id="contract-attacker") as client:
        response = client.post(f"/api/players/{context['player_id']}/contracts", json=payload)

    assert response.status_code == 403, response.text
    assert lifecycle_session.scalars(
        select(PlayerContract).where(PlayerContract.player_id == context["player_id"])
    ).all() == []


def test_injury_creation_requires_club_owner(lifecycle_session: Session) -> None:
    context = seed_base_context(lifecycle_session)
    _add_user_and_club(lifecycle_session, user_id="injury-attacker", club_id="injury-attacker-club")

    payload = {
        "club_id": context["club_profile_id"],
        "severity": InjurySeverity.MINOR.value,
        "injury_type": "ankle",
        "occurred_on": "2026-03-12",
    }

    with _client(lifecycle_session, user_id="injury-attacker") as client:
        response = client.post(f"/api/players/{context['player_id']}/injuries", json=payload)

    assert response.status_code == 403, response.text
    assert lifecycle_session.scalars(
        select(PlayerInjuryCase).where(PlayerInjuryCase.player_id == context["player_id"])
    ).all() == []
