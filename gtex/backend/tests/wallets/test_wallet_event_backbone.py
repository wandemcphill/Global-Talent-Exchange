from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.database import load_model_modules
from app.core.events import InMemoryEventPublisher
from app.models.base import Base
from app.models.event_backbone import EventOutbox
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.wallets.service import LedgerPosting, WalletService


def _build_session_factory(tmp_path):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'wallet-events.db').as_posix()}"
    load_model_modules()
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _create_user(session, *, suffix: str = "1") -> User:
    user = User(
        email=f"wallet-events-{suffix}@example.com",
        username=f"wallet_events_{suffix}",
        password_hash="test-password-hash",
    )
    session.add(user)
    session.flush()
    return user


def test_wallet_transaction_is_outboxed_and_published_after_commit(tmp_path) -> None:
    engine, session_factory = _build_session_factory(tmp_path)
    publisher = InMemoryEventPublisher()

    with session_factory() as session:
        user = _create_user(session)
        service = WalletService(event_publisher=publisher)
        user_account = service.get_user_account(session, user, LedgerUnit.CREDIT)
        platform_account = service.ensure_platform_account(session, LedgerUnit.CREDIT)

        service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=user_account, amount="1500.0000"),
                LedgerPosting(account=platform_account, amount="-1500.0000"),
            ],
            reason=LedgerEntryReason.DEPOSIT,
            reference="wallet-outbox-test",
        )

        outbox_rows = session.scalars(select(EventOutbox)).all()
        assert len(outbox_rows) == 1
        assert outbox_rows[0].event_type == "wallet.transaction.appended"
        assert len(publisher.published_events) == 0

        session.commit()

    event_names = {event.name for event in publisher.published_events}
    assert "wallet.transaction.appended" in event_names
    assert "wallet_credit_applied" in event_names
    assert "wallet.balance.updated" in event_names
    engine.dispose()
