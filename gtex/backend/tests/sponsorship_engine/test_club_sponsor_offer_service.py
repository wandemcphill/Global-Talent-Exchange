from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.club_identity.models.reputation  # noqa: F401
import app.ingestion.models  # noqa: F401
import app.models.club_profile  # noqa: F401
import app.models.club_sponsor  # noqa: F401
import app.models.club_sponsorship_contract  # noqa: F401
import app.models.club_infra  # noqa: F401
import app.models.competition_participant  # noqa: F401
import app.models.media_engine  # noqa: F401
from app.analytics.service import AnalyticsService
from app.club_identity.models.reputation import ClubReputationProfile
from app.core.config import get_settings
from app.ingestion.models import Player
from app.models.base import Base
from app.models.club_infra import ClubSupporterToken
from app.models.club_profile import ClubProfile
from app.models.competition_participant import CompetitionParticipant
from app.models.media_engine import MatchRevenueSnapshot
from app.models.user import User, UserRole
from app.services.sponsorship_placement_service import SponsorshipPlacementService
from app.sponsorship_engine.offer_service import ClubSponsorOfferService
from app.sponsorship_engine.schemas import (
    ClubSponsorAssignmentRequest,
    SponsorOfferCreateRequest,
    SponsorOfferRuleUpsertRequest,
)


def _session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine, SessionLocal


def _create_user(session, *, user_id: str, role: UserRole = UserRole.USER) -> User:
    user = User(id=user_id, email=f"{user_id}@example.com", username=user_id, password_hash="hashed", role=role)
    session.add(user)
    session.flush()
    return user


def _create_club(session, *, club_id: str, owner_user_id: str, name: str) -> ClubProfile:
    club = ClubProfile(
        id=club_id,
        owner_user_id=owner_user_id,
        club_name=name,
        short_name=name[:3].upper(),
        slug=name.lower().replace(" ", "-"),
        primary_color="#111111",
        secondary_color="#ffffff",
        accent_color="#ff9900",
        visibility="public",
    )
    session.add(club)
    session.flush()
    return club


def test_sponsor_metric_eligibility_and_assignment_flow() -> None:
    engine, SessionLocal = _session()
    with SessionLocal() as session:
        admin = _create_user(session, user_id="admin-sponsor", role=UserRole.ADMIN)
        owner = _create_user(session, user_id="club-owner")
        club = _create_club(session, club_id="club-1", owner_user_id=owner.id, name="Harbor City FC")

        session.add(
            ClubReputationProfile(
                club_id=club.id,
                current_score=550,
                highest_score=550,
                prestige_tier="Established",
                total_seasons=2,
            )
        )
        session.add(ClubSupporterToken(club_id=club.id, token_name="Harbor", token_symbol="HBR", holder_count=1800, circulating_supply=5000, influence_points=100))
        session.add(
            MatchRevenueSnapshot(
                match_key="match-1",
                competition_key="comp-1",
                home_club_id=club.id,
                away_club_id=None,
                total_views=25000,
                premium_purchases=10,
                total_revenue_coin=0,
                home_club_share_coin=0,
                away_club_share_coin=0,
                metadata_json={"rivalry_visibility": 24},
            )
        )
        session.add(CompetitionParticipant(competition_id="comp-1", club_id=club.id, status="joined"))
        session.add(
            Player(
                id="player-valuation",
                source_provider="test",
                provider_external_id="player-valuation",
                current_club_profile_id=club.id,
                full_name="Valuation Anchor",
                market_value_eur=2_400_000,
                is_tradable=True,
            )
        )
        session.flush()

        service = ClubSponsorOfferService(session=session, analytics=AnalyticsService())
        offer = service.create_offer(
            SponsorOfferCreateRequest(
                code="city-front",
                offer_name="City Front",
                sponsor_name="North Harbor Energy",
                category="front_of_kit",
                base_value_minor=500000,
                default_duration_months=4,
                approved_surfaces_json=["club_page", "stadium_board", "highlight_overlay"],
            )
        )
        service.upsert_offer_rule(
            offer_id=offer.id,
            payload=SponsorOfferRuleUpsertRequest(
                min_fan_count=1000,
                min_reputation_score=400,
                min_club_valuation=1_000_000,
                min_media_popularity=10_000,
                min_competition_count=1,
                min_rivalry_visibility=10,
                required_prestige_tier="Established",
                competition_allowlist_json=["comp-1"],
            ),
        )

        eligibility = service.list_eligible_offers(club_id=club.id)
        assert len(eligibility) == 1
        assert eligibility[0]["eligible"] is True
        assert eligibility[0]["unmet_rules"] == []

        sponsor = service.assign_offer_to_club(
            actor=admin,
            offer_id=offer.id,
            payload=ClubSponsorAssignmentRequest(club_id=club.id, start_at=datetime.now(UTC)),
        )
        assert sponsor.sponsor_name == "North Harbor Energy"
        assert sponsor.approved_surfaces_json == ["club_page", "stadium_board", "highlight_overlay"]

    engine.dispose()


def test_club_sponsor_assignments_drive_placement_resolution_and_analytics() -> None:
    engine, SessionLocal = _session()
    with SessionLocal() as session:
        admin = _create_user(session, user_id="admin-placement", role=UserRole.ADMIN)
        owner = _create_user(session, user_id="owner-placement")
        club = _create_club(session, club_id="club-placement", owner_user_id=owner.id, name="Docklands FC")
        session.add(ClubReputationProfile(club_id=club.id, current_score=300, highest_score=300, prestige_tier="Rising", total_seasons=1))
        session.add(ClubSupporterToken(club_id=club.id, token_name="Dock", token_symbol="DCK", holder_count=900, circulating_supply=2000, influence_points=40))
        session.flush()

        service = ClubSponsorOfferService(session=session, analytics=AnalyticsService())
        offer = service.create_offer(
            SponsorOfferCreateRequest(
                code="dock-banner",
                offer_name="Dock Banner",
                sponsor_name="Shipyard Group",
                category="stadium",
                base_value_minor=150000,
                default_duration_months=2,
                approved_surfaces_json=["club_page", "stadium_board"],
            )
        )
        service.assign_offer_to_club(
            actor=admin,
            offer_id=offer.id,
            payload=ClubSponsorAssignmentRequest(club_id=club.id, start_at=datetime.now(UTC)),
        )
        session.flush()

        placement_service = SponsorshipPlacementService(session=session, settings=get_settings(), analytics=AnalyticsService())
        placements = placement_service.resolve_placements(
            home_club_id=club.id,
            away_club_id=None,
            competition_id=None,
            stage_name=None,
            region_code=None,
            surfaces=("club_page", "stadium_board"),
        )
        assert [placement.sponsor_name for placement in placements] == ["Shipyard Group", "Shipyard Group"]
        assert all(placement.source == "club_sponsor" for placement in placements)

        analytics = service.sponsorship_analytics()
        assert analytics["assignment_count"] == 1
        assert analytics["render_event_count"] == 2
        assert analytics["placements_by_surface"]["club_page"] == 1
        assert analytics["placements_by_surface"]["stadium_board"] == 1

    engine.dispose()
