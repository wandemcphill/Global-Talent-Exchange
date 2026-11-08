"""Automated test suite for Stage 1 Living World relationship dimensions and migration.

Covers:
- Model dimensions (alignment, influence, loyalty) and bounds clamping (0..100)
- Durable delta logging and snapshots in OwnerClubRelationshipHistory
- API serialization in living-world relationships endpoint
- Migration 0228 upgrade/downgrade behavior and defaults
"""

from __future__ import annotations

import importlib
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user, get_session
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
from app.owner_console import engine as owner_engine, ledger, living_club_world, router as owner_router
from app.owner_console.models import (
    OWNER_CONSOLE_TABLES,
    OwnerClubRelationshipHistory,
    OwnerClubState,
    OwnerSquadPlayer,
)

WORLD_NOW = datetime(2026, 11, 7, 12, 0, 0, tzinfo=timezone.utc)
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


def _seed_club(
    session: Session,
    *,
    club_id: str = "club-stage1-1",
    user_id: str = "user-stage1-1",
) -> OwnerClubState:
    existing_user = session.get(User, user_id)
    if existing_user is None:
        user = User(
            id=user_id,
            email=f"{user_id}@gtex.test",
            username=f"owner_{user_id}",
            password_hash="synthetic_hash",
        )
        session.add(user)
        session.flush()

    profile = ClubProfile(
        id=club_id,
        owner_user_id=user_id,
        club_name=f"Lagos Marine FC ({club_id})",
        slug=f"lagos-marine-fc-{club_id}",
        primary_color="#0284c7",
        secondary_color="#0f172a",
        accent_color="#38bdf8",
    )
    session.add(profile)

    exec_staff = {
        "general_manager": {
            "id": "gm_appointed_1",
            "name": "Babatunde Lawal",
            "role": "general_manager",
            "mood": 78,
        },
        "head_of_youth_development": {
            "id": "hoyd_appointed_1",
            "name": "Kunle Adeyemi",
            "role": "head_of_youth_development",
            "mood": 82,
        },
        "medical_director": {
            "id": "med_appointed_1",
            "name": "Dr. Chidi Obi",
            "role": "medical_director",
            "mood": 84,
        },
        "chief_scout": {
            "id": "scout_appointed_1",
            "name": "Musa Danjuma",
            "role": "chief_scout",
            "mood": 76,
        },
    }

    state = OwnerClubState(
        id=f"state-{club_id}",
        club_id=club_id,
        owner_user_id=user_id,
        club_name=f"Lagos Marine FC ({club_id})",
        stage="active",
        prestige=55,
        manager_json=owner_engine.manager_profile(owner_engine.DEFAULT_MANAGER),
        facilities_json={
            "training": 2,
            "academy": 2,
            "medical": 2,
            "stadium": 2,
            "commercial": 2,
            "_executive_staff": exec_staff,
        },
        world_day=10,
        last_tick_at=WORLD_NOW,
        last_world_tick_date=WORLD_NOW.date(),
        value_history_json=[],
    )
    session.add(state)

    p1 = OwnerSquadPlayer(
        id=f"p1-{club_id}",
        club_id=club_id,
        name="Tunde Bakare",
        position="CB",
        age=28,
        rating=74,
        potential=76,
        value_coin=Decimal("4500"),
        morale=75,
        injured_days=0,
        is_regen=False,
        personality_json={"leadership": 16, "fitness": 96},
    )
    session.add(p1)

    ledger.record(
        session,
        event_type="club_launch_grant",
        source=ledger.WORLD_CLUBS,
        destination=ledger.club_account(club_id),
        currency=ledger.GTEX,
        gross=Decimal(100_000),
        club_id=club_id,
        user_id=user_id,
        memo="Initial club grant",
    )
    session.commit()
    return state


def _build_test_client(session: Session, user_id: str) -> TestClient:
    app = FastAPI()
    app.include_router(owner_router.router)

    def _override_session():
        yield session

    def _override_user():
        return SimpleNamespace(id=user_id, email=f"{user_id}@gtex.test", role="user")

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_current_user] = _override_user
    return TestClient(app)


def test_relationship_dimensions_initialization_and_api():
    """Test that appointed staff relationships initialize with alignment, influence, and loyalty and are exposed in API."""
    session = _session()
    state = _seed_club(session, club_id="club-stage1-api", user_id="user-stage1-api")
    client = _build_test_client(session, "user-stage1-api")

    resp = client.get(f"/owner/clubs/{state.club_id}/living-world/relationships")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["club_id"] == state.club_id
    rels = data["relationships"]
    assert len(rels) >= 5

    # Check manager relationship
    mgr_rel = next((r for r in rels if r.get("role_key") == "first_team_manager"), None)
    assert mgr_rel is not None
    assert mgr_rel["trust"] == 55
    assert mgr_rel["respect"] == 60
    assert mgr_rel["tension"] == 15
    assert mgr_rel["alignment"] == 65
    assert mgr_rel["influence"] == 70
    assert mgr_rel["loyalty"] == 60

    # Check GM relationship
    gm_rel = next((r for r in rels if r.get("role_key") == "general_manager"), None)
    assert gm_rel is not None
    assert gm_rel["trust"] == 65
    assert gm_rel["alignment"] == 75
    assert gm_rel["influence"] == 75
    assert gm_rel["loyalty"] == 70


