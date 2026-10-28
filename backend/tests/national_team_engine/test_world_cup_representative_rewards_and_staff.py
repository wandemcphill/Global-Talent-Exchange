from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.club_growth.schemas import StaffOfferRequest
from app.club_growth.service import ClubGrowthService
from app.ingestion.models import Country, Player
from app.models import Base
import app.models  # noqa: F401
from app.models.club_growth import ClubStaffProfile
from app.models.club_profile import ClubProfile
from app.models.national_team import NationalTeamCompetition, NationalTeamCompetitionEntry, NationalTeamEntry
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.national_team_engine.competition_lifecycle_service import (
    NationalCompetitionLifecycleError,
    NationalCompetitionLifecycleService,
)
from app.national_team_engine.schemas import NationalTeamCompetitionEntrySubmitRequest
from app.national_team_engine.tournament_service import NationalTeamTournamentService
from app.owner_console import ledger as oc_ledger
from app.owner_console import service as oc_service
from app.owner_console.models import OwnerClubState
from app.players.read_models import PlayerSummaryReadModel
from app.wallets.service import LedgerPosting, WalletService


def _build_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return SessionLocal()


def _create_user(session, suffix: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        id=f"user_{suffix}",
        email=f"{suffix}@example.com",
        username=f"user_{suffix}",
        display_name=f"User {suffix}",
        password_hash="not-used",
        role=role,
    )
    session.add(user)
    session.flush()
    return user


