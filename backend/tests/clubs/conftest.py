from __future__ import annotations

from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.auth.dependencies import get_current_admin, get_current_user
from backend.app.club_identity.models.reputation import ClubReputationProfile, ReputationEventLog, ReputationSnapshot
from backend.app.db import get_session
from backend.app.ingestion.models import Country, Player, PlayerVerification
from backend.app.models.base import Base
from backend.app.models.club_branding_asset import ClubBrandingAsset
from backend.app.models.club_cosmetic_catalog_item import ClubCosmeticCatalogItem
from backend.app.models.club_cosmetic_purchase import ClubCosmeticPurchase
from backend.app.models.club_dynasty_milestone import ClubDynastyMilestone
from backend.app.models.club_dynasty_progress import ClubDynastyProgress
from backend.app.models.club_identity_theme import ClubIdentityTheme
from backend.app.models.club_infra import ClubFacility
from backend.app.models.club_jersey_design import ClubJerseyDesign
from backend.app.models.club_profile import ClubProfile
from backend.app.models.player_cards import (
    PlayerCard,
    PlayerCardHolding,
    PlayerCardHistory,
    PlayerCardListing,
    PlayerCardOwnerHistory,
    PlayerCardSale,
    PlayerCardTier,
)
from backend.app.models.player_career_entry import PlayerCareerEntry
from backend.app.models.player_contract import PlayerContract
from backend.app.models.player_lifecycle_event import PlayerLifecycleEvent
from backend.app.models.regen import (
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
from backend.app.models.scouting_intelligence import (
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
from backend.app.models.club_showcase_snapshot import ClubShowcaseSnapshot
from backend.app.models.club_trophy import ClubTrophy
from backend.app.models.club_trophy_cabinet import ClubTrophyCabinet
from backend.app.models.user import KycStatus, User, UserRole
from backend.app.routes.admin_clubs import router as admin_clubs_router
from backend.app.routes.clubs import router as clubs_router


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
            ClubFacility.__table__,
            ClubReputationProfile.__table__,
            ReputationEventLog.__table__,
            ReputationSnapshot.__table__,
            ClubTrophyCabinet.__table__,
            ClubTrophy.__table__,
            ClubDynastyProgress.__table__,
            ClubDynastyMilestone.__table__,
            ClubBrandingAsset.__table__,
            ClubJerseyDesign.__table__,
            ClubCosmeticCatalogItem.__table__,
            ClubCosmeticPurchase.__table__,
            ClubIdentityTheme.__table__,
            ClubShowcaseSnapshot.__table__,
            Country.__table__,
            Player.__table__,
            PlayerVerification.__table__,
            PlayerCardTier.__table__,
            PlayerCard.__table__,
            PlayerCardHistory.__table__,
            PlayerCardHolding.__table__,
            PlayerCardListing.__table__,
            PlayerCardOwnerHistory.__table__,
            PlayerCardSale.__table__,
            PlayerContract.__table__,
            PlayerCareerEntry.__table__,
            PlayerLifecycleEvent.__table__,
            AcademyIntakeBatch.__table__,
            AcademyCandidate.__table__,
            RegenAward.__table__,
            RegenValueSnapshot.__table__,
            RegenMarketActivity.__table__,
            RegenScoutReport.__table__,
            RegenRecommendationItem.__table__,
            RegenDemandSignal.__table__,
            RegenDiscoveryBadge.__table__,
            RegenOnboardingFlag.__table__,
            RegenTransferFeeRule.__table__,
            RegenProfile.__table__,
            RegenPersonalityProfile.__table__,
            RegenOriginMetadata.__table__,
            RegenGenerationEvent.__table__,
            RegenLineageProfile.__table__,
            RegenRelationshipTag.__table__,
            RegenLegacyRecord.__table__,
            RegenTwinsGroup.__table__,
            RegenVisualProfile.__table__,
            ManagerScoutingProfile.__table__,
            ScoutingNetwork.__table__,
            ScoutingNetworkAssignment.__table__,
            ScoutMission.__table__,
            ScoutReport.__table__,
            HiddenPotentialEstimate.__table__,
            AcademySupplySignal.__table__,
            PlayerLifecycleProfile.__table__,
            TalentDiscoveryBadge.__table__,
        ],
    )
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
