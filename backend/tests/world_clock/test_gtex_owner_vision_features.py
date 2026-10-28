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
from app.owner_console import competitions as comps
from app.owner_console import engine as owner_engine
from app.owner_console import ledger, service, storytelling
from app.owner_console.models import (
    OWNER_CONSOLE_TABLES,
    OwnerClubState,
)
from app.services.world_clock_service import DEFAULT_CLOCK_ID, WorldClockService
from app.world_simulation.router import get_world_clock

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


def _seed_club(session: Session, *, prestige: int = 50, cash: int = 100_000) -> OwnerClubState:
    user = User(
        id="user-1",
        email="owner1@gtex.test",
        username="owner1",
        password_hash="hash",
    )
    profile = ClubProfile(
        id="club-1",
        owner_user_id="user-1",
        club_name="Lagos Sovereign FC",
        slug="lagos-sovereign-fc",
        primary_color="#10b981",
        secondary_color="#0f172a",
        accent_color="#f59e0b",
    )
    session.add(user)
    session.add(profile)
    state = OwnerClubState(
        id="state-1",
        club_id="club-1",
        owner_user_id="user-1",
        club_name="Lagos Sovereign FC",
        stage="active",
        prestige=prestige,
        manager_json=owner_engine.manager_profile(owner_engine.DEFAULT_MANAGER),
        facilities_json={"training": 2, "academy": 2, "medical": 2, "stadium": 2, "commercial": 2},
        world_day=10,
        last_tick_at=WORLD_NOW,
        last_world_tick_date=WORLD_NOW.date(),
        value_history_json=[],
    )
    session.add(state)
    ledger.record(
        session,
        event_type="club_launch_grant",
        source=ledger.WORLD_CLUBS,
        destination=ledger.club_account("club-1"),
        currency=ledger.GTEX,
        gross=Decimal(cash),
        club_id="club-1",
        user_id="user-1",
        memo="Initial club grant",
    )
    session.commit()
    return state


def test_world_clock_enrichment_fields():
    session = _session()
    view = get_world_clock(session=session)
    assert view.gtex_years_running >= 1
    assert view.current_season_number >= 1
    assert "GTEX Year" in view.current_season_label
    assert "Season" in view.current_season_label


def test_executive_staff_boardroom_prestige_gating_and_hiring():
    session = _session()
    _seed_club(session, prestige=30, cash=100_000)

    staff_data = service.get_club_staff(session, "user-1", "club-1")
    assert "appointed_staff" in staff_data
    assert "candidates" in staff_data
    assert "staff_effects" in staff_data
    assert set(staff_data["appointed_staff"].keys()) >= {
        "general_manager",
        "first_team_manager",
        "head_of_youth_development",
        "chief_scout",
        "medical_director",
    }

    elite_candidates = [c for c in staff_data["candidates"] if int(c.get("min_prestige", 0)) > 30]
    assert elite_candidates, "Expected at least one elite candidate requiring >30 prestige"
    elite = elite_candidates[0]

    with pytest.raises(service.OwnerError) as exc_info:
        service.hire_executive_staff(
            session,
            "user-1",
            "club-1",
            elite["id"],
            role=elite["role"],
            marquee_wage_premium=False,
        )
    assert exc_info.value.code == "insufficient_club_prestige"

    hired = service.hire_executive_staff(
        session,
        "user-1",
        "club-1",
        elite["id"],
        role=elite["role"],
        marquee_wage_premium=True,
    )
    assert hired["appointed"]["name"] == elite["name"]

    pol = service.update_delegation_policy(
        session,
        "user-1",
        "club-1",
        {
            "mode": "gm_led",
            "gm_transfer_autonomy": True,
            "hoyd_youth_contracts": True,
            "manager_tactics_autonomy": False,
        },
    )
    assert pol["delegation_policy"]["mode"] == "gm_led"


def test_showroom_prestige_tiers_and_staff_luxury_gifting():
    session = _session()
    _seed_club(session, prestige=55, cash=250_000)

    showroom = storytelling.get_club_showroom(session, "user-1", "club-1")
    assert showroom["club_prestige"] == 55
    assert "Tier" in showroom["prestige_tier"]
    assert all("academy_ceiling_bonus" in item for item in showroom["catalog"])
    assert all("can_gift_to_staff" in item for item in showroom["catalog"])

    gift_res = storytelling.gift_asset_to_squad_player(
        session,
        "user-1",
        "club-1",
        "staff:first_team_manager",
        catalog_key="chronos_tourbillon_watch",
        note="Thank you for leading the squad",
        recipient_type="staff",
        staff_role="first_team_manager",
    )
    assert gift_res["recipient_type"] == "staff"
    assert gift_res["mood_delta"] == 15
    assert gift_res["loyalty_delta"] == 3


def test_academy_readiness_youth_contract_and_senior_promotion():
    session = _session()
    _seed_club(session, prestige=75, cash=100_000)

    regens = service.academy_intake(session, "user-1", "club-1")
    assert len(regens) >= 1
    prospect = regens[0]

    pdict = service.player_dict(prospect)
    assert "archetype" in pdict
    assert "mood_state" in pdict
    assert "inner_monologue" in pdict
    assert "decision_factors" in pdict
    assert "readiness_assessment" in pdict

    contract_res = service.academy_contract(session, "user-1", "club-1", prospect.id)
    assert contract_res["player"]["morale"] > pdict["morale"] or contract_res["player"]["morale"] == 100

    promo_res = service.academy_promote(session, "user-1", "club-1", prospect.id)
    assert promo_res["player"]["squad_status"] == "senior"


def test_daily_briefing_and_boardroom_staff_chat():
    session = _session()
    _seed_club(session, prestige=60, cash=100_000)
    service.academy_intake(session, "user-1", "club-1")

    briefing = storytelling.get_daily_briefing(session, "user-1", "club-1")
    assert briefing["club_id"] == "club-1"
    assert len(briefing["sections"]) >= 3
    assert briefing["metrics"]["prestige"] == 60

    chat = storytelling.converse_with_staff(
        session,
        "user-1",
        "club-1",
        "general_manager",
        "How does our transfer budget and commercial outlook look?",
        "transfers",
    )
    assert "reply" in chat
    assert chat["role"] == "general_manager"
    assert chat["staff_message"]["role"] == "general_manager"
    assert "GTX" in chat["reply"] or "GTEX" in chat["reply"] or "Tier" in chat["reply"]


def test_ecosystem_revenue_waterfall_win_bonus_and_press_conference():
    session = _session()
    _seed_club(session, prestige=65, cash=100_000)

    wf = ledger.ecosystem_waterfall_summary(session, club_id="club-1")
    assert wf["tv_broadcast_pool_gtex"] > 0
    assert wf["competition_prize_pool_gtex"] > 0
    assert wf["jackpot_ecosystem_pool_gtex"] > 0

    bonus = service.pledge_win_bonus(session, "user-1", "club-1", 1500, "Win the derby!")
    assert bonus["pledged_win_bonus_gtex"] == 1500

    pc = service.conduct_press_conference(session, "user-1", "club-1", "praise_squad", "Proud of the boys")
    assert pc["tone"] == "praise_squad"
