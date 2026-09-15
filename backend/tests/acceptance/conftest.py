from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerTransactionType, LedgerUnit
from app.wallets.service import LedgerPosting, WalletService


@pytest.fixture(autouse=True)
def fund_bootstrap_admin_for_hosted_prize(app_session_factory, bootstrap_admin_headers):
    del bootstrap_admin_headers
    target_balance = Decimal("5000.0000")
    wallet_service = WalletService()

    with app_session_factory() as session:
        admin = session.scalar(select(User).where(User.role == UserRole.SUPER_ADMIN))
        assert admin is not None
        admin_account = wallet_service.get_user_account(session, admin, LedgerUnit.COIN)
        current_balance = wallet_service.get_balance(session, admin_account)
        if current_balance >= target_balance:
            return

        funding_account = wallet_service.ensure_named_system_account(
            session,
            code="test:coin:funding_pool",
            label="Test Coin Funding Pool",
            unit=LedgerUnit.COIN,
            allow_negative=True,
        )
        amount = target_balance - current_balance
        wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=admin_account, amount=amount),
                LedgerPosting(account=funding_account, amount=-amount),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            transaction_type=LedgerTransactionType.ADJUSTMENT,
            reference="test:funding:coin:bootstrap-admin:acceptance-host-prize",
            description="Dedicated acceptance funding for GTEX host-funded prize tests",
            external_reference="test:funding:coin:bootstrap-admin:acceptance-host-prize",
        )
        session.commit()
