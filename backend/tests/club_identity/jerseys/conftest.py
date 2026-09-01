from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.club_identity.jerseys.repository import InMemoryClubIdentityRepository
from app.club_identity.jerseys.router import (
    get_identity_service,
    require_club_identity_write_access,
    router,
)
from app.club_identity.jerseys.service import ClubIdentityService


@pytest.fixture
def identity_service() -> ClubIdentityService:
    return ClubIdentityService(InMemoryClubIdentityRepository())


@pytest.fixture
def client(identity_service: ClubIdentityService) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_identity_service] = lambda: identity_service
    # This fixture exercises the identity/jersey service in isolation (no DB,
    # no auth infra). The club-ownership authorization gate itself is covered
    # end-to-end by backend/tests/security/test_endpoint_authorization.py
    # against the real app + DB, so it is stubbed here to a passing actor
    # rather than bypassed by removing the dependency.
    app.dependency_overrides[require_club_identity_write_access] = lambda: None
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
