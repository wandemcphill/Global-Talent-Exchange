"""
GTEX Living Football World — Next-Gen Upgrades Backend Test Suite
Covers:
1. Showroom Operational Perks (Private Jet +6% recruitment bonus, travel recovery, VIP transport livery)
2. Showroom Commercial & Hospitality Yield Settlement & Idempotency
3. Cross-Club Staff Poaching, Retention Negotiation & Buyout Clause Treasury Credit
4. Live Matchday-to-Boardroom Consequence Bridge (Rushed Player Fallout + Wonderkid 3D Spotlight)
5. Interactive 3D Press Conference Q&A Stance Resolution & Multi-Stage Player Signing Choreography
6. FastAPI Router Endpoints & Cross-Club Tenancy Isolation
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, or_, select
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
from app.models.world_clock import WorldClockState
from app.owner_console import (
    ledger,
    living_cinema_showroom,
    living_club_world,
    living_politics_engine,
    living_staff_market,
    router as owner_router,
    storytelling,
)
from app.owner_console.models import (
    OWNER_CONSOLE_TABLES,
    OwnerClubRelationship,
    OwnerClubState,
    OwnerSquadPlayer,
)

WORLD_NOW = datetime(2026, 11, 8, 19, 0, 0, tzinfo=timezone.utc)
DEFAULT_CLOCK_ID = "00000000-0000-0000-0000-000000000001"


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
            WorldClockState.__table__,
            *OWNER_CONSOLE_TABLES,
        ],
    )
    factory = sessionmaker(bind=eng, autoflush=False, expire_on_commit=False)
    s = factory()
    s.add(
        WorldClockState(
            id=DEFAULT_CLOCK_ID,
            epoch_real_utc=WORLD_NOW,
            virtual_start_time=WORLD_NOW,
            progression_rate=1.0,
        )
    )
    s.commit()
    return s


def _bootstrap_club(
    session: Session,
    user_id: str,
    club_id: str,
    *,
    club_name: str = "Lagos Atlantic FC",
    prestige: int = 75,
    cash_gtex: int = 30000,
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
        owner_user_id=u.id,
        club_name=club_name,
        short_name=club_name[:3].upper(),
        slug=f"{club_id}-slug",
        primary_color="#10B981",
        secondary_color="#0F172A",
        accent_color="#F59E0B",
    )
    session.add_all([u, cp])
    session.flush()

    state = OwnerClubState(
        id=club_id,
        club_id=club_id,
        owner_user_id=u.id,
        club_name=cp.club_name,
        stage="active",
        prestige=prestige,
        mentality="balanced",
        world_day=25,
        facilities_json={
            "training": 3,
            "academy": 3,
            "medical": 3,
            "stadium": 3,
            "commercial": 2,
            "_club_politics": {
                "board_confidence": 78,
                "supporter_confidence": 65,
                "team_spirit": 72,
            },
            "_executive_staff": {
                "general_manager": {
                    "id": f"gm_{club_id}",
                    "name": "Dayo Adeleke",
                    "role": "general_manager",
                    "role_label": "General Manager",
                    "rating": 84,
                    "salary_gtex": 1800,
                    "is_appointed": True,
                },
                "medical_director": {
                    "id": f"med_{club_id}",
                    "name": "Dr. Chidi Obi",
                    "role": "medical_director",
                    "role_label": "Medical Director",
                    "rating": 83,
                    "salary_gtex": 1200,
                    "is_appointed": True,
                },
                "head_of_youth_development": {
                    "id": f"hoyd_{club_id}",
                    "name": "Kunle Adeyemi",
                    "role": "head_of_youth_development",
                    "role_label": "Head of Youth Development",
                    "rating": 81,
                    "salary_gtex": 1100,
                    "is_appointed": True,
                },
            },
        },
        manager_json={
            "id": f"mgr_{club_id}",
            "name": "Emmanuel Amuneke",
            "role": "first_team_manager",
            "rating": 85,
            "salary": 2400,
            "salary_gtex": 2400,
            "formation": "4-3-3",
            "style": "High-Press Possession",
            "is_appointed": True,
            "is_vacant": False,
        },
    )
    session.add(state)
    session.flush()

    star_player = OwnerSquadPlayer(
        id=f"p_star_{club_id}",
        club_id=club_id,
        name="Chukwudi Agbo",
        position="ST",
        age=25,
        rating=84,
        potential=87,
        value_coin=Decimal("180000"),
        morale=78,
        minutes=180,
        injured_days=0,
        is_regen=False,
    )
    session.add(star_player)
    session.flush()

    living_staff_market.ensure_staff_market_profiles(session)

    # Initialize relationships
    living_club_world.ensure_default_relationships(session, state, [star_player])

    cur = ledger.balance(session, ledger.club_account(cp.id), ledger.GTEX)
    target = Decimal(str(cash_gtex))
    if target > cur:
        ledger.record(
            session,
            event_type="test_seed_cash",
            source=ledger.PLATFORM_GRANTS,
            destination=ledger.club_account(cp.id),
            currency=ledger.GTEX,
            gross=target - cur,
            club_id=cp.id,
            user_id=u.id,
            memo="Seed NextGen test treasury",
            check_funds=False,
        )

    session.commit()
    return u, cp, state


def test_showroom_operational_perks_and_recruitment_bonus():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_ng_1", "c_ng_1", prestige=75, cash_gtex=35000)

    # Before owning any showroom asset
    perks_before = living_cinema_showroom.compute_club_showroom_perks(session, cp.id)
    assert perks_before["owned_distinct_assets"] == 0
    assert perks_before["recruitment_wage_bonus_pct"] == 0.0
    assert perks_before["vip_transport_asset"] is None

    # Purchase Sovereign 900X Private Jet & Vanguard XII Coach
    storytelling.purchase_showroom_asset(
        session, u.id, cp.id, "sovereign_900x_jet", custom_name="Atlantic Sovereign One"
    )
    storytelling.purchase_showroom_asset(
        session, u.id, cp.id, "vanguard_xii_coach", custom_name="Atlantic First-Team Express"
    )
    session.commit()

    perks_after = living_cinema_showroom.compute_club_showroom_perks(session, cp.id)
    assert perks_after["owned_distinct_assets"] == 2
    assert perks_after["recruitment_wage_bonus_pct"] == 8.0
    assert perks_after["away_recovery_boost_days"] == 2
    assert perks_after["squad_morale_floor_bonus"] == 5
    assert perks_after["vip_transport_asset"]["catalog_key"] == "sovereign_900x_jet"

    # Candidate offering 90% of expected wage normally triggers counter-offer,
    # but with +8.0% showroom recruitment bonus it crosses the 95% threshold and is accepted!
    candidate = ClubStaffProfile(
        id="stf_perk_test",
        market_key="stf_perk_test",
        display_name="Carlos Queiroz II",
        staff_type="first_team_manager",
        rarity="elite",
        rating=84,
        salary_minor=100000,  # 1,000 GTEX expected
        metadata_json={"min_prestige": 70, "ambition": 14, "loyalty": 10},
    )
    session.add(candidate)
    session.commit()

    eval_no_perk = living_staff_market.evaluate_staff_contract_offer(
        club_prestige=75,
        candidate_profile=candidate,
        offered_salary_gtex=900,
        contract_years=2,
        showroom_wage_bonus_pct=0.0,
    )
    assert eval_no_perk["accepted"] is False
    assert eval_no_perk["outcome"] == "counter_offer"

    eval_with_perk = living_staff_market.evaluate_staff_contract_offer(
        club_prestige=75,
        candidate_profile=candidate,
        offered_salary_gtex=900,
        contract_years=2,
        showroom_wage_bonus_pct=perks_after["recruitment_wage_bonus_pct"],
    )
    assert eval_with_perk["accepted"] is True
    assert eval_with_perk["outcome"] == "accepted"


def test_claim_showroom_commercial_yield_and_idempotency():
    session = _session()
    u, cp, _ = _bootstrap_club(session, "u_ng_2", "c_ng_2", prestige=75, cash_gtex=30000)

    storytelling.purchase_showroom_asset(session, u.id, cp.id, "sovereign_900x_jet")
    storytelling.purchase_showroom_asset(session, u.id, cp.id, "chronos_tourbillon_watch")
    session.commit()

    bal_before = ledger.balance(session, ledger.club_account(cp.id), ledger.GTEX)
    perks_pre_claim = living_cinema_showroom.compute_club_showroom_perks(session, cp.id)
    assert perks_pre_claim["already_claimed_today"] is False
    assert perks_pre_claim["unclaimed_commercial_yield_gtex"] > 0

    claim_1 = living_cinema_showroom.claim_showroom_commercial_yield(session, u.id, cp.id)
    session.commit()

    assert claim_1["success"] is True
    assert claim_1["already_claimed"] is False
    assert claim_1["yield_credited_gtex"] > 0
    assert claim_1["claimed_gtex"] == claim_1["yield_credited_gtex"]
    assert claim_1["operational_perks"]["already_claimed_today"] is True
    assert claim_1["operational_perks"]["unclaimed_commercial_yield_gtex"] == 0
    bal_after_1 = ledger.balance(session, ledger.club_account(cp.id), ledger.GTEX)
    assert bal_after_1 == bal_before + Decimal(str(claim_1["yield_credited_gtex"]))

    # Replay on the same world_day -> idempotent, no double credit
    claim_2 = living_cinema_showroom.claim_showroom_commercial_yield(session, u.id, cp.id)
    session.commit()
    assert claim_2["already_claimed"] is True
    bal_after_2 = ledger.balance(session, ledger.club_account(cp.id), ledger.GTEX)
    assert bal_after_2 == bal_after_1


def test_staff_poaching_approach_and_match_rival_offer():
    session = _session()
    u, cp, _ = _bootstrap_club(session, "u_ng_3", "c_ng_3", prestige=75, cash_gtex=25000)

    approach = living_staff_market.evaluate_external_poaching_approach(
        session,
        u.id,
        cp.id,
        role="first_team_manager",
        rival_club_name="Cairo Royal SC",
    )
    session.commit()

    assert approach["status"] == "open"
    assert approach["rival_club_name"] == "Cairo Royal SC"
    assert approach["buyout_clause_gtex"] >= 1800

    cash_before = ledger.balance(session, ledger.club_account(cp.id), ledger.GTEX)
    res = living_staff_market.resolve_external_poaching_approach(
        session,
        u.id,
        cp.id,
        event_id=approach["event_id"],
        choice="match_rival_offer",
    )
    session.commit()

    assert res["status"] == "resolved"
    assert res["resolution"]["retained"] is True
    assert res["resolution"]["new_salary_gtex"] == approach["rival_offered_salary_gtex"]
    cash_after = ledger.balance(session, ledger.club_account(cp.id), ledger.GTEX)
    assert cash_after == cash_before - Decimal(str(res["resolution"]["retention_bonus_paid_gtex"]))


def test_staff_poaching_accept_buyout_credits_treasury_and_vacates_role():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_ng_4", "c_ng_4", prestige=75, cash_gtex=20000)

    approach = living_staff_market.evaluate_external_poaching_approach(
        session,
        u.id,
        cp.id,
        role="general_manager",
        rival_club_name="Casablanca Athletic",
    )
    session.commit()

    cash_before = ledger.balance(session, ledger.club_account(cp.id), ledger.GTEX)
    res = living_staff_market.resolve_external_poaching_approach(
        session,
        u.id,
        cp.id,
        event_id=approach["event_id"],
        choice="accept_buyout_release",
    )
    session.commit()

    assert res["resolution"]["retained"] is False
    assert res["resolution"]["role_vacated"] == "general_manager"
    assert res["resolution"]["buyout_credited_gtex"] == approach["buyout_clause_gtex"]

    cash_after = ledger.balance(session, ledger.club_account(cp.id), ledger.GTEX)
    assert cash_after == cash_before + Decimal(str(approach["buyout_clause_gtex"]))

    session.refresh(state)
    roster = living_club_world.resolve_club_staff_roster(state)
    assert roster["general_manager"]["is_appointed"] is False


def test_matchday_consequence_bridge_rushed_player_and_wonderkid_spotlight():
    session = _session()
    u, cp, _ = _bootstrap_club(session, "u_ng_5", "c_ng_5", prestige=75, cash_gtex=30000)

    # Purchase Private Jet so VIP transport is attached to the wonderkid spotlight
    storytelling.purchase_showroom_asset(session, u.id, cp.id, "sovereign_900x_jet", custom_name="Lagos Jet One")

    squad = list(session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == cp.id)).all())
    rushed_striker = squad[0]
    rushed_striker.injured_days = 3

    wonderkid = OwnerSquadPlayer(
        id="p_ng_wonderkid",
        club_id=cp.id,
        name="Samuel Chukwueze Jr",
        position="RW",
        age=17,
        rating=77,
        potential=92,
        value_coin=Decimal("70000"),
        morale=74,
        minutes=90,
        injured_days=0,
        is_regen=True,
        personality_json={"squad_status": "senior", "face_bank_id": "fb_regen_777"},
    )
    session.add(wonderkid)
    session.commit()

    bridge_res = living_politics_engine.process_matchday_consequence_bridge(
        session,
        u.id,
        cp.id,
        match_outcome="win",
        rushed_player_id=rushed_striker.id,
        wonderkid_scorer_id=wonderkid.id,
        is_away_fixture=True,
    )
    session.commit()

    assert bridge_res["success"] is True
    action_types = [a["type"] for a in bridge_res["bridge_actions"]]
    assert "medical_recurrence_fallout" in action_types
    assert "wonderkid_matchday_breakthrough" in action_types
    assert "showroom_travel_perks_applied" in action_types

    session.refresh(rushed_striker)
    assert rushed_striker.injured_days >= 13

    # Verify Wonderkid 3D Cinema event has 4-stage camera sequence & VIP transport livery
    cin = bridge_res["wonderkid_cinematic"]
    assert cin is not None
    assert cin["event_type"] == "academy_wonderkid"
    assert cin["is_regen"] is True
    assert cin["vip_transport"]["catalog_key"] == "sovereign_900x_jet"
    assert cin["camera_sequence"] == [
        "vip_transport_touchdown",
        "medical_clearance_scan",
        "boardroom_contract_signing",
        "tunnel_shirt_reveal",
    ]


def test_interactive_3d_press_conference_qa_stances():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_ng_6", "c_ng_6", prestige=75, cash_gtex=25000)

    cin_res = living_cinema_showroom.trigger_verified_club_cinematic(
        session,
        u.id,
        cp.id,
        event_type="manager_arrival",
        subject_id="first_team_manager",
    )
    session.commit()

    ev_id = cin_res["cinematic_event"]["event_id"]
    qa_prompt = cin_res["cinematic_event"]["press_conference_qa"]
    assert qa_prompt["answered"] is False
    assert len(qa_prompt["options"]) == 3

    roster = living_club_world.resolve_club_staff_roster(state)
    mgr_person_id = roster["first_team_manager"]["person_id"]
    rel_before = session.scalar(
        select(OwnerClubRelationship).where(
            OwnerClubRelationship.club_id == cp.id,
            or_(
                OwnerClubRelationship.participant_a_id == mgr_person_id,
                OwnerClubRelationship.participant_b_id == mgr_person_id,
            ),
        )
    )
    trust_before = rel_before.trust

    ans_res = living_cinema_showroom.answer_cinematic_press_question(
        session,
        u.id,
        cp.id,
        event_id=ev_id,
        stance="tactical_pragmatism",
        custom_quote="We back our manager's tactical vision wholeheartedly.",
    )
    session.commit()

    assert ans_res["success"] is True
    assert ans_res["already_answered"] is False
    assert "Tactical" in ans_res["media_headline"]
    assert ans_res["quote"] == "We back our manager's tactical vision wholeheartedly."
    assert ans_res["political_impact"]["board_confidence"] == "+5"
    assert ans_res["cinematic_event"]["press_conference_qa"]["answered"] is True
    assert ans_res["cinematic_event"]["press_conference_qa"]["selected_stance"] == "tactical_pragmatism"

    session.refresh(rel_before)
    assert rel_before.trust == min(100, trust_before + 5)


def test_nextgen_api_routes_and_tenancy():
    session = _session()
    u1, cp1, _ = _bootstrap_club(session, "u_ng_api1", "c_ng_api1", prestige=75, cash_gtex=30000)
    u2, cp2, _ = _bootstrap_club(session, "u_ng_api2", "c_ng_api2", prestige=70, cash_gtex=20000)

    storytelling.purchase_showroom_asset(session, u1.id, cp1.id, "sovereign_900x_jet")
    session.commit()

    active_user = {"user": u1}
    app = FastAPI()
    app.include_router(owner_router.router)
    app.dependency_overrides[get_current_user] = lambda: active_user["user"]
    app.dependency_overrides[get_session] = lambda: session
    client = TestClient(app)

    # 1. Claim Showroom Yield
    r_yield = client.post(f"/owner/clubs/{cp1.id}/living-world/cinema-showroom/claim-yield")
    assert r_yield.status_code == 200
    assert r_yield.json()["yield_credited_gtex"] > 0

    # 2. Trigger Cinematic & Answer Press Q&A
    r_trig = client.post(
        f"/owner/clubs/{cp1.id}/living-world/cinema-showroom/trigger",
        json={"event_type": "manager_arrival", "subject_id": "first_team_manager"},
    )
    assert r_trig.status_code == 200
    ev_id = r_trig.json()["cinematic_event"]["event_id"]

    r_qa = client.post(
        f"/owner/clubs/{cp1.id}/living-world/cinema-showroom/{ev_id}/press-question",
        json={"stance": "championship_ambition"},
    )
    assert r_qa.status_code == 200
    assert r_qa.json()["stance"] == "championship_ambition"

    # 3. Evaluate & Resolve Staff Poaching
    r_poach = client.post(
        f"/owner/clubs/{cp1.id}/living-world/staff-market/poaching/evaluate",
        json={"role": "first_team_manager", "rival_club_name": "Abuja United"},
    )
    assert r_poach.status_code == 200
    poach_id = r_poach.json()["event_id"]

    r_res = client.post(
        f"/owner/clubs/{cp1.id}/living-world/staff-market/poaching/{poach_id}/resolve",
        json={"choice": "promise_facility_upgrade"},
    )
    assert r_res.status_code == 200
    assert r_res.json()["resolution"]["retained"] is True

    # 4. Matchday Consequence Bridge
    r_bridge = client.post(
        f"/owner/clubs/{cp1.id}/living-world/politics/matchday-bridge",
        json={"match_outcome": "win", "is_away_fixture": True},
    )
    assert r_bridge.status_code == 200
    assert r_bridge.json()["success"] is True

    # 5. Cross-club tenancy isolation
    active_user["user"] = u2
    r_forbidden = client.post(f"/owner/clubs/{cp1.id}/living-world/cinema-showroom/claim-yield")
    assert r_forbidden.status_code in (403, 404)
