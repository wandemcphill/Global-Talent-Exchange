from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
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
from app.owner_console import engine as owner_engine
from app.owner_console import ledger, prestige_campus_comms, service, storytelling
from app.owner_console.models import OWNER_CONSOLE_TABLES, OwnerClubState
from app.services.world_clock_service import DEFAULT_CLOCK_ID

WORLD_NOW = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)


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
            LedgerTransaction.__table__,
            LedgerEntry.__table__,
            LedgerBalanceProjection.__table__,
            WorldClockState.__table__,
            *OWNER_CONSOLE_TABLES,
        ],
    )
    factory = sessionmaker(bind=eng, autoflush=False, expire_on_commit=False)
    session = factory()
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
    session.commit()
    return session


def _seed_club(session: Session, *, prestige: int = 55, cash: int = 120_000) -> OwnerClubState:
    user = User(
        id="user-prestige-1",
        email="prestige@gtex.test",
        username="prestige_owner",
        password_hash="hash",  # pragma: allowlist secret
    )
    profile = ClubProfile(
        id="club-prestige-1",
        owner_user_id="user-prestige-1",
        club_name="Victoria Island Royals FC",
        slug="victoria-island-royals-fc",
        primary_color="#10b981",
        secondary_color="#0f172a",
        accent_color="#f59e0b",
    )
    session.add(user)
    session.add(profile)
    state = OwnerClubState(
        id="state-prestige-1",
        club_id="club-prestige-1",
        owner_user_id="user-prestige-1",
        club_name="Victoria Island Royals FC",
        stage="active",
        prestige=prestige,
        manager_json=owner_engine.manager_profile(owner_engine.DEFAULT_MANAGER),
        facilities_json={"training": 2, "academy": 2, "medical": 2, "stadium": 2, "commercial": 2},
        world_day=12,
        last_tick_at=WORLD_NOW,
        last_world_tick_date=WORLD_NOW.date(),
        value_history_json=[],
    )
    session.add(state)
    ledger.record(
        session,
        event_type="club_launch_grant",
        source=ledger.WORLD_CLUBS,
        destination=ledger.club_account("club-prestige-1"),
        currency=ledger.GTEX,
        gross=Decimal(cash),
        club_id="club-prestige-1",
        user_id="user-prestige-1",
        memo="Initial club grant",
    )
    session.commit()
    return state


def test_owner_office_showroom_visual_manifest_and_ownership_separation():
    session = _session()
    _seed_club(session, prestige=65, cash=150_000)

    showroom = storytelling.get_club_showroom(session, "user-prestige-1", "club-prestige-1")
    assert "visual_manifest" in showroom
    assert len(showroom["visual_manifest"]) == 12
    assert "owner_office_summary" in showroom
    assert showroom["owner_office_summary"]["club_name"] == "Victoria Island Royals FC"

    # Purchase a club-owned aviation asset and a personal luxury SUV
    jet_res = storytelling.purchase_showroom_asset(
        session,
        "user-prestige-1",
        "club-prestige-1",
        "sovereign_900x_jet",
        idempotency_key="office-jet-1",
    )
    assert jet_res["broadcast_globally"] is True
    assert Decimal(str(jet_res["asset"]["price_gtex"])) == Decimal("4800.0")

    suv_res = storytelling.purchase_showroom_asset(
        session,
        "user-prestige-1",
        "club-prestige-1",
        "executive_suv_command",
        idempotency_key="office-suv-1",
    )
    assert suv_res["broadcast_globally"] is False

    updated_showroom = storytelling.get_club_showroom(session, "user-prestige-1", "club-prestige-1")
    breakdown = updated_showroom["owner_office_summary"]["ownership_breakdown"]
    assert breakdown["club_owned_count"] >= 1
    assert breakdown["owner_personal_count"] >= 1


def test_campus_builder_3d_grid_validation_and_staged_construction():
    session = _session()
    _seed_club(session, prestige=55, cash=120_000)
    service.academy_intake(session, "user-prestige-1", "club-prestige-1")

    campus = prestige_campus_comms.get_club_campus(session, "user-prestige-1", "club-prestige-1")
    assert campus["grid"]["width"] == 24
    assert campus["grid"]["height"] == 18
    assert len(campus["placed_modules"]) >= 10
    assert len(campus["module_catalog"]) == 12
    assert campus["campus_metrics"]["stadium_capacity"] >= 30_000

    # 1. Protected core module cannot be demolished
    with pytest.raises(service.OwnerError) as exc_demolish:
        prestige_campus_comms.update_campus_layout(
            session,
            "user-prestige-1",
            "club-prestige-1",
            action="demolish",
            instance_id="mod_stadium_core",
        )
    assert exc_demolish.value.code == "module_protected"

    # 2. Out-of-bounds placement is rejected
    with pytest.raises(service.OwnerError) as exc_bounds:
        prestige_campus_comms.start_campus_construction(
            session,
            "user-prestige-1",
            "club-prestige-1",
            operation="place_new",
            module_key="north_stand_expansion",
            x=22,
            y=17,
            rotation=0,
        )
    assert exc_bounds.value.code == "out_of_bounds"

    # 3. Overlapping placement is rejected
    with pytest.raises(service.OwnerError) as exc_overlap:
        prestige_campus_comms.start_campus_construction(
            session,
            "user-prestige-1",
            "club-prestige-1",
            operation="place_new",
            module_key="north_stand_expansion",
            x=16,
            y=2,
            rotation=0,
        )
    assert exc_overlap.value.code == "module_overlap"

    # 4. Valid new module construction commits to ledger, starts staged construction, and emits broadcast/news
    bal_before = ledger.balance(session, ledger.club_account("club-prestige-1"), ledger.GTEX)
    build_res = prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="place_new",
        module_key="north_stand_expansion",
        x=18,
        y=8,
        rotation=0,
        fast_track_completion=False,
    )
    assert build_res["status"] == "commissioned"
    assert build_res["project"]["stage"] == "groundworks"
    assert build_res["broadcast_event"]["event_type"] == "facility_upgrade"
    new_inst_id = build_res["module"]["instance_id"]
    bal_after = ledger.balance(session, ledger.club_account("club-prestige-1"), ledger.GTEX)
    assert bal_after == bal_before - Decimal("2200")

    # 5. Advance construction stage to completion
    adv_res = prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="advance_stage",
        instance_id=new_inst_id,
        fast_track_completion=True,
    )
    assert adv_res["project"]["status"] == "completed"
    assert adv_res["project"]["progress_pct"] == 100


def test_club_communications_threads_meetings_announcements_and_newsroom():
    session = _session()
    _seed_club(session, prestige=60, cash=100_000)
    regens = service.academy_intake(session, "user-prestige-1", "club-prestige-1")
    star_regen = regens[0]

    comms = prestige_campus_comms.get_club_communications(session, "user-prestige-1", "club-prestige-1")
    assert len(comms["direct_threads"]) >= 5
    assert len(comms["staff_contacts"]) == 5
    assert len(comms["player_contacts"]) >= 1
    assert len(comms["staff_room"]) >= 2
    assert len(comms["squad_room"]) >= 2
    assert len(comms["meetings"]) >= 2

    # Message a player directly and verify morale boost + grounded reply
    morale_before = star_regen.morale
    msg_res = prestige_campus_comms.send_thread_message(
        session,
        "user-prestige-1",
        "club-prestige-1",
        thread_id=f"player:{star_regen.id}",
        message="How is your training going in the academy complex?",
        sender_role="owner",
    )
    assert msg_res["status"] == "sent"
    assert star_regen.morale >= morale_before
    assert "OVR" in msg_res["reply_message"]["body"] or "Fitness" in msg_res["reply_message"]["body"]

    # Convene a meeting
    mtg_res = prestige_campus_comms.schedule_club_meeting(
        session,
        "user-prestige-1",
        "club-prestige-1",
        title="Stadium Expansion & Matchday Pricing Alignment",
        meeting_type="boardroom",
        convene_now=True,
    )
    assert mtg_res["status"] == "completed"
    assert mtg_res["meeting"]["outcome_summary"]

    # Publish an official club announcement to both club & public newsroom
    ann_res = prestige_campus_comms.publish_club_announcement(
        session,
        "user-prestige-1",
        "club-prestige-1",
        title="Campus Expansion Phase II Ratified",
        body="On World Day 12, Victoria Island Royals FC ratified Phase II of our 3D Campus Masterplan.",
        audience="all_club",
        publish_to_newsroom=True,
    )
    assert ann_res["status"] == "published"
    assert ann_res["newsroom_article"] is not None
    art_id = ann_res["newsroom_article"]["id"]

    # Update editorial status in newsroom
    ed_res = prestige_campus_comms.update_newsroom_editorial_status(
        session,
        "user-prestige-1",
        art_id,
        new_status="approved",
        editorial_note="Verified against Club Owner charter.",
    )
    assert ed_res["status"] == "published"
    assert ed_res["established_facts"]["editorial_workflow_state"] == "approved"


