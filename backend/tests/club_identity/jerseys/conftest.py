from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user
from app.club_identity.jerseys.repository import InMemoryClubIdentityRepository
from app.club_identity.jerseys.router import (
    get_identity_service,
    require_club_identity_write_access,
    router,
)
from app.club_identity.jerseys.router import get_session as club_identity_get_session
from app.club_identity.jerseys.service import ClubIdentityService
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.user import KycStatus, User, UserRole

# Club ids the mutating-route tests in this package PATCH against. The router's
# ownership check (_require_club_editor) looks these up for real, so they need
# a real seeded ClubProfile row even though the identity/jersey data itself
# still comes from the in-memory repository below.
_OWNED_CLUB_IDS = ("oslo-orbit", "tokyo-tide")
_OWNER_USER_ID = "club-identity-test-owner"


@pytest.fixture
def identity_service() -> ClubIdentityService:
    return ClubIdentityService(InMemoryClubIdentityRepository())


@pytest.fixture
def client(identity_service: ClubIdentityService) -> TestClient:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[User.__table__, ClubProfile.__table__])
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with session_factory() as seed_session:
        owner = User(
            id=_OWNER_USER_ID,
            email="club-identity-owner@example.com",
            username="club_identity_owner",
            display_name="Club Identity Owner",
            password_hash="x",  # pragma: allowlist secret
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
        )
        seed_session.add(owner)
        for index, club_id in enumerate(_OWNED_CLUB_IDS):
            seed_session.add(
                ClubProfile(
                    id=club_id,
                    owner_user_id=owner.id,
                    club_name=club_id,
                    short_name=club_id[:8],
                    slug=f"{club_id}-{index}",
                    primary_color="#112233",
                    secondary_color="#445566",
                    accent_color="#778899",
                    country_code="NG",
                    region_name="Lagos",
                    city_name="Lagos",
                )
            )
        seed_session.commit()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_identity_service] = lambda: identity_service
    # This fixture exercises the identity/jersey service in isolation (the
    # identity/jersey data itself comes from an in-memory repository, not a
    # real service DB). It now also needs a real session for the router's
    # club-ownership check (_require_club_editor), and an authenticated actor
    # that owns the club ids used by these tests. The authorization gate
    # itself (rejecting a non-owner) is covered end-to-end by
    # backend/tests/security/test_endpoint_authorization.py against the real
    # app + DB, so it is stubbed here to a passing, owning actor rather than
    # bypassed by removing the dependency.
    app.dependency_overrides[club_identity_get_session] = lambda: session_factory()
    app.dependency_overrides[get_current_user] = lambda: User(
        id=_OWNER_USER_ID,
        email="club-identity-owner@example.com",
        username="club_identity_owner",
        display_name="Club Identity Owner",
        password_hash="x",  # pragma: allowlist secret
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    app.dependency_overrides[require_club_identity_write_access] = lambda: None
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()
