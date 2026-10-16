from __future__ import annotations

from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.models.base import Base
from app.models.risk_ops import AmlCase, AuditLog, FraudCase, RiskAction, RiskSignal, SystemEvent
from app.models.user import KycStatus, User, UserRole
from app.risk_ops_engine.router import admin_router as risk_admin_router
from app.risk_ops_engine.router import router as risk_router
from app.risk_ops_engine.service import RiskOpsService


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
            AmlCase.__table__,
            FraudCase.__table__,
            SystemEvent.__table__,
            AuditLog.__table__,
            RiskSignal.__table__,
            RiskAction.__table__,
        ],
    )
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_local() as db_session:
        db_session.add_all(
            [
                User(
                    id="user-alpha",
                    email="alpha@example.com",
                    username="alpha",
                    display_name="Alpha",
                    password_hash="x",
                    role=UserRole.USER,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                ),
                User(
                    id="user-bravo",
                    email="bravo@example.com",
                    username="bravo",
                    display_name="Bravo",
                    password_hash="x",
                    role=UserRole.USER,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                ),
                User(
                    id="admin-user",
                    email="admin@example.com",
                    username="admin",
                    display_name="Admin",
                    password_hash="x",
                    role=UserRole.ADMIN,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                ),
            ]
        )
        db_session.commit()
        yield db_session


@pytest.fixture()
def user_state(session: Session) -> dict[str, User]:
    return {"user": session.get(User, "user-alpha"), "admin": session.get(User, "admin-user")}


@pytest.fixture()
def app(session: Session, user_state: dict[str, User]) -> FastAPI:
    application = FastAPI()
    application.include_router(risk_router)
    application.include_router(risk_admin_router)

    def override_session() -> Iterator[Session]:
        yield session

    def override_user() -> User:
        return user_state["user"]

    def override_admin() -> User:
        return user_state["admin"]

    application.dependency_overrides[get_session] = override_session
    application.dependency_overrides[get_current_user] = override_user
    application.dependency_overrides[get_current_admin] = override_admin
    return application


@pytest.fixture()
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def service(session: Session) -> RiskOpsService:
    return RiskOpsService(session)
