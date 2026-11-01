from __future__ import annotations

from decimal import Decimal
import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.coin_trader import (
    CoinTraderProfile,
    CoinTraderProfileStatus,
    CoinTraderRate,
    CoinTraderTier,
)
from app.models.treasury import (
    PaymentMode,
    RateDirection,
    TreasurySettings,
    TreasuryWithdrawalStatus,
    UserBankAccount,
)
from app.models.user import KycStatus, PublicAccountType, User, UserRole
from app.models.wallet import (
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerTransactionType,
    LedgerUnit,
)
from app.wallets.funding_service import WalletFundingError, WalletFundingService
from app.wallets.providers.base import (
    PayoutSession,
    ProviderEvent,
    ProviderEventType,
    ProviderFeeEstimate,
)
from app.wallets.providers.korapay import KoraPayProviderAdapter
from app.wallets.providers.paystack import PaystackProviderAdapter
from app.wallets.providers.registry import (
    get_provider_adapter,
)
from app.wallets.rail_service import WalletRailService
from app.wallets.service import LedgerPosting, WalletService
from app.treasury.service import TreasuryService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.core.database import load_model_modules

    load_model_modules()
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_provider_registry_and_adapter_conformance():
    """Verify both KoraPay and Paystack are canonical, registered, and conform to the adapter protocol."""
    korapay = get_provider_adapter("korapay")
    paystack = get_provider_adapter("paystack")

    assert isinstance(korapay, KoraPayProviderAdapter)
    assert isinstance(paystack, PaystackProviderAdapter)
    assert korapay.provider_key == "korapay"
    assert paystack.provider_key == "paystack"

    # Both must provide fee estimates
    k_fee = korapay.estimate_fee(amount=Decimal("10000"), operation="checkout")
    p_fee = paystack.estimate_fee(amount=Decimal("10000"), operation="checkout")
    assert isinstance(k_fee, ProviderFeeEstimate)
    assert isinstance(p_fee, ProviderFeeEstimate)
    assert k_fee.estimated_fee > 0
    assert p_fee.estimated_fee > 0

    # Payout fee estimates
    k_payout_fee = korapay.estimate_fee(amount=Decimal("10000"), operation="payout")
    p_payout_fee = paystack.estimate_fee(amount=Decimal("10000"), operation="payout")
    assert k_payout_fee.estimated_fee > 0
    assert p_payout_fee.estimated_fee > 0


def test_korapay_webhook_signature_and_event_parsing():
    """Verify KoraPay SHA256 of JSON.stringify(payload.data) signature checking and webhook parsing."""
    adapter = KoraPayProviderAdapter()
    secret = "korapay_test_secret_key"  # pragma: allowlist secret
    data_dict = {
        "reference": "PO-KORA-TEST-001",
        "amount": 5000,
        "currency": "NGN",
        "status": "success",
    }
    raw_data_json = json.dumps(data_dict, separators=(",", ":"))
    expected_sig = hmac.new(secret.encode("utf-8"), raw_data_json.encode("utf-8"), hashlib.sha256).hexdigest()

    payload = {
        "event": "charge.success",
        "data": data_dict,
    }
    headers = {"x-korapay-signature": expected_sig}

    with patch.dict("os.environ", {"GTE_KORAPAY_SECRET_KEY": secret}):
        assert adapter.verify_webhook_signature(payload=payload, raw_body=None, headers=headers) is True

        # Invalid signature must fail
        bad_headers = {"x-korapay-signature": "invalid_signature"}
        with pytest.raises(ValueError, match="signature is invalid"):
            adapter.verify_webhook_signature(payload=payload, raw_body=None, headers=bad_headers)

    # Event parsing
    event = adapter.parse_webhook(payload, headers=headers)
    assert event is not None
    assert event.provider_key == "korapay"
    assert event.event_type == ProviderEventType.SETTLED
    assert event.provider_reference == "PO-KORA-TEST-001"
    assert event.amount == Decimal("5000")
    assert event.is_payout is False


