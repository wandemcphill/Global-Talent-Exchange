"""GTEX Living Football World - Stage 7
Test Suite: Cinema 3D, Staff Arrivals and Prestige Showroom Engine
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user, get_session
from app.models.base import Base
from app.models.club_growth import (
    ClubStaffAssignment,
    ClubStaffContract,
    ClubStaffProfile,
)
from app.models.club_profile import ClubProfile
from app.models.event_backbone import EventOutbox
from app.models.risk_ops import AuditLog
from app.models.user import User
from app.models.wallet import (
    LedgerAccount,
    LedgerBalanceProjection,
    LedgerEntry,
    LedgerTransaction,
)
from app.owner_console import (
    ledger,
    living_cinema_showroom,
    living_staff_market,
    router as owner_router,
)
from app.owner_console.models import (
    OWNER_CONSOLE_TABLES,
    OwnerClubEvent,
    OwnerClubState,
    OwnerShowroomAsset,
    OwnerSquadPlayer,
)


def _session() -> Session:
    eng = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        eng,
        tables=[
            User.__table__,
            ClubProfile.__table__,
            AuditLog.__table__,
            EventOutbox.__table__,
            LedgerAccount.__table__,
            LedgerBalanceProjection.__table__,
            LedgerEntry.__table__,
            LedgerTransaction.__table__,
            ClubStaffProfile.__table__,
            ClubStaffContract.__table__,
            ClubStaffAssignment.__table__,
            *OWNER_CONSOLE_TABLES,
        ],
    )
    return sessionmaker(bind=eng, autoflush=False, expire_on_commit=False)()


def _bootstrap_club(
    session: Session, user_id: str, club_id: str, prestige: int = 75, commercial_level: int = 2
) -> tuple[User, ClubProfile, OwnerClubState]:
    u = User(
        id=user_id,
        email=f"{user_id}@gtex.test",
        username=f"owner_{user_id}",
        password_hash="synthetic_hash",  # pragma: allowlist secret
        role="authenticated",
        is_active=True,
    )
    cp = ClubProfile(
        id=club_id,
        owner_user_id=user_id,
        club_name=f"FC {club_id}",
        slug=f"fc-{club_id}",
        primary_color="#10B981",
        secondary_color="#0F172A",
        accent_color="#F59E0B",
    )
    session.add_all([u, cp])
    session.flush()

    state = OwnerClubState(
        id=club_id,
        club_id=club_id,
        owner_user_id=user_id,
        club_name=cp.club_name,
        prestige=prestige,
        world_day=15,
        facilities_json={
            "commercial": commercial_level,
            "stadium": 2,
            "academy": 3,
            "_executive_staff": {
                "general_manager": {
                    "id": "staff_gm_1",
                    "name": "Dayo Adeleke",
                    "role": "general_manager",
                    "role_label": "General Manager",
                    "rating": 84,
                    "salary_gtex": 1800,
                    "is_appointed": True,
                }
            },
        },
        manager_json={
            "id": "staff_mgr_1",
            "name": "Emmanuel Amuneke",
            "role": "first_team_manager",
            "rating": 86,
            "salary": 3000,
        },
    )
    session.add(state)
    session.flush()

    # Seed canonical squad player and academy wonderkid regen
    star_player = OwnerSquadPlayer(
        id=f"p_star_{club_id}",
        club_id=club_id,
        name="Chukwudi Agbo",
        position="ST",
        age=25,
        rating=84,
        potential=87,
        value_coin=Decimal("180000"),
        morale=82,
        minutes=900,
        injured_days=0,
        is_regen=False,
    )
    wonderkid_regen = OwnerSquadPlayer(
        id=f"p_regen_{club_id}",
        club_id=club_id,
        name="Kelechi Nwakali Jr",
        position="CAM",
        age=18,
        rating=76,
        potential=91,
        value_coin=Decimal("140000"),
        morale=88,
        minutes=450,
        injured_days=0,
        is_regen=True,
    )
    session.add_all([star_player, wonderkid_regen])
    session.flush()

    # Seed candidates and a funded club treasury for authoritative settlement tests.
    living_staff_market.ensure_staff_market_profiles(session)
    ledger.record(
        session,
        event_type="test_club_funding",
        source=ledger.PLATFORM_GRANTS,
        destination=ledger.club_account(club_id),
        currency=ledger.GTEX,
        gross=2_000_000,
        club_id=club_id,
        user_id=user_id,
        memo="Deterministic test-club treasury funding",
    )

    return u, cp, state


def test_cinema_and_showroom_overview_initialization():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_cin_1", "c_cin_1", prestige=78)

    overview = living_cinema_showroom.get_cinema_and_showroom_overview(session, u.id, cp.id)

    assert overview["club_id"] == cp.id
    assert overview["club_name"] == cp.club_name
    assert len(overview["supported_event_types"]) >= 17

    # Verify 3D prestige showroom catalog has WebGL archetypes
    catalog = overview["prestige_3d_catalog"]
    assert len(catalog) >= 6
    jet = next((item for item in catalog if item["catalog_key"] == "sovereign_900x_jet"), None)
    assert jet is not None
    assert jet["webgl_3d"]["mesh_archetype"] == "private_jet"
    assert jet["webgl_3d"]["scene_id"] == "luxury_inspection_turntable"
    assert "exterior_front" in jet["webgl_3d"]["camera_presets"]
    assert jet["is_owned"] is False

    # Verify canonical players and regens are returned
    players = overview["eligible_players"]
    assert len(players) == 2
    regen = next((p for p in players if p["is_regen"]), None)
    assert regen is not None
    assert regen["name"] == "Kelechi Nwakali Jr"
    assert regen["potential"] == 91


def test_manager_appointment_triggers_verified_arrival_cinematic():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_cin_2", "c_cin_2", prestige=85)

    # Seed staff market profiles and hire a manager
    living_staff_market.ensure_staff_market_profiles(session)
    candidates = living_staff_market.list_staff_market_candidates(
        session, u.id, cp.id, role="first_team_manager", employment_status="unemployed"
    )["candidates"]
    assert len(candidates) >= 1
    target_mgr = candidates[0]

    res = living_staff_market.hire_staff_from_market(
        session=session,
        user_id=u.id,
        club_id=cp.id,
        profile_id=target_mgr["profile_id"],
        role="first_team_manager",
        offered_salary_gtex=target_mgr["expected_salary_gtex"] + 500,
        contract_years=3,
        marquee_wage_premium=True,
    )

    assert res["status"] == "accepted"
    assert res["success"] is True
    assert res["cinematic_event"] is not None

    cin = res["cinematic_event"]
    assert cin["event_type"] == "manager_arrival"
    assert cin["scene_id"] == "manager_arrival"
    assert cin["verified_transaction"] is True
    assert cin["subject_name"] == target_mgr["name"]
    assert cin["contract_id"] == res["contract_id"]

    # Verify durable OwnerClubEvent record exists
    db_events = session.scalars(
        select(OwnerClubEvent).where(
            OwnerClubEvent.club_id == cp.id,
            OwnerClubEvent.category == "cinema",
        )
    ).all()
    assert len(db_events) == 1
    assert db_events[0].event_type == "manager_arrival"


def test_rejected_staff_offer_never_triggers_arrival_cinematic():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_cin_3", "c_cin_3", prestige=40)

    living_staff_market.ensure_staff_market_profiles(session)
    candidates = living_staff_market.list_staff_market_candidates(
        session, u.id, cp.id, role="first_team_manager", employment_status="unemployed"
    )["candidates"]
    target_mgr = candidates[0]

    # Offer tiny wage that will be rejected
    res = living_staff_market.hire_staff_from_market(
        session=session,
        user_id=u.id,
        club_id=cp.id,
        profile_id=target_mgr["profile_id"],
        role="first_team_manager",
        offered_salary_gtex=50,
        contract_years=1,
        marquee_wage_premium=False,
    )

    assert res["success"] is False
    assert res["cinematic_event"] is None

    # Verify zero cinema events were created
    db_events = session.scalars(
        select(OwnerClubEvent).where(
            OwnerClubEvent.club_id == cp.id,
            OwnerClubEvent.category == "cinema",
        )
    ).all()
    assert len(db_events) == 0


def test_trigger_player_and_regen_wonderkid_presentation_preserves_identity():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_cin_4", "c_cin_4", prestige=75)

    res = living_cinema_showroom.trigger_verified_club_cinematic(
        session,
        u.id,
        cp.id,
        event_type="academy_wonderkid",
        subject_id=f"p_regen_{cp.id}",
    )

    assert res["success"] is True
    cin = res["cinematic_event"]
    assert cin["event_type"] == "academy_wonderkid"
    assert cin["scene_id"] == "wonderkid_emergence"
    assert cin["subject_id"] == f"p_regen_{cp.id}"
    assert cin["subject_name"] == "Kelechi Nwakali Jr"
    assert cin["overall_rating"] == 76
    assert cin["potential_rating"] == 91

    # Verify no duplicate player was created
    players = session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == cp.id)).all()
    assert len(players) == 2


def test_prestige_asset_showcase_requires_actual_ownership():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_cin_5", "c_cin_5", prestige=80)

    # 1. Attempting to trigger private jet showcase without owning the asset fails
    with pytest.raises(ValueError, match="does not own active showroom asset"):
        living_cinema_showroom.trigger_verified_club_cinematic(
            session,
            u.id,
            cp.id,
            event_type="private_jet_showcase",
            catalog_key="sovereign_900x_jet",
        )

    # 2. Record authoritative ownership of sovereign_900x_jet
    asset = OwnerShowroomAsset(
        club_id=cp.id,
        owner_user_id=u.id,
        catalog_key="sovereign_900x_jet",
        category="jet",
        custom_name="Lagos Sovereign 900X",
        purchase_price_gtex=Decimal("4800.0"),
        status="active",
    )
    session.add(asset)
    session.flush()

    # 3. Now triggering the 3D showcase succeeds
    res = living_cinema_showroom.trigger_verified_club_cinematic(
        session,
        u.id,
        cp.id,
        event_type="private_jet_showcase",
        catalog_key="sovereign_900x_jet",
    )
    assert res["success"] is True
    cin = res["cinematic_event"]
    assert cin["scene_id"] == "luxury_inspection_turntable"
    assert cin["mesh_archetype"] == "private_jet"
    assert cin["asset_catalog_key"] == "sovereign_900x_jet"
    assert cin["subject_name"] == "Lagos Sovereign 900X"


def test_sponsor_announcement_requires_verified_commercial_record():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_cin_6", "c_cin_6", prestige=65, commercial_level=1)

    # With commercial_level=1 and no _active_sponsors, sponsor_announcement is blocked
    with pytest.raises(ValueError, match="no verified active commercial sponsor"):
        living_cinema_showroom.trigger_verified_club_cinematic(session, u.id, cp.id, event_type="sponsor_announcement")

    # Add a verified sponsor record and verify it succeeds
    facs = dict(state.facilities_json or {})
    facs["_active_sponsors"] = [{"sponsor_id": "sp_1", "sponsor_name": "AeroNigeria Global"}]
    state.facilities_json = facs
    session.flush()

    res = living_cinema_showroom.trigger_verified_club_cinematic(
        session, u.id, cp.id, event_type="sponsor_announcement"
    )
    assert res["success"] is True
    assert res["cinematic_event"]["sponsor_name"] == "AeroNigeria Global"


def test_router_cinema_showroom_endpoints():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_router_cin", "c_router_cin", prestige=80)

    app = FastAPI()
    app.include_router(owner_router.router)
    app.dependency_overrides[get_current_user] = lambda: u
    app.dependency_overrides[get_session] = lambda: session

    client = TestClient(app)

    # 1. GET overview
    res_get = client.get(f"/owner/clubs/{cp.id}/living-world/cinema-showroom/overview")
    assert res_get.status_code == 200, res_get.text
    data = res_get.json()
    assert data["club_id"] == cp.id
    assert len(data["prestige_3d_catalog"]) >= 6

    # 2. POST trigger valid manager_arrival
    res_trig = client.post(
        f"/owner/clubs/{cp.id}/living-world/cinema-showroom/trigger",
        json={"event_type": "manager_arrival", "subject_id": "first_team_manager"},
    )
    assert res_trig.status_code == 200, res_trig.text
    assert res_trig.json()["success"] is True
    assert res_trig.json()["cinematic_event"]["subject_name"] == "Emmanuel Amuneke"

    # 3. POST trigger unowned showroom asset returns 400
    res_unowned = client.post(
        f"/owner/clubs/{cp.id}/living-world/cinema-showroom/trigger",
        json={"event_type": "luxury_car_showcase", "catalog_key": "veloce_gt9_hypercar"},
    )
    assert res_unowned.status_code == 400
