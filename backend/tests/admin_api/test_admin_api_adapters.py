from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from backend.tests.support.secrets import TEST_PASSWORD
import app.ingestion.models  # noqa: F401
import app.ledger.models  # noqa: F401
import app.models  # noqa: F401
import app.orders.models  # noqa: F401
from app.admin_api.router import router as admin_api_router
from app.auth.dependencies import get_current_admin, get_session
from app.auth.service import AuthService
from app.models.base import Base
from app.models.event_backbone import CompetitionQueueRecord
from app.models.user import User, UserRole


@pytest.fixture()
def admin_api_context(tmp_path: Path):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    auth = AuthService()
    super_admin = auth.ensure_admin_user(
        session,
        email="canonical-root@example.com",
        password=TEST_PASSWORD,
        username="canonical_root",
        display_name="Canonical Root",
        role=UserRole.SUPER_ADMIN,
    )
    scoped_admin = auth.ensure_admin_user(
        session,
        email="canonical-scoped@example.com",
        password=TEST_PASSWORD,
        username="canonical_scoped",
        display_name="Canonical Scoped",
        role=UserRole.ADMIN,
    )
    session.add(
        CompetitionQueueRecord(
            queue_name="match_simulation",
            job_name="match_simulation",
            idempotency_key="canonical-queue-1",
            aggregate_id="fixture-1",
            partition_key="competition-1",
            payload_json={
                "competition_id": "competition-1",
                "fixture_id": "fixture-1",
                "secret_token": "do-not-return",
            },
            metadata_json={"producer": "test", "api_token": "do-not-return"},
        )
    )
    session.commit()

    app = FastAPI()
    app.include_router(admin_api_router)
    app.state.settings = SimpleNamespace(config_root=tmp_path)
    app.state.session_factory = SessionLocal

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session

    def set_actor(actor: User) -> None:
        app.dependency_overrides[get_current_admin] = lambda: actor

    with TestClient(app) as client:
        yield client, set_actor, super_admin, scoped_admin

    session.close()
    engine.dispose()


@pytest.mark.parametrize(
    "path",
    [
        "/api/admin/readiness",
        "/api/admin/treasury",
        "/api/admin/payment-rails",
        "/api/admin/queues",
        "/api/admin/settlements",
        "/api/admin/competitions",
    ],
)
def test_canonical_admin_routes_fail_closed_without_capability(admin_api_context, path: str) -> None:
    client, set_actor, _super_admin, scoped_admin = admin_api_context
    set_actor(scoped_admin)

    response = client.get(path)

    assert response.status_code == 403
    assert "Permission" in response.json()["detail"]


def test_super_admin_can_read_canonical_admin_snapshots(admin_api_context) -> None:
    client, set_actor, super_admin, _scoped_admin = admin_api_context
    set_actor(super_admin)

    readiness = client.get("/api/admin/readiness")
    payment_rails = client.get("/api/admin/payment-rails")
    queues = client.get("/api/admin/queues")
    settlements = client.get("/api/admin/settlements")
    competitions = client.get("/api/admin/competitions")

    assert readiness.status_code == 200, readiness.text
    assert payment_rails.status_code == 200, payment_rails.text
    assert queues.status_code == 200, queues.text
    assert settlements.status_code == 200, settlements.text
    assert competitions.status_code == 200, competitions.text
    assert payment_rails.json()["rails"]
    queue_payload = queues.json()["jobs"][0]["payload"]
    queue_metadata = queues.json()["jobs"][0]["metadata"]
    assert queue_payload["competition_id"] == "competition-1"
    assert "secret_token" not in queue_payload
    assert "api_token" not in queue_metadata
    assert "trade_settlement" in settlements.json()["ledger_reason_counts"]
    assert competitions.json()["manager_competitions"]