def test_paystack_webhook_signature_and_payout_event_parsing():
    """Verify Paystack HMAC-SHA512 of raw body and disbursement event parsing."""
    adapter = PaystackProviderAdapter()
    secret = "paystack_test_secret_key"  # pragma: allowlist secret
    raw_body = json.dumps(
        {
            "event": "transfer.success",
            "data": {
                "reference": "WDL-PAYSTACK-TEST-001",
                "transfer_code": "TRF_123456",
                "amount": 1000000,  # 10,000 NGN in kobo
                "currency": "NGN",
                "status": "success",
            },
        }
    ).encode("utf-8")
    expected_sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
    headers = {"x-paystack-signature": expected_sig}
    payload = json.loads(raw_body.decode("utf-8"))

    with patch.dict("os.environ", {"GTE_PAYSTACK_SECRET_KEY": secret}):
        assert adapter.verify_webhook_signature(payload=payload, raw_body=raw_body, headers=headers) is True

    # Payout event parsing
    event = adapter.parse_webhook(payload, headers=headers)
    assert event is not None
    assert event.provider_key == "paystack"
    assert event.event_type == ProviderEventType.SETTLED
    assert event.provider_reference == "WDL-PAYSTACK-TEST-001"
    assert event.amount == Decimal("10000.00")
    assert event.is_payout is True


def test_unsupported_provider_rejected(db_session):
    """Unsupported provider keys must be rejected and suggest canonical providers."""
    funding = WalletFundingService(wallet_service=WalletService())
    user = User(
        id="test-user-unsupported-rail",
        email="user@test.org",
        username="unsupported_user",
        account_type=PublicAccountType.USER,
        password_hash="mock_hash_12345",  # pragma: allowlist secret
        is_active=True,
        kyc_status=KycStatus.VERIFIED,
    )
    db_session.add(user)
    db_session.flush()

    with pytest.raises(WalletFundingError, match="KoraPay and Paystack are the live automatic top-up providers"):
        funding.initiate_top_up(
            db_session,
            user=user,
            amount=Decimal("100"),
            provider="flutterwave",  # Unsupported 3rd party
        )


def test_trader_liquidity_purchase_atomically_updates_effective_available_liquidity(db_session):
    """
    Critical Trader Journey:
    Trader purchases coin liquidity via KoraPay/Paystack.
    Settle purchase order atomically credits wallet and increments CoinTraderRate.available_liquidity.
    _effective_available_liquidity immediately reflects the updated balance.
    """
    wallet_service = WalletService()
    rail_service = WalletRailService(session=db_session, wallet_service=wallet_service)

    # 1. Setup Trader User and Profile
    trader = User(
        id="trader-user-001",
        email="trader@test.org",
        username="lagos_trader",
        account_type=PublicAccountType.COIN_TRADER,
        password_hash="mock_hash_12345",  # pragma: allowlist secret
        is_active=True,
        kyc_status=KycStatus.VERIFIED,
    )
    db_session.add(trader)
    profile = CoinTraderProfile(
        id="trader-prof-001",
        user_id=trader.id,
        display_name="Lagos Desk",
        status=CoinTraderProfileStatus.APPROVED.value,
        tier=CoinTraderTier.SILVER.value,
        country_code="NG",
    )
    db_session.add(profile)
    rate = CoinTraderRate(
        id="rate-001",
        trader_profile_id=profile.id,
        coin_unit=LedgerUnit.COIN,
        fiat_currency="NGN",
        buy_rate_fiat=Decimal("850"),
        sell_rate_fiat=Decimal("950"),
        available_liquidity=Decimal("100.0000"),
        is_active=True,
    )
    db_session.add(rate)

    # Setup Treasury Settings
    settings = TreasurySettings(
        deposit_mode=PaymentMode.AUTOMATIC,
        withdrawal_mode=PaymentMode.AUTOMATIC,
        deposit_rate_value=Decimal("1000.000000"),
        deposit_rate_direction=RateDirection.COIN_PER_FIAT,
        withdrawal_rate_value=Decimal("1000.000000"),
        withdrawal_rate_direction=RateDirection.COIN_PER_FIAT,
        currency_code="NGN",
    )
    db_session.add(settings)
    db_session.flush()

    # Initial available liquidity before purchase
    from app.coin_traders.service import CoinTraderService

    trader_service = CoinTraderService(db_session, wallet_service)
    # With 0 balance in wallet, effective liquidity is 0
    assert trader_service._effective_available_liquidity(rate) == Decimal("0.0000")

    # 2. Trader purchases 5000 coins of trading liquidity via Paystack
    order = rail_service.create_purchase_order(
        user=trader,
        settings=settings,
        amount=Decimal("5000.0000"),
        input_unit="coin",
        provider_key="paystack",
        source_scope="trader_liquidity",
        unit=LedgerUnit.COIN,
        processor_mode="automatic_gateway",
        payout_channel="gateway",
        notes="trader liquidity replenishment",
        purchase_purpose="trader_liquidity",
    )
    assert order.purchase_purpose == "trader_liquidity"
    assert order.account_type_snapshot == "coin_trader"

    # 3. Simulate payment verification and settlement
    rail_service.settle_purchase_order(order=order, actor=trader)
    db_session.refresh(rate)
    db_session.refresh(profile)

    # Rate available_liquidity was incremented by order.net_amount (gross minus commission)
    assert rate.available_liquidity == Decimal("100.0000") + order.net_amount
    # Wallet was credited with order.net_amount
    wallet_balance = wallet_service.get_balance(
        db_session, wallet_service.get_user_account(db_session, trader, LedgerUnit.COIN)
    )
    assert wallet_balance == order.net_amount

    # Effective liquidity now immediately equals min(rate.available_liquidity, wallet_balance)
    effective_liq = trader_service._effective_available_liquidity(rate)
    assert effective_liq == order.net_amount
    # Snapshot was refreshed atomically
    assert profile.liquidity_snapshot_json is not None
    assert "last_provider_liquidity_purchase" in profile.metadata_json


