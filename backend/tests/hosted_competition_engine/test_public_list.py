from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_session
from app.hosted_competition_engine.router import router as hosted_router

import app.models.hosted_competition  # noqa: F401
import app.models.user  # noqa: F401


def test_public_hosted_competition_list_returns_empty_200(gtex_db_session) -> None:
    app = FastAPI()
    app.include_router(hosted_router)

    def override_session():
        yield gtex_db_session

    app.dependency_overrides[get_session] = override_session

    with TestClient(app) as client:
        response = client.get("/hosted-competitions")

    assert response.status_code == 200
    assert response.json() == {"competitions": []}
