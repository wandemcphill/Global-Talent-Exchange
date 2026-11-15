from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user, get_session
from app.core.database import load_model_modules
from app.models.base import Base
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.user import KycStatus, PublicAccountType, User, UserRole
from app.models.world_clock import WorldClockState
from app.owner_console import engine as owner_engine, ledger
from app.owner_console.models import OwnerClubState, OwnerSquadPlayer
from app.owner_console.router import router as owner_router
from app.services.world_clock_service import DEFAULT_CLOCK_ID

WORLD_NOW = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)
_SHARED_ENGINE = None


def _get_shared_engine():
    global _SHARED_ENGINE
    if _SHARED_ENGINE is None:
        load_model_modules()
        _SHARED_ENGINE = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(_SHARED_ENGINE)
    return _SHARED_ENGINE


def _setup_stage2_env() -> tuple[Session, TestClient, OwnerClubState, User]:
    engine_db = _get_shared_engine()
    SessionLocal = sessionmaker(bind=engine_db, autoflush=False, expire_on_commit=False)
    session = SessionLocal()

    uid = uuid4().hex[:8]
    user = User(
        id=f"u_s2_{uid}",
        email=f"stage2_{uid}@gtex.test",
        username=f"stage2owner_{uid}",
        full_name="Director Balogun",
        display_name="Director Balogun",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
        account_type=PublicAccountType.USER,
    )
    if session.get(WorldClockState, DEFAULT_CLOCK_ID) is None:
        session.add(
            WorldClockState(
                id=DEFAULT_CLOCK_ID,
                epoch_real_utc=WORLD_NOW,
                virtual_start_time=WORLD_NOW,
                progression_rate=1.0,
                is_paused=False,
                paused_at_virtual_time=None,
                virtual_months_per_season=12,
                metadata_json={"canonical": True},
            )
        )
    cp = ClubProfile(
        id=f"c_s2_{uid}",
        owner_user_id=user.id,
        club_name=f"Stage Two FC {uid}",
        short_name=f"T{uid[:3]}".upper(),
        slug=f"stage-two-{uid}",
        club_type=ClubType.COMMUNITY,
        lifecycle_status=ClubLifecycleStatus.ACTIVE,
        primary_color="#112233",
        secondary_color="#ffffff",
        accent_color="#00ff88",
        country_code="NG",
        visibility="public",
    )
    state = OwnerClubState(
        club_id=cp.id,
        owner_user_id=user.id,
        club_name=cp.club_name,
        stage="active",
        world_day=18,
        prestige=74,
        fans=21000,
        mentality="balanced",
        manager_json=owner_engine.manager_profile(owner_engine.DEFAULT_MANAGER),
        facilities_json={"training": 3, "academy": 3, "medical": 3, "stadium": 3, "commercial": 3},
    )
    session.add_all([user, cp, state])
    session.flush()
    ledger.record(
        session,
        event_type="test_grant",
        source=ledger.WORLD_CLUBS,
        destination=ledger.club_account(cp.id),
        currency=ledger.GTEX,
        gross=850000,
        balance_class="deposited",
        club_id=cp.id,
        user_id=user.id,
        memo="Stage 2 initial treasury",
    )
    for idx, (pos, age, rtg) in enumerate(
        [
            ("GK", 27, 78),
            ("CB", 28, 79),
            ("CB", 26, 77),
            ("LB", 24, 76),
            ("RB", 25, 76),
            ("CM", 27, 80),
            ("CDM", 29, 78),
            ("CAM", 23, 78),
            ("LW", 22, 77),
            ("RW", 24, 77),
            ("ST", 26, 81),
            ("ST", 19, 71),
        ],
        start=1,
    ):
        session.add(
            OwnerSquadPlayer(
                id=f"{cp.id}-p-{idx}",
                club_id=cp.id,
                name=f"StageTwo Player {idx}",
                position=pos,
                age=age,
                rating=rtg,
                potential=max(rtg + 2, 82),
                value_coin=Decimal(str(rtg * 15)),
                morale=78,
                minutes=160 if idx < 12 else 20,
                injured_days=3 if idx == 6 else 0,
                is_regen=idx == 12,
                personality_json={
                    "fitness": 78 if idx in (5, 6) else 94,
                    "is_academy": idx == 12,
                    "last_injury_type": "Hamstring Tightness" if idx == 6 else None,
                },
                status="active",
                acquired_via="academy" if idx == 12 else "market",
            )
        )
    session.commit()

    app = FastAPI()
    app.include_router(owner_router)

    def _get_db() -> Iterator[Session]:
        yield session

    def _get_user() -> User:
        return session.get(User, user.id)

    app.dependency_overrides[get_session] = _get_db
    app.dependency_overrides[get_current_user] = _get_user
    return session, TestClient(app), state, user


