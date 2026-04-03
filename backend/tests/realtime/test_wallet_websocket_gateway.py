from __future__ import annotations

import os

from backend.tests.support.secrets import (
    MEDIA_SIGNING_TEST_SECRET,
    TEST_PASSWORD_HASH,
    WALLET_WEBSOCKET_AUTH_SECRET,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.security import create_access_token
from app.core.events import InMemoryEventPublisher
from app.models.event_backbone import EventOutbox
from app.models.risk_ops import AuditLog
from app.models.user import User
from app.models.wallet import (
    LedgerAccount,
    LedgerBalanceProjection,
    LedgerEntry,
    LedgerEntryReason,
    LedgerTransaction,
    LedgerUnit,
)
from app.realtime.router import router as realtime_router
from app.realtime.service import RealtimeHub
from app.wallets.service import LedgerPosting, WalletService


def test_wallet_websocket_gateway_streams_committed_events(tmp_path) -> None:
    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{(tmp_path / 'settings.db').as_posix()}"
    os.environ["GTE_DATABASE_URL"] = f"sqlite+pysqlite:///{(tmp_path / 'auth.db').as_posix()}"
    os.environ["GTE_AUTH_SECRET"] = WALLET_WEBSOCKET_AUTH_SECRET
    os.environ["GTE_MEDIA_SIGNING_SECRET"] = MEDIA_SIGNING_TEST_SECRET

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            LedgerAccount.__table__,
            LedgerTransaction.__table__,
            LedgerEntry.__table__,
            LedgerBalanceProjection.__table__,
            EventOutbox.__table__,
            AuditLog.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    publisher = InMemoryEventPublisher()
    realtime = RealtimeHub()
    publisher.subscribe(realtime.handle_event)

    app = FastAPI()
    app.include_router(realtime_router)
    app.state.session_factory = session_factory
    app.state.realtime = realtime

    with session_factory() as session:
        user = User(
            email="wallet-websocket@example.com",
            username="wallet_websocket",
            password_hash=TEST_PASSWORD_HASH,
        )
        session.add(user)
        session.commit()
        user_id = user.id

    token = create_access_token(user_id)
    client = TestClient(app)
    with client.websocket_connect(f"/realtime/wallet/stream?token={token}") as websocket:
        initial_message = websocket.receive_json()
        assert initial_message == {
            "type": "subscription_ack",
            "data": {"topics": [f"wallet:{user_id}"]},
        }

        with session_factory() as session:
            user = session.get(User, user_id)
            assert user is not None
            wallet_service = WalletService(event_publisher=publisher)
            user_account = wallet_service.get_user_account(session, user, LedgerUnit.CREDIT)
            platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.CREDIT)
            wallet_service.append_transaction(
                session,
                postings=[
                    LedgerPosting(account=user_account, amount="1800.0000"),
                    LedgerPosting(account=platform_account, amount="-1800.0000"),
                ],
                reason=LedgerEntryReason.DEPOSIT,
                reference="wallet-websocket-test",
            )
            session.commit()

        events_message = websocket.receive_json()
        assert events_message["type"] == "wallet_update"
        assert events_message["data"]["user_id"] == user_id
        assert events_message["data"]["unit"] == LedgerUnit.CREDIT.value

    engine.dispose()
