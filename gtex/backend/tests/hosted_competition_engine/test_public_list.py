from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_session
from app.hosted_competition_engine.router import router as hosted_router
from app.models.base import Base

import app.models.hosted_competition  # noqa: F401
import app.models.user  # noqa: F401


def test_public_hosted_competition_list_returns_empty_200() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    app = FastAPI()
    app.include_router(hosted_router)

    def override_session():
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_session

    with TestClient(app) as client:
        response = client.get("/hosted-competitions")

    assert response.status_code == 200
    assert response.json() == {"competitions": []}
