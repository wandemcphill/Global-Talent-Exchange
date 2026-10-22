"""
Master Seed Script for GTEX Full Experience.
Seeds:
- Rebuilt demo market & world visibility
- Enabled feature flags (club_legacy, club_sale_market, etc.)
- Jackpot pool & past winner payout
- Club Sale listing & valuation
- Regen Awards & ceremony
- Executive staff (General Manager, Head of Youth Development, Club Manager) & interactions
- Squad players with luxury gifts & private jet purchase
- Live match in progress with pitch radar & gifting sheet
"""

from __future__ import annotations

import os
import sys
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(r"C:\Users\ayomc\.gemini\antigravity\scratch\gtex")
DB_PATH = REPO_ROOT / "gte_backend.db"
DB_URL = f"sqlite:///{DB_PATH.as_posix()}"

os.environ["PYTHONPATH"] = str(REPO_ROOT / "backend")
os.environ["DATABASE_URL"] = DB_URL
os.environ["GTE_DATABASE_URL"] = DB_URL
os.environ["GTE_AUTH_SECRET"] = "local-demo-secret-local-demo-secret-1234"
os.environ["GTE_MEDIA_SIGNING_SECRET"] = "local-media-secret-local-media-secret-1234"
os.environ["PYTHONWARNINGS"] = "ignore"

sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.config import reset_settings_cache
reset_settings_cache()

from app.ingestion.dev_cli import rebuild_demo_market
from app.core.database import get_session_factory
from sqlalchemy import select
from sqlalchemy.orm import Session

# Import models
from app.models.user import User, UserRole
from app.models.club_profile import ClubProfile
from app.models.admin_rules import AdminFeatureFlag
from app.owner_console.models import OwnerSquadPlayer, OwnerInboxItem
from app.club_legacy.models import (
    ClubLegacyCatalogueItem,
    ClubLegacyAsset,
    ClubLegacyGift,
    ClubLegacyExecutive,
    ClubLegacyReport,
    ClubLegacyManager,
    ClubLegacyManagerOffer,
    ClubLegacyPromise,
    ClubLegacyPolicy,
    ClubLegacyRecommendation,
    ClubLegacyRelationshipEvent,
)
from app.models.club_sale_market import (
    ClubSaleListing,
    ClubSaleInquiry,
    ClubSaleOffer,
    ClubValuationSnapshot,
    ClubSaleListingStatus,
)
from app.regen_universe.models import (
    RegenAward,
    RegenAwardWinner,
    RegenSeason,
)
from app.models.gtex_economy import (
    GtexJackpotRound,
    GtexJackpotPayout,
    GtexJackpotRoundStatus,
    GtexJackpotDistributionMode,
    GtexJackpotTriggerMode,
)
from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.club_legacy.operations import seed_catalogue
from app.club_legacy.full import phase2, phase4, phase7
from app.club_legacy.ledger import post_club_legacy_transfer
from app.owner_console import ledger

print("--- Step 1: Rebuilding demo market ---")
try:
    rebuild_demo_market(
        database_url=DB_URL,
        player_count=120,
        provider="demo-universe",
        signal_provider="demo-market-signals",
        password="DemoPass123",
        seed=20260311,
        batch_size=500,
        liquid_player_count=4,
        illiquid_player_count=2,
    )
    print("Demo market rebuild completed.")
except Exception as e:
    print(f"Demo market already populated or error: {e}")

