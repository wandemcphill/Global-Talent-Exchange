from __future__ import annotations

from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_admin, get_current_user
from app.models.access_control import (
    AccessAuditLog,
    Organization,
    OrganizationInvite,
    OrganizationMembership,
    PlayerOwnership,
)
from app.club_identity.models.reputation import ClubReputationProfile, ReputationEventLog, ReputationSnapshot
from app.db import get_session
from app.ingestion.models import Country, Player, PlayerImageMetadata, PlayerVerification
from app.models.base import Base
from app.models.club_branding_asset import ClubBrandingAsset
from app.models.club_cosmetic_catalog_item import ClubCosmeticCatalogItem
from app.models.club_cosmetic_purchase import ClubCosmeticPurchase
from app.models.club_dynasty_milestone import ClubDynastyMilestone
from app.models.club_dynasty_progress import ClubDynastyProgress
from app.models.club_identity_theme import ClubIdentityTheme
from app.models.club_infra import ClubFacility
from app.models.club_infra import ClubStadium, ClubSupporterHolding, ClubSupporterToken
from app.models.club_jersey_design import ClubJerseyDesign
from app.models.club_lifecycle import (
    ClubEligibilityFlag,
    ClubLifecycleAuditEvent,
    ClubLifecycleState,
    ClubOperatingStatus,
    ClubReadinessStatus,
    ClubRegistrationSlot,
    ClubSquadRegistration,
)
from app.models.club_growth import (
    AcademyGenerationRun,
    AcademyProfile,
    AcademyProspect,
    ClubGrowthAuditEvent,
    ClubStaffAssignment,
    ClubStaffContract,
    ClubStaffProfile,
)
from app.models.club_profile import ClubProfile
from app.models.player_contract import PlayerContract
from app.players.read_models import PlayerSummaryReadModel
from app.models.club_sale_market import (
    ClubSaleAuditEvent,
    ClubSaleInquiry,
    ClubSaleListing,
    ClubSaleOffer,
    ClubSaleTransfer,
    ClubValuationSnapshot,
)
from app.models.club_ranking_integrity import ClubRankingAbuseFlag, ClubRankingEvent, CompetitionIntegrityScore
from app.models.club_sponsorship_contract import ClubSponsorshipContract
from app.models.club_sponsorship_package import ClubSponsorshipPackage
from app.models.club_sponsorship_payout import ClubSponsorshipPayout
from app.models.player_cards import (
    PlayerCard,
    PlayerCardHolding,
    PlayerCardHistory,
    PlayerCardListing,
    PlayerCardOwnerHistory,
    PlayerCardSale,
    PlayerCardTier,
    PlayerMarketValueSnapshot,
)
from app.models.competition import Competition
from app.models.competition_entry import CompetitionEntry
from app.models.competition_match import CompetitionMatch
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_round import CompetitionRound
from app.models.player_career_entry import PlayerCareerEntry
from app.models.player_contract import PlayerContract
from app.models.player_lifecycle_event import PlayerLifecycleEvent
from app.models.player_token_market import PlayerShareMarket
from app.models.sponsorship_engine import SponsorshipLead
from app.models.transfer_market import (
    MarketWatchlistEntry,
    TransferHubOffer,
    TransferListing,
    TransferListingBid,
    TransferRequest,
)
from app.models.transfer_window import TransferWindow
from app.models.regen import (
    AcademyCandidate,
    AcademyIntakeBatch,
    RegenAward,
    RegenDemandSignal,
    RegenDiscoveryBadge,
    RegenGenerationEvent,
    RegenLineageProfile,
    RegenMarketActivity,
    RegenLegacyRecord,
    RegenOnboardingFlag,
    RegenOriginMetadata,
    RegenPersonalityProfile,
    RegenProfile,
    RegenRelationshipTag,
    RegenRecommendationItem,
    RegenScoutReport,
    RegenTransferFeeRule,
    RegenTwinsGroup,
    RegenValueSnapshot,
    RegenVisualProfile,
)
from app.models.scouting_intelligence import (
    AcademySupplySignal,
    HiddenPotentialEstimate,
    ManagerScoutingProfile,
    PlayerLifecycleProfile,
    ScoutMission,
    ScoutReport,
    ScoutingNetwork,
    ScoutingNetworkAssignment,
    TalentDiscoveryBadge,
)
from app.models.club_showcase_snapshot import ClubShowcaseSnapshot
from app.models.club_trophy import ClubTrophy
from app.models.club_trophy_cabinet import ClubTrophyCabinet
from app.models.user import KycStatus, User, UserRole
from app.models.wallet import LedgerAccount, LedgerBalanceProjection, LedgerEntry, LedgerTransaction
from app.routes.admin_clubs import router as admin_clubs_router
from app.routes.clubs import router as clubs_router


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    import app.models  # noqa: F401
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_local() as db_session:
        db_session.add_all(
            [
                User(
                    id="user-owner",
                    email="owner@example.com",
                    username="owner",
                    display_name="Owner",
                    password_hash="x",
                    role=UserRole.USER,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                ),
                User(
                    id="user-admin",
                    email="admin@example.com",
                    username="admin",
                    display_name="Admin",
                    password_hash="x",
                    role=UserRole.ADMIN,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                ),
                User(
                    id="user-other",
                    email="other@example.com",
                    username="other",
                    display_name="Other",
                    password_hash="x",
                    role=UserRole.USER,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                ),
            ]
        )
        db_session.commit()
        yield db_session
    engine.dispose()


@pytest.fixture()
def client(session: Session) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(clubs_router)
    app.include_router(admin_clubs_router)
    app.state.current_user_id = "user-owner"
    app.state.current_admin_id = "user-admin"
    app.state.session_factory = sessionmaker(
        bind=session.get_bind(),
        autoflush=False,
        expire_on_commit=False,
    )

    def override_session() -> Iterator[Session]:
        yield session

    def override_current_user() -> User:
        user = session.get(User, app.state.current_user_id)
        assert user is not None
        return user

    def override_current_admin() -> User:
        user = session.get(User, app.state.current_admin_id)
        assert user is not None
        return user

    app.dependency_overrides[get_session] = override_session
    from app.auth.dependencies import get_session as auth_get_session
    app.dependency_overrides[auth_get_session] = override_session
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_current_admin] = override_current_admin
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def create_club(client: TestClient):
    def _create_club(*, slug: str = "legacy-fc") -> dict[str, object]:
        response = client.post(
            "/api/clubs",
            json={
                "club_name": "Legacy FC",
                "short_name": "LFC",
                "slug": slug,
                "primary_color": "#112233",
                "secondary_color": "#445566",
                "accent_color": "#778899",
                "home_venue_name": "Legacy Park",
                "description": "Built for long-term club identity.",
                "visibility": "public",
            },
        )
        assert response.status_code == 201, response.text
        return response.json()["profile"]

    return _create_club
