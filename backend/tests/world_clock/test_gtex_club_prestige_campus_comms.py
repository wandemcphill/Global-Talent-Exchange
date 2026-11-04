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