def test_construction_economy_idempotency_concurrency_cancellation_and_asset_sync():
    session = _session()
    _seed_club(session, prestige=60, cash=10_000)

    bal_start = ledger.balance(session, ledger.club_account("club-prestige-1"), ledger.GTEX)
    assert bal_start == Decimal("10000")

    # 1. Commission construction with idempotency_key
    res1 = prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="place_new",
        module_key="north_stand_expansion",
        x=18,
        y=8,
        rotation=0,
        fast_track_completion=False,
        idempotency_key="idem-campus-build-001",
    )
    assert res1["status"] == "commissioned"
    assert res1["idempotent_replay"] is False
    inst_id = res1["module"]["instance_id"]
    proj_id = res1["project"]["project_id"]
    bal_after_first = ledger.balance(session, ledger.club_account("club-prestige-1"), ledger.GTEX)
    assert bal_after_first == Decimal("7800")

    # 2. Replay exact same request with same idempotency_key -> zero duplicate debit!
    res_replay = prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="place_new",
        module_key="north_stand_expansion",
        x=18,
        y=8,
        rotation=0,
        fast_track_completion=False,
        idempotency_key="idem-campus-build-001",
    )
    assert res_replay["idempotent_replay"] is True
    assert res_replay["project"]["project_id"] == proj_id
    assert ledger.balance(session, ledger.club_account("club-prestige-1"), ledger.GTEX) == Decimal("7800")

    # 3. Reusing same idempotency_key for a different module raises 409 conflict
    with pytest.raises(service.OwnerError) as exc_idem_conflict:
        prestige_campus_comms.start_campus_construction(
            session,
            "user-prestige-1",
            "club-prestige-1",
            operation="place_new",
            module_key="vip_skybox_concourse",
            x=18,
            y=11,
            rotation=0,
            idempotency_key="idem-campus-build-001",
        )
    assert exc_idem_conflict.value.code == "idempotency_key_conflict"
    assert exc_idem_conflict.value.status == 409

    # 4. Concurrent upgrade on a module that is already under_construction raises 409
    with pytest.raises(service.OwnerError) as exc_in_prog:
        prestige_campus_comms.start_campus_construction(
            session,
            "user-prestige-1",
            "club-prestige-1",
            operation="upgrade_existing",
            instance_id=inst_id,
        )
    assert exc_in_prog.value.code == "construction_in_progress"
    assert exc_in_prog.value.status == 409

    # 5. Verify OwnerShowroomAsset was synchronized for the commissioned infrastructure
    showroom_before_cancel = storytelling.get_club_showroom(session, "user-prestige-1", "club-prestige-1")
    assert any(a["catalog_key"] == "campus:north_stand_expansion" for a in showroom_before_cancel["owned_assets"])

    # 6. Cancel active project -> reverses ledger debit, refunds club treasury, and retracts broadcast/asset
    cancel_res = prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="cancel_project",
        instance_id=inst_id,
    )
    assert cancel_res["status"] == "cancelled"
    assert ledger.balance(session, ledger.club_account("club-prestige-1"), ledger.GTEX) == Decimal("10000")
    showroom_after_cancel = storytelling.get_club_showroom(session, "user-prestige-1", "club-prestige-1")
    assert all(a["catalog_key"] != "campus:north_stand_expansion" for a in showroom_after_cancel["owned_assets"])


def test_communications_anti_farming_caps_and_dynamic_club_grounding():
    session = _session()
    _seed_club(session, prestige=62, cash=85_000)
    regens = service.academy_intake(session, "user-prestige-1", "club-prestige-1")
    regen = regens[0]
    regen.morale = 70
    session.commit()

    # 1. Trivial message (< 8 chars) does not grant morale boost
    trivial_res = prestige_campus_comms.send_thread_message(
        session,
        "user-prestige-1",
        "club-prestige-1",
        thread_id=f"player:{regen.id}",
        message="hi",
    )
    assert trivial_res["morale_boost_applied"] is False
    assert trivial_res["morale_delta"] == 0
    assert regen.morale == 70

    # 2. First substantive message on World Day 12 grants +4 morale and cites real club/player stats
    sub_res1 = prestige_campus_comms.send_thread_message(
        session,
        "user-prestige-1",
        "club-prestige-1",
        thread_id=f"player:{regen.id}",
        message="Keep pushing in training this week, you are central to our future.",
    )
    assert sub_res1["morale_boost_applied"] is True
    assert sub_res1["morale_delta"] == 4
    assert regen.morale == 74
    assert "Victoria Island Royals FC" in sub_res1["reply_message"]["body"]
    assert str(regen.rating) in sub_res1["reply_message"]["body"]

    # 3. Second substantive message on the SAME World Day 12 is delivered but cannot farm extra morale
    sub_res2 = prestige_campus_comms.send_thread_message(
        session,
        "user-prestige-1",
        "club-prestige-1",
        thread_id=f"player:{regen.id}",
        message="Another follow-up message on the exact same world day to test farming cap.",
    )
    assert sub_res2["morale_boost_applied"] is False
    assert sub_res2["morale_delta"] == 0
    assert regen.morale == 74

    # 4. Meetings also enforce once-per-world-day morale/mood boost cap and generate departmental minutes
    mtg1 = prestige_campus_comms.schedule_club_meeting(
        session,
        "user-prestige-1",
        "club-prestige-1",
        title="Morning Tactical Briefing",
        convene_now=True,
    )
    assert mtg1["morale_boost_applied"] is True
    assert len(mtg1["meeting"]["minutes"]) == 3
    morale_after_mtg1 = regen.morale

    mtg2 = prestige_campus_comms.schedule_club_meeting(
        session,
        "user-prestige-1",
        "club-prestige-1",
        title="Duplicate Afternoon Briefing",
        convene_now=True,
    )
    assert mtg2["morale_boost_applied"] is False
    assert regen.morale == morale_after_mtg1


def test_cross_club_isolation_and_unauthorized_access_rejection():
    session = _session()
    _seed_club(session, prestige=55, cash=90_000)

    intruder = User(
        id="user-intruder-2",
        email="intruder@gtex.test",
        username="intruder_owner",
        password_hash="hash",  # pragma: allowlist secret
    )
    session.add(intruder)
    session.commit()

    # Intruder cannot read or mutate club-prestige-1 campus or communications
    with pytest.raises(service.OwnerError) as exc1:
        prestige_campus_comms.get_club_campus(session, "user-intruder-2", "club-prestige-1")
    assert exc1.value.status in (403, 404)

    with pytest.raises(service.OwnerError) as exc2:
        prestige_campus_comms.get_club_communications(session, "user-intruder-2", "club-prestige-1")
    assert exc2.value.status in (403, 404)

    with pytest.raises(service.OwnerError) as exc3:
        prestige_campus_comms.send_thread_message(
            session,
            "user-intruder-2",
            "club-prestige-1",
            thread_id="room:staff",
            message="Unauthorized directive",
        )
    assert exc3.value.status in (403, 404)


def test_newsroom_editorial_quality_provenance_grounding_and_retraction_ticker_removal():
    session = _session()
    _seed_club(session, prestige=65, cash=100_000)

    # Commission a campus building so a broadcast + newsroom story is created
    build_res = prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="place_new",
        module_key="high_performance_centre",
        x=18,
        y=12,
        rotation=0,
        fast_track_completion=True,
    )
    b_id = build_res["broadcast_event"]["id"]

    sync_res = prestige_campus_comms.sync_club_verified_newsroom(session, "user-prestige-1", "club-prestige-1")
    assert len(sync_res["articles"]) >= 1
    for art in sync_res["articles"]:
        assert art["grounding_report"].get("valid") is True
        assert art["source_event_id"]

    # Find article linked to b_id and retract it -> must vanish from both newsroom and global ticker
    linked_art = next((a for a in sync_res["articles"] if a.get("source_event_id") == b_id), sync_res["articles"][0])
    retracted = prestige_campus_comms.update_newsroom_editorial_status(
        session,
        "user-prestige-1",
        linked_art["id"],
        new_status="retracted",
        editorial_note="Editorial retraction test",
    )
    assert retracted["status"] == "retracted"

    active_articles = storytelling.list_newsroom_articles(session, user_id="user-prestige-1", club_id="club-prestige-1")
    assert all(a["id"] != linked_art["id"] for a in active_articles)
    if linked_art.get("source_event_id") == b_id:
        ticker = storytelling.list_ticker_events(session, club_id="club-prestige-1")
        assert all(e["id"] != b_id for e in ticker)


