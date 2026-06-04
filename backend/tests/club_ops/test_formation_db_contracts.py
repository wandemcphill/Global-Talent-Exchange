from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models as _app_models  # noqa: F401
from app.access_control.service import AccessControlService
from app.auth.dependencies import get_current_user, get_session
from app.ingestion.models import Player
from app.models.base import Base
from app.models.club_formation import ClubFormation, ClubFormationAuditEvent
from app.models.club_profile import ClubProfile
from app.models.user import User, UserRole
from app.routes.club_ops import router as club_ops_router
from app.services.club_squad_sources_service import ClubSquadSourcesService


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def db_backed_club_ops_client(db_session: Session) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(club_ops_router)

    def _session_override() -> Iterator[Session]:
        yield db_session

    def _current_user_override() -> User:
        user = db_session.get(User, "club-owner")
        assert user is not None
        AccessControlService(db_session).bind_user_access_context(user)
        return user

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[get_current_user] = _current_user_override
    with TestClient(app) as client:
        yield client


def test_club_ops_formation_routes_persist_to_durable_table(
    db_backed_club_ops_client: TestClient,
    db_session: Session,
) -> None:
    club_id = _seed_club_context(db_session)

    draft_response = db_backed_club_ops_client.post(
        f"/api/v2/clubs/{club_id}/formations/draft",
        json=_formation_payload(_player_ids()),
    )
    assert draft_response.status_code == 200, draft_response.text
    draft = draft_response.json()["formation"]
    assert draft["status"] == "draft"
    assert draft["audit_trail"][0]["action"] == "club_formation.draft_saved"
    assert draft["health"]["blockers"] == []
    assert draft["can_publish"] is True

    persisted_draft = db_session.get(ClubFormation, draft["id"])
    assert persisted_draft is not None
    assert persisted_draft.club_id == club_id
    assert persisted_draft.status == "draft"
    assert persisted_draft.validation_blockers_json == []

    publish_response = db_backed_club_ops_client.post(
        f"/api/v2/clubs/{club_id}/formations/{draft['id']}/publish",
    )
    assert publish_response.status_code == 200, publish_response.text
    published = publish_response.json()["formation"]
    assert published["status"] == "published"
    assert published["audit_ref"].startswith(f"formation:{draft['id']}:published")
    assert [event["action"] for event in published["audit_trail"]] == [
        "club_formation.draft_saved",
        "club_formation.published",
    ]
    assert published["published_by"] == "club-owner"

    audit_events = db_session.query(ClubFormationAuditEvent).filter_by(formation_id=draft["id"]).all()
    assert [event.action for event in audit_events] == [
        "club_formation.draft_saved",
        "club_formation.published",
    ]

    active_response = db_backed_club_ops_client.get(f"/api/v2/clubs/{club_id}/formation/active")
    assert active_response.status_code == 200
    assert active_response.json()["formation"]["id"] == draft["id"]

    history_response = db_backed_club_ops_client.get(f"/api/v2/clubs/{club_id}/formations")
    assert history_response.status_code == 200
    assert any(item["id"] == draft["id"] for item in history_response.json()["items"])

    restore_response = db_backed_club_ops_client.post(
        f"/api/v2/clubs/{club_id}/formations/{draft['id']}/restore",
    )
    assert restore_response.status_code == 200, restore_response.text
    restored = restore_response.json()["formation"]
    assert restored["status"] == "draft"
    assert restored["id"] != draft["id"]
    assert restored["audit_trail"][0]["action"] == "club_formation.restored"

    persisted_restore = db_session.get(ClubFormation, restored["id"])
    assert persisted_restore is not None
    assert persisted_restore.source_formation_id == draft["id"]


def test_club_ops_formation_publish_blocks_invalid_durable_shape(
    db_backed_club_ops_client: TestClient,
    db_session: Session,
) -> None:
    club_id = _seed_club_context(db_session)
    player_ids = _player_ids()
    invalid_payload = _formation_payload(player_ids)
    slots = list(invalid_payload["slots"])
    slots[1] = {**slots[1], "assigned_player_id": player_ids[0]}
    slots[3] = {key: value for key, value in slots[3].items() if key != "x"}
    invalid_payload["slots"] = slots

    draft_response = db_backed_club_ops_client.post(
        f"/api/v2/clubs/{club_id}/formations/draft",
        json=invalid_payload,
    )
    assert draft_response.status_code == 200, draft_response.text
    draft = draft_response.json()["formation"]
    assert draft["can_publish"] is False
    assert "Publish requires unique player assignments." in draft["health"]["blockers"]
    assert "slot-4" in " ".join(draft["health"]["blockers"])

    publish_response = db_backed_club_ops_client.post(
        f"/api/v2/clubs/{club_id}/formations/{draft['id']}/publish",
    )

    assert publish_response.status_code == 409
    detail = publish_response.json()["detail"]
    assert detail["code"] == "formation_publish_blocked"
    assert "Publish requires unique player assignments." in detail["blockers"]
    assert "slot-4" in " ".join(detail["blockers"])


def _seed_club_context(session: Session) -> str:
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
    for index, position in enumerate(_POSITIONS):
        session.add(
            Player(
                id=f"player-{index + 1}",
                source_provider="club-ops-db-contract",
                provider_external_id=f"club-ops-db-contract-{index + 1}",
                full_name=f"Contract Player {index + 1}",
                canonical_display_name=f"Contract Player {index + 1}",
                position=position,
                normalized_position=position,
                current_club_profile_id=club.id,
                morale=78.0,
                profile_completeness_score=82.0,
                dna_profile={"contract_end": "2028-06-30"},
            )
        )
    session.flush()
    _seed_squad_sources(session, club_id=club.id)
    session.commit()
    return club.id


def _seed_squad_sources(session: Session, *, club_id: str) -> None:
    service = ClubSquadSourcesService(session)
    today = date.today()
    for player_id in _player_ids():
        service.upsert_medical_status(club_id=club_id, player_id=player_id, status="cleared")
        service.upsert_player_sources(
            club_id=club_id,
            player_id=player_id,
            morale_score=76,
            chemistry_overall_score=84,
            chemistry_position_fit=84,
            chemistry_team_fit=84,
            source_ref="formation-test",
        )
        service.upsert_contract(
            club_id=club_id,
            player_id=player_id,
            signed_on=today - timedelta(days=30),
            starts_on=today - timedelta(days=30),
            ends_on=today + timedelta(days=730),
            status="active",
        )


def _player_ids() -> list[str]:
    return [f"player-{index + 1}" for index in range(len(_POSITIONS))]


def _formation_payload(player_ids: list[str]) -> dict[str, object]:
    return {
        "name": "Contract XI",
        "scheme": "4-3-3",
        "slots": [
            {
                "slot_id": f"slot-{index + 1}",
                "position": _SLOT_POSITIONS[index],
                "assigned_player_id": player_id,
                "x": float((index % 4) + 1),
                "y": float((index // 4) + 1),
                "role": "balanced",
                "filled": True,
            }
            for index, player_id in enumerate(player_ids)
        ],
    }


_POSITIONS = (
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

_SLOT_POSITIONS = ("GK", "LB", "CB", "CB", "RB", "CM", "CM", "AM", "LW", "ST", "RW")
