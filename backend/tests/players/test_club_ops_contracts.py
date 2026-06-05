from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.models as _app_models  # noqa: F401
from app.access_control.service import AccessControlService
from app.auth.dependencies import get_current_user, get_session
from app.ingestion.models import Player
from app.models.club_profile import ClubProfile
from app.models.club_formation import ClubFormation  # noqa: F401
from app.models.user import User, UserRole
from app.routes.club_ops import router as club_ops_router
from app.services.club_squad_sources_service import ClubSquadSourcesService


@pytest.fixture()
def club_ops_session(gtex_db_session: Session) -> Iterator[Session]:
    # Shared session-scoped schema (tests/conftest.py::gtex_db_engine) with
    # per-test rollback, instead of rebuilding all ~567 tables per test.
    yield gtex_db_session


@pytest.fixture()
def club_ops_api(club_ops_session: Session) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(club_ops_router)

    def _session_override() -> Iterator[Session]:
        yield club_ops_session

    def _current_user_override() -> User:
        user = club_ops_session.get(User, "club-owner")
        assert user is not None
        AccessControlService(club_ops_session).bind_user_access_context(user)
        return user

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[get_current_user] = _current_user_override
    with TestClient(app) as client:
        yield client


def test_club_ops_squad_and_formation_contracts_use_backend_players(
    club_ops_api: TestClient,
    club_ops_session: Session,
) -> None:
    club_id = _seed_club_context(club_ops_session, player_count=10)

    selection_ready = club_ops_api.get(f"/api/clubs/{club_id}/squad/selection-ready")
    assert selection_ready.status_code == 200
    assert selection_ready.json()["state"] == "ready"
    assert len(selection_ready.json()["players"]) == 10

    roster = club_ops_api.get(f"/api/clubs/{club_id}/squad")
    assert roster.status_code == 200
    assert roster.json()["selection_ready_count"] == 10

    blocked_draft = club_ops_api.post(
        f"/api/v2/clubs/{club_id}/formations/draft",
        json=_formation_payload(_player_ids(10)),
    )
    assert blocked_draft.status_code == 200
    blocked_formation_id = blocked_draft.json()["formation"]["id"]

    blocked_publish = club_ops_api.post(f"/api/v2/clubs/{club_id}/formations/{blocked_formation_id}/publish")
    assert blocked_publish.status_code == 409
    assert blocked_publish.json()["detail"]["reason"] == (
        "Insufficient eligible players - update squad before editing formation."
    )
    assert blocked_publish.json()["detail"]["eligible_player_count"] == 10

    _add_player(club_ops_session, club_id=club_id, index=10)
    club_ops_session.commit()

    ready = club_ops_api.get(f"/api/clubs/{club_id}/squad/selection-ready")
    assert ready.status_code == 200
    assert len(ready.json()["players"]) == 11

    draft = club_ops_api.post(
        f"/api/v2/clubs/{club_id}/formations/draft",
        json=_formation_payload(_player_ids(11)),
    )
    assert draft.status_code == 200
    formation = draft.json()["formation"]
    assert formation["status"] == "draft"
    assert len(formation["slots"]) == 11

    published = club_ops_api.post(f"/api/v2/clubs/{club_id}/formations/{formation['id']}/publish")
    assert published.status_code == 200
    published_formation = published.json()["formation"]
    assert published_formation["status"] == "published"
    assert published_formation["audit_ref"].startswith(f"formation:{formation['id']}:published:")

    active = club_ops_api.get(f"/api/v2/clubs/{club_id}/formation/active")
    assert active.status_code == 200
    assert active.json()["formation"]["id"] == formation["id"]

    history = club_ops_api.get(f"/api/v2/clubs/{club_id}/formations")
    assert history.status_code == 200
    assert any(item["id"] == formation["id"] for item in history.json()["items"])

    detail = club_ops_api.get(f"/api/v2/formations/{formation['id']}")
    assert detail.status_code == 200
    assert detail.json()["formation"]["id"] == formation["id"]

    restored = club_ops_api.post(f"/api/v2/clubs/{club_id}/formations/{formation['id']}/restore")
    assert restored.status_code == 200
    restored_formation = restored.json()["formation"]
    assert restored_formation["status"] == "draft"
    persisted_restore = club_ops_session.get(ClubFormation, restored_formation["id"])
    assert persisted_restore is not None
    assert persisted_restore.source_formation_id == formation["id"]


def _seed_club_context(session: Session, *, player_count: int) -> str:
    owner = User(
        id="club-owner",
        email="club.owner@example.com",
        username="club-owner",
        display_name="Club Owner",
        password_hash="x",
        role=UserRole.USER,
    )
    club = ClubProfile(
        id="club-profile-contract",
        owner_user_id=owner.id,
        club_name="Contract FC",
        short_name="CFC",
        slug="contract-fc",
        primary_color="#102030",
        secondary_color="#405060",
        accent_color="#d0e0f0",
        country_code="NG",
        region_name="Lagos",
        city_name="Lagos",
    )
    session.add_all([owner, club])
    session.flush()
    AccessControlService(session).ensure_club_organization(club, owner_user_id=owner.id)
    for index in range(player_count):
        _add_player(session, club_id=club.id, index=index)
    session.commit()
    return club.id


def _add_player(session: Session, *, club_id: str, index: int) -> None:
    positions = (
        "goalkeeper",
        "defender",
        "defender",
        "defender",
        "defender",
        "midfielder",
        "midfielder",
        "midfielder",
        "forward",
        "forward",
        "forward",
    )
    player = Player(
        id=f"player-{index + 1}",
        source_provider="club-ops-contract",
        provider_external_id=f"club-ops-contract-{index + 1}",
        full_name=f"Contract Player {index + 1}",
        canonical_display_name=f"Contract Player {index + 1}",
        position=positions[index],
        normalized_position=positions[index],
        current_club_profile_id=club_id,
        morale=78.0,
        profile_completeness_score=82.0,
        dna_profile={"contract_end": "2028-06-30"},
    )
    session.add(player)
    session.flush()
    _seed_player_sources(session, club_id=club_id, player_id=player.id)


def _seed_player_sources(session: Session, *, club_id: str, player_id: str) -> None:
    service = ClubSquadSourcesService(session)
    today = date.today()
    service.upsert_medical_status(club_id=club_id, player_id=player_id, status="cleared")
    service.upsert_player_sources(
        club_id=club_id,
        player_id=player_id,
        morale_score=78,
        chemistry_overall_score=82,
        chemistry_position_fit=82,
        chemistry_team_fit=82,
        source_ref="players-contract-test",
    )
    service.upsert_contract(
        club_id=club_id,
        player_id=player_id,
        signed_on=today - timedelta(days=30),
        starts_on=today - timedelta(days=30),
        ends_on=today + timedelta(days=730),
        status="active",
    )


def _player_ids(count: int) -> list[str]:
    return [f"player-{index + 1}" for index in range(count)]


def _formation_payload(player_ids: list[str]) -> dict[str, object]:
    positions = (
        "GK",
        "LB",
        "CB",
        "CB",
        "RB",
        "CM",
        "CM",
        "AM",
        "LW",
        "ST",
        "RW",
    )
    slots = [
        {
            "slot_id": f"slot-{index + 1}",
            "position": positions[index],
            "assigned_player_id": player_id,
            "x": float((index % 4) + 1),
            "y": float((index // 4) + 1),
            "role": "balanced",
            "filled": True,
        }
        for index, player_id in enumerate(player_ids)
    ]
    return {
        "name": "Contract XI",
        "scheme": "4-3-3",
        "slots": slots,
    }
