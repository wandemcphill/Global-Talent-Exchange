from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.club_identity.jerseys.repository import InMemoryClubIdentityRepository
from app.club_identity.jerseys.router import get_identity_service, router
from app.club_identity.jerseys.service import ClubIdentityService


@pytest.fixture
def identity_service() -> ClubIdentityService:
    return ClubIdentityService(InMemoryClubIdentityRepository())


@pytest.fixture
def client(identity_service: ClubIdentityService) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_identity_service] = lambda: identity_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