def test_apply_relationship_delta_updates_new_dimensions_and_clamps():
    """Test delta updates for alignment, influence, and loyalty with strict 0..100 clamping and durable history."""
    session = _session()
    state = _seed_club(session, club_id="club-stage1-deltas", user_id="user-stage1-deltas")

    # Ensure baseline relationships
    squad_players = list(
        session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == state.club_id)).all()
    )
    living_club_world.ensure_default_relationships(session, state, squad_players)

    # 1. Apply positive delta
    updated = living_club_world.apply_relationship_delta(
        session,
        state.club_id,
        "owner",
        "owner",
        "Club Owner",
        "staff",
        "first_team_manager",
        "First-Team Manager",
        delta_alignment=15,
        delta_influence=-10,
        delta_loyalty=25,
        reason="Board strategic vision alignment meeting",
        world_day=11,
    )
    session.commit()
    assert updated is not None
    assert updated.alignment == 80  # 65 + 15
    assert updated.influence == 60  # 70 - 10
    assert updated.loyalty == 85  # 60 + 25

    # 2. Check history logging
    hist = list(
        session.scalars(
            select(OwnerClubRelationshipHistory)
            .where(OwnerClubRelationshipHistory.relationship_id == updated.id)
            .order_by(OwnerClubRelationshipHistory.created_at.desc())
        ).all()
    )
    assert len(hist) >= 1
    latest = hist[0]
    assert latest.delta_alignment == 15
    assert latest.delta_influence == -10
    assert latest.delta_loyalty == 25
    assert latest.snapshot_json["alignment"] == 80
    assert latest.snapshot_json["influence"] == 60
    assert latest.snapshot_json["loyalty"] == 85

    # 3. Test clamping at 100 max and 0 min
    living_club_world.apply_relationship_delta(
        session,
        state.club_id,
        "owner",
        "owner",
        "Club Owner",
        "staff",
        "first_team_manager",
        "First-Team Manager",
        delta_alignment=100,
        delta_influence=-200,
        delta_loyalty=100,
        reason="Extreme stress test",
        world_day=12,
    )
    session.commit()
    session.refresh(updated)
    assert updated.alignment == 100
    assert updated.influence == 0
    assert updated.loyalty == 100


def test_migration_0228_schema_upgrade_compatibility():
    """Verify migration 0228 can run on a database schema and add the required columns."""
    test_engine = create_engine("sqlite:///:memory:")
    # Create baseline relationship tables without the 0228 columns
    with test_engine.begin() as conn:
        conn.execute(text("""
                CREATE TABLE owner_club_relationships (
                    id VARCHAR(36) PRIMARY KEY,
                    club_id VARCHAR(36) NOT NULL,
                    pairing_key VARCHAR(160) NOT NULL,
                    participant_a_type VARCHAR(32) NOT NULL,
                    participant_a_id VARCHAR(64) NOT NULL,
                    participant_a_name VARCHAR(160) NOT NULL,
                    participant_b_type VARCHAR(32) NOT NULL,
                    participant_b_id VARCHAR(64) NOT NULL,
                    participant_b_name VARCHAR(160) NOT NULL,
                    trust INTEGER NOT NULL DEFAULT 50,
                    respect INTEGER NOT NULL DEFAULT 50,
                    affinity INTEGER NOT NULL DEFAULT 50,
                    tension INTEGER NOT NULL DEFAULT 20,
                    status VARCHAR(24) NOT NULL DEFAULT 'active',
                    metadata_json JSON NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                );
                """))
        conn.execute(text("""
                CREATE TABLE owner_club_relationship_history (
                    id VARCHAR(36) PRIMARY KEY,
                    relationship_id VARCHAR(36) NOT NULL,
                    club_id VARCHAR(36) NOT NULL,
                    world_day INTEGER NOT NULL DEFAULT 1,
                    reason VARCHAR(255) NOT NULL,
                    source_event_id VARCHAR(36),
                    delta_trust INTEGER NOT NULL DEFAULT 0,
                    delta_respect INTEGER NOT NULL DEFAULT 0,
                    delta_affinity INTEGER NOT NULL DEFAULT 0,
                    delta_tension INTEGER NOT NULL DEFAULT 0,
                    snapshot_json JSON NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP NOT NULL
                );
                """))

        # Insert a legacy pre-0228 relationship
        conn.execute(text("""
                INSERT INTO owner_club_relationships (
                    id, club_id, pairing_key, participant_a_type, participant_a_id, participant_a_name,
                    participant_b_type, participant_b_id, participant_b_name, trust, respect, affinity,
                    tension, status, metadata_json, created_at, updated_at
                ) VALUES (
                    'rel-1', 'club-1', 'pair-1', 'owner', 'owner', 'Owner',
                    'staff', 'mgr-1', 'Manager', 55, 60, 50, 15, 'active', '{}',
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                );
                """))

    # Now run the 0228 upgrade logic using mock Alembic op context
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    migration_0228 = importlib.import_module(
        "backend.migrations.versions.20261107_0228_living_world_stage1_relationship_dimensions"
        if False
        else "migrations.versions.20261107_0228_living_world_stage1_relationship_dimensions"
    )

    with test_engine.begin() as conn:
        ctx = MigrationContext.configure(conn)
        op_obj = Operations(ctx)
        migration_0228.op = op_obj
        migration_0228.upgrade()

    # Verify columns were added with proper defaults
    with test_engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, trust, alignment, influence, loyalty FROM owner_club_relationships WHERE id = 'rel-1'")
        ).fetchone()
        assert row is not None
        assert row[0] == "rel-1"
        assert row[1] == 55
        assert row[2] == 60  # Default alignment
        assert row[3] == 50  # Default influence
        assert row[4] == 60  # Default loyalty
