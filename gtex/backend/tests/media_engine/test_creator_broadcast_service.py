from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
import sys
import types

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

APP_ROOT = Path(__file__).resolve().parents[2] / "app"
PACKAGE_PATHS = {
    "backend.app": APP_ROOT,
    "backend.app.common": APP_ROOT / "common",
    "backend.app.common.enums": APP_ROOT / "common" / "enums",
    "backend.app.media_engine": APP_ROOT / "media_engine",
    "backend.app.models": APP_ROOT / "models",
    "backend.app.services": APP_ROOT / "services",
    "backend.app.wallets": APP_ROOT / "wallets",
}
for package_name, package_path in PACKAGE_PATHS.items():
    if package_name not in sys.modules:
        module = types.ModuleType(package_name)
        module.__path__ = [str(package_path)]
        sys.modules[package_name] = module

from app.admin_engine.schemas import AdminRewardRuleStabilityControls
from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.competition_start_mode import CompetitionStartMode
from app.common.enums.competition_status import CompetitionStatus
from app.common.enums.competition_visibility import CompetitionVisibility
from app.models.admin_rules import AdminRewardRule
from app.models.base import Base
from app.models.club_infra import ClubStadium
from app.models.club_profile import ClubProfile
from app.models.competition import Competition
from app.models.competition_match import CompetitionMatch
from app.models.competition_round import CompetitionRound
from app.models.creator_league import CreatorLeagueConfig, CreatorLeagueSeason, CreatorLeagueSeasonTier
from app.models.creator_monetization import (
    CreatorBroadcastModeConfig,
    CreatorBroadcastPurchase,
    CreatorMatchGiftEvent,
    CreatorRevenueSettlement,
    CreatorSeasonPass,
    CreatorStadiumControl,
    CreatorStadiumPlacement,
    CreatorStadiumPricing,
    CreatorStadiumProfile,
    CreatorStadiumTicketPurchase,
)
from app.models.creator_share_market import (
    CreatorClubShareDistribution,
    CreatorClubShareHolding,
    CreatorClubShareMarket,
    CreatorClubShareMarketControl,
    CreatorClubSharePayout,
    CreatorClubSharePurchase,
)
from app.models.creator_profile import CreatorProfile
from app.models.creator_provisioning import CreatorSquad
from app.models.media_engine import MatchView
from app.models.risk_ops import AuditLog
from app.models.spending_control import SpendingControlAuditEvent, SpendingControlDecision
from app.models.user import KycStatus, User, UserRole
from app.models.wallet import LedgerAccount, LedgerEntry, LedgerEntryReason, LedgerUnit
from app.services.creator_analytics_service import CreatorAnalyticsService
from app.services.creator_broadcast_service import CreatorBroadcastError, CreatorBroadcastService
from app.services.creator_revenue_service import CreatorRevenueService
from app.services.creator_share_market_service import CreatorClubShareMarketError, CreatorClubShareMarketService
from app.services.creator_stadium_service import (
    IN_STADIUM_AD,
    MATCHDAY_TICKET,
    SPONSOR_BANNER,
    VIP_TICKET,
    CreatorStadiumError,
    CreatorStadiumService,
)
from app.wallets.service import LedgerPosting, WalletService


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            AdminRewardRule.__table__,
            ClubStadium.__table__,
            ClubProfile.__table__,
            Competition.__table__,
            CompetitionRound.__table__,
            CompetitionMatch.__table__,
            CreatorLeagueConfig.__table__,
            CreatorLeagueSeason.__table__,
            CreatorLeagueSeasonTier.__table__,
            CreatorProfile.__table__,
            CreatorSquad.__table__,
            MatchView.__table__,
            CreatorBroadcastModeConfig.__table__,
            CreatorBroadcastPurchase.__table__,
            CreatorSeasonPass.__table__,
            CreatorMatchGiftEvent.__table__,
            CreatorStadiumControl.__table__,
            CreatorStadiumProfile.__table__,
            CreatorStadiumPricing.__table__,
            CreatorStadiumTicketPurchase.__table__,
            CreatorStadiumPlacement.__table__,
            CreatorRevenueSettlement.__table__,
            CreatorClubShareMarketControl.__table__,
            CreatorClubShareMarket.__table__,
            CreatorClubShareHolding.__table__,
            CreatorClubSharePurchase.__table__,
            CreatorClubShareDistribution.__table__,
            CreatorClubSharePayout.__table__,
            AuditLog.__table__,
            SpendingControlAuditEvent.__table__,
            LedgerAccount.__table__,
            LedgerEntry.__table__,
        ],
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = SessionLocal()
    seed_creator_broadcast_fixture(db)
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def seed_creator_broadcast_fixture(session: Session) -> None:
    users = [
        User(
            id="admin-user",
            email="admin@example.com",
            username="admin",
            full_name="Admin",
            display_name="Admin",
            password_hash="not-used",
            role=UserRole.ADMIN,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
        User(
            id="viewer-one",
            email="viewer1@example.com",
            username="viewer-one",
            full_name="Viewer One",
            display_name="Viewer One",
            password_hash="not-used",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
        User(
            id="viewer-two",
            email="viewer2@example.com",
            username="viewer-two",
            full_name="Viewer Two",
            display_name="Viewer Two",
            password_hash="not-used",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
        User(
            id="creator-home",
            email="creatorhome@example.com",
            username="creator-home",
            full_name="Creator Home",
            display_name="Creator Home",
            password_hash="not-used",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
        User(
            id="creator-away",
            email="creatoraway@example.com",
            username="creator-away",
            full_name="Creator Away",
            display_name="Creator Away",
            password_hash="not-used",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
    ]
    session.add_all(users)
    session.flush()

    session.add_all(
        [
            ClubProfile(
                id="club-home",
                owner_user_id="creator-home",
                club_name="Home Creators FC",
                short_name="HCF",
                slug="home-creators-fc",
                primary_color="#111111",
                secondary_color="#ffffff",
                accent_color="#ff6600",
                home_venue_name="Home Arena",
                country_code="NG",
                region_name="Lagos",
                city_name="Lagos",
                description="Home creator club",
                visibility="public",
            ),
            ClubProfile(
                id="club-away",
                owner_user_id="creator-away",
                club_name="Away Creators FC",
                short_name="ACF",
                slug="away-creators-fc",
                primary_color="#222222",
                secondary_color="#eeeeee",
                accent_color="#00aa88",
                home_venue_name="Away Arena",
                country_code="NG",
                region_name="Lagos",
                city_name="Lagos",
                description="Away creator club",
                visibility="public",
            ),
        ]
    )
    session.add_all(
        [
            CreatorProfile(
                id="profile-home",
                user_id="creator-home",
                handle="creator-home",
                display_name="Creator Home",
                tier="verified",
                default_competition_id="creator-comp",
                revenue_share_percent=Decimal("50.00"),
            ),
            CreatorProfile(
                id="profile-away",
                user_id="creator-away",
                handle="creator-away",
                display_name="Creator Away",
                tier="verified",
                default_competition_id="creator-comp",
                revenue_share_percent=Decimal("50.00"),
            ),
        ]
    )
    session.add_all(
        [
            CreatorSquad(
                id="squad-home",
                club_id="club-home",
                creator_profile_id="profile-home",
                metadata_json={},
            ),
            CreatorSquad(
                id="squad-away",
                club_id="club-away",
                creator_profile_id="profile-away",
                metadata_json={},
            ),
        ]
    )
    session.add(
        CreatorLeagueConfig(
            id="config-1",
            league_key="creator_league",
            enabled=True,
            seasons_paused=False,
            league_format="double_round_robin",
            default_club_count=20,
            match_frequency_days=7,
            season_duration_days=266,
            metadata_json={},
        )
    )
    session.add(
        CreatorLeagueSeason(
            id="season-1",
            config_id="config-1",
            season_number=1,
            name="Season One",
            status="live",
            start_date=date(2026, 1, 4),
            end_date=date(2026, 9, 27),
            match_frequency_days=7,
            season_duration_days=266,
            metadata_json={},
        )
    )
    session.add(
        CreatorLeagueSeasonTier(
            id="season-tier-1",
            season_id="season-1",
            tier_id="tier-1",
            competition_id="creator-comp",
            competition_name="Creator League Division 1",
            tier_name="Division 1",
            tier_order=1,
            club_ids_json=["club-home", "club-away"],
            round_count=38,
            fixture_count=380,
            status="live",
            banner_title="Division 1",
            banner_subtitle="Creator League",
            metadata_json={},
        )
    )
    session.add_all(
        [
            Competition(
                id="creator-comp",
                host_user_id="admin-user",
                name="Creator League Division 1",
                description="Creator League",
                competition_type="creator_league",
                source_type="creator_league",
                source_id="season-tier-1",
                format=CompetitionFormat.LEAGUE.value,
                visibility=CompetitionVisibility.PUBLIC.value,
                status=CompetitionStatus.LIVE.value,
                start_mode=CompetitionStartMode.SCHEDULED.value,
                stage="league",
                currency="coin",
                entry_fee_minor=0,
                platform_fee_bps=0,
                host_fee_bps=0,
                host_creation_fee_minor=0,
                gross_pool_minor=0,
                net_prize_pool_minor=0,
                metadata_json={"creator_league": True},
            ),
            Competition(
                id="champions-comp",
                host_user_id="admin-user",
                name="Champions League",
                description="Not creator league",
                competition_type="champions_league",
                source_type="champions_league",
                source_id="external-season",
                format=CompetitionFormat.LEAGUE.value,
                visibility=CompetitionVisibility.PUBLIC.value,
                status=CompetitionStatus.LIVE.value,
                start_mode=CompetitionStartMode.SCHEDULED.value,
                stage="league",
                currency="coin",
                entry_fee_minor=0,
                platform_fee_bps=0,
                host_fee_bps=0,
                host_creation_fee_minor=0,
                gross_pool_minor=0,
                net_prize_pool_minor=0,
                metadata_json={},
            ),
        ]
    )
    session.add_all(
        [
            CompetitionRound(
                id="round-creator",
                competition_id="creator-comp",
                round_number=1,
                stage="league",
                status="scheduled",
                metadata_json={},
            ),
            CompetitionRound(
                id="round-champions",
                competition_id="champions-comp",
                round_number=1,
                stage="league",
                status="scheduled",
                metadata_json={},
            ),
        ]
    )
    session.add_all(
        [
            CompetitionMatch(
                id="match-creator",
                competition_id="creator-comp",
                round_id="round-creator",
                round_number=1,
                stage="league",
                home_club_id="club-home",
                away_club_id="club-away",
                status="scheduled",
                metadata_json={},
            ),
            CompetitionMatch(
                id="match-champions",
                competition_id="champions-comp",
                round_id="round-champions",
                round_number=1,
                stage="league",
                home_club_id="club-home",
                away_club_id="club-away",
                status="scheduled",
                metadata_json={},
            ),
        ]
    )
    session.flush()

    wallet_service = WalletService()
    admin_user = session.get(User, "admin-user")
    for user_id in ("viewer-one", "viewer-two"):
        user = session.get(User, user_id)
        assert user is not None
        user_account = wallet_service.get_user_account(session, user, LedgerUnit.COIN)
        platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.COIN)
        wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=user_account, amount=Decimal("200.0000")),
                LedgerPosting(account=platform_account, amount=Decimal("-200.0000")),
            ],
            reason=LedgerEntryReason.DEPOSIT,
            reference=f"seed-funds:{user_id}",
            description=f"Seed funds for {user_id}",
            actor=admin_user,
        )
    session.commit()


def test_creator_broadcast_pricing_by_duration(session: Session) -> None:
    service = CreatorBroadcastService(session)
    viewer = session.get(User, "viewer-one")

    key_moments = service.quote_for_match(actor=viewer, match_id="match-creator", duration_minutes=12)
    extended = service.quote_for_match(actor=viewer, match_id="match-creator", duration_minutes=18)
    full_match = service.quote_for_match(actor=viewer, match_id="match-creator", duration_minutes=90)

    assert key_moments.mode.mode_key == "key_moments"
    assert key_moments.price_coin == Decimal("2.4000")
    assert extended.mode.mode_key == "extended"
    assert extended.price_coin == Decimal("4.0000")
    assert full_match.mode.mode_key == "full_match"
    assert full_match.price_coin == Decimal("12.0000")


def test_creator_season_pass_scope_enforcement(session: Session) -> None:
    service = CreatorBroadcastService(session)
    viewer = session.get(User, "viewer-one")

    season_pass = service.purchase_season_pass(actor=viewer, season_id="season-1", club_id="club-home")
    creator_match_access = service.access_for_match(actor=viewer, match_id="match-creator")

    assert season_pass.club_id == "club-home"
    assert creator_match_access.has_access is True
    assert creator_match_access.source == "season_pass"

    with pytest.raises(CreatorBroadcastError) as exc_info:
        service.access_for_match(actor=viewer, match_id="match-champions")

    assert exc_info.value.reason == "creator_league_only"


def test_creator_revenue_settlement_split(session: Session) -> None:
    broadcast_service = CreatorBroadcastService(session)
    revenue_service = CreatorRevenueService(session, broadcast_service=broadcast_service)
    viewer_one = session.get(User, "viewer-one")
    viewer_two = session.get(User, "viewer-two")

    purchase = broadcast_service.purchase_broadcast(
        actor=viewer_one,
        match_id="match-creator",
        duration_minutes=90,
    )
    assert purchase.price_coin == Decimal("12.0000")

    session.add_all(
        [
            MatchView(
                user_id="viewer-one",
                match_key="match-creator",
                competition_key="creator-comp",
                view_date_key="2026-03-16",
                watch_seconds=600,
                premium_unlocked=True,
                metadata_json={},
            ),
            MatchView(
                user_id="viewer-two",
                match_key="match-creator",
                competition_key="creator-comp",
                view_date_key="2026-03-16",
                watch_seconds=120,
                premium_unlocked=True,
                metadata_json={},
            ),
        ]
    )
    broadcast_service.send_match_gift(
        actor=viewer_two,
        match_id="match-creator",
        club_id="club-home",
        amount_coin=Decimal("10.0000"),
        gift_label="Mega Gift",
    )
    session.flush()

    settlement = revenue_service.build_match_settlement(match_id="match-creator")

    assert settlement.ticket_sales_gross_coin == Decimal("12.0000")
    assert settlement.ticket_sales_creator_share_coin == Decimal("6.0000")
    assert settlement.ticket_sales_platform_share_coin == Decimal("6.0000")
    assert settlement.video_viewer_revenue_coin == Decimal("0.1000")
    assert settlement.video_viewer_creator_share_coin == Decimal("0.0600")
    assert settlement.video_viewer_platform_share_coin == Decimal("0.0400")
    assert settlement.gift_revenue_gross_coin == Decimal("10.0000")
    assert settlement.gift_creator_share_coin == Decimal("7.0000")
    assert settlement.gift_platform_share_coin == Decimal("3.0000")
    assert settlement.home_creator_share_coin == Decimal("10.0300")
    assert settlement.away_creator_share_coin == Decimal("3.0300")
    assert settlement.total_creator_share_coin == Decimal("13.0600")
    assert settlement.total_platform_share_coin == Decimal("9.0400")
    assert settlement.total_revenue_coin == Decimal("22.1000")


def test_creator_match_gift_respects_spending_controls(session: Session) -> None:
    session.add(
        AdminRewardRule(
            rule_key="creator-gift-controls",
            title="Creator Gift Controls",
            description="Clamp creator match gift spikes.",
            trading_fee_bps=2000,
            gift_platform_rake_bps=3000,
            withdrawal_fee_bps=1000,
            minimum_withdrawal_fee_credits=Decimal("5.0000"),
            competition_platform_fee_bps=1000,
            stability_controls_json=AdminRewardRuleStabilityControls(
                creator_match_gift={
                    "max_amount": "5.0000",
                    "daily_sender_limit": "50.0000",
                    "daily_recipient_limit": "100.0000",
                    "daily_pair_limit": "20.0000",
                    "cooldown_seconds": 0,
                    "burst_window_seconds": 120,
                    "burst_max_count": 5,
                    "review_threshold_bps": 8000,
                }
            ).model_dump(mode="json"),
            active=True,
        )
    )
    session.commit()

    service = CreatorBroadcastService(session)
    viewer_two = session.get(User, "viewer-two")
    assert viewer_two is not None

    with pytest.raises(CreatorBroadcastError) as exc_info:
        service.send_match_gift(
            actor=viewer_two,
            match_id="match-creator",
            club_id="club-home",
            amount_coin=Decimal("10.0000"),
            gift_label="Mega Gift",
        )

    assert exc_info.value.reason == "spending_controls_blocked"
    audit = session.scalar(
        select(SpendingControlAuditEvent)
        .where(SpendingControlAuditEvent.decision == SpendingControlDecision.BLOCKED)
        .order_by(SpendingControlAuditEvent.created_at.desc())
    )
    assert audit is not None
    assert audit.control_scope == "creator_match_gift"
    assert audit.primary_reason_code == "max_amount_exceeded"


def test_creator_financial_policy_can_pause_broadcast_and_gifting(session: Session) -> None:
    service = CreatorBroadcastService(session)
    viewer = session.get(User, "viewer-one")
    config = session.get(CreatorLeagueConfig, "config-1")

    assert viewer is not None
    assert config is not None

    config.broadcast_purchases_enabled = False
    session.flush()
    with pytest.raises(CreatorBroadcastError) as broadcast_exc:
        service.purchase_broadcast(actor=viewer, match_id="match-creator", duration_minutes=18)

    assert broadcast_exc.value.reason == "broadcast_sales_disabled"

    config.broadcast_purchases_enabled = True
    config.match_gifting_enabled = False
    session.flush()

    with pytest.raises(CreatorBroadcastError) as gift_exc:
        service.send_match_gift(
            actor=viewer,
            match_id="match-creator",
            club_id="club-home",
            amount_coin=Decimal("5.0000"),
            gift_label="Paused Gift",
        )

    assert gift_exc.value.reason == "match_gifting_disabled"


def test_creator_viewer_purchase_controls_span_broadcast_and_stadium(session: Session) -> None:
    session.add(
        AdminRewardRule(
            rule_key="creator-viewer-controls",
            title="Creator Viewer Controls",
            description="Limit rapid repeat creator monetization purchases.",
            trading_fee_bps=2000,
            gift_platform_rake_bps=3000,
            withdrawal_fee_bps=1000,
            minimum_withdrawal_fee_credits=Decimal("5.0000"),
            competition_platform_fee_bps=1000,
            stability_controls_json=AdminRewardRuleStabilityControls(
                creator_viewer_purchase={
                    "max_amount": "100.0000",
                    "daily_user_limit": "200.0000",
                    "daily_user_count_limit": 1,
                    "burst_window_seconds": 900,
                    "burst_max_count": 2,
                    "duplicate_window_seconds": 900,
                    "review_threshold_bps": 8000,
                }
            ).model_dump(mode="json"),
            active=True,
        )
    )
    session.commit()

    broadcast_service = CreatorBroadcastService(session)
    stadium_service = CreatorStadiumService(session)
    creator = session.get(User, "creator-home")
    viewer = session.get(User, "viewer-one")
    assert creator is not None
    assert viewer is not None

    stadium_service.configure_club_stadium(
        actor=creator,
        club_id="club-home",
        season_id="season-1",
        matchday_ticket_price_coin=Decimal("12.0000"),
        season_pass_price_coin=Decimal("88.0000"),
        vip_ticket_price_coin=Decimal("24.0000"),
        visual_upgrade_level=1,
        custom_chant_text="Home roar",
        custom_visuals_json={"banner": "flames"},
    )

    purchase = broadcast_service.purchase_broadcast(
        actor=viewer,
        match_id="match-creator",
        duration_minutes=12,
    )
    session.commit()

    with pytest.raises(CreatorStadiumError) as exc_info:
        stadium_service.purchase_match_ticket(
            actor=viewer,
            match_id="match-creator",
            ticket_type=MATCHDAY_TICKET,
        )

    assert exc_info.value.reason == "spending_controls_blocked"
    review_audit = session.scalar(
        select(SpendingControlAuditEvent)
        .where(SpendingControlAuditEvent.entity_id == purchase.id)
        .order_by(SpendingControlAuditEvent.created_at.asc())
    )
    assert review_audit is not None
    assert review_audit.control_scope == "creator_viewer_purchase"
    assert review_audit.decision == SpendingControlDecision.REVIEW
    assert review_audit.primary_reason_code == "daily_user_count_limit_near"

    blocked_audit = session.scalar(
        select(SpendingControlAuditEvent)
        .where(
            SpendingControlAuditEvent.control_scope == "creator_viewer_purchase",
            SpendingControlAuditEvent.decision == SpendingControlDecision.BLOCKED,
        )
        .order_by(SpendingControlAuditEvent.created_at.desc())
    )
    assert blocked_audit is not None
    assert blocked_audit.primary_reason_code == "daily_user_count_limit_exceeded"


def test_creator_analytics_aggregation(session: Session) -> None:
    broadcast_service = CreatorBroadcastService(session)
    analytics_service = CreatorAnalyticsService(session, broadcast_service=broadcast_service)
    viewer_one = session.get(User, "viewer-one")
    viewer_two = session.get(User, "viewer-two")
    creator_home = session.get(User, "creator-home")

    broadcast_service.purchase_broadcast(actor=viewer_one, match_id="match-creator", duration_minutes=18)
    session.add_all(
        [
            MatchView(
                user_id="viewer-one",
                match_key="match-creator",
                competition_key="creator-comp",
                view_date_key="2026-03-17",
                watch_seconds=600,
                premium_unlocked=True,
                metadata_json={},
            ),
            MatchView(
                user_id="viewer-two",
                match_key="match-creator",
                competition_key="creator-comp",
                view_date_key="2026-03-17",
                watch_seconds=120,
                premium_unlocked=True,
                metadata_json={},
            ),
        ]
    )
    broadcast_service.send_match_gift(
        actor=viewer_two,
        match_id="match-creator",
        club_id="club-home",
        amount_coin=Decimal("10.0000"),
        gift_label="Mega Gift",
    )
    broadcast_service.send_match_gift(
        actor=viewer_one,
        match_id="match-creator",
        club_id="club-home",
        amount_coin=Decimal("5.0000"),
        gift_label="Support Gift",
    )
    session.flush()

    dashboard = analytics_service.build_match_dashboard(
        actor=creator_home,
        match_id="match-creator",
    )

    assert dashboard.club_id == "club-home"
    assert dashboard.total_viewers == 2
    assert dashboard.video_viewers == 2
    assert dashboard.gift_totals_coin == Decimal("15.0000")
    assert dashboard.top_gifters[0].user_id == "viewer-two"
    assert dashboard.top_gifters[0].total_gift_coin == Decimal("10.0000")
    assert dashboard.fan_engagement_pct == Decimal("100.0000")
    assert dashboard.engaged_fans == 2
    assert dashboard.total_watch_seconds == 720


def test_creator_stadium_controls_enforce_ticket_toggle_and_placement_cap(session: Session) -> None:
    stadium_service = CreatorStadiumService(session)
    admin = session.get(User, "admin-user")
    creator = session.get(User, "creator-home")
    viewer = session.get(User, "viewer-one")

    assert admin is not None
    assert creator is not None
    assert viewer is not None

    stadium_service.update_admin_control(
        actor=admin,
        max_matchday_ticket_price_coin=Decimal("25.0000"),
        max_season_pass_price_coin=Decimal("120.0000"),
        max_vip_ticket_price_coin=Decimal("60.0000"),
        max_stadium_level=5,
        vip_seat_ratio_bps=500,
        max_in_stadium_ad_slots=4,
        max_sponsor_banner_slots=4,
        ad_placement_enabled=True,
        ticket_sales_enabled=False,
        max_placement_price_coin=Decimal("5.0000"),
    )
    stadium_service.configure_club_stadium(
        actor=creator,
        club_id="club-home",
        season_id="season-1",
        matchday_ticket_price_coin=Decimal("12.0000"),
        season_pass_price_coin=Decimal("88.0000"),
        vip_ticket_price_coin=Decimal("24.0000"),
        visual_upgrade_level=1,
        custom_chant_text="Home roar",
        custom_visuals_json={"banner": "flames"},
    )

    with pytest.raises(CreatorStadiumError) as ticket_exc:
        stadium_service.purchase_match_ticket(actor=viewer, match_id="match-creator", ticket_type=MATCHDAY_TICKET)

    assert ticket_exc.value.reason == "ticket_sales_disabled"

    stadium_service.update_admin_control(
        actor=admin,
        max_matchday_ticket_price_coin=Decimal("25.0000"),
        max_season_pass_price_coin=Decimal("120.0000"),
        max_vip_ticket_price_coin=Decimal("60.0000"),
        max_stadium_level=5,
        vip_seat_ratio_bps=500,
        max_in_stadium_ad_slots=4,
        max_sponsor_banner_slots=4,
        ad_placement_enabled=True,
        ticket_sales_enabled=True,
        max_placement_price_coin=Decimal("5.0000"),
    )

    with pytest.raises(CreatorStadiumError) as placement_exc:
        stadium_service.create_match_placement(
            actor=creator,
            match_id="match-creator",
            placement_type=IN_STADIUM_AD,
            slot_key="north-board-cap",
            sponsor_name="Cap Corp",
            price_coin=Decimal("6.0000"),
        )

    assert placement_exc.value.reason == "placement_price_cap_exceeded"


def test_creator_stadium_pricing_respects_admin_caps(session: Session) -> None:
    service = CreatorStadiumService(session)
    admin = session.get(User, "admin-user")
    creator = session.get(User, "creator-home")

    service.update_admin_control(
        actor=admin,
        max_matchday_ticket_price_coin=Decimal("10.0000"),
        max_season_pass_price_coin=Decimal("50.0000"),
        max_vip_ticket_price_coin=Decimal("20.0000"),
        max_stadium_level=5,
        vip_seat_ratio_bps=500,
        max_in_stadium_ad_slots=4,
        max_sponsor_banner_slots=4,
        ad_placement_enabled=True,
    )

    with pytest.raises(CreatorStadiumError) as exc_info:
        service.configure_club_stadium(
            actor=creator,
            club_id="club-home",
            season_id="season-1",
            matchday_ticket_price_coin=Decimal("11.0000"),
            season_pass_price_coin=Decimal("45.0000"),
            vip_ticket_price_coin=Decimal("18.0000"),
            visual_upgrade_level=1,
            custom_chant_text="Home roar",
            custom_visuals_json={"banner": "flames"},
        )

    assert exc_info.value.reason == "ticket_price_cap_exceeded"


def test_creator_share_market_control_caps_primary_purchase_value(session: Session) -> None:
    share_service = CreatorClubShareMarketService(session)
    admin = session.get(User, "admin-user")
    creator = session.get(User, "creator-home")
    viewer = session.get(User, "viewer-two")

    assert admin is not None
    assert creator is not None
    assert viewer is not None

    share_service.update_admin_control(
        actor=admin,
        max_shares_per_club=100,
        max_shares_per_fan=10,
        shareholder_revenue_share_bps=2000,
        issuance_enabled=True,
        purchase_enabled=True,
        max_primary_purchase_value_coin=Decimal("9.0000"),
    )
    share_service.issue_market(
        actor=creator,
        club_id="club-home",
        share_price_coin=Decimal("5.0000"),
        max_shares_issued=10,
        max_shares_per_fan=5,
        metadata_json={},
    )

    with pytest.raises(CreatorClubShareMarketError) as exc_info:
        share_service.purchase_shares(actor=viewer, club_id="club-home", share_count=2)

    assert exc_info.value.reason == "share_purchase_value_cap_exceeded"


def test_creator_stadium_config_overrides_season_pass_price(session: Session) -> None:
    stadium_service = CreatorStadiumService(session)
    broadcast_service = CreatorBroadcastService(session)
    creator = session.get(User, "creator-home")
    viewer = session.get(User, "viewer-one")

    stadium_service.configure_club_stadium(
        actor=creator,
        club_id="club-home",
        season_id="season-1",
        matchday_ticket_price_coin=Decimal("12.0000"),
        season_pass_price_coin=Decimal("88.0000"),
        vip_ticket_price_coin=Decimal("24.0000"),
        visual_upgrade_level=1,
        custom_chant_text="Home roar",
        custom_visuals_json={"banner": "flames"},
    )

    season_pass = broadcast_service.purchase_season_pass(actor=viewer, season_id="season-1", club_id="club-home")

    assert season_pass.price_coin == Decimal("88.0000")
    assert season_pass.creator_share_coin == Decimal("44.0000")
    assert season_pass.platform_share_coin == Decimal("44.0000")


def test_creator_stadium_ticket_access_and_vip_rules(session: Session) -> None:
    stadium_service = CreatorStadiumService(session)
    broadcast_service = CreatorBroadcastService(session)
    admin = session.get(User, "admin-user")
    creator = session.get(User, "creator-home")
    viewer_one = session.get(User, "viewer-one")
    viewer_two = session.get(User, "viewer-two")

    stadium_service.update_admin_control(
        actor=admin,
        max_matchday_ticket_price_coin=Decimal("25.0000"),
        max_season_pass_price_coin=Decimal("120.0000"),
        max_vip_ticket_price_coin=Decimal("60.0000"),
        max_stadium_level=5,
        vip_seat_ratio_bps=2,
        max_in_stadium_ad_slots=4,
        max_sponsor_banner_slots=4,
        ad_placement_enabled=True,
    )
    stadium_service.configure_club_stadium(
        actor=creator,
        club_id="club-home",
        season_id="season-1",
        matchday_ticket_price_coin=Decimal("12.0000"),
        season_pass_price_coin=Decimal("88.0000"),
        vip_ticket_price_coin=Decimal("24.0000"),
        visual_upgrade_level=1,
        custom_chant_text="Home roar",
        custom_visuals_json={"banner": "flames"},
    )

    vip_ticket = stadium_service.purchase_match_ticket(actor=viewer_one, match_id="match-creator", ticket_type=VIP_TICKET)
    access = broadcast_service.access_for_match(actor=viewer_one, match_id="match-creator")

    assert vip_ticket.includes_premium_seating is True
    assert vip_ticket.seat_tier == "premium"
    assert access.source == "stadium_ticket"
    assert access.stadium_ticket is not None
    assert access.stadium_ticket.ticket_type == VIP_TICKET

    with pytest.raises(CreatorStadiumError) as exc_info:
        stadium_service.purchase_match_ticket(actor=viewer_two, match_id="match-creator", ticket_type=VIP_TICKET)

    assert exc_info.value.reason == "vip_seating_sold_out"

    matchday_ticket = stadium_service.purchase_match_ticket(
        actor=viewer_two,
        match_id="match-creator",
        ticket_type=MATCHDAY_TICKET,
    )
    assert matchday_ticket.includes_premium_seating is False
    assert matchday_ticket.seat_tier == "general"

    with pytest.raises(CreatorBroadcastError) as access_exc:
        broadcast_service.purchase_broadcast(actor=viewer_one, match_id="match-creator", duration_minutes=90)

    assert access_exc.value.reason == "stadium_ticket_already_grants_access"


def test_creator_shareholder_distributions_flow_into_match_settlement(session: Session) -> None:
    share_service = CreatorClubShareMarketService(session)
    broadcast_service = CreatorBroadcastService(session)
    revenue_service = CreatorRevenueService(session, broadcast_service=broadcast_service)
    creator = session.get(User, "creator-home")
    viewer_one = session.get(User, "viewer-one")
    viewer_two = session.get(User, "viewer-two")

    share_service.issue_market(
        actor=creator,
        club_id="club-home",
        share_price_coin=Decimal("5.0000"),
        max_shares_issued=10,
        max_shares_per_fan=5,
        metadata_json={"season_scope": "season-1"},
    )
    share_service.purchase_shares(actor=viewer_two, club_id="club-home", share_count=2)

    broadcast_service.purchase_broadcast(actor=viewer_one, match_id="match-creator", duration_minutes=90)
    broadcast_service.send_match_gift(
        actor=viewer_one,
        match_id="match-creator",
        club_id="club-home",
        amount_coin=Decimal("20.0000"),
        gift_label="Mega Gift",
    )

    settlement = revenue_service.build_match_settlement(match_id="match-creator")
    holding = share_service.get_holding(club_id="club-home", user_id="viewer-two")

    assert holding is not None
    assert holding.revenue_earned_coin == Decimal("3.4000")
    assert settlement.shareholder_match_video_distribution_coin == Decimal("0.6000")
    assert settlement.shareholder_gift_distribution_coin == Decimal("2.8000")
    assert settlement.shareholder_ticket_sales_distribution_coin == Decimal("0.0000")
    assert settlement.shareholder_total_distribution_coin == Decimal("3.4000")


def test_creator_shareholders_receive_early_ticket_access(session: Session) -> None:
    share_service = CreatorClubShareMarketService(session)
    stadium_service = CreatorStadiumService(session)
    creator = session.get(User, "creator-home")
    viewer_one = session.get(User, "viewer-one")
    viewer_two = session.get(User, "viewer-two")
    match = session.get(CompetitionMatch, "match-creator")

    assert match is not None
    match.scheduled_at = datetime(2026, 3, 20, 18, 0, tzinfo=UTC)

    share_service.issue_market(
        actor=creator,
        club_id="club-home",
        share_price_coin=Decimal("5.0000"),
        max_shares_issued=10,
        max_shares_per_fan=5,
        metadata_json={},
    )
    share_service.purchase_shares(actor=viewer_two, club_id="club-home", share_count=1)

    stadium_service.configure_club_stadium(
        actor=creator,
        club_id="club-home",
        season_id="season-1",
        matchday_ticket_price_coin=Decimal("12.0000"),
        season_pass_price_coin=Decimal("88.0000"),
        vip_ticket_price_coin=Decimal("24.0000"),
        visual_upgrade_level=1,
        custom_chant_text="Home roar",
        custom_visuals_json={"banner": "flames"},
    )

    early_window = datetime(2026, 3, 19, 6, 0, tzinfo=UTC)
    with pytest.raises(CreatorStadiumError) as exc_info:
        stadium_service.purchase_match_ticket(
            actor=viewer_one,
            match_id="match-creator",
            ticket_type=MATCHDAY_TICKET,
            now=early_window,
        )

    assert exc_info.value.reason == "shareholder_early_access_required"

    early_ticket = stadium_service.purchase_match_ticket(
        actor=viewer_two,
        match_id="match-creator",
        ticket_type=MATCHDAY_TICKET,
        now=early_window,
    )

    assert early_ticket.metadata_json["ticket_access_phase"] == "shareholder_early"


def test_creator_settlement_flags_review_threshold_breaches(session: Session) -> None:
    broadcast_service = CreatorBroadcastService(session)
    revenue_service = CreatorRevenueService(session, broadcast_service=broadcast_service)
    config = session.get(CreatorLeagueConfig, "config-1")
    viewer = session.get(User, "viewer-one")

    assert config is not None
    assert viewer is not None

    config.settlement_review_total_revenue_coin = Decimal("10.0000")
    config.settlement_review_creator_share_coin = Decimal("5.0000")
    config.settlement_review_platform_share_coin = Decimal("5.0000")
    config.settlement_review_shareholder_distribution_coin = Decimal("1.0000")
    session.flush()

    broadcast_service.purchase_broadcast(actor=viewer, match_id="match-creator", duration_minutes=90)
    settlement = revenue_service.build_match_settlement(match_id="match-creator")

    assert settlement.review_status == "review_required"
    assert "total_revenue_threshold_exceeded" in settlement.review_reason_codes_json
    assert "creator_share_threshold_exceeded" in settlement.review_reason_codes_json
    assert "platform_share_threshold_exceeded" in settlement.review_reason_codes_json


def test_creator_stadium_revenue_settlement_includes_ads_and_banners(session: Session) -> None:
    stadium_service = CreatorStadiumService(session)
    revenue_service = CreatorRevenueService(session)
    creator = session.get(User, "creator-home")
    viewer_one = session.get(User, "viewer-one")
    viewer_two = session.get(User, "viewer-two")

    stadium_service.configure_club_stadium(
        actor=creator,
        club_id="club-home",
        season_id="season-1",
        matchday_ticket_price_coin=Decimal("12.0000"),
        season_pass_price_coin=Decimal("88.0000"),
        vip_ticket_price_coin=Decimal("24.0000"),
        visual_upgrade_level=1,
        custom_chant_text="Home roar",
        custom_visuals_json={"banner": "flames"},
    )

    stadium_service.purchase_match_ticket(actor=viewer_one, match_id="match-creator", ticket_type=MATCHDAY_TICKET)
    stadium_service.purchase_match_ticket(actor=viewer_two, match_id="match-creator", ticket_type=VIP_TICKET)
    stadium_service.create_match_placement(
        actor=creator,
        match_id="match-creator",
        placement_type=IN_STADIUM_AD,
        slot_key="north-board-1",
        sponsor_name="BoardCorp",
        price_coin=Decimal("8.0000"),
        creative_asset_url="https://example.com/board.png",
    )
    stadium_service.create_match_placement(
        actor=creator,
        match_id="match-creator",
        placement_type=SPONSOR_BANNER,
        slot_key="south-banner-1",
        sponsor_name="BannerCorp",
        price_coin=Decimal("6.0000"),
        creative_asset_url="https://example.com/banner.png",
    )

    settlement = revenue_service.build_match_settlement(match_id="match-creator")

    assert settlement.ticket_sales_gross_coin == Decimal("36.0000")
    assert settlement.ticket_sales_creator_share_coin == Decimal("18.0000")
    assert settlement.ticket_sales_platform_share_coin == Decimal("18.0000")
    assert settlement.stadium_matchday_revenue_coin == Decimal("12.0000")
    assert settlement.stadium_matchday_creator_share_coin == Decimal("6.0000")
    assert settlement.stadium_matchday_platform_share_coin == Decimal("6.0000")
    assert settlement.premium_seating_revenue_coin == Decimal("24.0000")
    assert settlement.premium_seating_creator_share_coin == Decimal("12.0000")
    assert settlement.premium_seating_platform_share_coin == Decimal("12.0000")
    assert settlement.in_stadium_ads_revenue_coin == Decimal("8.0000")
    assert settlement.in_stadium_ads_creator_share_coin == Decimal("4.0000")
    assert settlement.in_stadium_ads_platform_share_coin == Decimal("4.0000")
    assert settlement.sponsor_banner_revenue_coin == Decimal("6.0000")
    assert settlement.sponsor_banner_creator_share_coin == Decimal("3.0000")
    assert settlement.sponsor_banner_platform_share_coin == Decimal("3.0000")
    assert settlement.total_revenue_coin == Decimal("50.0000")
    assert settlement.total_creator_share_coin == Decimal("25.0000")
    assert settlement.total_platform_share_coin == Decimal("25.0000")
    assert settlement.home_creator_share_coin == Decimal("25.0000")
    assert settlement.away_creator_share_coin == Decimal("0.0000")