def test_visual_png_webp_and_glb_binary_asset_contracts_on_disk():
    import json
    import struct
    from pathlib import Path

    repo_public = Path(__file__).resolve().parents[3] / "frontend" / "react-shell" / "public"
    assert repo_public.exists()

    # 1. Verify all 12 manifest high-res PNGs exist in public/img/prestige and public/img/showroom
    for item in prestige_campus_comms.PRESTIGE_VISUAL_MANIFEST:
        rel_png = item["file"].replace("/console/", "")
        rel_webp = item["webp"].replace("/console/", "")
        png_path = repo_public / rel_png
        webp_path = repo_public / rel_webp
        assert png_path.exists() and png_path.stat().st_size > 100_000, f"Invalid PNG: {png_path}"
        assert webp_path.exists() and webp_path.stat().st_size > 20_000, f"Invalid WebP: {webp_path}"

    # 2. Verify all 10 campus .glb 3D models exist and have valid glTF 2.0 binary headers + JSON/BIN chunks
    for mod in prestige_campus_comms.CAMPUS_MODULE_CATALOG.values():
        rel_glb = mod["model_glb_url"].replace("/console/", "")
        glb_path = repo_public / rel_glb
        assert glb_path.exists(), f"Missing GLB: {glb_path}"
        raw = glb_path.read_bytes()
        magic, version, total_len = struct.unpack("<4sII", raw[:12])
        assert magic == b"glTF"
        assert version == 2
        assert total_len == len(raw)
        j_len, j_type = struct.unpack("<II", raw[12:20])
        assert j_type == 0x4E4F534A
        gltf_json = json.loads(raw[20 : 20 + j_len].decode("utf-8"))
        assert len(gltf_json.get("meshes", [])) >= 1
        assert len(gltf_json.get("accessors", [])) >= 3
        assert len(gltf_json.get("materials", [])) >= 5
        # Verify multi-primitive PBR geometry (not a single low-poly box)
        primitives = gltf_json["meshes"][0]["primitives"]
        assert len(primitives) >= 4

    # 3. Verify Phase 2 3D Model Library Manifest, Master Exports, and 6-Stage Construction Models
    campus_models_dir = repo_public / "models" / "campus"
    assert (campus_models_dir / "MODEL_LIBRARY_MANIFEST.md").exists()
    manifest_data = json.loads((campus_models_dir / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest_data["models"]) >= 18
    for stage_file in (
        "stage_1_site_prep.glb",
        "stage_2_groundworks.glb",
        "stage_3_foundations.glb",
        "stage_4_structural.glb",
        "stage_5_finishing.glb",
        "indoor_training_arena.glb",
        "campus_tree_cluster.glb",
        "campus_road_plaza_segment.glb",
    ):
        assert (campus_models_dir / stage_file).exists(), f"Missing stage/scene GLB: {stage_file}"
        master_key = stage_file.replace(".glb", ".master.glb")
        assert (campus_models_dir / "masters" / master_key).exists(), f"Missing master GLB: {master_key}"

    # Verify all 6 construction stage mappings
    assert prestige_campus_comms._stage_from_progress(10) == "site_prep"
    assert prestige_campus_comms._stage_from_progress(25) == "groundworks"
    assert prestige_campus_comms._stage_from_progress(45) == "foundations"
    assert prestige_campus_comms._stage_from_progress(65) == "structural"
    assert prestige_campus_comms._stage_from_progress(85) == "finishing"
    assert prestige_campus_comms._stage_from_progress(100) == "completed"


def test_phase2_1_six_stage_construction_progression_and_28_model_inventory():
    import json
    import struct
    from pathlib import Path

    session = _session()
    _seed_club(session, prestige=75, cash=250_000)
    repo_public = Path(__file__).resolve().parents[3] / "frontend" / "react-shell" / "public"
    campus_models_dir = repo_public / "models" / "campus"
    manifest_data = json.loads((campus_models_dir / "manifest.json").read_text(encoding="utf-8"))

    # 1. Verify all 28 production models and 28 master models exist, are valid GLB, and conform to footprint
    assert len(manifest_data["models"]) == 28
    for item in manifest_data["models"]:
        assert (
            item["bounding_box_units"]["conforms_to_grid_footprint"] is True
        ), f"Model overhangs footprint: {item['model_key']}"
        assert item["production_stats"]["vertices"] >= 140
        assert item["production_stats"]["pbr_materials"] >= 3
        prod_path = repo_public / item["production_glb"].lstrip("/")
        master_path = repo_public / item["master_glb"].lstrip("/")
        assert prod_path.exists(), f"Missing production GLB: {prod_path}"
        assert master_path.exists(), f"Missing master GLB: {master_path}"
        for p in (prod_path, master_path):
            raw = p.read_bytes()
            magic, version, total_len = struct.unpack("<4sII", raw[:12])
            assert magic == b"glTF" and version == 2 and total_len == len(raw)

    # 2. Commission a new facility at Stage 1 (site_prep, 15%) and step through all 6 stages
    start_res = prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="place_new",
        module_key="recovery_hydro_hub",
        x=18,
        y=12,
        rotation=90,
        fast_track_completion=False,
        initial_stage="site_prep",
    )
    inst_id = start_res["module"]["instance_id"]
    assert start_res["module"]["status"] == "under_construction"
    assert start_res["module"]["construction_stage"] == "site_prep"
    assert start_res["module"]["progress_pct"] == 15
    assert start_res["module"]["lifecycle_state"] == "under_construction"
    assert start_res["module"]["ready_for_completion"] is False

    expected_sequence = [
        ("groundworks", 25, "under_construction", False),
        ("foundations", 45, "under_construction", False),
        ("structural", 65, "under_construction", False),
        ("finishing", 85, "ready_for_completion", True),
        ("completed", 100, "eligible_for_upgrade", False),
    ]
    for exp_stage, exp_pct, exp_lifecycle, exp_ready in expected_sequence:
        step_res = prestige_campus_comms.start_campus_construction(
            session,
            "user-prestige-1",
            "club-prestige-1",
            operation="advance_stage",
            instance_id=inst_id,
            fast_track_completion=False,
        )
        mod = step_res["module"]
        assert mod["construction_stage"] == exp_stage
        assert mod["progress_pct"] == exp_pct
        assert mod["lifecycle_state"] == exp_lifecycle
        assert mod["ready_for_completion"] is exp_ready

    # 3. Verify completed facility enrichment (current_effects, next_level_effects, upgrade_eligible)
    final_campus = prestige_campus_comms.get_club_campus(session, "user-prestige-1", "club-prestige-1")
    completed_mod = next(m for m in final_campus["placed_modules"] if m["instance_id"] == inst_id)
    assert completed_mod["status"] == "operational"
    assert completed_mod["upgrade_eligible"] is True
    assert completed_mod["current_effects"]["injury_reduction_pct"] > 0
    assert (
        completed_mod["next_level_effects"]["injury_reduction_pct"]
        > completed_mod["current_effects"]["injury_reduction_pct"]
    )

    # 4. Verify ChatGPT PR #378 GLB integrity audit reports 56/56 valid files and 0 duplicates
    import importlib.util

    audit_path = Path(__file__).resolve().parents[3] / "tools" / "audit_gtex_campus_glb.py"
    spec = importlib.util.spec_from_file_location("audit_gtex_campus_glb", audit_path)
    assert spec and spec.loader
    audit_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit_mod)
    audit_report = audit_mod.audit_library(campus_models_dir)
    assert audit_report["summary"]["files"] == 56
    assert audit_report["summary"]["valid_files"] == 56
    assert audit_report["summary"]["invalid_files"] == 0
    assert audit_report["summary"]["exact_binary_duplicates"] == []
    assert audit_report["summary"]["matching_geometry"] == []
    assert audit_report["summary"]["same_metrics_only"] == []


@pytest.mark.parametrize("rotation", [45, 135, 225, 315])
def test_campus_grid_rejects_non_right_angle_rotations(rotation: int):
    result = prestige_campus_comms.validate_module_placement(
        [],
        module_key="north_stand_expansion",
        x=0,
        y=0,
        rotation=rotation,
    )
    assert result["valid"] is False
    assert result["code"] == "invalid_rotation"


def test_campus_read_reconciliation_does_not_write_unchanged_projects():
    session = _session()
    _seed_club(session, prestige=60, cash=100_000)

    prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="place_new",
        module_key="recovery_hydro_hub",
        x=18,
        y=12,
        rotation=0,
        initial_stage="site_prep",
    )
    session.commit()
    state = session.get(OwnerClubState, "state-prestige-1")
    assert state is not None

    prestige_campus_comms.get_club_campus(session, "user-prestige-1", "club-prestige-1")
    assert session.is_modified(state, include_collections=True) is False


def test_upgrade_cancellation_does_not_resurrect_or_award_facility_benefits():
    session = _session()
    state = _seed_club(session, prestige=60, cash=120_000)
    original_level = int(state.facilities_json["stadium"])
    original_prestige = int(state.prestige)

    started = prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="upgrade_existing",
        instance_id="mod_stadium_core",
        fast_track_completion=False,
    )
    assert started["status"] == "commissioned"
    assert state.prestige == original_prestige
    assert int(state.facilities_json["stadium"]) == original_level

    cancelled = prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="cancel_project",
        instance_id="mod_stadium_core",
    )
    assert cancelled["status"] == "cancelled"
    cancelled_project = next(
        p for p in cancelled["campus"]["construction_projects"] if p["project_id"] == started["project"]["project_id"]
    )
    assert cancelled_project["status"] == "cancelled"

    session.commit()
    state.world_day += 10
    session.commit()
    later = prestige_campus_comms.get_club_campus(session, "user-prestige-1", "club-prestige-1")
    later_project = next(
        p for p in later["construction_projects"] if p["project_id"] == started["project"]["project_id"]
    )
    stadium = next(m for m in later["placed_modules"] if m["instance_id"] == "mod_stadium_core")
    assert later_project["status"] == "cancelled"
    assert later["active_projects_count"] == 0
    assert stadium["status"] == "operational"
    assert stadium["level"] == 2
    assert state.prestige == original_prestige
    assert int(state.facilities_json["stadium"]) == original_level

    # A fresh upgrade awards the facility level and prestige exactly when it becomes operational.
    prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="upgrade_existing",
        instance_id="mod_stadium_core",
        fast_track_completion=False,
    )
    assert state.prestige == original_prestige
    assert int(state.facilities_json["stadium"]) == original_level

    for _ in range(4):
        advanced = prestige_campus_comms.start_campus_construction(
            session,
            "user-prestige-1",
            "club-prestige-1",
            operation="advance_stage",
            instance_id="mod_stadium_core",
            fast_track_completion=False,
        )
    assert advanced["project"]["status"] == "completed"
    assert state.prestige > original_prestige
    assert int(state.facilities_json["stadium"]) == original_level + 1


