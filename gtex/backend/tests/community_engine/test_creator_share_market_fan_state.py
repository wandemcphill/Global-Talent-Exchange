from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.club_infra import ClubSupporterHolding
from app.models.club_profile import ClubProfile
from app.models.competition import Competition
from app.models.competition_match import CompetitionMatch
from app.models.competition_round import CompetitionRound
from app.models.creator_fan_engagement import (
    CreatorClubFollow,
    CreatorFanCompetition,
    CreatorFanCompetitionEntry,
    CreatorFanGroup,
    CreatorFanGroupMembership,
)
from app.models.creator_league import CreatorLeagueConfig, CreatorLeagueSeason, CreatorLeagueSeasonTier
from app.models.creator_monetization import CreatorBroadcastPurchase, CreatorMatchGiftEvent, CreatorSeasonPass
from app.models.creator_profile import CreatorProfile
from app.models.creator_provisioning import CreatorSquad
from app.models.creator_share_market import (
    CreatorClubShareHolding,
    CreatorClubShareMarket,
    CreatorClubShareMarketControl,
)
from app.models.media_engine import PremiumVideoPurchase
from app.models.user import KycStatus, User, UserRole
from app.services.creator_fan_engagement_service import CreatorFanEngagementService


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
            ClubProfile.__table__,
            ClubSupporterHolding.__table__,
            Competition.__table__,
            CompetitionRound.__table__,
            CompetitionMatch.__table__,
            CreatorLeagueConfig.__table__,
            CreatorLeagueSeason.__table__,
            CreatorLeagueSeasonTier.__table__,
            CreatorProfile.__table__,
            CreatorSquad.__table__,
            CreatorBroadcastPurchase.__table__,
            CreatorSeasonPass.__table__,
            CreatorMatchGiftEvent.__table__,
            CreatorClubFollow.__table__,
            CreatorFanGroup.__table__,
            CreatorFanGroupMembership.__table__,
            CreatorFanCompetition.__table__,
            CreatorFanCompetitionEntry.__table__,
            PremiumVideoPurchase.__table__,
            CreatorClubShareMarketControl.__table__,
            CreatorClubShareMarket.__table__,
            CreatorClubShareHolding.__table__,
        ],
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def test_creator_shareholders_boost_fan_visibility_priority(session: Session) -> None:
    session.add_all(
            [
                User(
                    id="creator-home",
                    email="creatorhome@example.com",
                    username="creator-home",
                    full_name="Creator Home",
                    display_name="Creator Home",
                    password_hash="x",
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
                    password_hash="x",
                    role=UserRole.USER,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                    is_active=True,
                ),
                User(
                    id="fan-user",
                    email="fan@example.com",
                    username="fan-user",
                    full_name="Fan User",
                    display_name="Fan User",
                    password_hash="x",
                    role=UserRole.USER,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                    is_active=True,
                ),
            ]
        )
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
                CreatorProfile(id="profile-home", user_id="creator-home", handle="creator-home", display_name="Creator Home", status="active"),
                CreatorProfile(id="profile-away", user_id="creator-away", handle="creator-away", display_name="Creator Away", status="active"),
                CreatorSquad(id="squad-home", club_id="club-home", creator_profile_id="profile-home", metadata_json={}),
                CreatorSquad(id="squad-away", club_id="club-away", creator_profile_id="profile-away", metadata_json={}),
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
                start_date=date(2026, 1, 1),
                end_date=date(2026, 9, 30),
                match_frequency_days=7,
                season_duration_days=266,
                metadata_json={},
            )
        )
    session.add(
            CreatorLeagueSeasonTier(
                id="tier-1",
                season_id="season-1",
                tier_id="division-1",
                competition_id="creator-comp",
                competition_name="Creator League",
                tier_name="Division 1",
                tier_order=1,
                club_ids_json=["club-home", "club-away"],
                round_count=38,
                fixture_count=380,
                status="live",
                metadata_json={},
            )
        )
    session.add(
            Competition(
                id="creator-comp",
                host_user_id="creator-home",
                name="Creator League",
                competition_type="creator_league",
                source_type="creator_league",
                source_id="tier-1",
                format="league",
                visibility="public",
                status="live",
                start_mode="scheduled",
                stage="league",
                currency="coin",
                metadata_json={"creator_league": True},
            )
        )
    session.add(
            CompetitionRound(
                id="round-1",
                competition_id="creator-comp",
                round_number=1,
                stage="league",
                status="scheduled",
                metadata_json={},
            )
        )
    session.add(
            CompetitionMatch(
                id="match-1",
                competition_id="creator-comp",
                round_id="round-1",
                round_number=1,
                stage="league",
                home_club_id="club-home",
                away_club_id="club-away",
                status="scheduled",
                metadata_json={},
            )
        )
    session.add(
            CreatorBroadcastPurchase(
                id="purchase-1",
                user_id="fan-user",
                season_id="season-1",
                competition_id="creator-comp",
                match_id="match-1",
                mode_key="extended",
                duration_minutes=18,
                price_coin=Decimal("4.0000"),
                platform_share_coin=Decimal("2.0000"),
                home_creator_share_coin=Decimal("1.0000"),
                away_creator_share_coin=Decimal("1.0000"),
                metadata_json={},
            )
        )
    session.add(
            CreatorClubShareMarketControl(
                id="share-control",
                control_key="default",
                max_shares_per_club=100,
                max_shares_per_fan=10,
                shareholder_revenue_share_bps=2000,
                metadata_json={},
            )
        )
    session.add(
            CreatorClubShareMarket(
                id="share-market",
                club_id="club-home",
                creator_user_id="creator-home",
                issued_by_user_id="creator-home",
                status="active",
                share_price_coin=Decimal("5.0000"),
                max_shares_issued=20,
                shares_sold=2,
                max_shares_per_fan=5,
                creator_controlled_shares=21,
                shareholder_revenue_share_bps=2000,
                metadata_json={},
            )
        )
    session.add(
            CreatorClubShareHolding(
                id="share-holding",
                market_id="share-market",
                club_id="club-home",
                user_id="fan-user",
                share_count=2,
                total_spent_coin=Decimal("10.0000"),
                revenue_earned_coin=Decimal("0.0000"),
                metadata_json={},
            )
        )
    session.commit()

    service = CreatorFanEngagementService(session)
    actor = session.get(User, "fan-user")

    payload = service.get_fan_state(actor=actor, club_id="club-home", match_id="match-1")

    assert payload["shareholder"] is True
    assert payload["creator_shareholder"] is True
    assert payload["creator_share_balance"] == 2
    assert payload["has_cosmetic_voting_rights"] is True
    assert payload["cosmetic_vote_power"] == 2
    assert payload["paying_viewer"] is True
    assert payload["visibility_priority"] == 200
