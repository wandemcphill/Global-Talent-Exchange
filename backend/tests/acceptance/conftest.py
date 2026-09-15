from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.ingestion.models import Country
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerTransactionType, LedgerUnit
from app.wallets.service import LedgerPosting, WalletService
from backend.tests.players.test_player_share_market_routes import _seed_imported_real_player


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


@pytest.fixture(autouse=True)
def seed_national_rental_pool_player(app_session_factory):
    """Provision one NG reference country and one eligible player for the rental pool."""
    with app_session_factory() as session:
        country = session.scalar(select(Country).where(Country.alpha2_code == "NG"))
        if country is None:
            country = Country(
                id="full-journey-20260915-country-ng",
                source_provider="gtex-acceptance-fixture",
                provider_external_id="NG",
                name="Nigeria",
                alpha2_code="NG",
                alpha3_code="NGA",
                fifa_code="NGA",
                confederation_code="CAF",
                market_region="africa",
            )
            session.add(country)
            session.flush()

        player = _seed_imported_real_player(session, player_id="full-journey-20260915-national-real")
        player.country_id = country.id
        player.date_of_birth = date(2010, 1, 1)
        session.commit()