def test_phase2_2_matchday_economics_gate_receipts_vip_hospitality_and_broadcast_integration():
    from sqlalchemy import select
    from app.owner_console import competitions
    from app.owner_console.models import LedgerEvent, OwnerCompetition, OwnerCompetitionEntry, OwnerMatch

    session = _session()
    state = _seed_club(session, prestige=65, cash=180_000)
    service.academy_intake(session, "user-prestige-1", "club-prestige-1")

    comp = OwnerCompetition(
        id="comp-matchday-econ-1",
        name="Lagos Premier Dynasty Cup",
        host_type="user",
        format="league",
        tier="Development",
        status="running",
        current_round=1,
        total_rounds=2,
    )
    entry = OwnerCompetitionEntry(
        id="entry-matchday-econ-1",
        competition_id=comp.id,
        club_id=state.club_id,
        owner_user_id=state.owner_user_id,
        club_name=state.club_name,
        is_ai=False,
        strength=70.0,
    )
    session.add_all([comp, entry])
    session.commit()

    def _run_home_match_and_capture_revenues(match_id: str) -> tuple[Decimal, Decimal]:
        state.fans = 2500
        state.prestige = 65
        match = OwnerMatch(
            id=match_id,
            competition_id=comp.id,
            round_number=1,
            home_club_id=state.club_id,
            away_club_id="ai-rival-1",
            home_name=state.club_name,
            away_name="Abuja Capital FC",
            status="played",
        )
        session.add(match)
        session.flush()
        side = competitions._side(session, entry, "balanced", "strongest", is_home=True)
        competitions._post_match_club(session, side, True, 2, 1, match)
        session.flush()
        gate_ev = session.scalar(
            select(LedgerEvent).where(
                LedgerEvent.event_type == "gate_receipts",
                LedgerEvent.related_object_id == match_id,
            )
        )
        tv_ev = session.scalar(
            select(LedgerEvent).where(
                LedgerEvent.event_type == "tv_broadcast_revenue",
                LedgerEvent.related_object_id == match_id,
            )
        )
        assert gate_ev is not None and tv_ev is not None
        return Decimal(gate_ev.gross_amount), Decimal(tv_ev.gross_amount)

    # 1. Baseline home matchday revenues & sponsor offers
    base_effects = prestige_campus_comms.compute_authoritative_campus_effects(session, state)
    base_gate, base_tv = _run_home_match_and_capture_revenues("match-econ-base")
    base_sponsors = service.get_sponsor_offers(session, "user-prestige-1", "club-prestige-1")
    base_airways_per_match = base_sponsors["offers"][0]["per_match_gross_gtex"]

    # 2. Place North Stand Expansion, VIP Skybox Concourse, and Floodlight Pylon Array UNDER CONSTRUCTION
    ns_build = prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="place_new",
        module_key="north_stand_expansion",
        x=18,
        y=8,
        rotation=0,
        fast_track_completion=False,
    )
    vip_build = prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="place_new",
        module_key="vip_skybox_concourse",
        x=18,
        y=11,
        rotation=0,
        fast_track_completion=False,
    )
    fl_build = prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="place_new",
        module_key="floodlight_pylon_array",
        x=22,
        y=15,
        rotation=0,
        fast_track_completion=False,
    )

    # Under-construction modules must grant ZERO matchday economics bonuses!
    uc_effects = prestige_campus_comms.compute_authoritative_campus_effects(session, state)
    assert uc_effects["stadium_capacity"] == base_effects["stadium_capacity"]
    assert uc_effects["matchday_revenue_bonus_pct"] == base_effects["matchday_revenue_bonus_pct"]
    assert uc_effects["vip_hospitality_flat_gtex"] == 0
    assert uc_effects["broadcast_revenue_bonus_pct"] == base_effects["broadcast_revenue_bonus_pct"]
    uc_gate, uc_tv = _run_home_match_and_capture_revenues("match-econ-uc")
    assert uc_gate == base_gate
    assert uc_tv == base_tv

    # 3. Complete all three facilities -> operational bonuses immediately feed into matchday simulation & sponsors
    for inst_id in (
        ns_build["module"]["instance_id"],
        vip_build["module"]["instance_id"],
        fl_build["module"]["instance_id"],
    ):
        prestige_campus_comms.start_campus_construction(
            session,
            "user-prestige-1",
            "club-prestige-1",
            operation="advance_stage",
            instance_id=inst_id,
            fast_track_completion=True,
        )

    op_effects = prestige_campus_comms.compute_authoritative_campus_effects(session, state)
    assert op_effects["stadium_capacity"] == base_effects["stadium_capacity"] + 8500
    assert op_effects["matchday_revenue_bonus_pct"] == base_effects["matchday_revenue_bonus_pct"] + 18
    assert op_effects["vip_hospitality_flat_gtex"] == 180
    assert op_effects["broadcast_revenue_bonus_pct"] == base_effects["broadcast_revenue_bonus_pct"] + 10
    assert op_effects["sponsor_revenue_bonus_pct"] >= base_effects["sponsor_revenue_bonus_pct"] + 20

    op_gate, op_tv = _run_home_match_and_capture_revenues("match-econ-op-l1")
    assert op_gate > base_gate + Decimal("600")
    assert op_tv > base_tv

    op_sponsors = service.get_sponsor_offers(session, "user-prestige-1", "club-prestige-1")
    assert op_sponsors["offers"][0]["per_match_gross_gtex"] > base_airways_per_match

    # 4. Upgrade North Stand Expansion from L1 -> L2: retains L1 during build, applies only incremental (L2 - L1) on completion
    prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="upgrade_existing",
        instance_id=ns_build["module"]["instance_id"],
        fast_track_completion=False,
    )
    upg_uc_effects = prestige_campus_comms.compute_authoritative_campus_effects(session, state)
    assert upg_uc_effects["stadium_capacity"] == op_effects["stadium_capacity"]
    assert upg_uc_effects["matchday_revenue_bonus_pct"] == op_effects["matchday_revenue_bonus_pct"]

    prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="advance_stage",
        instance_id=ns_build["module"]["instance_id"],
        fast_track_completion=True,
    )
    upg_done_effects = prestige_campus_comms.compute_authoritative_campus_effects(session, state)
    assert upg_done_effects["stadium_capacity"] == op_effects["stadium_capacity"] + 3500
    assert upg_done_effects["matchday_revenue_bonus_pct"] == op_effects["matchday_revenue_bonus_pct"] + 3
    l2_gate, _ = _run_home_match_and_capture_revenues("match-econ-op-l2")
    assert l2_gate > op_gate


def test_phase2_2_medical_hydrotherapy_and_high_performance_world_clock_recovery():
    session = _session()
    state = _seed_club(session, prestige=70, cash=200_000)
    regens = service.academy_intake(session, "user-prestige-1", "club-prestige-1")
    patient = regens[0]
    patient.injured_days = 14
    pers = dict(patient.personality_json or {})
    pers["fitness"] = 55
    patient.personality_json = pers
    session.commit()

    # 1. Baseline world-clock tick recovery
    tick_base = service.tick_club(session, state)
    base_heal_days = tick_base["medical_recovery"]["daily_injury_heal_days"]
    base_fitness_gain = tick_base["medical_recovery"]["daily_fitness_recovery"]
    assert patient.injured_days == 14 - base_heal_days
    assert int(patient.personality_json["fitness"]) == 55 + base_fitness_gain

    # 2. Commission High-Performance Centre and an upgrade to Hydrotherapy Hub (under_construction)
    hpc_build = prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="place_new",
        module_key="high_performance_centre",
        x=18,
        y=12,
        rotation=0,
        fast_track_completion=False,
    )
    prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="upgrade_existing",
        instance_id="mod_hydro_hub",
        fast_track_completion=False,
    )

    # Under construction (at start_world_day): medical recovery bonuses must not jump prematurely
    uc_effects = prestige_campus_comms.compute_authoritative_campus_effects(session, state, reconcile=False)
    assert uc_effects["stamina_retention_pct"] == tick_base["campus_effects"]["stamina_retention_pct"]
    assert uc_effects["daily_fitness_recovery"] == base_fitness_gain

    # 3. Complete both projects via world-clock ticks (tick_club reconciles campus projects automatically!)
    for _ in range(4):
        service.tick_club(session, state)

    campus_after_ticks = prestige_campus_comms.get_club_campus(session, "user-prestige-1", "club-prestige-1")
    hpc_mod = next(
        m for m in campus_after_ticks["placed_modules"] if m["instance_id"] == hpc_build["module"]["instance_id"]
    )
    hydro_mod = next(m for m in campus_after_ticks["placed_modules"] if m["instance_id"] == "mod_hydro_hub")
    assert hpc_mod["status"] == "operational"
    assert hydro_mod["status"] == "operational"
    assert hydro_mod["level"] == 3

    # 4. Reset patient injury/fitness and verify accelerated world-clock healing & fitness recovery
    patient.injured_days = 14
    pers = dict(patient.personality_json or {})
    pers["fitness"] = 55
    patient.personality_json = pers
    session.commit()

    tick_upgraded = service.tick_club(session, state)
    upgraded_heal_days = tick_upgraded["medical_recovery"]["daily_injury_heal_days"]
    upgraded_fitness_gain = tick_upgraded["medical_recovery"]["daily_fitness_recovery"]
    assert upgraded_heal_days >= base_heal_days + 2
    assert upgraded_fitness_gain > base_fitness_gain
    assert patient.injured_days == 14 - upgraded_heal_days
    assert int(patient.personality_json["fitness"]) == 55 + upgraded_fitness_gain


def test_phase2_2_academy_infrastructure_youth_intake_and_regen_development_integration():
    session = _session()
    state = _seed_club(session, prestige=70, cash=220_000)

    # 1. Baseline intake & growth driver snapshot before academy expansion
    base_effects = prestige_campus_comms.compute_authoritative_campus_effects(session, state)
    base_cohort = owner_engine.generate_regens(
        state.club_id,
        "phase2-2-fixed-seed",
        2,
        12,
        2,
        club_prestige=state.prestige,
        hoyd_youth=12,
        campus_intake_quality_pct=base_effects["regen_intake_quality_pct"],
        campus_ceiling_bonus=base_effects["academy_ceiling_bonus"],
    )

    # 2. Place Academy Youth Pitch and High-Performance Centre, and upgrade Elite Academy Complex (under_construction)
    pitch_build = prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="place_new",
        module_key="academy_youth_pitch",
        x=18,
        y=8,
        rotation=0,
        fast_track_completion=False,
    )
    hpc_build = prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="place_new",
        module_key="high_performance_centre",
        x=18,
        y=12,
        rotation=0,
        fast_track_completion=False,
    )
    prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="upgrade_existing",
        instance_id="mod_academy_hq",
        fast_track_completion=False,
    )

    # Under construction: academy bonuses must remain at baseline (retaining L2 mod_academy_hq, 0 from new builds)
    uc_effects = prestige_campus_comms.compute_authoritative_campus_effects(session, state)
    assert uc_effects["regen_intake_quality_pct"] == base_effects["regen_intake_quality_pct"]
    assert uc_effects["regen_development_speed_pct"] == base_effects["regen_development_speed_pct"]
    assert uc_effects["academy_ceiling_bonus"] == base_effects["academy_ceiling_bonus"]

    # 3. Complete all three projects -> operational academy & training bonuses activate
    for inst_id in (
        pitch_build["module"]["instance_id"],
        hpc_build["module"]["instance_id"],
        "mod_academy_hq",
    ):
        prestige_campus_comms.start_campus_construction(
            session,
            "user-prestige-1",
            "club-prestige-1",
            operation="advance_stage",
            instance_id=inst_id,
            fast_track_completion=True,
        )

    op_effects = prestige_campus_comms.compute_authoritative_campus_effects(session, state)
    assert op_effects["regen_intake_quality_pct"] > base_effects["regen_intake_quality_pct"]
    assert op_effects["regen_development_speed_pct"] > base_effects["regen_development_speed_pct"]
    assert op_effects["academy_ceiling_bonus"] >= base_effects["academy_ceiling_bonus"] + 3
    assert op_effects["training_efficiency_bonus_pct"] > base_effects["training_efficiency_bonus_pct"]
    assert op_effects["academy_intake_bonus_count"] >= 1

    # 4. Deterministic comparison with identical seed proves higher initial rating and higher potential ceiling
    elite_cohort = owner_engine.generate_regens(
        state.club_id,
        "phase2-2-fixed-seed",
        2,
        12,
        2,
        club_prestige=state.prestige,
        hoyd_youth=12,
        campus_intake_quality_pct=op_effects["regen_intake_quality_pct"],
        campus_ceiling_bonus=op_effects["academy_ceiling_bonus"],
    )
    for b_p, e_p in zip(base_cohort, elite_cohort):
        assert e_p["rating"] > b_p["rating"]
        assert e_p["potential"] > b_p["potential"]

    # 5. Authoritative academy_intake persists enhanced cohort & get_club_campus reads persisted DB potential
    persisted_regens = service.academy_intake(session, "user-prestige-1", "club-prestige-1")
    assert len(persisted_regens) >= 3
    campus_view = prestige_campus_comms.get_club_campus(session, "user-prestige-1", "club-prestige-1")
    by_id = {p.id: p for p in persisted_regens}
    for prospect in campus_view["academy_campus_prospects"]:
        if prospect["id"] in by_id:
            assert prospect["potential"] == by_id[prospect["id"]].potential

    # 6. World-clock tick_club applies campus_infrastructure growth driver to academy regens
    tick_res = service.tick_club(session, state)
    assert len(tick_res["growth"]) >= len(persisted_regens)
    for g_entry in tick_res["growth"]:
        assert "campus_infrastructure" in g_entry["drivers"]
        assert g_entry["drivers"]["campus_infrastructure"] > 0