def test_withdrawal_quote_and_payout_lifecycle(db_session):
    """
    Test Withdrawal Lifecycle:
    1. Quote with fee breakdown: Platform fee vs Processor fee estimate.
    2. Request withdrawal with provider rail selection.
    3. Hold funds on ledger.
    4. Payout initiation via adapter.
    5. Webhook confirmation settling withdrawal to PAID.
    6. Manual reconciliation marking is_manual_reconciliation=True.
    """
    wallet_service = WalletService()
    treasury_service = TreasuryService(wallet_service=wallet_service)

    user = User(
        id="user-withdrawal-001",
        email="withdrawer@test.org",
        username="withdrawer",
        account_type=PublicAccountType.USER,
        password_hash="mock_hash_12345",  # pragma: allowlist secret
        is_active=True,
        kyc_status=KycStatus.VERIFIED,
    )
    db_session.add(user)

    # Fund user with 10,000 coins
    user_account = wallet_service.get_user_account(db_session, user, LedgerUnit.COIN)
    issuance_account = wallet_service.ensure_platform_account(db_session, LedgerUnit.COIN)
    wallet_service.append_transaction(
        db_session,
        postings=[
            LedgerPosting(account=issuance_account, amount=Decimal("-10000.0000")),
            LedgerPosting(account=user_account, amount=Decimal("10000.0000")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        transaction_type=LedgerTransactionType.ADJUSTMENT,
        actor=user,
    )

    # Bank account
    bank = UserBankAccount(
        user_id=user.id,
        bank_name="Access Bank",
        account_number="0123456789",
        account_name="Withdrawer User",
        bank_code="044",
        currency_code="NGN",
        is_active=True,
    )
    db_session.add(bank)

    settings = TreasurySettings(
        deposit_mode=PaymentMode.AUTOMATIC,
        withdrawal_mode=PaymentMode.AUTOMATIC,
        deposit_rate_value=Decimal("1000.000000"),
        deposit_rate_direction=RateDirection.COIN_PER_FIAT,
        withdrawal_rate_value=Decimal("1000.000000"),
        withdrawal_rate_direction=RateDirection.COIN_PER_FIAT,
        currency_code="NGN",
    )
    db_session.add(settings)
    db_session.flush()

    from app.models.policy import CountryFeaturePolicy
    from app.policies.service import PolicyService

    country_policy = CountryFeaturePolicy(
        country_code="GLOBAL",
        bucket_type="default",
        deposits_enabled=True,
        market_trading_enabled=True,
        platform_reward_withdrawals_enabled=True,
        user_hosted_gift_withdrawals_enabled=True,
        gtex_competition_gift_withdrawals_enabled=True,
        national_reward_withdrawals_enabled=True,
        one_time_region_change_after_days=180,
        active=True,
    )
    db_session.add(country_policy)
    db_session.flush()

    policy_service = PolicyService(db_session)
    policy_service.seed_defaults()
    policy_service.ensure_user_region_profile(user=user, region_code="NG")
    for version in policy_service.list_missing_acceptances(user_id=user.id):
        policy_service.accept_document(
            user_id=user.id,
            document_key=version.document.document_key,
            version_label=version.version_label,
            ip_address=None,
            device_id=None,
        )
    db_session.flush()

    from backend.tests.support.economic_policy import seed_economic_policy

    seed_economic_policy(db_session)

    # 1. Create withdrawal request for 2000 coins via Paystack
    withdrawal = treasury_service.create_withdrawal_request(
        db_session,
        user=user,
        amount_coin=Decimal("2000.0000"),
        bank_account_id=bank.id,
        source_scope="trade",
        provider_key="paystack",
        idempotency_key="wdl-test-idemp-001",
    )
    assert withdrawal.provider_key == "paystack"
    assert withdrawal.status == TreasuryWithdrawalStatus.PENDING_REVIEW
    assert withdrawal.processor_fee > Decimal("0.0000")  # Processor fee estimated

    # 2. Admin initiates payout
    admin_user = User(
        id="admin-payout-001",
        email="admin@test.org",
        username="treasury_admin",
        role=UserRole.ADMIN,
        account_type=PublicAccountType.USER,
        password_hash="mock_hash_12345",  # pragma: allowlist secret
        is_active=True,
        kyc_status=KycStatus.VERIFIED,
    )
    db_session.add(admin_user)
    db_session.flush()

    # Mock provider payout adapter
    with patch("app.treasury.service.get_live_provider_adapter") as mock_adapter_getter, patch(
        "app.treasury.service.provider_live_payout_ready", return_value=True
    ):
        mock_adapter = MagicMock()
        mock_adapter.display_name = "Paystack"
        mock_adapter.initiate_payout.return_value = PayoutSession(
            reference="TRF_REF_9999",
            transfer_code="TRF_CODE_9999",
            status="pending",
            provider_reference="TRF_REF_9999",
            currency="NGN",
            amount=withdrawal.amount_fiat,
        )
        mock_adapter_getter.return_value = mock_adapter

        initiated = treasury_service.initiate_withdrawal_payout(
            db_session,
            actor=admin_user,
            withdrawal_id=withdrawal.id,
        )
        assert initiated.status == TreasuryWithdrawalStatus.PROCESSING
        assert initiated.provider_reference == "TRF_REF_9999"
        assert initiated.provider_transfer_code == "TRF_CODE_9999"

    # 3. Simulate Payout Webhook Event (transfer.success)
    payout_event = ProviderEvent(
        event_id="evt_transfer_success_001",
        provider_key="paystack",
        event_type=ProviderEventType.SETTLED,
        reference=withdrawal.reference,
        provider_reference="TRF_REF_9999",
        amount=withdrawal.amount_fiat,
        currency="NGN",
        is_payout=True,
    )
    settled = treasury_service.handle_provider_payout_event(db_session, event=payout_event)
    assert settled is not None
    assert settled.status == TreasuryWithdrawalStatus.PAID
    assert settled.paid_at is not None

    # 4. Manual Reconciliation
    recon = treasury_service.manual_reconcile_withdrawal(
        db_session,
        actor=admin_user,
        withdrawal_id=withdrawal.id,
        resolution_status=TreasuryWithdrawalStatus.PAID,
        note="Verified bank debits matched Paystack log.",
    )
    assert recon.is_manual_reconciliation is True