sf = get_session_factory()
with sf() as s:
    print("--- Step 2: Enabling feature flags ---")
    flags_to_enable = [
        "club_legacy",
        "club_legacy_market",
        "club_legacy_preseason",
        "club_legacy_sponsors",
        "club_legacy_governance",
        "club_sale_market",
        "creator_stadium_monetization",
        "creator_league_admin",
        "creator_share_market",
        "matchday_economy",
        "jackpot",
    ]
    for key in flags_to_enable:
        existing = s.scalar(select(AdminFeatureFlag).where(AdminFeatureFlag.feature_key == key))
        if existing:
            existing.enabled = True
        else:
            s.add(AdminFeatureFlag(
                feature_key=key,
                title=key.replace("_", " ").title(),
                description=f"Auto-enabled for local demo: {key}",
                enabled=True,
                audience="global"
            ))
    s.commit()
    print("Feature flags enabled.")

    print("--- Step 3: Resolving Seed Users & Clubs ---")
    admin_user = s.scalar(select(User).where(User.email == "seed.admin@gte.local"))
    fan_user = s.scalar(select(User).where(User.email == "seed.fan@gte.local"))
    scout_user = s.scalar(select(User).where(User.email == "seed.scout@gte.local"))

    # Ensure Valencia Crest is owned by seed.admin
    valencia = s.scalar(select(ClubProfile).where(ClubProfile.id == "00000000-0000-0000-0000-000000000103"))
    if not valencia:
        valencia = ClubProfile(
            id="00000000-0000-0000-0000-000000000103",
            owner_user_id=admin_user.id,
            club_name="Valencia Crest CF",
            short_name="Crest",
            club_slug="valencia-crest-cf",
            stadium_name="Estadio del Crest",
            prestige_rating=85,
        )
        s.add(valencia)
    else:
        valencia.owner_user_id = admin_user.id
        valencia.prestige_rating = 85
    
    # Rio Norte owned by scout
    rio_norte = s.scalar(select(ClubProfile).where(ClubProfile.id == "00000000-0000-0000-0000-000000000102"))
    # Lagos Atlas owned by fan
    lagos_atlas = s.scalar(select(ClubProfile).where(ClubProfile.id == "00000000-0000-0000-0000-000000000101"))
    s.commit()

    print("--- Step 4: Funding Valencia Crest & Buying Private Jet ---")
    seed_catalogue(s)
    # Fund club
    try:
        src = ledger.wallet_account(s, ledger.PLATFORM_GRANTS, ledger.GTEX)
        dst = ledger.wallet_account(s, ledger.club_account(valencia.id), ledger.GTEX)
        post_club_legacy_transfer(
            s,
            idempotency_key="master-fund-valencia-01",
            source=src,
            destination=dst,
            amount=Decimal("500000"),
            description="Master demo club treasury grant",
        )
        s.commit()
    except Exception as e:
        s.rollback()
        print(f"Club funding note: {e}")

    # Buy Private Jet
    jet_asset = s.scalar(select(ClubLegacyAsset).where(ClubLegacyAsset.club_id == valencia.id, ClubLegacyAsset.idempotency_key == "master-jet-valencia-01"))
    if not jet_asset:
        jet_asset = phase4.purchase_asset(
            s,
            club_id=valencia.id,
            user_id=admin_user.id,
            sku="gtex-jet-harbour",
            owner_class="club",
            idempotency_key="master-jet-valencia-01"
        )
        s.commit()
    print(f"Private Jet purchased/confirmed: {jet_asset.id}")

    print("--- Step 5: Adding Squad Players & Gifting Luxury Items ---")
    squad_specs = [
        ("Mateo Alvarez", "ST", 24, 82, 88),
        ("Diego Salazar", "CM", 27, 79, 82),
        ("Iker Montoya", "CB", 22, 76, 84),
        ("Lucas Silva", "GK", 25, 78, 83),
    ]
    created_players = list(s.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == valencia.id)).all())
    if not created_players:
        for nm, pos, age, rt, pot in squad_specs:
            p = OwnerSquadPlayer(
                club_id=valencia.id,
                name=nm,
                position=pos,
                age=age,
                rating=rt,
                potential=pot,
                morale=85,
                value_coin=Decimal(rt * 1500),
                status="active",
            )
            s.add(p)
            created_players.append(p)
        s.commit()

    # Buy watch and coach, gift to striker Mateo Alvarez
    striker = created_players[0]
    watch_asset = s.scalar(select(ClubLegacyAsset).where(ClubLegacyAsset.idempotency_key == "master-watch-valencia-01"))
    if not watch_asset:
        watch_asset = phase4.purchase_asset(
            s,
            club_id=valencia.id,
            user_id=admin_user.id,
            sku="gtex-watch-icon",
            owner_class="club",
            idempotency_key="master-watch-valencia-01"
        )
        gift_watch = phase4.offer_gift(s, asset_id=watch_asset.id, user_id=admin_user.id, recipient_ref=striker.id)
        phase4.resolve_gift(s, gift_id=gift_watch.id, accept=True, actor_user_id=admin_user.id)

    coach_asset = s.scalar(select(ClubLegacyAsset).where(ClubLegacyAsset.idempotency_key == "master-coach-valencia-01"))
    if not coach_asset:
        coach_asset = phase4.purchase_asset(
            s,
            club_id=valencia.id,
            user_id=admin_user.id,
            sku="gtex-coach-lagoon",
            owner_class="club",
            idempotency_key="master-coach-valencia-01"
        )
        gift_coach = phase4.offer_gift(s, asset_id=coach_asset.id, user_id=admin_user.id, recipient_ref=striker.id)
        phase4.resolve_gift(s, gift_id=gift_coach.id, accept=True, actor_user_id=admin_user.id)
    s.commit()
    print("Luxury items gifted to squad striker.")

    print("--- Step 6: Hiring Executives & Manager (GM, HoYD, Manager) ---")
    # 1. General Manager
    gm = s.scalar(select(ClubLegacyExecutive).where(ClubLegacyExecutive.club_id == valencia.id, ClubLegacyExecutive.role == "gm"))
    if not gm:
        gm = phase2.hire_executive(
            s,
            club_id=valencia.id,
            user_id=admin_user.id,
            role="gm",
            name="Marcus Vance",
            personality="ambitious",
            wage=Decimal("8500"),
            authority="operations",
        )
    # Generate recruitment report by GM
    report = phase2.recruitment_report(s, club_id=valencia.id, user_id=admin_user.id)

    # 2. Head of Youth Development
    hoyd = s.scalar(select(ClubLegacyExecutive).where(ClubLegacyExecutive.club_id == valencia.id, ClubLegacyExecutive.role == "hoyd"))
    if not hoyd:
        hoyd = phase2.hire_executive(
            s,
            club_id=valencia.id,
            user_id=admin_user.id,
            role="hoyd",
            name="Santiago Cruz",
            personality="methodical",
            wage=Decimal("6200"),
            authority="academy",
        )
    # Generate academy plan with wonderkids
    academy_plan = phase2.academy_plan(s, club_id=valencia.id, user_id=admin_user.id, seed=2026)

    # 3. Manager
    manager = s.scalar(select(ClubLegacyManager).where(ClubLegacyManager.club_id == valencia.id))
    if not manager:
        manager = phase7.register_manager(
            s,
            name="Carlos Bianchi",
            personality="ambitious",
            ambition=18,
            wage_expectation=Decimal("12000"),
            club_id=valencia.id,
        )
        # Make a promise to manager from club owner
        promise = phase7.make_promise(
            s,
            club_id=valencia.id,
            user_id=admin_user.id,
            subject="Qualify for Continental Prestige League knockout phase.",
            manager_id=manager.id,
        )
        # Record luxury gift to manager
        mgr_rel = phase7.record_gift(s, manager_id=manager.id, club_id=valencia.id)
    s.commit()
    print(f"Hired GM {gm.name}, HoYD {hoyd.name}, and registered Manager {manager.name}.")

    print("--- Step 7: Seeding Active Club Sale Listing ---")
    now = datetime.now(timezone.utc)
    if rio_norte:
        from app.club_sale_market.service import ClubSaleMarketService
        cs_service = ClubSaleMarketService(s)
        try:
            listing_dict = cs_service.create_listing(
                actor=scout_user,
                club_id=rio_norte.id,
                asking_price=Decimal("175000.00"),
                visibility="public",
                note="Historic South American Club With Elite Youth Academy",
                instant_sell_enabled=True,
                instant_sell_minimum_price=Decimal("185000.00"),
            )
            s.commit()
            print("Club sale listing created via service.")
        except Exception as e:
            s.rollback()
            print(f"Listing note: {e}")

        try:
            cs_service.create_inquiry(
                actor=fan_user,
                club_id=rio_norte.id,
                message="Interested in the academy facilities. Are they debt-free?",
            )
            s.commit()
        except Exception as e:
            s.rollback()
            print(f"Inquiry note: {e}")

        try:
            cs_service.create_offer(
                actor=admin_user,
                club_id=rio_norte.id,
                offer_price=Decimal("165000.00"),
                inquiry_id=None,
                message="Formal cash bid from Valencia Crest ownership group.",
                expires_at=now + timedelta(days=7),
            )
            s.commit()
            print("Club sale offer created.")
        except Exception as e:
            s.rollback()
            print(f"Offer note: {e}")

    print("--- Step 8: Seeding Live Viral Jackpot ---")
    now = datetime.now(timezone.utc)
    try:
        past_round = s.scalar(select(GtexJackpotRound).where(GtexJackpotRound.pool_key == "global", GtexJackpotRound.round_number == 1))
        if not past_round:
            past_round = GtexJackpotRound(
                pool_key="global",
                round_number=1,
                status=GtexJackpotRoundStatus.SETTLED,
                distribution_mode=GtexJackpotDistributionMode.SINGLE_WINNER,
                threshold_amount=Decimal("50000.0000"),
                max_probability_limit=Decimal("100000.0000"),
                failsafe_at=now - timedelta(hours=2),
                settled_at=now - timedelta(hours=2),
            )
            s.add(past_round)
            s.flush()

            payout = GtexJackpotPayout(
                round_id=past_round.id,
                user_id=fan_user.id,
                rank=1,
                payout_amount=Decimal("50000.0000"),
                payout_ratio=Decimal("1.0000"),
                eligibility_weight=Decimal("1.0000"),
            )
            s.add(payout)

        live_round = s.scalar(select(GtexJackpotRound).where(GtexJackpotRound.pool_key == "global", GtexJackpotRound.round_number == 2))
        if not live_round:
            live_round = GtexJackpotRound(
                pool_key="global",
                round_number=2,
                status=GtexJackpotRoundStatus.OPEN,
                distribution_mode=GtexJackpotDistributionMode.SINGLE_WINNER,
                threshold_amount=Decimal("125000.0000"),
                max_probability_limit=Decimal("200000.0000"),
                failsafe_at=now + timedelta(hours=6),
            )
            s.add(live_round)
        s.commit()
        print("Jackpot live round and past winner seeded.")
    except Exception as e:
        s.rollback()
        print(f"Jackpot note: {e}")

    print("--- Step 9: Seeding Regen Universe Awards ---")
    season = s.scalar(select(RegenSeason).limit(1))
    if not season:
        season = RegenSeason(
            season_number=1,
            name="2026 Inaugural Season",
            status="active",
            starts_at=now - timedelta(days=60),
            ends_at=now + timedelta(days=30),
        )
        s.add(season)
        s.flush()

    award_specs = [
        ("gtex_best_player", "Regen Ballon d'Or", "World's most outstanding regen player of the year", "gtex_best_player", 1),
        ("gtex_golden_boy", "Golden Boy", "Top performing under-21 wonderkid", "gtex_golden_boy", 2),
        ("gtex_top_scorer", "Golden Boot", "Highest goal tally in all competitions", "gtex_top_scorer", 3),
        ("gtex_breakout_star", "Breakout Star of the Season", "Most improved prospect from youth intake", "gtex_breakout_star", 4),
    ]

    for code, name, desc, m_code, s_order in award_specs:
        aw = s.scalar(select(RegenAward).where(RegenAward.code == code))
        if not aw:
            aw = RegenAward(
                code=code,
                name=name,
                description=desc,
                category="seasonal",
                ranking_category="overall",
                is_regen_only=True,
                sort_order=s_order,
                metadata_json={"market_award_code": m_code, "market_award_name": name},
            )
            s.add(aw)
            s.flush()
        
        # Add a winner for each
        w = s.scalar(select(RegenAwardWinner).where(RegenAwardWinner.award_id == aw.id))
        if not w:
            w = RegenAwardWinner(
                award_id=aw.id,
                season_id=season.id,
                subject_key=f"regen_{code}_winner",
                player_name="Mateo Alvarez" if code == "gtex_golden_boy" else ("Kofi Mensah" if code == "gtex_best_player" else "Tariq Al-Mansoor"),
                ranking_score=94.5 if code == "gtex_best_player" else 89.2,
                rank=1,
                awarded_at=now - timedelta(days=2),
            )
            s.add(w)
    s.commit()
    print("Regen awards seeded.")

    print("--- Step 10: Seeding In-Progress Live Match with 2D Visualizer ---")
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from app.models.competition_round import CompetitionRound
    from app.match_engine.services.match_simulation_service import MatchSimulationService
    from app.services.match_timeline_service import MatchTimelineService
    from tests.match_engine.helpers import build_request, build_team
    from app.match_engine.simulation.models import TacticalStyle

    comp = s.scalar(select(UserCompetition).where(UserCompetition.id == "00000000-0000-0000-0000-000000000403"))
    if not comp:
        comp = UserCompetition(
            id="00000000-0000-0000-0000-000000000403",
            host_user_id=admin_user.id,
            name="Continental Prestige League",
            format="league",
            currency="coin",
            metadata_json={"source_type": "gtex_official"},
        )
        s.add(comp)
        s.flush()
    else:
        comp.host_user_id = admin_user.id

    round_1 = s.scalar(select(CompetitionRound).where(CompetitionRound.competition_id == comp.id, CompetitionRound.round_number == 1))
    if not round_1:
        round_1 = CompetitionRound(
            competition_id=comp.id,
            round_number=1,
            stage="league",
            name="Championship Matchday",
            status="in_progress",
        )
        s.add(round_1)
        s.flush()

    round_2 = s.scalar(select(CompetitionRound).where(CompetitionRound.competition_id == comp.id, CompetitionRound.round_number == 2))
    if not round_2:
        round_2 = CompetitionRound(
            competition_id=comp.id,
            round_number=2,
            stage="league",
            name="Prestige Clash",
            status="in_progress",
        )
        s.add(round_2)
        s.flush()

    # Generate full-fidelity replay simulation
    sim_req = build_request(
        seed=2026,
        match_id="fixture-final",
        home_team=build_team(valencia.id, "Valencia Crest CF", 85, style=TacticalStyle.ATTACKING),
        away_team=build_team(lagos_atlas.id if lagos_atlas else "away_001", "Lagos Atlas FC", 80, style=TacticalStyle.DEFENSIVE),
        is_final=True,
    )
    replay_payload = MatchSimulationService().build_replay_payload(sim_req)
    base_view = MatchTimelineService().build_from_replay_payload(replay_payload)
    viewer_payload = base_view.model_dump(mode="json")

    match_configs = [
        ("fixture-final", round_1, valencia.id, lagos_atlas.id if lagos_atlas else "away_001"),
        ("fixture-1", round_2, lagos_atlas.id if lagos_atlas else "away_001", valencia.id),
    ]
    for match_id, rnd, h_id, a_id in match_configs:
        meta = {
            "home_team_name": "Valencia Crest CF" if h_id == valencia.id else "Lagos Atlas FC",
            "away_team_name": "Lagos Atlas FC" if h_id == valencia.id else "Valencia Crest CF",
            "competition_name": "Continental Prestige League",
            "match_viewer": viewer_payload,
            "creator_name": "Valencia Crest CF",
            "host_name": "Seed Admin",
            "gift_source_scope": "gtex_competition",
            "current_score": {"home": 2, "away": 1},
            "minute": 68,
        }

        cm = s.scalar(select(CompetitionMatch).where(CompetitionMatch.id == match_id))
        if cm:
            cm.status = "in_progress"
            cm.home_score = 2
            cm.away_score = 1
            cm.metadata_json = meta
            cm.competition_id = comp.id
            cm.round_id = rnd.id
            cm.round_number = rnd.round_number
            cm.home_club_id = h_id
            cm.away_club_id = a_id
        else:
            cm = CompetitionMatch(
                id=match_id,
                competition_id=comp.id,
                round_id=rnd.id,
                round_number=rnd.round_number,
                stage="league",
                home_club_id=h_id,
                away_club_id=a_id,
                status="in_progress",
                home_score=2,
                away_score=1,
                metadata_json=meta,
            )
            s.add(cm)
    s.commit()
    print("In-progress matches fixture-final and fixture-1 created with full 2D pitch visualizer frames.")

print("=== ALL MASTER SEED STEPS COMPLETED SUCCESSFULLY ===")