def test_phase2_2_sponsor_campus_uplift_is_applied_once_to_offer_and_active_deal_payout():
    from sqlalchemy import select
    from app.owner_console import competitions
    from app.owner_console.models import LedgerEvent, OwnerMatch, OwnerSponsorDeal

    session = _session()
    state = _seed_club(session, prestige=70, cash=200_000)

    # One operational VIP module provides a 20% campus sponsor-revenue bonus.
    facs = dict(state.facilities_json or {})
    facs["_campus_modules"] = [
        {
            "instance_id": "mod_vip_sponsor_test",
            "module_key": "vip_skybox_concourse",
            "category": "commercial",
            "x": 18,
            "y": 12,
            "rotation": 0,
            "level": 1,
            "status": "operational",
            "construction_stage": "completed",
            "progress_pct": 100,
        }
    ]
    state.facilities_json = facs
    session.commit()

    effects = prestige_campus_comms.compute_authoritative_campus_effects(session, state)
    sponsor_bonus_pct = int(effects["sponsor_revenue_bonus_pct"])
    assert sponsor_bonus_pct == 20

    offers = service.get_sponsor_offers(session, "user-prestige-1", "club-prestige-1")
    offer = offers["offers"][0]
    base_rate = int(offer["base_per_match_gross_gtex"])
    quoted_effective_rate = int(offer["per_match_gross_gtex"])
    expected_effective_rate = int(round(base_rate * (1.0 + sponsor_bonus_pct / 200.0)))
    assert quoted_effective_rate == expected_effective_rate

    signed = service.sign_sponsor_offer(
        session,
        "user-prestige-1",
        "club-prestige-1",
        offer["offer_id"],
    )
    deal = session.get(OwnerSponsorDeal, signed["deal_id"])
    assert deal is not None
    # Persist only the negotiated base. The current campus effect is applied at settlement.
    assert int(deal.per_match_gross) == base_rate

    match = OwnerMatch(
        id="match-sponsor-campus-uplift-once",
        competition_id="comp-sponsor-campus-uplift",
        round_number=1,
        home_club_id=state.club_id,
        away_club_id="ai-sponsor-rival",
        home_name=state.club_name,
        away_name="Abuja Capital FC",
        status="played",
    )
    session.add(match)
    session.flush()
    competitions._post_match_club(
        session,
        {"state": state, "xi": [], "campus_effects": effects},
        True,
        1,
        0,
        match,
    )
    session.flush()

    payout = session.scalar(
        select(LedgerEvent).where(
            LedgerEvent.event_type == "sponsor_revenue",
            LedgerEvent.related_object_id == deal.id,
        )
    )
    assert payout is not None
    assert int(Decimal(payout.gross_amount)) == expected_effective_rate

    active = service.get_sponsor_offers(session, "user-prestige-1", "club-prestige-1")["active_deals"]
    signed_view = next(item for item in active if item["id"] == deal.id)
    assert int(Decimal(signed_view["per_match_gross"])) == expected_effective_rate
    assert int(Decimal(signed_view["contract_base_per_match_gross"])) == base_rate


def test_phase2_2_matchday_attendance_increases_with_stadium_infrastructure_and_never_exceeds_capacity():
    from sqlalchemy import select
    from app.owner_console import competitions
    from app.owner_console.models import LedgerEvent, OwnerCompetition, OwnerCompetitionEntry, OwnerMatch

    session = _session()
    state = _seed_club(session, prestige=68, cash=240_000)
    service.academy_intake(session, "user-prestige-1", "club-prestige-1")

    comp = OwnerCompetition(
        id="comp-attendance-cap-1",
        name="GTEX Attendance Dynasty Shield",
        host_type="user",
        format="league",
        tier="Friends",
        status="running",
        current_round=1,
        total_rounds=4,
    )
    entry = OwnerCompetitionEntry(
        id="entry-attendance-cap-1",
        competition_id=comp.id,
        club_id=state.club_id,
        owner_user_id=state.owner_user_id,
        club_name=state.club_name,
        is_ai=False,
        strength=72.0,
    )
    session.add_all([comp, entry])
    session.commit()

    def _run_home_fixture(match_id: str, *, fans: int, prestige: int) -> tuple[OwnerMatch, dict, Decimal]:
        state.fans = fans
        state.prestige = prestige
        match = OwnerMatch(
            id=match_id,
            competition_id=comp.id,
            round_number=1,
            home_club_id=state.club_id,
            away_club_id="ai-att-rival",
            home_name=state.club_name,
            away_name="Kano Pillars FC",
            status="played",
        )
        session.add(match)
        session.flush()
        side = competitions._side(session, entry, "balanced", "strongest", is_home=True)
        competitions._post_match_club(session, side, True, 2, 0, match)
        session.flush()
        gate_ev = session.scalar(
            select(LedgerEvent).where(
                LedgerEvent.event_type == "gate_receipts",
                LedgerEvent.related_object_id == match_id,
            )
        )
        assert gate_ev is not None
        return match, competitions.match_dict(match, full=True), Decimal(gate_ev.gross_amount)

    # 1. Sub-capacity regime: attendance increases with operational stadium infrastructure
    base_match, base_resp, base_gate = _run_home_fixture("match-att-sub-base", fans=2_500, prestige=68)
    assert base_match.attendance is not None and base_match.stadium_capacity == 33_500
    assert base_resp["attendance"] == base_match.attendance
    assert base_resp["narrative"]["attendance"] == base_match.attendance
    assert base_match.attendance < base_match.stadium_capacity
    assert int(base_gate) == base_resp["gate_receipts_gtex"]

    # Place North Stand Expansion L1 (+8,500 cap) and VIP Skybox L1 -> complete construction
    ns = prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="place_new",
        module_key="north_stand_expansion",
        x=18,
        y=8,
        rotation=0,
        fast_track_completion=True,
    )
    prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="place_new",
        module_key="vip_skybox_concourse",
        x=18,
        y=11,
        rotation=0,
        fast_track_completion=True,
    )

    exp_match, exp_resp, exp_gate = _run_home_fixture("match-att-sub-expanded", fans=2_500, prestige=68)
    assert exp_match.stadium_capacity == 42_000
    assert exp_match.attendance > base_match.attendance
    assert exp_match.attendance <= exp_match.stadium_capacity
    assert exp_resp["attendance"] == exp_match.attendance
    assert exp_gate > base_gate

    # 2. High-demand sellout regime: raw demand exceeds capacity, attendance is hard-capped at operational stadium_capacity
    # Reset North Stand Expansion to test 33,500 cap vs 42,000 cap vs 45,500 cap under sellout demand (fans=20,000)
    prestige_campus_comms.update_campus_layout(
        session,
        "user-prestige-1",
        "club-prestige-1",
        action="demolish",
        instance_id=ns["module"]["instance_id"],
    )
    cap33_match, cap33_resp, cap33_gate = _run_home_fixture("match-att-cap-33k", fans=20_000, prestige=88)
    assert cap33_match.stadium_capacity == 33_500
    assert cap33_resp["narrative"]["raw_attendance_demand"] > 33_500
    assert cap33_match.attendance == 33_500

    ns2 = prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="place_new",
        module_key="north_stand_expansion",
        x=18,
        y=8,
        rotation=0,
        fast_track_completion=True,
    )
    cap42_match, cap42_resp, cap42_gate = _run_home_fixture("match-att-cap-42k", fans=20_000, prestige=88)
    assert cap42_match.stadium_capacity == 42_000
    assert cap42_resp["narrative"]["raw_attendance_demand"] > 42_000
    assert cap42_match.attendance == 42_000
    assert cap42_match.attendance > cap33_match.attendance
    assert cap42_gate > cap33_gate

    # Upgrade North Stand Expansion to L2 (+3,500 cap -> 45,500 total capacity)
    prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="upgrade_existing",
        instance_id=ns2["module"]["instance_id"],
        fast_track_completion=True,
    )
    cap45_match, cap45_resp, cap45_gate = _run_home_fixture("match-att-cap-45k", fans=20_000, prestige=88)
    assert cap45_match.stadium_capacity == 45_500
    assert cap45_resp["narrative"]["raw_attendance_demand"] > 45_500
    assert cap45_match.attendance == 45_500
    assert cap45_match.attendance > cap42_match.attendance
    assert cap45_gate > cap42_gate


