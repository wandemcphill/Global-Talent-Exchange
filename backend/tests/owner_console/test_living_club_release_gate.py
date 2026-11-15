"""Release-gate verification tests for the unified GTEX Living Club integration."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.pool import StaticPool

from app.admin_engine.service import AdminEngineService
from app.auth.dependencies import get_current_user, get_session
from app.core.database import load_model_modules
from app.models.base import Base
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.user import KycStatus, PublicAccountType, User, UserRole
from app.models.world_clock import WorldClockState
from app.owner_console import (
    autonomous_staff_engine,
    comms_persistence,
    engine as owner_engine,
    ledger,
    living_club_world,
    living_institution,
    service,
)
from app.owner_console.institutional_models import (
    OwnerClubHistoryEntry,
    OwnerClubManagerialTenure,
    OwnerClubTransferRecord,
    OwnerMediaStory,
    OwnerSupporterEvent,
    OwnerSupporterProfile,
)
from app.owner_console.models import (
    ClubDelegatedDecision,
    OwnerClubConversation,
    OwnerClubEvent,
    OwnerClubMessage,
    OwnerClubRelationship,
    OwnerClubState,
    OwnerInboxItem,
    OwnerSquadPlayer,
)
from app.owner_console.router import router as owner_router
from app.services.world_clock_service import DEFAULT_CLOCK_ID

WORLD_NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)
BACKEND_DIR = Path(__file__).resolve().parents[2]

INSTITUTIONAL_TABLES = (
    "owner_supporter_profiles",
    "owner_supporter_segments",
    "owner_supporter_events",
    "owner_media_outlets",
    "owner_media_stories",
    "owner_club_history_entries",
    "owner_club_season_archives",
    "owner_club_managerial_tenures",
    "owner_club_transfer_records",
    "owner_club_academy_graduates",
    "owner_club_rivalries",
)


def _create_isolated_session_factory() -> sessionmaker[Session]:
    load_model_modules()
    eng = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng, autoflush=False, expire_on_commit=False)


def _seed_club_world(
    session: Session,
    *,
    club_name: str = "Gatekeeping United",
    world_day: int = 10,
) -> tuple[User, OwnerClubState]:
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
                officially_started=True,
                metadata_json={"canonical": True},
            )
        )
        session.flush()

    AdminEngineService(session).seed_defaults()

    uid = uuid4().hex[:8]
    owner = User(
        id=f"gate-owner-{uid}",
        email=f"gate-owner-{uid}@gtex.test",
        username=f"gate_owner_{uid}",
        display_name=f"Gate Owner {uid}",
        password_hash="not-used-in-test",
        role=UserRole.USER,
        kyc_status=KycStatus.VERIFIED,
        account_type=PublicAccountType.USER,
        nationality="Nigeria",
        is_active=True,
    )
    club = ClubProfile(
        id=f"gate-club-{uid}",
        owner_user_id=owner.id,
        club_name=club_name,
        short_name=f"G{uid[:3].upper()}",
        slug=f"gate-club-{uid}",
        club_type=ClubType.PROFESSIONAL,
        lifecycle_status=ClubLifecycleStatus.ACTIVE,
        primary_color="#10B981",
        secondary_color="#0F172A",
        accent_color="#F59E0B",
        country_code="NG",
        visibility="public",
    )
    state = OwnerClubState(
        club_id=club.id,
        owner_user_id=owner.id,
        club_name=club.club_name,
        stage="active",
        world_day=world_day,
        prestige=74,
        fans=18000,
        mentality="balanced",
        manager_json=owner_engine.manager_profile(owner_engine.DEFAULT_MANAGER),
        facilities_json={"training": 3, "academy": 4, "medical": 3, "stadium": 3, "commercial": 3},
    )
    session.add_all([owner, club, state])
    session.flush()

    ledger.record(
        session,
        event_type="test_grant",
        source=ledger.WORLD_CLUBS,
        destination=ledger.club_account(club.id),
        currency=ledger.GTEX,
        gross=850000,
        balance_class="deposited",
        club_id=club.id,
        user_id=owner.id,
        memo="Initial release-gate treasury",
    )
    ledger.record(
        session,
        event_type="test_fan_grant",
        source=ledger.WORLD_CLUBS,
        destination=ledger.user_account(owner.id),
        currency=ledger.FAN,
        gross=50000,
        club_id=club.id,
        user_id=owner.id,
        memo="Initial release-gate fan coin",
    )
    ledger.record(
        session,
        event_type="test_club_fan_grant",
        source=ledger.WORLD_CLUBS,
        destination=ledger.club_account(club.id),
        currency=ledger.FAN,
        gross=50000,
        club_id=club.id,
        user_id=owner.id,
        memo="Initial release-gate club fan coin",
    )

    squad_spec = [
        ("p-gk-1", "Emeka Obi", "Goalkeeper", 28, 79, 80, False),
        ("p-gk-2", "Tariq Bello", "Goalkeeper", 21, 71, 79, False),
        ("p-def-1", "Chidi Nwachukwu", "CB", 29, 80, 80, False),
        ("p-def-2", "Kofi Mensah", "CB", 27, 78, 79, False),
        ("p-def-3", "Seyi Balogun", "LB", 25, 77, 80, False),
        ("p-def-4", "Ibrahim Diallo", "RB", 26, 77, 79, False),
        ("p-def-5", "Dapo Afolabi", "CB", 22, 73, 81, False),
        ("p-mid-1", "Yusuf Lawal", "CM", 28, 81, 82, False),
        ("p-mid-2", "Nuno Silva", "CDM", 30, 79, 79, False),
        ("p-mid-3", "Tobi Ojo", "CAM", 24, 78, 83, False),
        ("p-mid-4", "Chuka Eze", "CM", 22, 76, 81, False),
        ("p-mid-5", "Akin Cole", "RM", 26, 76, 78, False),
        ("p-fwd-1", "Victor Okafor", "ST", 29, 82, 82, False),
        ("p-fwd-2", "Samuel Kalu", "LW", 27, 78, 79, False),
        ("p-fwd-3", "Musa Danjuma", "RW", 26, 77, 79, False),
        ("p-acad-st-16", "Lucas Vance", "ST", 16, 67, 89, True),
    ]
    for pid_base, name, pos, age, rtg, pot, is_regen in squad_spec:
        session.add(
            OwnerSquadPlayer(
                id=f"{club.id}:{pid_base}",
                club_id=club.id,
                name=name,
                position=pos,
                age=age,
                rating=rtg,
                potential=pot,
                value_coin=Decimal(str(rtg * 15)),
                morale=80,
                minutes=180 if not is_regen else 15,
                injured_days=0,
                is_regen=is_regen,
                personality_json={"fitness": 94, "is_academy": is_regen, "ambition": 16, "professionalism": 15},
                status="active",
                acquired_via="academy" if is_regen else "market",
            )
        )

    living_institution.ensure_club_institutional_ecosystem(session, state)
    comms_persistence.ensure_club_conversations_seeded(session, state)
    session.commit()
    return owner, state


def _alembic_config(database_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "migrations" / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def test_single_event_partial_projection_failure_retry_completes_without_duplication(monkeypatch) -> None:
    factory = _create_isolated_session_factory()
    session = factory()
    try:
        _, state = _seed_club_world(session, club_name="Idempotency FC")

        real_publish_media = living_institution.publish_media_story
        transfer_idem = f"gate-transfer-{uuid4().hex[:8]}"

        hist_before = len(session.scalars(select(OwnerClubHistoryEntry).where(OwnerClubHistoryEntry.club_id == state.club_id)).all())
        sup_before = len(session.scalars(select(OwnerSupporterEvent).where(OwnerSupporterEvent.club_id == state.club_id)).all())
        story_before = len(session.scalars(select(OwnerMediaStory).where(OwnerMediaStory.club_id == state.club_id)).all())

        def _failing_media(*args, **kwargs):
            raise RuntimeError("simulated downstream media outage")

        monkeypatch.setattr(living_institution, "publish_media_story", _failing_media)
        failed = False
        try:
            living_institution.record_transfer_movement(
                session,
                state,
                direction="in",
                transfer_type="market",
                player_id="p-new-gate-1",
                player_name="Kelechi Iheanacho",
                position="ST",
                age=24,
                overall_rating=81,
                fee_gtex=55000,
                wage_gtex=1200,
                counterparty_club_name="Kano Pillars",
                idempotency_key=transfer_idem,
            )
        except RuntimeError:
            failed = True
            session.commit()
        assert failed is True

        assert len(session.scalars(select(OwnerClubTransferRecord).where(OwnerClubTransferRecord.club_id == state.club_id)).all()) == 1
        assert len(session.scalars(select(OwnerClubHistoryEntry).where(OwnerClubHistoryEntry.club_id == state.club_id)).all()) == hist_before + 1
        assert len(session.scalars(select(OwnerSupporterEvent).where(OwnerSupporterEvent.club_id == state.club_id)).all()) == sup_before + 1
        assert len(session.scalars(select(OwnerMediaStory).where(OwnerMediaStory.club_id == state.club_id)).all()) == story_before

        canon_transfer = session.scalar(
            select(OwnerClubEvent).where(
                OwnerClubEvent.club_id == state.club_id,
                OwnerClubEvent.category == "recruitment",
                OwnerClubEvent.event_type == "transfer_in",
            )
        )
        assert canon_transfer is not None
        assert living_institution.has_canonical_projection(canon_transfer, "club_history", "OwnerClubHistoryEntry") is True
        assert living_institution.has_canonical_projection(canon_transfer, "supporters", "OwnerSupporterEvent") is True
        assert living_institution.has_canonical_projection(canon_transfer, "media", "OwnerMediaStory") is False

        sentiment_after_partial = session.scalar(
            select(OwnerSupporterProfile.overall_sentiment).where(OwnerSupporterProfile.club_id == state.club_id)
        )

        # Retry after recovery must finish ONLY the missing media projection without duplicating history/supporter/transfer rows.
        monkeypatch.setattr(living_institution, "publish_media_story", real_publish_media)
        retried = living_institution.record_transfer_movement(
            session,
            state,
            direction="in",
            transfer_type="market",
            player_id="p-new-gate-1",
            player_name="Kelechi Iheanacho",
            position="ST",
            age=24,
            overall_rating=81,
            fee_gtex=55000,
            wage_gtex=1200,
            counterparty_club_name="Kano Pillars",
            idempotency_key=transfer_idem,
        )
        session.commit()
        assert retried.player_name == "Kelechi Iheanacho"

        assert len(session.scalars(select(OwnerClubTransferRecord).where(OwnerClubTransferRecord.club_id == state.club_id)).all()) == 1
        assert len(session.scalars(select(OwnerClubHistoryEntry).where(OwnerClubHistoryEntry.club_id == state.club_id)).all()) == hist_before + 1
        assert len(session.scalars(select(OwnerSupporterEvent).where(OwnerSupporterEvent.club_id == state.club_id)).all()) == sup_before + 1
        assert len(session.scalars(select(OwnerMediaStory).where(OwnerMediaStory.club_id == state.club_id)).all()) == story_before + 1
        session.refresh(canon_transfer)
        assert living_institution.has_canonical_projection(canon_transfer, "media", "OwnerMediaStory") is True
        assert (
            session.scalar(select(OwnerSupporterProfile.overall_sentiment).where(OwnerSupporterProfile.club_id == state.club_id))
            == sentiment_after_partial
        )

        # 3rd replay remains strict no-op.
        living_institution.record_transfer_movement(
            session,
            state,
            direction="in",
            transfer_type="market",
            player_id="p-new-gate-1",
            player_name="Kelechi Iheanacho",
            position="ST",
            age=24,
            overall_rating=81,
            fee_gtex=55000,
            wage_gtex=1200,
            counterparty_club_name="Kano Pillars",
            idempotency_key=transfer_idem,
        )
        session.commit()
        assert len(session.scalars(select(OwnerMediaStory).where(OwnerMediaStory.club_id == state.club_id)).all()) == story_before + 1

        # Subcase B: Managerial change partial failure + retry completes missing media story without closing/opening twice.
        living_institution.ensure_active_manager_tenure(session, state, state.manager_json)
        session.commit()
        mgr_idem = f"gate-mgr-resign-{uuid4().hex[:8]}"
        new_mgr = {"manager_id": "mgr_bellini", "id": "mgr_bellini", "name": "Marco Bellini", "display_name": "Marco Bellini"}

        monkeypatch.setattr(living_institution, "publish_media_story", _failing_media)
        mgr_failed = False
        try:
            living_institution.record_managerial_change(
                session,
                state,
                action="resigned",
                new_manager=new_mgr,
                previous_manager=state.manager_json,
                reason="repeated_owner_interference",
                idempotency_key=mgr_idem,
                source_subsystem="autonomous_staff",
            )
        except RuntimeError:
            mgr_failed = True
            session.commit()
        assert mgr_failed is True

        assert len(session.scalars(select(OwnerClubManagerialTenure).where(OwnerClubManagerialTenure.club_id == state.club_id)).all()) == 2
        assert len(session.scalars(select(OwnerMediaStory).where(OwnerMediaStory.club_id == state.club_id)).all()) == story_before + 1

        monkeypatch.setattr(living_institution, "publish_media_story", real_publish_media)
        living_institution.record_managerial_change(
            session,
            state,
            action="resigned",
            new_manager=new_mgr,
            previous_manager=state.manager_json,
            reason="repeated_owner_interference",
            idempotency_key=mgr_idem,
            source_subsystem="autonomous_staff",
        )
        living_institution.record_managerial_change(
            session,
            state,
            action="resigned",
            new_manager=new_mgr,
            previous_manager=state.manager_json,
            reason="repeated_owner_interference",
            idempotency_key=mgr_idem,
            source_subsystem="autonomous_staff",
        )
        session.commit()

        tenures = list(
            session.scalars(select(OwnerClubManagerialTenure).where(OwnerClubManagerialTenure.club_id == state.club_id)).all()
        )
        assert len(tenures) == 2
        assert sum(1 for t in tenures if t.status == "active") == 1
        assert next(t for t in tenures if t.status == "active").manager_name == "Marco Bellini"
        assert len(session.scalars(select(OwnerMediaStory).where(OwnerMediaStory.club_id == state.club_id)).all()) == story_before + 2
        assert (
            len(
                session.scalars(
                    select(OwnerClubHistoryEntry).where(
                        OwnerClubHistoryEntry.club_id == state.club_id,
                        OwnerClubHistoryEntry.category == "managerial_change",
                    )
                ).all()
            )
            == 1
        )
    finally:
        session.close()


def test_tick_club_savepoint_recovery_and_authoritative_clock_idempotency(tmp_path: Path, monkeypatch) -> None:
    load_model_modules()
    db_path = tmp_path / "clock_gate.db"
    db_url = f"sqlite+pysqlite:///{db_path.as_posix()}"

    eng1 = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng1)
    f1 = sessionmaker(bind=eng1, autoflush=False, expire_on_commit=False)
    s1 = f1()
    try:
        _, state = _seed_club_world(s1, club_name="Clockwork FC", world_day=10)
        club_id = state.club_id

        real_inst_tick = living_institution.process_world_day_institutional_tick

        def _failing_inst_tick(*args, **kwargs):
            raise RuntimeError("simulated institutional subsystem transient error")

        monkeypatch.setattr(living_institution, "process_world_day_institutional_tick", _failing_inst_tick)
        d1 = date(2026, 11, 14)
        res1 = service.tick_club(s1, state, use_ai=False, world_tick_date=d1)
        s1.commit()

        assert not res1.get("already_ticked", False)
        assert res1["world_day"] == 11
        pending = list((state.facilities_json or {}).get("_pending_institutional_retry_days") or [])
        assert pending == [11]

        # Same world_tick_date must be idempotent even when Stage 3 deferred retry.
        dup_res = service.tick_club(s1, state, use_ai=False, world_tick_date=d1)
        assert dup_res.get("already_ticked") is True
        assert dup_res["world_day"] == 11

        # Restore institutional tick; next day catches up day 11 + executes day 12 and clears pending list.
        caught_up_days: list[int] = []

        def _recording_inst_tick(sess, club_state, *args, **kwargs):
            caught_up_days.append(int(club_state.world_day))
            return real_inst_tick(sess, club_state, *args, **kwargs)

        monkeypatch.setattr(living_institution, "process_world_day_institutional_tick", _recording_inst_tick)
        d2 = date(2026, 11, 15)
        res2 = service.tick_club(s1, state, use_ai=False, world_tick_date=d2)
        s1.commit()

        assert res2["world_day"] == 12
        assert caught_up_days == [11, 12]
        assert list((state.facilities_json or {}).get("_pending_institutional_retry_days") or []) == []

        # Set last_world_tick_date cleanly so scheduler catches up exactly once for current virtual date.
        state.last_world_tick_date = d2
        flag_modified(state, "facilities_json")
        clk = s1.get(WorldClockState, DEFAULT_CLOCK_ID)
        assert clk is not None
        clk.epoch_real_utc = datetime.now(timezone.utc)
        clk.virtual_start_time = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)
        s1.commit()

        first_sched = service.process_due_owner_world_ticks(s1)
        s1.commit()
        assert first_sched["ticks_executed"] == 1
        world_day_after_sched = s1.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id)).world_day
    finally:
        s1.close()
        eng1.dispose()

    # Simulate process restart: fresh engine & session on same DB -> same virtual day must produce 0 ticks.
    eng2 = create_engine(db_url, connect_args={"check_same_thread": False})
    f2 = sessionmaker(bind=eng2, autoflush=False, expire_on_commit=False)
    s2 = f2()
    try:
        restart_sched = service.process_due_owner_world_ticks(s2)
        s2.commit()
        assert restart_sched["ticks_executed"] == 0
        assert s2.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id)).world_day == world_day_after_sched

        # Advance authoritative WorldClock by +1 virtual day and run scheduler after another restart.
        clk2 = s2.get(WorldClockState, DEFAULT_CLOCK_ID)
        assert clk2 is not None
        clk2.epoch_real_utc = datetime.now(timezone.utc)
        clk2.virtual_start_time = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
        s2.commit()
    finally:
        s2.close()
        eng2.dispose()

    eng3 = create_engine(db_url, connect_args={"check_same_thread": False})
    f3 = sessionmaker(bind=eng3, autoflush=False, expire_on_commit=False)
    s3 = f3()
    try:
        next_day_sched = service.process_due_owner_world_ticks(s3)
        s3.commit()
        assert next_day_sched["ticks_executed"] == 1
        assert s3.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id)).world_day == world_day_after_sched + 1
    finally:
        s3.close()
        eng3.dispose()


def test_alembic_fresh_and_seeded_upgrade_preserves_legacy_records(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("GTE_MIGRATION_DATABASE_URL", raising=False)
    load_model_modules()

    fresh_db = tmp_path / "alembic_fresh.db"
    fresh_url = f"sqlite+pysqlite:///{fresh_db.as_posix()}"
    fresh_cfg = _alembic_config(fresh_url)

    script = ScriptDirectory.from_config(fresh_cfg)
    heads = script.get_heads()
    assert heads == ["20261115_0250_academy_first_team_minutes"]

    command.upgrade(fresh_cfg, "head")
    fresh_eng = create_engine(fresh_url)
    try:
        insp = inspect(fresh_eng)
        table_names = set(insp.get_table_names())
        for table_name in INSTITUTIONAL_TABLES + ("owner_staff_decision_records", "owner_recruitment_assignments"):
            assert table_name in table_names, f"Missing table after fresh upgrade: {table_name}"

        seg_uqs = {uq["name"] for uq in insp.get_unique_constraints("owner_supporter_segments")}
        assert "uq_owner_supporter_segments_club_segment" in seg_uqs
        story_uqs = {uq["name"] for uq in insp.get_unique_constraints("owner_media_stories")}
        assert "uq_owner_media_stories_idempotency" in story_uqs
        story_idx = {idx["name"] for idx in insp.get_indexes("owner_media_stories")}
        assert len(story_idx) >= 1
        msg_fks = {fk["referred_table"] for fk in insp.get_foreign_keys("owner_club_messages")}
        assert "owner_club_conversations" in msg_fks
    finally:
        fresh_eng.dispose()

    # Seeded upgrade from pre-0246 revision preserves legacy owner/staff/comms records cleanly.
    seeded_db = tmp_path / "alembic_seeded.db"
    seeded_url = f"sqlite+pysqlite:///{seeded_db.as_posix()}"
    seeded_cfg = _alembic_config(seeded_url)
    command.upgrade(seeded_cfg, "20261114_0245_attach_player_traits_and_playstyles")

    seeded_eng = create_engine(seeded_url)
    sf = sessionmaker(bind=seeded_eng, autoflush=False, expire_on_commit=False)
    s_pre = sf()
    legacy_uid = f"legacy-u-{uuid4().hex[:8]}"
    legacy_cid = f"legacy-c-{uuid4().hex[:8]}"
    legacy_conv_id = f"legacy-conv-{uuid4().hex[:8]}"
    legacy_msg_id = f"legacy-msg-{uuid4().hex[:8]}"
    legacy_rel_id = f"legacy-rel-{uuid4().hex[:8]}"
    try:
        s_pre.add_all(
            [
                User(
                    id=legacy_uid,
                    email=f"{legacy_uid}@gtex.test",
                    username=legacy_uid.replace("-", "_"),
                    display_name="Legacy Owner",
                    password_hash="x",
                    role=UserRole.USER,
                    kyc_status=KycStatus.VERIFIED,
                    account_type=PublicAccountType.USER,
                    nationality="Nigeria",
                    is_active=True,
                ),
                ClubProfile(
                    id=legacy_cid,
                    owner_user_id=legacy_uid,
                    club_name="Legacy Wanderers FC",
                    short_name="LWFC",
                    slug=f"legacy-{legacy_uid}",
                    club_type=ClubType.PROFESSIONAL,
                    lifecycle_status=ClubLifecycleStatus.ACTIVE,
                    primary_color="#111827",
                    secondary_color="#10B981",
                    accent_color="#F59E0B",
                    country_code="NG",
                    visibility="public",
                ),
                OwnerClubState(
                    club_id=legacy_cid,
                    owner_user_id=legacy_uid,
                    club_name="Legacy Wanderers FC",
                    stage="active",
                    world_day=7,
                    prestige=66,
                    fans=9400,
                    mentality="balanced",
                    manager_json=owner_engine.manager_profile(owner_engine.DEFAULT_MANAGER),
                    facilities_json={"training": 2, "academy": 3, "medical": 2, "stadium": 2, "commercial": 2},
                ),
                OwnerClubConversation(
                    id=legacy_conv_id,
                    club_id=legacy_cid,
                    owner_user_id=legacy_uid,
                    channel_type="direct",
                    thread_key="staff:first_team_manager",
                    participant_type="staff",
                    participant_id="gtex-staff-coach",
                    participant_name="Tunde Bakare",
                    participant_role="first_team_manager",
                    last_message_seq=1,
                ),
                OwnerClubMessage(
                    id=legacy_msg_id,
                    conversation_id=legacy_conv_id,
                    club_id=legacy_cid,
                    seq=1,
                    sender_type="staff",
                    sender_id="gtex-staff-coach",
                    sender_name="Tunde Bakare",
                    sender_role="first_team_manager",
                    body="Pre-migration training update preserved.",
                    source="staff_briefing",
                    priority="normal",
                    is_read=False,
                ),
                OwnerClubRelationship(
                    id=legacy_rel_id,
                    club_id=legacy_cid,
                    pairing_key=f"{legacy_cid}:owner:first_team_manager",
                    participant_a_type="owner",
                    participant_a_id=legacy_uid,
                    participant_a_name="Legacy Owner",
                    participant_b_type="staff",
                    participant_b_id="gtex-staff-coach",
                    participant_b_name="Tunde Bakare",
                    trust=62,
                    respect=64,
                    affinity=60,
                    tension=18,
                    alignment=61,
                    influence=55,
                    loyalty=66,
                    status="aligned",
                ),
            ]
        )
        s_pre.commit()
    finally:
        s_pre.close()
        seeded_eng.dispose()

    command.upgrade(seeded_cfg, "head")

    post_eng = create_engine(seeded_url)
    sf_post = sessionmaker(bind=post_eng, autoflush=False, expire_on_commit=False)
    s_post = sf_post()
    try:
        upgraded_state = s_post.scalar(select(OwnerClubState).where(OwnerClubState.club_id == legacy_cid))
        assert upgraded_state is not None
        assert upgraded_state.club_name == "Legacy Wanderers FC"
        assert upgraded_state.world_day == 7
        assert s_post.get(User, legacy_uid) is not None
        assert s_post.get(ClubProfile, legacy_cid) is not None
        assert s_post.get(OwnerClubConversation, legacy_conv_id) is not None
        assert s_post.get(OwnerClubMessage, legacy_msg_id).body == "Pre-migration training update preserved."
        assert s_post.get(OwnerClubRelationship, legacy_rel_id).trust == 62

        profile, segments = living_institution.ensure_club_institutional_ecosystem(s_post, upgraded_state)
        s_post.commit()
        assert profile.club_id == legacy_cid
        assert len(segments) == 6
    finally:
        s_post.close()
        post_eng.dispose()


def test_cross_club_privacy_redaction_and_staff_replacement_isolation() -> None:
    factory = _create_isolated_session_factory()
    session = factory()
    try:
        owner_a, state_a = _seed_club_world(session, club_name="Private Shield FC", world_day=12)
        owner_b, _state_b = _seed_club_world(session, club_name="Rival Spy FC", world_day=12)

        secret_phrase = "SECRET-BOARDROOM-CONFLICT-771"
        public_phrase = "PUBLIC-SIGNED-ACADEMY-SHOWCASE-882"

        living_institution.emit_canonical_club_event(
            session,
            state_a,
            category="staff_conflict",
            event_type="internal_ultimatum",
            source_subsystem="autonomous_staff",
            title=f"Confidential Dressing Room Friction ({secret_phrase})",
            description=f"Confidential internal friction details {secret_phrase}.",
            visibility_classification=living_institution.VISIBILITY_PRIVATE_INTERNAL,
            idempotency_key=f"secret-{uuid4().hex[:8]}",
        )
        living_institution.publish_media_story(
            session,
            state_a,
            outlet_key="football_chronicle",
            story_type="club_news",
            classification="verified_event",
            headline=f"Open Stadium Milestone ({public_phrase})",
            subheadline="Public announcement",
            body=f"Public club progress story ({public_phrase}).",
            idempotency_key=f"pub-{uuid4().hex[:8]}",
        )
        session.add(
            ClubDelegatedDecision(
                club_id=state_a.club_id,
                owner_user_id=owner_a.id,
                activity_key="recruitment_signing",
                domain="recruitment",
                proposed_by_role="general_manager",
                proposed_by_staff_name="Claire Moreau",
                title=f"Confidential Offer ({secret_phrase})",
                summary="Sensitive private approval item.",
                financial_amount_gtex=Decimal("40000"),
                requires_owner_approval=True,
                status="pending_approval",
                payload_json={},
            )
        )
        session.add(
            OwnerInboxItem(
                club_id=state_a.club_id,
                user_id=owner_a.id,
                kind="staff_alert",
                category="staff_recommendations",
                priority="high",
                sender="Claire Moreau (General Manager)",
                title=f"Private Alert ({secret_phrase})",
                what="Confidential alert summary",
                why="Internal confidential staff alert",
                body="Confidential alert body",
                status="open",
                is_read=False,
            )
        )
        session.commit()

        active_user = {"user": owner_a}
        app = FastAPI()
        app.include_router(owner_router)

        def _override_session() -> Iterator[Session]:
            yield session

        def _override_user() -> User:
            return active_user["user"]

        app.dependency_overrides[get_session] = _override_session
        app.dependency_overrides[get_current_user] = _override_user
        client = TestClient(app)

        # Owner A sees full internal telemetry.
        pulse_a = client.get(f"/owner/clubs/{state_a.club_id}/institutional-pulse")
        assert pulse_a.status_code == 200
        pulse_a_json = pulse_a.json()
        assert pulse_a_json["is_private_redacted"] is False
        assert pulse_a_json["staff_and_governance"]["unresolved_decisions_count"] >= 1
        assert pulse_a_json["staff_and_governance"]["unread_proactive_alerts_count"] >= 1
        assert secret_phrase in str(pulse_a_json["unified_timeline"])

        # Owner B must NOT see confidential internal details or counts across ANY institutional endpoint.
        active_user["user"] = owner_b
        pulse_b = client.get(f"/owner/clubs/{state_a.club_id}/institutional-pulse")
        hist_b = client.get(f"/owner/clubs/{state_a.club_id}/history")
        story_b = client.get(f"/owner/clubs/{state_a.club_id}/story")
        comms_b = client.get(f"/owner/clubs/{state_a.club_id}/communications")

        assert pulse_b.status_code == 200
        pb = pulse_b.json()
        assert pb["is_private_redacted"] is True
        assert pb["staff_and_governance"]["unresolved_decisions_count"] is None
        assert pb["staff_and_governance"]["open_recruitments_count"] is None
        assert pb["staff_and_governance"]["unread_proactive_alerts_count"] is None
        assert pb["staff_and_governance"]["recent_meetings_count"] is None
        assert pb["staff_and_governance"]["supporter_driven_agenda"] == []
        assert secret_phrase not in str(pb)
        assert public_phrase in str(pb)

        assert hist_b.status_code == 200
        hb = hist_b.json()
        assert hb["is_private_redacted"] is True
        assert secret_phrase not in str(hb)

        assert story_b.status_code == 200
        sb = story_b.json()
        assert sb["privacy_redacted"] is True
        assert sb["unresolved_issues"] == []
        assert sb["institutional_pulse"]["is_private_redacted"] is True
        assert sb["institutional_pulse"]["staff_and_governance"]["unread_proactive_alerts_count"] is None
        assert secret_phrase not in str(sb)
        assert public_phrase in str(sb)

        assert comms_b.status_code in (403, 404)

        # Staff replacement isolation: Manager & GM replacement archive predecessor threads & reset relationships.
        active_user["user"] = owner_a
        session.expire_all()
        mgr_cand = dict(owner_engine.MANAGER_CATALOG[1])
        service.appoint_manager(session, owner_a.id, state_a.club_id, dict(mgr_cand))
        session.commit()

        first_mgr_rel = session.scalar(
            select(OwnerClubRelationship).where(
                OwnerClubRelationship.club_id == state_a.club_id,
                OwnerClubRelationship.pairing_key == f"{state_a.club_id}:owner:first_team_manager",
            )
        )
        assert first_mgr_rel is not None
        first_mgr_rel.trust = 19
        first_mgr_rel.tension = 86
        first_mgr_name = first_mgr_rel.participant_b_name
        first_mgr_conv = session.scalar(
            select(OwnerClubConversation).where(
                OwnerClubConversation.club_id == state_a.club_id,
                OwnerClubConversation.thread_key == "staff:first_team_manager",
                OwnerClubConversation.archived_at.is_(None),
            )
        )
        assert first_mgr_conv is not None
        first_mgr_conv_id = first_mgr_conv.id
        session.commit()

        service.fire_manager(session, owner_a.id, state_a.club_id)
        second_mgr_cand = next(
            dict(c)
            for c in owner_engine.MANAGER_CATALOG
            if (c.get("id") or c.get("manager_id")) not in {(mgr_cand.get("id") or mgr_cand.get("manager_id")), "gtex-staff-coach"}
        )
        service.appoint_manager(session, owner_a.id, state_a.club_id, dict(second_mgr_cand))
        session.commit()

        session.refresh(first_mgr_conv)
        assert first_mgr_conv.archived_at is not None

        active_mgr_conv = session.scalar(
            select(OwnerClubConversation).where(
                OwnerClubConversation.club_id == state_a.club_id,
                OwnerClubConversation.thread_key == "staff:first_team_manager",
                OwnerClubConversation.archived_at.is_(None),
            )
        )
        assert active_mgr_conv is not None
        assert active_mgr_conv.id != first_mgr_conv_id
        assert active_mgr_conv.participant_name != first_mgr_name

        new_mgr_rel = session.scalar(
            select(OwnerClubRelationship).where(
                OwnerClubRelationship.club_id == state_a.club_id,
                OwnerClubRelationship.pairing_key == f"{state_a.club_id}:owner:first_team_manager",
            )
        )
        assert new_mgr_rel is not None
        assert new_mgr_rel.tension < 50
        assert new_mgr_rel.trust >= 45
        archived_rels = list((state_a.facilities_json or {}).get("_archived_staff_relationships") or [])
        assert any((r.get("staff_name") or r.get("participant_b_name")) == first_mgr_name for r in archived_rels)

        # Executive GM hire -> strain -> fire -> vacancy archives relationship & conversation thread.
        gm_cand = next(c for c in owner_engine.EXECUTIVE_STAFF_CATALOG if c.get("role") == "general_manager")
        gm_id = str(gm_cand.get("id") or gm_cand.get("staff_id"))
        service.hire_executive_staff(session, owner_a.id, state_a.club_id, gm_id, role="general_manager")
        session.commit()

        gm_rel = session.scalar(
            select(OwnerClubRelationship).where(
                OwnerClubRelationship.club_id == state_a.club_id,
                OwnerClubRelationship.pairing_key == f"{state_a.club_id}:owner:general_manager",
            )
        )
        assert gm_rel is not None
        gm_rel.tension = 79
        gm_rel.trust = 22
        gm_conv = session.scalar(
            select(OwnerClubConversation).where(
                OwnerClubConversation.club_id == state_a.club_id,
                OwnerClubConversation.thread_key == "staff:general_manager",
                OwnerClubConversation.archived_at.is_(None),
            )
        )
        assert gm_conv is not None
        session.commit()

        service.fire_executive_staff(session, owner_a.id, state_a.club_id, "general_manager")
        session.commit()
        session.refresh(gm_rel)
        assert gm_rel.status == "former"
        session.refresh(gm_conv)
        assert gm_conv.archived_at is not None
        living_club_world.reconcile_staff_relationships(session, state_a)
        session.commit()
    finally:
        session.close()


def test_simulation_quality_bounds_multi_day_stability() -> None:
    factory = _create_isolated_session_factory()
    session = factory()
    try:
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
                    officially_started=True,
                    metadata_json={"canonical": True},
                )
            )
            session.flush()
        AdminEngineService(session).seed_defaults()

        uid = uuid4().hex[:8]
        owner = User(
            id=f"sim-owner-{uid}",
            email=f"sim-{uid}@gtex.test",
            username=f"sim_{uid}",
            display_name="Simulation Owner",
            password_hash="x",
            role=UserRole.USER,
            kyc_status=KycStatus.VERIFIED,
            account_type=PublicAccountType.USER,
            nationality="Nigeria",
            is_active=True,
        )
        session.add(owner)
        session.flush()

        state = service.claim_starter_club(session, owner, city_name="Lagos", country_code="NG")
        service.start_activation(session, owner.id, state.club_id)
        session.commit()

        start_date = date(2026, 11, 14)
        for day_offset in range(14):
            service.tick_club(
                session,
                state,
                use_ai=False,
                world_tick_date=start_date + timedelta(days=day_offset),
            )
        session.commit()

        stories = list(
            session.scalars(select(OwnerMediaStory).where(OwnerMediaStory.club_id == state.club_id)).all()
        )
        headlines = [s.headline for s in stories]
        assert len(headlines) == len(set(headlines)), f"Duplicate headlines detected: {headlines}"

        messages = list(
            session.scalars(select(OwnerClubMessage).where(OwnerClubMessage.club_id == state.club_id)).all()
        )
        pending_topics = [m for m in messages if (m.topic or "") == "Pending Approvals"]
        academy_topics = [m for m in messages if (m.topic or "") == "Academy Standout"]
        assert len(pending_topics) <= 3
        assert len(academy_topics) <= 3

        identities = autonomous_staff_engine.ensure_club_staff_identities(session, state)
        convs = list(
            session.scalars(
                select(OwnerClubConversation).where(
                    OwnerClubConversation.club_id == state.club_id,
                    OwnerClubConversation.archived_at.is_(None),
                    OwnerClubConversation.channel_type == "direct",
                )
            ).all()
        )
        for conv in convs:
            identity = identities.get(conv.participant_role)
            if identity and not identity.get("is_vacant"):
                assert conv.participant_name == identity["name"]

        pulse = living_institution.get_unified_club_pulse(session, state, include_internal=True)
        supp = pulse["supporters"]
        assert 0 <= supp["overall_sentiment"] <= 100
        assert 0 <= supp["confidence_in_owner"] <= 100
        assert supp["active_protest_stage"] != "organised_boycott"

        expected_unread = len(
            session.scalars(
                select(OwnerInboxItem).where(
                    OwnerInboxItem.club_id == state.club_id,
                    OwnerInboxItem.status == "open",
                    OwnerInboxItem.is_read.is_(False),
                    OwnerInboxItem.archived_at.is_(None),
                )
            ).all()
        )
        assert pulse["staff_and_governance"]["unread_proactive_alerts_count"] == min(8, expected_unread)
    finally:
        session.close()
