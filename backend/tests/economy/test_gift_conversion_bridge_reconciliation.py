"""The gift conversion bridge is observable and reconciles against the ledger.

PHASE_A_CROSS_CURRENCY_CONVERSION deliberately lets the Coin bridge carry the
withdrawable-Coin liability a FanCoin gift creates, but requires that liability
to be separately tracked. These tests exercise the reconciliation surface
directly against a real conversion and a real reversal.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.auth.service import AuthService  # noqa: E402
from app.economy.conversion_service import FanCoinGiftConversionService  # noqa: E402
from app.gift_engine.canonical_service import GiftEngineService  # noqa: E402
from app.models import (  # noqa: E402
    Base,
    EconomicConversion,
    GiftCatalogItem,
    LedgerEntryReason,
    LedgerUnit,
)
from app.wallets.service import LedgerPosting, WalletService  # noqa: E402
from backend.tests.support.economic_policy import seed_economic_policy  # noqa: E402
from scripts.audit_gift_conversion_bridge import audit_bridge  # noqa: E402

GROSS = Decimal("100.0000")
FAN_NET = Decimal("70.0000")
GTEX_OUT = Decimal("0.7000")
PURCHASED_GTEX = Decimal("1.0000")


def _make_session_and_url(tmp_path):
    db_path = tmp_path / "bridge.db"
    url = f"sqlite+pysqlite:///{db_path.as_posix()}"
    engine = create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    seed_economic_policy(session)
    session.commit()
    return session, url


def _user(session, *, email, username):
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password="SuperSecret1",  # pragma: allowlist secret
    )
    session.commit()
    return user


def _send_gift(session, sender, recipient):
    session.add(GiftCatalogItem(key="bridge-star", display_name="Bridge Star", fancoin_price=GROSS, active=True))
    session.commit()
    wallet = WalletService()
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=wallet.get_user_account(session, sender, LedgerUnit.COIN), amount=PURCHASED_GTEX),
            LedgerPosting(account=wallet.ensure_platform_account(session, LedgerUnit.COIN), amount=-PURCHASED_GTEX),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-bridge-gtex",
        actor=sender,
    )
    session.commit()
    wallet.convert_wallet_units(
        session,
        user=sender,
        amount=PURCHASED_GTEX,
        source_unit=LedgerUnit.COIN,
        actor=sender,
        idempotency_key="bridge-purchase",
    )
    session.commit()
    tx = GiftEngineService(session).send_gift(
        sender=sender,
        recipient_user_id=recipient.id,
        gift_key="bridge-star",
        quantity=Decimal("1.0000"),
        source_scope="user_hosted",
        idempotency_key="bridge-gift",
    )
    session.commit()
    return tx


def test_bridge_reports_outstanding_coin_liability_after_a_gift(tmp_path) -> None:
    session, url = _make_session_and_url(tmp_path)
    try:
        sender = _user(session, email="bridge-sender@example.com", username="bridge-sender")
        recipient = _user(session, email="bridge-recipient@example.com", username="bridge-recipient")
        _send_gift(session, sender, recipient)
    finally:
        session.close()

    report = audit_bridge(database_url=url)

    assert report["settled_conversions"] == 1
    assert Decimal(report["fancoin_consumed"]) == GROSS
    assert Decimal(report["coin_issued"]) == GTEX_OUT
    assert Decimal(report["outstanding_coin_liability"]) == GTEX_OUT
    # The purchase left 1 GTEX on the bridge. The gift spends the Fan Coin
    # remainder converted at 100:1, so 0.70 GTEX leaves and 0.30 stays backed.
    assert Decimal(report["coin_bridge_balance"]) == PURCHASED_GTEX - GTEX_OUT
    assert Decimal(report["credit_bridge_balance"]) == FAN_NET
    assert report["bridge_accounts_exist"] is True
    assert report["pass"] is True


def test_bridge_liability_returns_to_zero_after_a_reversal(tmp_path) -> None:
    session, url = _make_session_and_url(tmp_path)
    try:
        sender = _user(session, email="rev-sender@example.com", username="rev-sender")
        recipient = _user(session, email="rev-recipient@example.com", username="rev-recipient")
        tx = _send_gift(session, sender, recipient)

        conversion = session.get(EconomicConversion, tx.economic_conversion_id)
        FanCoinGiftConversionService(session).reverse(conversion=conversion, actor=sender)
        session.commit()
    finally:
        session.close()

    report = audit_bridge(database_url=url)

    assert report["reversed_conversions"] == 1
    assert Decimal(report["outstanding_coin_liability"]) == Decimal("0.0000")
    # Reversal returns the gifted GTEX to the bridge. The purchase backing remains.
    assert Decimal(report["coin_bridge_balance"]) == PURCHASED_GTEX
    assert Decimal(report["credit_bridge_balance"]) == Decimal("0.0000")
    assert report["pass"] is True


def test_bridge_audit_is_clean_on_an_untouched_ledger(tmp_path) -> None:
    session, url = _make_session_and_url(tmp_path)
    session.close()

    report = audit_bridge(database_url=url)

    assert report["settled_conversions"] == 0
    assert Decimal(report["outstanding_coin_liability"]) == Decimal("0.0000")
    assert report["bridge_accounts_exist"] is False
    assert report["pass"] is True