def test_phase2_2_medical_injury_reduction_pct_reduces_authoritative_injury_incidence_and_severity():
    session = _session()
    state = _seed_club(session, prestige=75, cash=240_000)

    # 1. Compare authoritative injury-risk evaluation with 0% vs operational medical campus reduction
    base_effects = prestige_campus_comms.compute_authoritative_campus_effects(session, state)
    assert base_effects["injury_reduction_pct"] == 24  # starter recovery_hydro_hub L2 + high_performance_centre L1

    # Upgrade Hydrotherapy Hub to L3 and build High-Performance Centre L1 + second Hydrotherapy Hub L2
    prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="upgrade_existing",
        instance_id="mod_hydro_hub",
        fast_track_completion=True,
    )
    prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="place_new",
        module_key="recovery_hydro_hub",
        x=18,
        y=12,
        rotation=0,
        fast_track_completion=True,
    )
    elite_effects = prestige_campus_comms.compute_authoritative_campus_effects(session, state)
    assert elite_effects["injury_reduction_pct"] > base_effects["injury_reduction_pct"]

    # 2. Across a cohort of fatigued player states, higher injury_reduction_pct strictly lowers effective risk,
    # reduces total injury incidence count, and reduces total injured_days layoff severity
    unmitigated_injuries = 0
    unmitigated_days = 0
    elite_injuries = 0
    elite_days = 0
    for idx in range(40):
        pid = f"player-strain-{idx}"
        res_zero = owner_engine.evaluate_player_injury_risk(
            club_id=state.club_id,
            player_id=pid,
            context_key="fixture-congestion-1",
            fitness=38,
            minutes_load=90,
            mentality="attacking",
            medical_level=1,
            med_director_expertise=10,
            campus_injury_reduction_pct=0,
        )
        res_elite = owner_engine.evaluate_player_injury_risk(
            club_id=state.club_id,
            player_id=pid,
            context_key="fixture-congestion-1",
            fitness=38,
            minutes_load=90,
            mentality="attacking",
            medical_level=1,
            med_director_expertise=10,
            campus_injury_reduction_pct=elite_effects["injury_reduction_pct"],
        )
        assert res_elite["effective_risk"] < res_zero["effective_risk"]
        if res_zero["injured"]:
            unmitigated_injuries += 1
            unmitigated_days += res_zero["injured_days"]
        if res_elite["injured"]:
            elite_injuries += 1
            elite_days += res_elite["injured_days"]
            assert res_elite["injured_days"] < res_zero["injured_days"]

    assert unmitigated_injuries > elite_injuries
    assert unmitigated_days > elite_days

    # 3. Verify tick_club consumes injury_reduction_pct and reports avg_effective_injury_risk in medical_recovery
    service.academy_intake(session, "user-prestige-1", "club-prestige-1")
    tick_res = service.tick_club(session, state)
    assert tick_res["medical_recovery"]["injury_reduction_pct"] == elite_effects["injury_reduction_pct"]
    assert tick_res["medical_recovery"]["avg_effective_injury_risk"] > 0


def test_phase2_2_tv_revenue_settlement_matches_match_dict_and_handles_historical_matches():
    from sqlalchemy import select
    from app.owner_console import competitions
    from app.owner_console.models import LedgerEvent, OwnerCompetition, OwnerCompetitionEntry, OwnerMatch

    session = _session()
    state = _seed_club(session, prestige=72, cash=200_000)
    service.academy_intake(session, "user-prestige-1", "club-prestige-1")

    comp = OwnerCompetition(
        id="comp-tv-rev-1",
        name="GTEX Broadcast Integrity Cup",
        host_type="user",
        format="league",
        tier="Friends",
        status="running",
        current_round=1,
        total_rounds=2,
    )
    entry = OwnerCompetitionEntry(
        id="entry-tv-rev-1",
        competition_id=comp.id,
        club_id=state.club_id,
        owner_user_id=state.owner_user_id,
        club_name=state.club_name,
        is_ai=False,
        strength=70.0,
    )
    session.add_all([comp, entry])
    session.commit()

    # 1. Historical/unsettled match without persisted TV revenue must NOT invent 650
    historical_match = OwnerMatch(
        id="match-tv-historical-unpersisted",
        competition_id=comp.id,
        round_number=1,
        home_club_id=state.club_id,
        away_club_id="ai-tv-rival",
        home_name=state.club_name,
        away_name="Enugu Rangers FC",
        status="played",
        home_goals=1,
        away_goals=1,
        narrative_json={"momentum": [50] * 18},
    )
    session.add(historical_match)
    session.flush()
    hist_dict = competitions.match_dict(historical_match, full=True)
    assert hist_dict["tv_revenue"] is None
    assert hist_dict["tv_revenue_gtex"] is None
    assert historical_match.tv_revenue is None

    # 2. Settled match persists actual TV broadcast revenue and match_dict agrees 100% with LedgerEvent
    settled_match = OwnerMatch(
        id="match-tv-settled-base",
        competition_id=comp.id,
        round_number=1,
        home_club_id=state.club_id,
        away_club_id="ai-tv-rival",
        home_name=state.club_name,
        away_name="Enugu Rangers FC",
        status="played",
        home_goals=2,
        away_goals=0,
    )
    session.add(settled_match)
    session.flush()
    side = competitions._side(session, entry, "balanced", "strongest", is_home=True)
    competitions._post_match_club(session, side, True, 2, 0, settled_match)
    session.flush()

    tv_ledger = session.scalar(
        select(LedgerEvent).where(
            LedgerEvent.event_type == "tv_broadcast_revenue",
            LedgerEvent.related_object_id == settled_match.id,
        )
    )
    assert tv_ledger is not None
    settled_dict = competitions.match_dict(settled_match, full=True)
    assert settled_dict["tv_revenue"] == int(Decimal(tv_ledger.gross_amount))
    assert settled_dict["tv_revenue_gtex"] == int(Decimal(tv_ledger.gross_amount))
    assert settled_match.tv_revenue == int(Decimal(tv_ledger.gross_amount))
    assert settled_dict["tv_revenue"] != 650

    # 3. Add Floodlight Pylon Array -> higher settled TV revenue reflected identically in ledger and match_dict
    prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="place_new",
        module_key="floodlight_pylon_array",
        x=22,
        y=15,
        rotation=0,
        fast_track_completion=True,
    )
    upgraded_match = OwnerMatch(
        id="match-tv-settled-upgraded",
        competition_id=comp.id,
        round_number=2,
        home_club_id=state.club_id,
        away_club_id="ai-tv-rival",
        home_name=state.club_name,
        away_name="Enugu Rangers FC",
        status="played",
        home_goals=2,
        away_goals=0,
    )
    session.add(upgraded_match)
    session.flush()
    side_upg = competitions._side(session, entry, "balanced", "strongest", is_home=True)
    competitions._post_match_club(session, side_upg, True, 2, 0, upgraded_match)
    session.flush()

    tv_ledger_upg = session.scalar(
        select(LedgerEvent).where(
            LedgerEvent.event_type == "tv_broadcast_revenue",
            LedgerEvent.related_object_id == upgraded_match.id,
        )
    )
    assert tv_ledger_upg is not None
    upg_dict = competitions.match_dict(upgraded_match, full=True)
    assert upg_dict["tv_revenue"] == int(Decimal(tv_ledger_upg.gross_amount))
    assert upg_dict["tv_revenue"] > settled_dict["tv_revenue"]


def test_phase2_2_post_match_club_injury_integration_persistence_and_idempotency():
    from sqlalchemy import func, select
    from sqlalchemy.orm.attributes import flag_modified
    from app.owner_console import competitions
    from app.owner_console.models import (
        LedgerEvent,
        OwnerCompetition,
        OwnerCompetitionEntry,
        OwnerMatch,
        OwnerSquadPlayer,
    )

    session = _session()
    state = _seed_club(session, prestige=75, cash=260_000)
    # Seed 14 squad players so we have 11 fatigued starters + bench + 1 already-injured player
    for idx in range(14):
        pers = {"fitness": 48, "ambition": 12, "professionalism": 12}
        p = OwnerSquadPlayer(
            id=f"post-match-inj-p-{idx}",
            club_id=state.club_id,
            name=f"Match Starter {idx}",
            position="midfielder" if idx > 0 else "goalkeeper",
            age=23,
            rating=72 - (idx // 3),
            potential=80,
            value_coin=Decimal("2500"),
            morale=75,
            minutes=180,
            injured_days=11 if idx == 13 else 0,
            is_regen=False,
            personality_json=pers,
        )
        session.add(p)
    session.commit()

    comp = OwnerCompetition(
        id="comp-post-match-inj-1",
        name="GTEX Matchday Medical Shield",
        host_type="user",
        format="league",
        tier="Friends",
        status="running",
        current_round=1,
        total_rounds=2,
    )
    entry = OwnerCompetitionEntry(
        id="entry-post-match-inj-1",
        competition_id=comp.id,
        club_id=state.club_id,
        owner_user_id=state.owner_user_id,
        club_name=state.club_name,
        is_ai=False,
        strength=72.0,
    )
    session.add_all([comp, entry])
    session.commit()

    # 1. Run _post_match_club with zero campus medical reduction vs elite campus medical reduction
    side_zero = competitions._side(session, entry, "attacking", "strongest", is_home=True)
    zero_effects = dict(side_zero["campus_effects"])
    zero_effects["injury_reduction_pct"] = 0
    zero_effects["stamina_retention_pct"] = 0
    side_zero["campus_effects"] = zero_effects
    # Include the pre-injured player in side["xi"] intentionally to verify _post_match_club never overwrites existing injury state
    side_zero["xi"] = list(side_zero["xi"][:10]) + ["post-match-inj-p-13"]

    match_zero = OwnerMatch(
        id="match-post-inj-settlement-check",
        competition_id=comp.id,
        round_number=1,
        home_club_id=state.club_id,
        away_club_id="ai-inj-rival",
        home_name=state.club_name,
        away_name="Ibadan Shooting Stars",
        status="played",
    )
    session.add(match_zero)
    session.flush()

    notes_first = competitions._post_match_club(session, side_zero, True, 2, 1, match_zero)
    session.flush()

    assessments_zero = match_zero.narrative_json.get("home_injury_assessments") or []
    assert len(assessments_zero) == 10  # 10 healthy starters assessed; pre-injured player skipped
    pre_injured = session.get(OwnerSquadPlayer, "post-match-inj-p-13")
    assert pre_injured is not None and pre_injured.injured_days == 11  # Existing injury state preserved untouched!

    # Verify idempotency: calling _post_match_club again for the same match & side is a deterministic no-op
    p0 = session.get(OwnerSquadPlayer, "post-match-inj-p-0")
    fitness_after_first = int(p0.personality_json["fitness"])
    minutes_after_first = p0.minutes
    gate_count_first = session.scalar(
        select(func.count())
        .select_from(LedgerEvent)
        .where(LedgerEvent.event_type == "gate_receipts", LedgerEvent.related_object_id == match_zero.id)
    )
    notes_second = competitions._post_match_club(session, side_zero, True, 2, 1, match_zero)
    session.flush()
    assert notes_second == notes_first
    assert int(p0.personality_json["fitness"]) == fitness_after_first
    assert p0.minutes == minutes_after_first
    gate_count_second = session.scalar(
        select(func.count())
        .select_from(LedgerEvent)
        .where(LedgerEvent.event_type == "gate_receipts", LedgerEvent.related_object_id == match_zero.id)
    )
    assert gate_count_second == gate_count_first == 1

    # 2. Reset squad to identical pre-match state and run _post_match_club with upgraded medical campus facilities
    for idx in range(13):
        pl = session.get(OwnerSquadPlayer, f"post-match-inj-p-{idx}")
        pl.injured_days = 0
        pl.minutes = 180
        pers = dict(pl.personality_json or {})
        pers["fitness"] = 48
        pl.personality_json = pers
        flag_modified(pl, "personality_json")
    session.flush()

    prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="upgrade_existing",
        instance_id="mod_hydro_hub",
        fast_track_completion=True,
    )
    prestige_campus_comms.start_campus_construction(
        session,
        "user-prestige-1",
        "club-prestige-1",
        operation="place_new",
        module_key="recovery_hydro_hub",
        x=18,
        y=12,
        rotation=0,
        fast_track_completion=True,
    )
    side_med = competitions._side(session, entry, "attacking", "strongest", is_home=True)
    side_med["xi"] = list(side_zero["xi"])

    match_med = OwnerMatch(
        id="match-post-inj-settlement-check",
        competition_id=comp.id,
        round_number=2,
        home_club_id=state.club_id,
        away_club_id="ai-inj-rival",
        home_name=state.club_name,
        away_name="Ibadan Shooting Stars",
        status="played",
    )
    # Use a fresh match instance with same context seed or distinct match to compare assessments
    match_med.id = "match-post-inj-med-upgraded"
    session.add(match_med)
    session.flush()
    competitions._post_match_club(session, side_med, True, 2, 1, match_med)
    session.flush()

    assessments_med = match_med.narrative_json.get("home_injury_assessments") or []
    assert len(assessments_med) == 10
    for a_zero, a_med in zip(assessments_zero, assessments_med):
        assert a_med["injury_reduction_pct"] > a_zero["injury_reduction_pct"]
        assert a_med["effective_risk"] < a_zero["effective_risk"]
        assert a_med["post_match_fitness"] > a_zero["post_match_fitness"]


