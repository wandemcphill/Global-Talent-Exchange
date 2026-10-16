"""Rivalry match history is cross-club state and needs an authorized writer.

``POST /api/rivalries/matches`` took no authentication dependency at all, so any
anonymous caller could name two club ids and persist a fabricated result into
their shared rivalry record — inflating intensity, derby and giant-killer
markers that other surfaces read back as competitive history.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from app.club_social.router import router as club_social_router
from app.db import get_session
from app.models.club_social import RivalryMatchHistory, RivalryProfile
from app.models.user import User


def _payload(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "home_club_id": "club-alpha",
        "away_club_id": "club-bravo",
        "home_score": 9,
        "away_score": 0,
        "match_id": "fabricated-match",
    }
    body.update(overrides)
    return body


@pytest.fixture()
def anonymous_client(session: Session):
    """A client with the router mounted but no authenticated identity."""
    application = FastAPI()
    application.include_router(club_social_router)

    def override_session():
        yield session

    application.dependency_overrides[get_session] = override_session
    with TestClient(application) as test_client:
        yield test_client


def _rivalry_rows(session: Session) -> tuple[int, int]:
    return (
        session.query(RivalryProfile).count(),
        session.query(RivalryMatchHistory).count(),
    )


def test_anonymous_callers_cannot_record_a_rivalry_match(anonymous_client: TestClient, session: Session) -> None:
    before = _rivalry_rows(session)

    response = anonymous_client.post("/api/rivalries/matches", json=_payload())

    assert response.status_code == 401
    assert _rivalry_rows(session) == before


def test_an_unrelated_club_owner_cannot_record_someone_elses_rivalry_match(
    client: TestClient, session: Session, user_state: dict[str, User]
) -> None:
    # Charlie owns neither Alpha nor Bravo.
    user_state["user"] = session.get(User, "user-charlie")
    before = _rivalry_rows(session)

    response = client.post("/api/rivalries/matches", json=_payload())

    assert response.status_code == 403
    assert response.json()["detail"] == "club_owner_required"
    assert _rivalry_rows(session) == before


def test_the_home_club_owner_can_record_the_match(client: TestClient, session: Session) -> None:
    response = client.post("/api/rivalries/matches", json=_payload())

    assert response.status_code == 201
    session.expire_all()
    profile_count, history_count = _rivalry_rows(session)
    assert profile_count == 1
    assert history_count == 1


def test_the_away_club_owner_can_also_record_the_match(
    client: TestClient, session: Session, user_state: dict[str, User]
) -> None:
    user_state["user"] = session.get(User, "user-bravo")

    response = client.post("/api/rivalries/matches", json=_payload())

    assert response.status_code == 201
    session.expire_all()
    assert _rivalry_rows(session) == (1, 1)


def test_recording_the_same_match_twice_does_not_duplicate_history(client: TestClient, session: Session) -> None:
    assert client.post("/api/rivalries/matches", json=_payload()).status_code == 201
    assert client.post("/api/rivalries/matches", json=_payload()).status_code == 201

    session.expire_all()
    assert _rivalry_rows(session) == (1, 1)
    profile = session.query(RivalryProfile).one()
    assert profile.matches_played == 1


def test_an_unknown_club_is_reported_as_not_found_without_writing(client: TestClient, session: Session) -> None:
    before = _rivalry_rows(session)

    response = client.post("/api/rivalries/matches", json=_payload(away_club_id="club-missing"))

    assert response.status_code == 404
    assert _rivalry_rows(session) == before
