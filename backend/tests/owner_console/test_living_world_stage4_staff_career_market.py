"""
GTEX Living Football World — Stage 4
Test Suite: Autonomous Staff Career & Professional Employment Market
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user, get_session
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.club_growth import (
    ClubStaffProfile,
    ClubStaffContract,
    ClubStaffAssignment,
)
from app.models.event_backbone import EventOutbox
from app.models.risk_ops import AuditLog
from app.models.wallet import (
    LedgerAccount,
    LedgerBalanceProjection,
    LedgerEntry,
    LedgerTransaction,
)
from app.models.user import User
from app.owner_console import ledger, living_staff_market, router as owner_router
from app.owner_console.staff_supply import (
    GENERAL_MANAGER_FREE_AGENT_FLOOR,
    replenish_scarce_staff,
)
from app.owner_console.models import (
    OWNER_CONSOLE_TABLES,
    OwnerClubState,
)

WORLD_NOW = datetime(2026, 11, 8, 12, 0, 0, tzinfo=timezone.utc)


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
            ClubStaffProfile.__table__,
            ClubStaffContract.__table__,
            ClubStaffAssignment.__table__,
            EventOutbox.__table__,
            AuditLog.__table__,
            LedgerAccount.__table__,
            LedgerBalanceProjection.__table__,
            LedgerEntry.__table__,
            LedgerTransaction.__table__,
            *OWNER_CONSOLE_TABLES,
        ],
    )
    return sessionmaker(bind=eng, autoflush=False, expire_on_commit=False)()


def _bootstrap_club(
    session: Session, user_id: str, club_id: str, prestige: int = 50
) -> tuple[User, ClubProfile, OwnerClubState]:
    u = User(
        id=user_id,
        email=f"{user_id}@gtex.test",
        username=f"owner_{user_id}",
        password_hash="synthetic_hash",  # pragma: allowlist secret
        role="authenticated",
        is_active=True,
    )
    c = ClubProfile(
        id=club_id,
        owner_user_id=user_id,
        club_name="Enugu Coal City",
        slug=f"enugu-coal-city-{club_id}",
        primary_color="#10B981",
        secondary_color="#0F172A",
        accent_color="#F59E0B",
    )
    session.add_all([u, c])
    session.flush()

    state = OwnerClubState(
        id=club_id,
        club_id=club_id,
        owner_user_id=user_id,
        club_name="Enugu Coal City",
        prestige=prestige,
        world_day=10,
        facilities_json={"_executive_staff": {}},
        manager_json={"name": "Interim Coach", "is_default": True},
    )
    session.add(state)
    session.flush()
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
    return u, c, state


def test_ensure_staff_market_profiles_seeding():
    session = _session()
    profiles = living_staff_market.ensure_staff_market_profiles(session)
    assert len(profiles) >= 5
    first_mgr = next((p for p in profiles if p.staff_type == "first_team_manager"), None)
    assert first_mgr is not None
    assert first_mgr.display_name
    meta = first_mgr.metadata_json or {}
    assert meta.get("employment_status") == "unemployed"
    assert "career_history" in meta
    assert meta.get("min_prestige") is not None


def test_get_club_vacancies_identifies_unfilled_roles():
    session = _session()
    u, c, state = _bootstrap_club(session, "u_vac_1", "c_vac_1", prestige=40)
    vac_report = living_staff_market.get_club_vacancies(session, u.id, c.id)

    assert vac_report["club_id"] == c.id
    assert vac_report["vacancies_count"] >= 4
    role_keys = [v["role_key"] for v in vac_report["vacancies"]]
    assert "first_team_manager" in role_keys
    assert "general_manager" in role_keys


def test_list_staff_market_candidates_filtering():
    session = _session()
    u, c, state = _bootstrap_club(session, "u_list_1", "c_list_1", prestige=60)
    candidates_data = living_staff_market.list_staff_market_candidates(session, u.id, c.id, role="first_team_manager")

    assert candidates_data["club_id"] == c.id
    assert candidates_data["total_count"] > 0
    for cand in candidates_data["candidates"]:
        assert cand["role_key"] == "first_team_manager"
        assert "interest_level" in cand
        assert "expected_salary_gtex" in cand
        assert "can_attract" in cand


def test_evaluate_staff_contract_offer_prestige_rejected():
    session = _session()
    living_staff_market.ensure_staff_market_profiles(session)

    # Candidate with high min prestige
    high_profile = ClubStaffProfile(
        market_key="staff:elite_boss",
        display_name="Elite Tactician",
        staff_type="first_team_manager",
        rating=88,
        salary_minor=120000,
        metadata_json={"min_prestige": 75, "ambition": 15, "loyalty": 10},
    )
    session.add(high_profile)
    session.flush()

    # Offer from prestige 30 club with standard wage
    evaluation = living_staff_market.evaluate_staff_contract_offer(
        club_prestige=30,
        candidate_profile=high_profile,
        offered_salary_gtex=1200,
        contract_years=3,
        marquee_premium=False,
    )
    assert evaluation["accepted"] is False
    assert evaluation["reason"] == "insufficient_prestige"


def test_evaluate_staff_contract_offer_marquee_premium_accepted():
    session = _session()
    high_profile = ClubStaffProfile(
        market_key="staff:elite_boss_2",
        display_name="Elite Tactician 2",
        staff_type="first_team_manager",
        rating=85,
        salary_minor=100000,
        metadata_json={"min_prestige": 65, "ambition": 12, "loyalty": 10},
    )
    session.add(high_profile)
    session.flush()

    # Low prestige club pays marquee wage premium (1.5x expected wage)
    evaluation = living_staff_market.evaluate_staff_contract_offer(
        club_prestige=35,
        candidate_profile=high_profile,
        offered_salary_gtex=1600,
        contract_years=3,
        marquee_premium=True,
    )
    assert evaluation["accepted"] is True
    assert evaluation["outcome"] == "accepted"


def test_evaluate_staff_contract_offer_insufficient_wage():
    session = _session()
    prof = ClubStaffProfile(
        market_key="staff:coach_wage_test",
        display_name="Solid Coach",
        staff_type="first_team_coach",
        rating=75,
        salary_minor=80000,
        metadata_json={"min_prestige": 20, "ambition": 10},
    )
    session.add(prof)
    session.flush()

    # Lowball wage (400 vs 800)
    evaluation = living_staff_market.evaluate_staff_contract_offer(
        club_prestige=50,
        candidate_profile=prof,
        offered_salary_gtex=400,
        contract_years=2,
    )
    assert evaluation["accepted"] is False
    assert evaluation["reason"] == "insufficient_wage"


def test_hire_staff_from_market_ratification():
    session = _session()
    u, c, state = _bootstrap_club(session, "u_hire_1", "c_hire_1", prestige=55)

    prof = ClubStaffProfile(
        market_key="staff:amuneke_hiring_test",
        display_name="Emmanuel Amuneke",
        staff_type="first_team_manager",
        rating=82,
        salary_minor=80000,
        metadata_json={
            "min_prestige": 40,
            "style": "Tiki-Taka",
            "temperament": "analytical",
            "employment_status": "unemployed",
            "career_history": [],
        },
    )
    session.add(prof)
    session.flush()

    hire_res = living_staff_market.hire_staff_from_market(
        session,
        user_id=u.id,
        club_id=c.id,
        profile_id=prof.id,
        role="first_team_manager",
        offered_salary_gtex=900,
        contract_years=3,
    )

    assert hire_res["status"] == "accepted"
    assert hire_res["success"] is True
    assert hire_res["contract_id"]

    # Verify ClubStaffContract was created
    contract = session.get(ClubStaffContract, hire_res["contract_id"])
    assert contract is not None
    assert contract.status == "active"
    assert contract.salary_minor == 90000

    # Verify ClubStaffAssignment was created
    assignment = session.scalar(
        select(ClubStaffAssignment).where(
            ClubStaffAssignment.club_id == c.id,
            ClubStaffAssignment.role_key == "first_team_manager",
            ClubStaffAssignment.active.is_(True),
        )
    )
    assert assignment is not None

    # Verify facilities_json and manager_json sync
    assert state.facilities_json["_executive_staff"]["first_team_manager"]["name"] == "Emmanuel Amuneke"
    assert state.manager_json["name"] == "Emmanuel Amuneke"

    # Verify ClubStaffProfile career history
    session.refresh(prof)
    assert prof.metadata_json["employment_status"] == "employed"
    assert prof.metadata_json["current_club_id"] == c.id
    history = prof.metadata_json["career_history"]
    assert len(history) == 1
    assert history[0]["club_id"] == c.id
    assert history[0]["status"] == "ongoing"


def test_dismiss_staff_free_agency_preservation():
    session = _session()
    u, c, state = _bootstrap_club(session, "u_dism_1", "c_dism_1", prestige=50)

    # 1. First hire candidate
    prof = ClubStaffProfile(
        market_key="staff:gm_dayo_dismiss_test",
        display_name="Dayo Adeleke",
        staff_type="general_manager",
        rating=78,
        salary_minor=60000,
        metadata_json={
            "min_prestige": 30,
            "employment_status": "unemployed",
            "career_history": [],
        },
    )
    session.add(prof)
    session.flush()

    hire_res = living_staff_market.hire_staff_from_market(
        session, u.id, c.id, prof.id, role="general_manager", offered_salary_gtex=650
    )
    assert hire_res["success"] is True

    # 2. Dismiss staff member
    dism_res = living_staff_market.dismiss_staff_with_free_agency(
        session, u.id, c.id, role="general_manager", reason="philosophical_rift"
    )

    assert dism_res["status"] == "dismissed"
    assert dism_res["success"] is True
    assert dism_res["severance_paid"] > 0
    assert dism_res["entered_free_agency"] is True

    # 3. Verify assignment deactivated
    assignment = session.scalar(
        select(ClubStaffAssignment).where(
            ClubStaffAssignment.club_id == c.id,
            ClubStaffAssignment.role_key == "general_manager",
            ClubStaffAssignment.active.is_(True),
        )
    )
    assert assignment is None

    # 4. Verify removed from club facilities
    assert "general_manager" not in (state.facilities_json.get("_executive_staff") or {})

    # 5. Verify ClubStaffProfile retained and transitioned to UNEMPLOYED free agent
    session.refresh(prof)
    assert prof.metadata_json["employment_status"] == "unemployed"
    assert prof.metadata_json["current_club_id"] is None
    history = prof.metadata_json["career_history"]
    assert len(history) >= 1
    assert history[-1]["status"] == "dismissed"
    assert history[-1]["reason_for_leaving"] == "philosophical_rift"


def test_rehire_dismissed_staff_by_second_club():
    session = _session()
    # Club 1: Lagos
    u1, c1, state1 = _bootstrap_club(session, "u_club1", "c_club1", prestige=50)
    # Club 2: Kano
    u2, c2, state2 = _bootstrap_club(session, "u_club2", "c_club2", prestige=60)

    prof = ClubStaffProfile(
        market_key="staff:journeyman_tactician",
        display_name="Kofi Mensah",
        staff_type="chief_scout",
        rating=80,
        salary_minor=70000,
        metadata_json={
            "min_prestige": 35,
            "employment_status": "unemployed",
            "career_history": [],
        },
    )
    session.add(prof)
    session.flush()

    # 1. Club 1 hires candidate
    h1 = living_staff_market.hire_staff_from_market(
        session, u1.id, c1.id, prof.id, role="chief_scout", offered_salary_gtex=750
    )
    assert h1["success"] is True

    # 2. Club 1 dismisses candidate
    d1 = living_staff_market.dismiss_staff_with_free_agency(
        session, u1.id, c1.id, role="chief_scout", reason="budget_reduction"
    )
    assert d1["entered_free_agency"] is True

    # 3. Club 2 browses the market and finds Kofi Mensah in the free agent pool
    pool = living_staff_market.list_staff_market_candidates(session, u2.id, c2.id, role="chief_scout")
    kofi_candidate = next((c for c in pool["candidates"] if c["profile_id"] == prof.id), None)
    assert kofi_candidate is not None
    assert kofi_candidate["employment_status"] == "unemployed"
    assert len(kofi_candidate["career_history"]) >= 1

    # 4. Club 2 hires Kofi Mensah
    h2 = living_staff_market.hire_staff_from_market(
        session, u2.id, c2.id, prof.id, role="chief_scout", offered_salary_gtex=800
    )
    assert h2["success"] is True

    session.refresh(prof)
    assert prof.metadata_json["current_club_id"] == c2.id
    assert prof.metadata_json["employment_status"] == "employed"
    assert len(prof.metadata_json["career_history"]) == 2
    assert prof.metadata_json["career_history"][0]["club_id"] == c1.id
    assert prof.metadata_json["career_history"][1]["club_id"] == c2.id


def test_stage4_router_endpoints():
    session = _session()
    u, c, state = _bootstrap_club(session, "u_router_s4", "c_router_s4", prestige=50)

    living_staff_market.ensure_staff_market_profiles(session)

    app = FastAPI()
    app.include_router(owner_router.router)
    app.dependency_overrides[get_current_user] = lambda: u
    app.dependency_overrides[get_session] = lambda: session

    client = TestClient(app)

    # 1. Vacancies endpoint
    res_vac = client.get(f"/owner/clubs/{c.id}/living-world/staff-market/vacancies")
    assert res_vac.status_code == 200
    vac_json = res_vac.json()
    assert "vacancies" in vac_json

    # 2. Candidates endpoint
    res_cand = client.get(f"/owner/clubs/{c.id}/living-world/staff-market/candidates")
    assert res_cand.status_code == 200
    cand_json = res_cand.json()
    assert "candidates" in cand_json
    assert len(cand_json["candidates"]) > 0

    first_cand = cand_json["candidates"][0]
    profile_id = first_cand["profile_id"]

    # 3. Dossier endpoint
    res_dos = client.get(f"/owner/clubs/{c.id}/living-world/staff-market/candidates/{profile_id}")
    assert res_dos.status_code == 200
    dos_json = res_dos.json()
    assert dos_json["name"] == first_cand["name"]

    # 4. Submit offer endpoint
    res_offer = client.post(
        f"/owner/clubs/{c.id}/living-world/staff-market/offers",
        json={
            "profile_id": profile_id,
            "role": first_cand["role_key"],
            "offered_salary_gtex": int(first_cand.get("expected_salary_gtex", 1000) * 1.5),
            "contract_years": 3,
            "marquee_wage_premium": True,
        },
    )
    assert res_offer.status_code == 200
    offer_json = res_offer.json()
    assert offer_json["success"] is True

    # 5. Dismiss endpoint
    res_dism = client.post(
        f"/owner/clubs/{c.id}/living-world/staff-market/dismiss",
        json={
            "role": first_cand["role_key"],
            "reason": "tactical_restructure",
        },
    )
    assert res_dism.status_code == 200
    dism_json = res_dism.json()
    assert dism_json["status"] == "dismissed"
    assert dism_json["entered_free_agency"] is True


def test_unemployed_staff_follow_a_corrected_catalog_role():
    session = _session()
    from app.owner_console import engine

    director = next(
        item
        for item in engine.EXECUTIVE_STAFF_CATALOG
        if item.get("role") == "general_manager" and item.get("source_job") == "Technical Director"
    )
    session.add(
        ClubStaffProfile(
            market_key=f"staff:{director['id']}",
            display_name=director["name"],
            staff_type="first_team_manager",
            rating=12,
            salary_minor=100,
            metadata_json={"employment_status": "unemployed", "career_history": [{"club_id": "kept"}]},
        )
    )
    session.flush()

    living_staff_market.ensure_staff_market_profiles(session)
    profile = session.scalar(
        select(ClubStaffProfile).where(ClubStaffProfile.market_key == f"staff:{director['id']}")
    )
    assert profile is not None
    assert profile.staff_type == "general_manager"
    assert profile.metadata_json["career_history"] == [{"club_id": "kept"}]


def test_general_manager_bench_refills_when_clubs_hire():
    session = _session()
    first = replenish_scarce_staff(session)
    assert first["general_manager_added"] == GENERAL_MANAGER_FREE_AGENT_FLOOR
    assert first["general_manager_available"] == GENERAL_MANAGER_FREE_AGENT_FLOOR

    held = replenish_scarce_staff(session)
    assert held["general_manager_added"] == 0
    assert held["general_manager_available"] == GENERAL_MANAGER_FREE_AGENT_FLOOR

    appointed = session.scalars(
        select(ClubStaffProfile).where(ClubStaffProfile.staff_type == "general_manager")
    ).all()
    for profile in appointed[:12]:
        meta = dict(profile.metadata_json or {})
        meta["employment_status"] = "employed"
        meta["current_club_id"] = "club-holding"
        profile.metadata_json = meta
    session.flush()

    refilled = replenish_scarce_staff(session)
    assert refilled["general_manager_added"] == 12
    assert refilled["general_manager_available"] == GENERAL_MANAGER_FREE_AGENT_FLOOR

    affordable = [
        profile
        for profile in session.scalars(
            select(ClubStaffProfile).where(ClubStaffProfile.staff_type == "general_manager")
        ).all()
        if (profile.metadata_json or {}).get("employment_status") == "unemployed"
        and int((profile.metadata_json or {}).get("min_prestige") or 99) <= 20
        and (profile.salary_minor or 0) // 100 <= 1100
    ]
    assert len(affordable) >= 20