def test_phase2_2_daily_training_workload_exposure_and_injured_regen_development_restriction():
    from sqlalchemy.orm.attributes import flag_modified

    session = _session()
    state = _seed_club(session, prestige=70, cash=220_000)
    state.mentality = "attacking"
    regens = service.academy_intake(session, "user-prestige-1", "club-prestige-1")
    assert len(regens) >= 2

    healthy_regen = regens[0]
    injured_regen = regens[1]

    # Configure identical attributes/personalities so only injury status differs for development comparison
    shared_pers = {
        "ambition": 14,
        "loyalty": 14,
        "marketability": 12,
        "professionalism": 15,
        "adaptability": 14,
        "growth_responsiveness": 16,
        "environment_sensitivity": 15,
        "transfer_pressure": 10,
        "growth_buffer": 0.85,
        "fitness": 88,
    }
    for r in (healthy_regen, injured_regen):
        r.rating = 62
        r.potential = 86
        r.morale = 80
        r.minutes = 270
        r.personality_json = dict(shared_pers)
        flag_modified(r, "personality_json")

    injured_regen.injured_days = 10  # Sidelined with a 10-day injury

    # Add a low-minute reserve regen to verify deterministic daily training workload tiers
    if len(regens) >= 3:
        reserve_regen = regens[2]
    else:
        reserve_regen = service.academy_intake(session, "user-prestige-1", "club-prestige-1")[0]
    reserve_regen.rating = 50
    reserve_regen.minutes = 0
    reserve_pers = dict(shared_pers)
    reserve_pers["fitness"] = 96
    reserve_regen.personality_json = reserve_pers
    flag_modified(reserve_regen, "personality_json")
    session.commit()

    # 1. Verify deterministic workload calculation across starter, rotation, and unplayed reserve profiles
    w_starter = owner_engine.calculate_daily_training_workload_minutes(
        {"minutes": 270, "age": 19, "personality": {"fitness": 88, "professionalism": 15}},
        is_starter=True,
        mentality="attacking",
        training_level=2,
    )
    w_rotation = owner_engine.calculate_daily_training_workload_minutes(
        {"minutes": 45, "age": 19, "personality": {"fitness": 88, "professionalism": 15}},
        is_starter=False,
        mentality="balanced",
        training_level=2,
    )
    w_reserve = owner_engine.calculate_daily_training_workload_minutes(
        {"minutes": 0, "age": 19, "personality": {"fitness": 96, "professionalism": 15}},
        is_starter=False,
        mentality="defensive",
        training_level=1,
    )
    assert w_starter["minutes_load"] > w_rotation["minutes_load"] > w_reserve["minutes_load"]
    assert w_starter["workload_tier"] == "high_intensity"
    assert w_reserve["workload_tier"] == "light_recovery"

    # Higher training workload produces strictly higher unmitigated & effective injury risk
    risk_starter = owner_engine.evaluate_player_injury_risk(
        club_id=state.club_id,
        player_id="workload-cmp",
        context_key="day-1",
        fitness=65,
        minutes_load=w_starter["minutes_load"],
        mentality="attacking",
        campus_injury_reduction_pct=20,
    )
    risk_reserve = owner_engine.evaluate_player_injury_risk(
        club_id=state.club_id,
        player_id="workload-cmp",
        context_key="day-1",
        fitness=65,
        minutes_load=w_reserve["minutes_load"],
        mentality="defensive",
        campus_injury_reduction_pct=20,
    )
    assert risk_starter["effective_risk"] > risk_reserve["effective_risk"]

    # 2. Run world-clock tick_club and verify:
    # - Healthy regen cashes out growth_buffer -> gains +1 rating point normally
    # - Injured regen is restricted during rehabilitation (points == 0, rehab_growth_multiplier == 0.15, rating unchanged)
    tick_res = service.tick_club(session, state)
    assert tick_res["medical_recovery"]["avg_training_workload_minutes"] > 0

    growth_by_name = {g["player"]: g for g in tick_res["growth"]}
    h_growth = growth_by_name[healthy_regen.name]
    i_growth = growth_by_name[injured_regen.name]

    assert h_growth["injury_rehab_restriction"] is False
    assert h_growth["rehab_growth_multiplier"] == 1.0
    assert h_growth["points"] >= 1
    assert healthy_regen.rating == 62 + h_growth["points"]

    assert i_growth["injury_rehab_restriction"] is True
    assert i_growth["rehab_growth_multiplier"] == 0.15
    assert i_growth["points"] == 0
    assert injured_regen.rating == 62
    assert injured_regen.personality_json["last_training_workload_tier"] == "rehabilitation"
    assert injured_regen.personality_json["last_training_workload_minutes"] == 0
    assert sum(i_growth["drivers"].values()) < sum(h_growth["drivers"].values()) * 0.25


def test_phase2_3_owner_daily_briefing_six_authoritative_sections_and_world_day_idempotency():
    from sqlalchemy.orm.attributes import flag_modified
    from app.owner_console import daily_operations_hub

    session = _session()
    state = _seed_club(session, prestige=68, cash=180_000)
    regens = service.academy_intake(session, "user-prestige-1", "club-prestige-1")
    assert len(regens) >= 2

    # Put one player in the medical room (injured_days = 6) and lower fitness on another
    regens[0].injured_days = 6
    p0_pers = dict(regens[0].personality_json or {})
    p0_pers["last_injury_type"] = "Hamstring Grade-1 Strain"
    regens[0].personality_json = p0_pers
    flag_modified(regens[0], "personality_json")

    regens[1].morale = 52
    p1_pers = dict(regens[1].personality_json or {})
    p1_pers["fitness"] = 76
    regens[1].personality_json = p1_pers
    flag_modified(regens[1], "personality_json")
    session.commit()

    # 1. Generate Daily Briefing via storytelling.get_daily_briefing (which delegates to daily_operations_hub)
    briefing = storytelling.get_daily_briefing(session, "user-prestige-1", "club-prestige-1")
    assert briefing["club_id"] == "club-prestige-1"
    assert briefing["world_day"] == state.world_day
    assert len(briefing["sections"]) == 6

    # Verify all 6 required sections exist and are grounded in real club state
    for key in (
        "executive_briefing",
        "managers_report",
        "general_managers_report",
        "hoyd_report",
        "medical_directors_report",
        "financial_commercial_report",
    ):
        assert key in briefing, f"Missing briefing section {key}"

    exec_sec = briefing["executive_briefing"]
    assert exec_sec["financial_position"]["cash_gtex"] == 177_000  # 180k - 3k academy intake
    assert exec_sec["squad_condition_and_availability"]["injured_players"] == 1
    assert any(r["risk_id"] == "risk_medical_load" for r in exec_sec["urgent_risks"])
    assert any(r["risk_id"] == "risk_squad_morale" for r in exec_sec["urgent_risks"])

    med_sec = briefing["medical_directors_report"]
    assert len(med_sec["injured_players"]) == 1
    inj_dossier = med_sec["injured_players"][0]
    assert inj_dossier["id"] == regens[0].id
    assert inj_dossier["injured_days"] == 6
    assert inj_dossier["injury_type"] == "Hamstring Grade-1 Strain"
    assert inj_dossier["estimated_recovery_world_days"] >= 1

    fin_sec = briefing["financial_commercial_report"]
    assert fin_sec["current_club_balance"]["cash_gtex"] == 177_000
    assert fin_sec["wage_obligations"]["total_daily_obligations_gtex"] > 0
    assert fin_sec["matchday_revenue"]["operational_stadium_capacity"] >= 15_000

    # 2. Verify World-Day Idempotency: calling get_daily_briefing again on the same world_day
    # returns the exact same briefing & department_decisions without duplicating items
    decision_ids_first = [d["decision_id"] for d in briefing["department_decisions"]]
    briefing_second = storytelling.get_daily_briefing(session, "user-prestige-1", "club-prestige-1")
    decision_ids_second = [d["decision_id"] for d in briefing_second["department_decisions"]]
    assert decision_ids_second == decision_ids_first
    assert briefing_second["id"] == briefing["id"]

    # 3. Advance the world clock (tick_club) -> new world_day generates a fresh day's briefing
    old_day = state.world_day
    service.tick_club(session, state)
    assert state.world_day == old_day + 1

    briefing_next_day = daily_operations_hub.build_authoritative_daily_briefing(
        session, "user-prestige-1", "club-prestige-1"
    )
    assert briefing_next_day["world_day"] == old_day + 1
    assert briefing_next_day["id"] == f"briefing:club-prestige-1:{old_day + 1}"