def test_operations_hub_exposes_18_physical_stations_and_complete_reports() -> None:
    session, client, state, _user = _setup_stage2_env()
    try:
        res = client.get(f"/owner/clubs/{state.club_id}/operations-hub")
        assert res.status_code == 200
        hub = res.json()
        destinations = {d["destination_key"]: d for d in hub["destinations"]}
        assert len(destinations) == 6

        expected_actions = {
            "executive_office": {"inspect_briefing", "inspect_decisions", "inspect_timeline"},
            "managers_office": {"set_mentality", "pledge_win_bonus", "chat_manager"},
            "general_managers_office": {"configure_delegation", "inspect_campus", "chat_gm"},
            "academy_department": {"commission_intake", "manage_regens", "chat_hoyd"},
            "medical_department": {"run_conditioning", "inspect_workloads", "chat_med"},
            "finance_commercial_office": {"inspect_ledger", "sign_sponsor", "inspect_matchday_econ"},
        }
        for dest_key, actions in expected_actions.items():
            dest = destinations[dest_key]
            hotspots = dest["hotspots"]
            assert len(hotspots) == 3
            assert {h["action"] for h in hotspots} == actions
            assert len(dest["camera_position"]) == 3
            assert len(dest["camera_target"]) == 3
            for h in hotspots:
                assert len(h["offset"]) == 3

        # Finance report must not impersonate the General Manager once finance director identity is separated
        fin_report = destinations["finance_commercial_office"]["report"]
        assert fin_report["staff_profile"]["role_key"] == "finance_commercial_director"
        assert destinations["medical_department"]["report"]["rehabilitation_status"]["protocol_cost_gtex"] == 800
        assert destinations["medical_department"]["report"]["rehabilitation_status"]["protocol_executed_today"] is False
    finally:
        session.close()


def test_medical_recovery_protocol_endpoint_is_authoritative_and_daily_idempotent() -> None:
    session, client, state, _user = _setup_stage2_env()
    try:
        injured_before = session.get(OwnerSquadPlayer, f"{state.club_id}-p-6")
        fatigued_before = session.get(OwnerSquadPlayer, f"{state.club_id}-p-5")
        assert injured_before is not None and injured_before.injured_days == 3
        assert fatigued_before is not None and fatigued_before.personality_json["fitness"] == 78

        first = client.post(
            f"/owner/clubs/{state.club_id}/medical/recovery-protocol",
            json={"cost_gtex": 800},
        )
        assert first.status_code == 200
        payload = first.json()
        assert payload["status"] == "executed"
        assert payload["rehab_accelerated"] == 1
        assert payload["squad_updated"] == 12
        assert payload["ledger_event_id"]

        session.expire_all()
        injured_after = session.get(OwnerSquadPlayer, f"{state.club_id}-p-6")
        fatigued_after = session.get(OwnerSquadPlayer, f"{state.club_id}-p-5")
        assert injured_after is not None and injured_after.injured_days == 2
        assert fatigued_after is not None and fatigued_after.personality_json["fitness"] == 84

        hub = payload["operations_hub"]
        med_dest = next(d for d in hub["destinations"] if d["destination_key"] == "medical_department")
        assert med_dest["report"]["rehabilitation_status"]["protocol_executed_today"] is True

        # Matching daily operational recommendation should also be synced as approved/resolved
        all_decs = {
            d["decision_id"]: d
            for d in hub["daily_briefing"].get("department_decisions", [])
        }
        med_dec = next((d for k, d in all_decs.items() if k.startswith("op_med_protocol_")), None)
        assert med_dec is not None and med_dec["status"] == "approved"

        # Second invocation on same world day must reject with 409 (no double-heal exploit)
        duplicate = client.post(
            f"/owner/clubs/{state.club_id}/medical/recovery-protocol",
            json={"cost_gtex": 800},
        )
        assert duplicate.status_code == 409
    finally:
        session.close()


def test_medical_recovery_protocol_handles_vacant_director_without_fake_npc() -> None:
    session, client, state, _user = _setup_stage2_env()
    try:
        facs = dict(state.facilities_json or {})
        facs["_executive_staff"] = {}
        state.facilities_json = facs
        flag_modified(state, "facilities_json")
        session.commit()

        res = client.post(
            f"/owner/clubs/{state.club_id}/medical/recovery-protocol",
            json={"cost_gtex": 800},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["medical_director_appointed"] is False
        assert data["medical_director_name"] is None
    finally:
        session.close()


def test_gm_delegation_and_staff_dismiss_work_with_operations_hub() -> None:
    session, client, state, _user = _setup_stage2_env()
    try:
        facs = dict(state.facilities_json or {})
        facs["_executive_staff"] = {
            "general_manager": {
                "id": "gm_paul_mitchell",
                "name": "Paul Mitchell",
                "role": "general_manager",
                "role_label": "General Manager",
                "mood": 82,
            }
        }
        state.facilities_json = facs
        flag_modified(state, "facilities_json")
        session.commit()

        del_res = client.put(
            f"/owner/clubs/{state.club_id}/delegation",
            json={"mode": "hands_on", "gm_transfer_autonomy": False, "hoyd_youth_contracts": False},
        )
        assert del_res.status_code == 200

        dismiss_res = client.post(
            f"/owner/clubs/{state.club_id}/living-world/staff-market/dismiss",
            json={"role": "general_manager", "reason": "Stage 2 test dismissal"},
        )
        assert dismiss_res.status_code == 200

        hub_res = client.get(f"/owner/clubs/{state.club_id}/operations-hub", params={"force_refresh": True})
        assert hub_res.status_code == 200
        gm_dest = next(
            d for d in hub_res.json()["destinations"] if d["destination_key"] == "general_managers_office"
        )
        assert gm_dest["staff_lead"]["is_vacant"] is True
        assert gm_dest["report"]["administrative_matters"]["delegation_policy"]["mode"] == "hands_on"
    finally:
        session.close()
