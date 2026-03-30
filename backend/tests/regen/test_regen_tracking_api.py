from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_session
from app.regen_universe.router import router as regen_universe_router
from tests.regen_universe_support import build_regen_universe_session


def test_regen_tracking_endpoint_returns_zero_state_payload() -> None:
    session = build_regen_universe_session()
    try:
        app = FastAPI()
        app.include_router(regen_universe_router)

        def override_session():
            yield session

        app.dependency_overrides[get_session] = override_session

        with TestClient(app) as client:
            response = client.get("/regen-universe/tracking")

        assert response.status_code == 200
        assert response.json() == {
            "total_seeded_players": 0,
            "seed_types": [],
            "rarity_breakdown": [],
            "country_distribution": [],
            "global_peak_rating": 0,
            "tracked_achievements": [],
        }
    finally:
        session.close()