def _fund_user_wallet(session, user: User, *, coin: str = "5000.0000", fan_coin: str = "5000.0000") -> None:
    ws = WalletService()
    ws.ensure_default_accounts(session, user)
    if Decimal(coin) > 0:
        user_coin = ws.get_user_account(session, user, LedgerUnit.COIN)
        plat_coin = ws.ensure_platform_account(session, LedgerUnit.COIN)
        ws.append_transaction(
            session,
            postings=[
                LedgerPosting(account=plat_coin, amount=-Decimal(coin), source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT),
                LedgerPosting(account=user_coin, amount=Decimal(coin), source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            reference=f"seed-coin:{user.id}",
            description="Test coin funding",
            actor=user,
        )
    if Decimal(fan_coin) > 0:
        user_fan = ws.get_user_account(session, user, LedgerUnit.CREDIT)
        plat_fan = ws.ensure_platform_account(session, LedgerUnit.CREDIT)
        ws.append_transaction(
            session,
            postings=[
                LedgerPosting(account=plat_fan, amount=-Decimal(fan_coin), source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT),
                LedgerPosting(account=user_fan, amount=Decimal(fan_coin), source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            reference=f"seed-fan:{user.id}",
            description="Test fan coin funding",
            actor=user,
        )


def test_seeded_competitions_include_asian_cup_and_user_hosted_national_tournaments():
    with _build_session() as session:
        admin = _create_user(session, "admin_seed", role=UserRole.ADMIN)
        zero_club_user = _create_user(session, "zero_club_host", role=UserRole.USER)
        service = NationalTeamTournamentService(session)

        seeded = service.seed_default_competitions(actor=admin)
        keys = {item["key"] for item in seeded}
        assert "gtex-world-cup" in keys
        assert "gtex-afcon" in keys
        assert "gtex-euros" in keys
        assert "gtex-copa" in keys
        assert "gtex-asian-cup" in keys
        assert "gtex-u20-asian-cup" in keys
        assert "gtex-u17-asian-cup" in keys

        # Non-admin user with 0 clubs can host a custom national team competition
        hosted = service.host_user_competition(
            actor=zero_club_user,
            title="Global diaspora Nations Cup",
            season_label="2026",
            competition_family="world_cup",
        )
        assert hosted["title"] == "Global diaspora Nations Cup"
        assert hosted["metadata_json"]["host_type"] == "user"
        assert hosted["metadata_json"]["entry_fee_coin"] == "0.0000"


def test_national_team_manager_hiring_upfront_fan_coin_and_tactical_autobuild():
    with _build_session() as session:
        admin = _create_user(session, "admin_mgr", role=UserRole.ADMIN)
        user_no_club = _create_user(session, "nomad_user", role=UserRole.USER)
        _fund_user_wallet(session, user_no_club, coin="2000.0000", fan_coin="1000.0000")

        service = NationalTeamTournamentService(session)
        seeded = service.seed_default_competitions(actor=admin)
        wc_id = next(c["id"] for c in seeded if c["key"] == "gtex-world-cup")

        # Create a national team entry with 0 clubs owned (strictly user_id)
        entry = NationalTeamEntry(
            competition_id=wc_id,
            country_code="NG",
            country_name="Nigeria",
            entry_owner_user_id=user_no_club.id,
            manager_user_id=user_no_club.id,
            squad_size=0,
            metadata_json={},
        )
        session.add(entry)
        session.flush()

        # Verify catalog and hire manager with upfront Fan Coin
        catalog = service.list_available_national_managers()
        assert len(catalog) >= 5
        tiki_mgr = next(m for m in catalog if m["tactical_style"] == "tiki_taka")

        ws = WalletService()
        before_fan = ws.get_balance(session, ws.get_user_account(session, user_no_club, LedgerUnit.CREDIT))
        hire_res = service.hire_national_team_manager(
            entry_id=entry.id,
            actor=user_no_club,
            manager_id=tiki_mgr["manager_id"],
        )
        after_fan = ws.get_balance(session, ws.get_user_account(session, user_no_club, LedgerUnit.CREDIT))

        assert hire_res["hired_manager"]["upfront_paid"] is True
        assert hire_res["hired_manager"]["preferred_formation"] == "4-3-3"
        assert hire_res["hired_manager"]["staff_roles_required"] == ["manager"]
        assert before_fan - after_fan == Decimal(tiki_mgr["fee_fan_coin"])

        # Verify tactical resolution for tiki_taka & gegenpress
        t_label, form = service._resolve_auto_build_formation("tiki_taka")
        assert t_label == "tiki_taka"
        assert form == "4-3-3"
        g_label, g_form = service._resolve_auto_build_formation("gegenpress")
        assert g_label == "gegenpress"
        assert g_form == "4-2-3-1"


def test_prequalifier_representative_continuity_finals_squad_window_and_multitier_world_cup_rewards():
    with _build_session() as session:
        admin = _create_user(session, "wc_admin", role=UserRole.ADMIN)
        # 4 users want England (ENG), plus 5 other countries
        eng_users = [_create_user(session, f"eng_{i}") for i in range(4)]
        other_users = [_create_user(session, f"other_{i}") for i in range(5)]
        outsider = _create_user(session, "outsider_hijacker")

        for code, name, conf in [
            ("ENG", "England", "UEFA"),
            ("FRA", "France", "UEFA"),
            ("BRA", "Brazil", "CONMEBOL"),
            ("ARG", "Argentina", "CONMEBOL"),
            ("NGA", "Nigeria", "CAF"),
            ("JPN", "Japan", "AFC"),
        ]:
            session.add(
                Country(
                    source_provider="test",
                    provider_external_id=code,
                    name=name,
                    alpha2_code=code[:2],
                    fifa_code=code,
                    confederation_code=conf,
                )
            )
        session.flush()

        competition = NationalTeamCompetition(
            key="gtex-world-cup-2026-test",
            title="GTEX World Cup",
            season_label="2026",
            region_type="global",
            age_band="senior",
            format_type="cup",
            status="published",
            metadata_json={
                "competition_family": "world_cup",
                "minimum_squad_size": 2,
                "maximum_squad_size": 5,
                "competition_engine": {
                    "tournament_slots": 4,
                    "group_size": 2,
                    "advance_per_group": 1,
                    "best_third_slots": 0,
                    "qualifier_group_size": 3,
                    "preferred_cycle_week": 4,
                    "schedule_label": "Week 4 -> World Cup",
                },
            },
            created_by_user_id=admin.id,
        )
        session.add(competition)
        session.commit()

        lifecycle = NationalCompetitionLifecycleService(session)

        def _make_squad(country_code: str, country_name: str, r1: int, r2: int):
            return NationalTeamCompetitionEntrySubmitRequest(
                country_code=country_code,
                country_name=country_name,
                squad=[
                    {"player_name": f"{country_code} Star 1", "age": 24, "overall_rating": r1, "position": "ST"},
                    {"player_name": f"{country_code} Star 2", "age": 23, "overall_rating": r2, "position": "CM"},
                ],
            )

        # 4 users submit England; eng_users[0] has the strongest squad
        lifecycle.submit_entry(
            competition_id=competition.id,
            actor=eng_users[0],
            payload=_make_squad("ENG", "England", 94, 92),
        )
        for idx, u in enumerate(eng_users[1:], start=1):
            lifecycle.submit_entry(
                competition_id=competition.id,
                actor=u,
                payload=_make_squad("ENG", "England", 75 - idx, 74 - idx),
            )

        other_nations = [
            ("FRA", "France", 88, 86),
            ("BRA", "Brazil", 87, 85),
            ("ARG", "Argentina", 86, 84),
            ("NGA", "Nigeria", 72, 71),
            ("JPN", "Japan", 70, 69),
        ]
        for u, (code, cname, r1, r2) in zip(other_users, other_nations):
            lifecycle.submit_entry(
                competition_id=competition.id,
                actor=u,
                payload=_make_squad(code, cname, r1, r2),
            )

        # Lock entries -> stage starts at pre_qualifier because 4 users picked England
        locked = lifecycle.lock_entries(competition_id=competition.id)
        assert locked["current_stage"] == "pre_qualifier"

        # Run pre_qualifier -> narrows 4 England contestants down to 1 single England representative!
        after_pre = lifecycle.advance_lifecycle(competition_id=competition.id)
        assert after_pre["current_stage"] == "qualifier"
        eng_reps = [e for e in after_pre["representative_entries"] if e["country_code"] == "ENG"]
        assert len(eng_reps) == 1
        eng_rep_user_id = eng_reps[0]["user_id"]
        eng_rep_user = next(u for u in eng_users if u.id == eng_rep_user_id)

        # Run qualifier -> top 4 nations qualify for the World Cup Finals ("tournament" stage)
        after_qual = lifecycle.advance_lifecycle(competition_id=competition.id)
        assert after_qual["current_stage"] == "tournament"
        qualified_codes = {e["country_code"] for e in after_qual["qualified_entries"]}
        assert "ENG" in qualified_codes

        # Outsider CANNOT hijack England's World Cup Finals spot
        try:
            lifecycle.update_qualified_finals_squad(
                competition_id=competition.id,
                actor=outsider,
                payload=_make_squad("ENG", "England", 99, 99),
            )
        except NationalCompetitionLifecycleError as exc:
            assert exc.reason == "country_representative_locked"
        else:
            raise AssertionError("Expected outsider to be blocked from England's representative spot")

        # Qualified England representative CAN update 1-2 players in their squad for the World Cup Finals
        updated_eng = lifecycle.update_qualified_finals_squad(
            competition_id=competition.id,
            actor=eng_rep_user,
            payload=NationalTeamCompetitionEntrySubmitRequest(
                country_code="ENG",
                country_name="England",
                squad=[
                    {"player_name": "ENG Star 1", "age": 24, "overall_rating": 95, "position": "ST"},
                    {"player_name": "ENG Star 2", "age": 23, "overall_rating": 93, "position": "CM"},
                    {"player_name": "ENG Finals Callup 3", "age": 21, "overall_rating": 91, "position": "GK"},
                ],
            ),
        )
        assert len(updated_eng["squad"]) == 3

        # Run World Cup Finals ("tournament" stage) -> completed!
        completed = lifecycle.advance_lifecycle(competition_id=competition.id, actor=admin)
        assert completed["current_stage"] == "completed"

        # Verify multi-tier World Cup reward breakdown (Guaranteed Qualification + Every Match Win/Draw/Loss + Stage Progression)
        breakdown = completed["reward_breakdown"]
        assert breakdown is not None
        assert len(breakdown["entry_rewards"]) == 4
        for row in breakdown["entry_rewards"]:
            # Every qualified Finals team gets >= 250.0000 qualification guarantee + group stage + match payouts
            assert Decimal(row["qualification_guaranteed_coin"]) == Decimal("250.0000")
            assert row["matches_played"] >= 1
            assert Decimal(row["match_earnings_coin"]) > Decimal("0.0000")
            assert Decimal(row["stage_progression_coin"]) >= Decimal("100.0000")
            assert Decimal(row["total_gross_coin"]) > Decimal("350.0000")

        # Settle all multi-tier rewards into participant wallets
        settled = lifecycle.settle_tournament_rewards(competition_id=competition.id, actor=admin)
        assert settled["settlement_count"] == 4
        assert Decimal(settled["total_distributed_coin"]) > Decimal("1500.0000")


def test_club_staff_upfront_fan_coin_and_manager_first_tactical_autopick():
    with _build_session() as session:
        owner = _create_user(session, "club_owner_tiki")
        _fund_user_wallet(session, owner, coin="100000.0000", fan_coin="10000.0000")

        # 1. Test ClubGrowthService.accept_staff_contract upfront Fan Coin deduction
        staff_profile = ClubStaffProfile(
            id="staff_gm_1",
            market_key="gm_elite_01",
            display_name="Txiki Begiristain",
            staff_type="general_manager",
            rarity="elite",
            rating=91,
            salary_minor=40000,  # 400 Fan Coin / year
            skills_json=["general_manager", "negotiation"],
        )
        club_prof = ClubProfile(
            id="club_tiki_1",
            owner_user_id=owner.id,
            club_name="Tiki Taka FC",
            slug="tiki-taka-fc",
            primary_color="#00E676",
            secondary_color="#0A0E17",
            accent_color="#F5B83D",
        )
        session.add_all([staff_profile, club_prof])
        session.flush()

        cg = ClubGrowthService(session)
        offered = cg.offer_staff_contract(
            actor=owner,
            club_id=club_prof.id,
            staff_id=staff_profile.id,
            payload=StaffOfferRequest(
                role_scope="general_manager",
                duration_days=1095,  # 3-year contract
                salary_minor=40000,
                exclusive=False,
            ),
        )
        ws = WalletService()
        fan_before = ws.get_balance(session, ws.get_user_account(session, owner, LedgerUnit.CREDIT))
        accepted = cg.accept_staff_contract(actor=owner, club_id=club_prof.id, contract_id=offered.id)
        fan_after = ws.get_balance(session, ws.get_user_account(session, owner, LedgerUnit.CREDIT))
        # 400 Fan Coin/yr * 3 years = 1200 Fan Coin deducted once upfront
        assert fan_before - fan_after == Decimal("1200.0000")
        assert accepted.status == "active"

        # 2. Test OwnerConsole Manager-First Onboarding + Tactical 4-3-3 Auto-Pick
        state = OwnerClubState(
            club_id=club_prof.id,
            owner_user_id=owner.id,
            club_name=club_prof.club_name,
            stage="squad",
            prestige=50,
        )
        session.add(state)
        session.flush()

        # Fund club treasury in GTEX for player signings
        oc_ledger.record(
            session,
            event_type="launch_grant",
            source=oc_ledger.PLATFORM_GRANTS,
            destination=oc_ledger.club_account(club_prof.id),
            currency=oc_ledger.GTEX,
            gross=100_000,
            club_id=club_prof.id,
            user_id=owner.id,
            memo="Launch grant",
        )

        # Seed market players across GK, DEF, MID, FWD
        positions = (
            ["GK", "GK"]
            + ["CB", "CB", "RB", "LB", "CB", "LB"]
            + ["CM", "CM", "DM", "AM", "CM", "RM"]
            + ["ST", "RW", "LW", "ST", "RW"]
        )
        for idx, pos in enumerate(positions):
            p = Player(
                id=f"mkt_p_{idx}",
                source_provider="test",
                provider_external_id=f"ext_{idx}",
                full_name=f"Tactical Player {idx}",
                position=pos,
                normalized_position=pos,
            )
            from app.models.base import utcnow

            summary = PlayerSummaryReadModel(
                player_id=p.id,
                player_name=p.full_name,
                last_snapshot_at=utcnow(),
                current_value_credits=10.0,
                previous_value_credits=9.0,
                movement_pct=4.3,
                average_rating=7.8,
                summary_json={},
            )
            session.add_all([p, summary])
        session.flush()

        # Appoint Manager FIRST while state.stage == "squad"!
        oc_service.appoint_manager(
            session,
            owner.id,
            club_prof.id,
            {
                "manager_id": "mgr_pep_tiki",
                "name": "Pep Tiki-Taka",
                "style": "tiki_taka",
                "preferred_formation": "4-3-3",
                "tactical_rating": 92,
                "salary": 1500,
            },
        )
        assert state.stage == "squad"

        # Now run staff-guided tactical auto-pick with budget cap
        res = oc_service.autopick_squad(
            session,
            owner.id,
            club_prof.id,
            budget_gtex=50_000,
            tactic="tiki_taka",
            formation="4-3-3",
            target_squad_size=11,
        )
        assert res["signed_count"] == 11
        assert res["tactic"] == "tiki_taka"
        assert res["formation"] == "4-3-3"
        assert res["total_spent_gtex"] <= 50_000
        assert res["staff_committee"]["first_team_manager"] == "Pep Tiki-Taka"
        # Because manager was already appointed, completing the squad advances directly to "competition"!
        assert res["stage"] == "competition"