def test_phase2_3_living_club_management_centre_six_destinations_and_decision_execution_lifecycle():
    from decimal import Decimal
    from sqlalchemy import select
    from app.owner_console import daily_operations_hub, ledger
    from app.owner_console.models import LedgerEvent
    from app.owner_console.service import OwnerError

    session = _session()
    state = _seed_club(session, prestige=72, cash=200_000)
    regens = service.academy_intake(session, "user-prestige-1", "club-prestige-1")
    regens[0].injured_days = 4
    session.commit()

    # 1. Fetch the Club Operations Hub (Living Club Management Centre payload)
    hub = daily_operations_hub.get_club_operations_hub(session, "user-prestige-1", "club-prestige-1")
    assert hub["club"]["club_id"] == "club-prestige-1"
    dest_keys = [d["destination_key"] for d in hub["destinations"]]
    assert dest_keys == [
        "executive_office",
        "managers_office",
        "general_managers_office",
        "academy_department",
        "medical_department",
        "finance_commercial_office",
    ]
    for dest in hub["destinations"]:
        assert dest["glb_model"].startswith("/models/campus/")
        assert len(dest["camera_position"]) == 3
        assert len(dest["camera_target"]) == 3
        assert len(dest["hotspots"]) >= 3
        assert isinstance(dest["report"], dict)

    # 2. Verify non-owner permission check rejects unauthorized user with 403 Forbidden
    from app.models import User, UserRole

    other_user = User(
        id="intruder-user-999",
        email="intruder@example.com",
        username="intruder",
        password_hash="hashed",  # pragma: allowlist secret
        role=UserRole.SCOUT,
    )
    session.add(other_user)
    session.commit()

    open_decisions = hub["actionable_decisions"]["department_decisions"]
    assert len(open_decisions) >= 4
    target_med_dec = next(d for d in open_decisions if d["department"] == "medical_department")

    try:
        daily_operations_hub.execute_owner_operational_decision(
            session,
            "intruder-user-999",
            "club-prestige-1",
            decision_id=target_med_dec["decision_id"],
            action="approve",
        )
        assert False, "Expected OwnerError(not_club_owner) for non-owner user"
    except OwnerError as exc:
        assert exc.code in ("not_owner", "not_club_owner")
        assert exc.status == 403

    # 3. Execute Medical Department decision (Authoritative Sports-Science Conditioning Protocol)
    cash_before = float(ledger.balance(session, ledger.club_account(state.club_id), ledger.GTEX))
    inj_before = regens[0].injured_days
    exec_res = daily_operations_hub.execute_owner_operational_decision(
        session,
        "user-prestige-1",
        "club-prestige-1",
        decision_id=target_med_dec["decision_id"],
        action="approve",
        note="Approved from 3D Medical Department",
    )
    assert exec_res["decision"]["status"] == "approved"
    assert regens[0].injured_days == max(0, inj_before - 1)
    cash_after = float(ledger.balance(session, ledger.club_account(state.club_id), ledger.GTEX))
    assert cash_after == cash_before - target_med_dec["cost_gtex"]

    # Verify authoritative LedgerEvent was recorded
    med_ledger = session.scalar(
        select(LedgerEvent).where(
            LedgerEvent.event_type == "medical_conditioning_protocol",
            LedgerEvent.related_object_id == target_med_dec["decision_id"],
        )
    )
    assert med_ledger is not None
    assert int(Decimal(med_ledger.gross_amount)) == target_med_dec["cost_gtex"]

    # 4. Duplicate execution of the same decision must be rejected with HTTP 409 Conflict
    try:
        daily_operations_hub.execute_owner_operational_decision(
            session,
            "user-prestige-1",
            "club-prestige-1",
            decision_id=target_med_dec["decision_id"],
            action="approve",
        )
        assert False, "Expected 409 decision_already_resolved on duplicate execution"
    except OwnerError as exc:
        assert exc.code == "decision_already_resolved"
        assert exc.status == 409

    # 5. Execute Finance & Commercial Sponsor decision and Manager's Office decision, verify persistence in decision_history
    fin_dec = next(d for d in open_decisions if d["department"] == "finance_commercial_office")
    fin_res = daily_operations_hub.execute_owner_operational_decision(
        session,
        "user-prestige-1",
        "club-prestige-1",
        decision_id=fin_dec["decision_id"],
        action="approve",
    )
    assert fin_res["decision"]["status"] == "approved"

    mgr_dec = next(d for d in open_decisions if d["department"] == "managers_office")
    mgr_res = daily_operations_hub.execute_owner_operational_decision(
        session,
        "user-prestige-1",
        "club-prestige-1",
        decision_id=mgr_dec["decision_id"],
        action="reject",
        note="Deferred until next fixture",
    )
    assert mgr_res["decision"]["status"] == "rejected"

    refreshed_hub = mgr_res["operations_hub"]
    history_ids = [h["decision_id"] for h in refreshed_hub["decision_history"]]
    assert target_med_dec["decision_id"] in history_ids
    assert fin_dec["decision_id"] in history_ids
    assert mgr_dec["decision_id"] in history_ids


def test_phase2_3_medical_director_appointment_and_healing_calculations():
    from app.owner_console import daily_operations_hub
    from sqlalchemy.orm.attributes import flag_modified

    session = _session()
    state = _seed_club(session, prestige=70, cash=150_000)
    user_id = state.owner_user_id
    club_id = state.club_id

    # 1. Unappointed Medical Director (role is vacant in _executive_staff)
    facs = dict(state.facilities_json or {})
    exec_staff = dict(facs.get("_executive_staff") or {})
    exec_staff.pop("medical_director", None)
    facs["_executive_staff"] = exec_staff
    facs["medical"] = 2
    state.facilities_json = facs
    flag_modified(state, "facilities_json")
    session.commit()

    briefing_unappointed = daily_operations_hub.build_authoritative_daily_briefing(session, user_id, club_id)
    med_sec_unappointed = briefing_unappointed["medical_directors_report"]
    med_profile = med_sec_unappointed["staff_profile"]

    assert med_profile["is_appointed"] is False
    assert med_profile["status"] == "vacant"
    assert "Vacant" in med_profile["name"]
    assert med_profile["medical_expertise"] == 10
    assert med_profile["salary_gtex"] == 0
    # Formula: 1 + medical//2 (2//2=1) + med_bonus (10//5=2) + rehab_campus_bonus (4) = 8
    unappointed_heal_rate = med_sec_unappointed["rehabilitation_status"]["daily_injury_heal_days"]
    assert unappointed_heal_rate == 8

    # 2. Appoint an authoritative Medical Director with expertise 18 in _executive_staff
    exec_staff["medical_director"] = {
        "name": "Dr. Fatima Al-Mansoor",
        "role": "medical_director",
        "role_label": "Medical Director",
        "medical_expertise": 18,
        "salary_gtex": 450,
        "mood": 88,
        "loyalty": 17,
        "personal_agenda": "Biomechanics & Soft-Tissue Optimization",
        "signature_trait": "Hyperbaric Specialist",
    }
    facs["_executive_staff"] = exec_staff
    state.facilities_json = facs
    flag_modified(state, "facilities_json")
    session.commit()

    briefing_appointed = daily_operations_hub.build_authoritative_daily_briefing(
        session, user_id, club_id, force_refresh=True
    )
    med_sec_appointed = briefing_appointed["medical_directors_report"]
    med_profile_app = med_sec_appointed["staff_profile"]

    assert med_profile_app["is_appointed"] is True
    assert med_profile_app["status"] == "appointed"
    assert med_profile_app["name"] == "Dr. Fatima Al-Mansoor"
    assert med_profile_app["medical_expertise"] == 18
    assert med_profile_app["salary_gtex"] == 450
    # Formula: 1 + 1 (facility) + med_bonus (18//5=3) + rehab_campus_bonus (4) = 9
    appointed_heal_rate = med_sec_appointed["rehabilitation_status"]["daily_injury_heal_days"]
    assert appointed_heal_rate == 9
    assert appointed_heal_rate == unappointed_heal_rate + 1

    # Verify simulation synchronization with service.tick_club
    regens = service.academy_intake(session, user_id, club_id)
    regens[0].injured_days = 12
    session.commit()

    service.tick_club(session, state)
    # 12 - 9 = 3 days remaining after tick
    assert regens[0].injured_days == 3


def test_phase2_3_medical_injury_dossier_recorded_and_unrecorded_classifications():
    from app.owner_console import daily_operations_hub
    from sqlalchemy.orm.attributes import flag_modified

    session = _session()
    state = _seed_club(session, prestige=74, cash=180_000)
    user_id = state.owner_user_id
    club_id = state.club_id

    regens = service.academy_intake(session, user_id, club_id)
    assert len(regens) >= 2

    # Player 0 has an authoritative persisted injury classification
    regens[0].injured_days = 9
    p0_pers = dict(regens[0].personality_json or {})
    p0_pers["last_injury_type"] = "Severe Ankle Ligament Sprain"
    regens[0].personality_json = p0_pers
    flag_modified(regens[0], "personality_json")

    # Player 1 has injured_days > 0 but NO classification in personality_json (unrecorded)
    regens[1].injured_days = 4
    p1_pers = dict(regens[1].personality_json or {})
    p1_pers.pop("last_injury_type", None)
    regens[1].personality_json = p1_pers
    flag_modified(regens[1], "personality_json")
    session.commit()

    briefing = daily_operations_hub.build_authoritative_daily_briefing(session, user_id, club_id, force_refresh=True)
    dossiers = {d["id"]: d for d in briefing["medical_directors_report"]["injured_players"]}

    # Recorded player exposes the exact persisted diagnosis
    assert dossiers[regens[0].id]["injury_type"] == "Severe Ankle Ligament Sprain"
    assert dossiers[regens[0].id]["injured_days"] == 9

    # Unrecorded player displays authoritative unrecorded state without inventing a diagnosis
    assert dossiers[regens[1].id]["injury_type"] == "Injury type not recorded"
    assert dossiers[regens[1].id]["injury_type"] != "Muscular Strain"
    assert dossiers[regens[1].id]["injured_days"] == 4
