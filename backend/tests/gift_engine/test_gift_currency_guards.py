from __future__ import annotations

from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import AuthService
from app.gift_engine.canonical_service import CanonicalGiftEngineService, GiftEngineError
from app.gift_engine.router import _map_transaction
from app.gift_engine.schemas import (
    GiftCatalogAdminPatchRequest,
    GiftCatalogAdminUpsertRequest,
    GiftTransactionView,
)
from app.models import (
    AdminRewardRule,
    Base,
    LedgerEntryReason,
    LedgerUnit,
)
from app.models.user import User
from app.wallets.service import LedgerPosting, WalletService


@pytest.fixture()
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        db_session.add(
            AdminRewardRule(
                rule_key="platform-economy-defaults",
                title="Platform Economy Defaults",
                description="Canonical Admin fee and rake policy.",
                trading_fee_bps=2000,
                gift_platform_rake_bps=3000,
                withdrawal_fee_bps=1000,
                minimum_withdrawal_fee_credits=Decimal("5.0000"),
                competition_platform_fee_bps=3000,
                stability_controls_json={},
                active=True,
            )
        )
        db_session.commit()
        yield db_session
    engine.dispose()


def _create_user(session: Session, *, email: str, username: str) -> User:
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password="SuperSecretPassword123!",  # pragma: allowlist secret — synthetic fixture password, not a credential
    )
    session.commit()
    return user


def _fund_fancoin(session: Session, user: User, amount: Decimal) -> None:
    wallet = WalletService()
    account = wallet.get_user_account(session, user, LedgerUnit.CREDIT)
    platform = wallet.ensure_platform_account(session, LedgerUnit.CREDIT)
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=account, amount=amount),
            LedgerPosting(account=platform, amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference=f"seed-fancoin:{user.id}",
        actor=user,
    )
    session.commit()


def test_gift_rejects_gtex_coin_source_currency(session: Session) -> None:
    sender = _create_user(session, email="sender1@example.com", username="sender1")
    recipient = _create_user(session, email="recipient1@example.com", username="recipient1")
    _fund_fancoin(session, sender, Decimal("100.0000"))

    service = CanonicalGiftEngineService(session)
    service.ensure_football_gift_catalog()

    # Attempting to send with currency='coin'
    with pytest.raises(GiftEngineError) as exc_info:
        service.send_gift(
            sender=sender,
            recipient_user_id=recipient.id,
            gift_key="whistle_blow",
            quantity=Decimal("1.0000"),
            currency="coin",
        )
    assert exc_info.value.reason == "invalid_gift_source_currency"
    assert "GTEX Coin cannot be used as a gift source currency" in str(exc_info.value)


def test_gift_catalog_admin_rejects_coin_currency() -> None:
    # Upsert request
    with pytest.raises(ValueError, match="GTEX Coin cannot be used as a gift currency"):
        GiftCatalogAdminUpsertRequest(
            code="test-coin-gift",
            display_name="Coin Gift",
            cost_amount=Decimal("10.0000"),
            currency="coin",
        )

    # Patch request
    with pytest.raises(ValueError, match="GTEX Coin cannot be used as a gift currency"):
        GiftCatalogAdminPatchRequest(currency="gtex_coin")


def test_gift_transaction_view_contains_currency_provenance(session: Session) -> None:
    sender = _create_user(session, email="sender2@example.com", username="sender2")
    recipient = _create_user(session, email="recipient2@example.com", username="recipient2")
    _fund_fancoin(session, sender, Decimal("100.0000"))

    service = CanonicalGiftEngineService(session)
    service.ensure_football_gift_catalog()

    tx = service.send_gift(
        sender=sender,
        recipient_user_id=recipient.id,
        gift_key="whistle_blow",
        quantity=Decimal("1.0000"),
    )
    session.commit()

    view = _map_transaction(tx)
    assert isinstance(view, GiftTransactionView)
    assert view.source_ledger_unit == "credit"
    assert view.destination_ledger_unit == "coin"
    assert view.economic_conversion_id == tx.economic_conversion_id
    assert view.conversion_rate == Decimal("1.0000")
    assert view.fee_policy_rule_key == "platform-economy-defaults"
    assert view.fee_policy_version is not None
