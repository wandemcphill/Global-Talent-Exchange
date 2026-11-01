from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hmac
from hashlib import sha256
import json
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from pydantic import ValidationError

import app.models  # noqa: F401
from app.auth.eligibility import (
    AccountEligibilityService,
    AccountTypeConflictError,
    TradingEligibilityError,
)
from app.coin_traders.schemas import (
    CoinTradeOrderCreateRequest,
    CoinTraderProfileCreateRequest,
    CoinTraderRateUpsertRequest,
)
from app.coin_traders.service import CoinTraderPermissionError, CoinTraderService, CoinTraderValidationError
from app.identity.providers import DIDitAdapter, SandboxAdapter, SmileIdAdapter, get_identity_provider
from app.identity.service import (
    IdentityVerificationService,
    IdentityWebhookSignatureError,
)
from app.models.base import Base
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.coin_trader import (
    CoinTradeOrderStatus,
    CoinTraderProfile,
    CoinTraderProfileStatus,
    CoinTraderRate,
)
from app.models.creator_application import (
    CREATOR_APPLICATION_ADDITIONAL_INFO,
    CREATOR_APPLICATION_PENDING,
    CREATOR_APPLICATION_REJECTED,
    CREATOR_APPLICATION_SUSPENDED,
    CREATOR_APPLICATION_VERIFICATION_REQUESTED,
)
from app.models.creator_profile import CreatorProfile
from app.models.user import KycStatus, PublicAccountType, User, UserRole
from app.models.wallet import LedgerSourceTag, LedgerUnit
from app.schemas.creator_application import (
    CreatorApplicationSubmitRequest,
)
from app.services.creator_application_service import (
    CreatorApplicationConflictError,
    CreatorApplicationService,
)
from app.treasury.service import TreasuryService
from app.wallets.service import WalletService


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _make_user(
    session: Session,
    *,
    user_id: str,
    email: str,
    account_type: PublicAccountType = PublicAccountType.USER,
    role: UserRole = UserRole.USER,
    kyc_status: KycStatus = KycStatus.UNVERIFIED,
) -> User:
    user = User(
        id=user_id,
        email=email,
        username=email.split("@")[0],
        display_name=email.split("@")[0].title(),
        password_hash="test_password_hash",  # pragma: allowlist secret
        account_type=account_type,
        role=role,
        kyc_status=kyc_status,
    )
    session.add(user)
    session.flush()
    return user


# ==============================================================================
# 1. ORDINARY USER ACCOUNTS - NO UNIVERSAL KYC
# ==============================================================================


def test_ordinary_user_no_universal_kyc_for_withdrawal(db_session: Session) -> None:
    """Ordinary users are not blocked from withdrawals simply because global KYC is unverified."""
    user = _make_user(db_session, user_id="ord-user-1", email="ordinary1@example.com")
    wallet_service = WalletService()
    wallet_service.credit_trade_proceeds(
        db_session,
        user=user,
        amount=Decimal("50000.0000"),
        unit=LedgerUnit.COIN,
        reference="seed:ord-user-1",
        description="Seed ordinary user balance",
        external_reference="seed-1",
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
    )
    db_session.commit()

    # Treasury eligibility check must report requires_kyc = False
    treasury = TreasuryService(wallet_service=wallet_service)
    eligibility = treasury.get_withdrawal_eligibility(db_session, user)
    assert eligibility.requires_kyc is False
    assert eligibility.kyc_status == KycStatus.UNVERIFIED

    # AccountEligibilityService passes without error
    AccountEligibilityService.assert_can_withdraw(user, db_session, Decimal("1000"))


def test_ordinary_user_withdrawal_respects_risk_hold(db_session: Session) -> None:
    """Security and fraud controls remain in place even without universal KYC."""
    user = _make_user(db_session, user_id="risk-user-1", email="risky@example.com")
    wallet_service = WalletService()
    wallet_service.credit_trade_proceeds(
        db_session,
        user=user,
        amount=Decimal("50000.0000"),
        unit=LedgerUnit.COIN,
        reference="seed:risk-user-1",
        description="Seed balance",
        external_reference="seed-risk",
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
    )
    db_session.commit()

    # When risk flags or policy holds apply, withdrawal eligibility reflects the block
    treasury = TreasuryService(wallet_service=wallet_service)
    eligibility = treasury.get_withdrawal_eligibility(
        db_session,
        user,
        country_code="NG",
        country_withdrawals_enabled=True,
        missing_required_policies=("aml-policy",),
    )
    assert eligibility.policy_blocked is True
    assert "Accept the latest required policies" in (eligibility.policy_block_reason or "")


# ==============================================================================
# 2. CREATOR ACCOUNTS - AUDIENCE & IDENTITY VERIFICATION
# ==============================================================================


def test_creator_application_platform_and_follower_validation() -> None:
    """Creator applications require >= 20,000 followers on one eligible platform, excluding Facebook."""
    # Eligible platforms: tiktok, instagram, twitch, youtube, x
    for platform in ["tiktok", "instagram", "twitch", "youtube", "x"]:
        req = CreatorApplicationSubmitRequest(
            requested_handle=f"test.{platform}",
            display_name="Test Creator",
            platform=platform,
            follower_count=20000,
            profile_url=f"https://{platform}.com/testcreator",
        )
        assert req.platform == platform
        assert req.follower_count == 20000

    # Facebook explicitly excluded
    with pytest.raises(ValidationError) as exc:
        CreatorApplicationSubmitRequest(
            requested_handle="test.fb",
            display_name="Test FB",
            platform="facebook",
            follower_count=50000,
            profile_url="https://facebook.com/testfb",
        )
    assert "Facebook is not an eligible platform" in str(exc.value)

    # Followers below 20,000 rejected
    with pytest.raises(ValidationError) as exc:
        CreatorApplicationSubmitRequest(
            requested_handle="test.low",
            display_name="Test Low",
            platform="youtube",
            follower_count=19999,
            profile_url="https://youtube.com/@low",
        )
    assert "20000" in str(exc.value)

    # Missing or invalid profile URL rejected
    with pytest.raises(ValidationError):
        CreatorApplicationSubmitRequest(
            requested_handle="test.url",
            display_name="Test URL",
            platform="youtube",
            follower_count=25000,
            profile_url="not-a-valid-url",
        )


def test_creator_application_no_privileges_while_pending(db_session: Session) -> None:
    """An applicant does not receive Creator privileges or account type while pending."""
    user = _make_user(db_session, user_id="creator-app-1", email="applicant@example.com")
    user.email_verified_at = datetime.now(timezone.utc)
    db_session.commit()

    service = CreatorApplicationService(db_session)
    payload = CreatorApplicationSubmitRequest(
        requested_handle="great.creator",
        display_name="Great Creator",
        platform="youtube",
        follower_count=45000,
        profile_url="https://youtube.com/@greatcreator",
        selfie_attachment_id="selfie-uuid-001",
    )
    app_result = service.submit_application(actor=user, payload=payload)
    assert app_result.status == CREATOR_APPLICATION_PENDING
    assert app_result.profile_url == "https://youtube.com/@greatcreator"
    assert app_result.selfie_attachment_id == "selfie-uuid-001"

    # User remains ordinary USER account type
    db_session.refresh(user)
    assert user.account_type == PublicAccountType.USER

    # Attempting to trade player shares as creator or access creator features is not permitted
    assert db_session.scalar(select(CreatorProfile).where(CreatorProfile.user_id == user.id)) is None


def test_creator_application_blocked_by_active_club(db_session: Session) -> None:
    """A user who owns an active club cannot apply for or be promoted to Creator."""
    user = _make_user(db_session, user_id="club-owner-1", email="owner@example.com")
    club = ClubProfile(
        id="club-1",
        owner_user_id=user.id,
        club_name="Active FC",
        slug="active-fc",
        club_type=ClubType.COMMUNITY,
        lifecycle_status=ClubLifecycleStatus.ACTIVE,
        primary_color="#0F766E",
        secondary_color="#F8FAFC",
        accent_color="#F59E0B",
    )
    db_session.add(club)
    db_session.commit()

    service = CreatorApplicationService(db_session)
    payload = CreatorApplicationSubmitRequest(
        requested_handle="active.owner",
        display_name="Active Owner",
        platform="tiktok",
        follower_count=30000,
        profile_url="https://tiktok.com/@owner",
    )
    with pytest.raises(CreatorApplicationConflictError) as exc:
        service.submit_application(actor=user, payload=payload)
    assert "club_ownership_prevents_creator_promotion" in str(exc.value)


def test_creator_application_admin_workflow_and_audit(db_session: Session) -> None:
    """Admin reviewer can request info, approve, reject, or suspend with auditable history."""
    admin = _make_user(db_session, user_id="admin-rev", email="admin@gtex.local", role=UserRole.ADMIN)
    user = _make_user(db_session, user_id="creator-flow-1", email="flow@example.com")
    user.email_verified_at = datetime.now(timezone.utc)
    db_session.commit()

    service = CreatorApplicationService(db_session)
    payload = CreatorApplicationSubmitRequest(
        requested_handle="flow.creator",
        display_name="Flow Creator",
        platform="x",
        follower_count=85000,
        profile_url="https://x.com/flowcreator",
        selfie_attachment_id="selfie-flow-1",
    )
    application = service.submit_application(actor=user, payload=payload)
    assert application.status == CREATOR_APPLICATION_PENDING

    # 1. Admin requests additional information
    info_app = service.request_verification(
        application_id=application.id,
        reviewer=admin,
        review_notes="Please update your selfie with better lighting.",
        reason="Selfie lighting insufficient",
    )
    assert info_app.status in {CREATOR_APPLICATION_VERIFICATION_REQUESTED, CREATOR_APPLICATION_ADDITIONAL_INFO}
    assert len(info_app.decision_history_json) >= 2
    assert any(
        h.get("decision") in {"verification_requested", "additional_info_required"}
        for h in info_app.decision_history_json
    )

    # 2. Admin suspends application
    suspended_app = service.suspend_application(
        application_id=application.id,
        reviewer=admin,
        reason="Account flagged for audience authenticity review.",
    )
    assert suspended_app.status == CREATOR_APPLICATION_SUSPENDED
    assert any(h.get("decision") == "suspended" for h in suspended_app.decision_history_json)

    # 3. Admin rejects application
    rejected_app = service.reject_application(
        application_id=application.id,
        reviewer=admin,
        review_notes="Audience review concluded non-genuine followers.",
        reason="Follower authenticity check failed",
    )
    assert rejected_app.status == CREATOR_APPLICATION_REJECTED
    assert any(h.get("decision") == "rejected" for h in rejected_app.decision_history_json)


# ==============================================================================
# 3. COIN TRADER ACCOUNTS - FULL IDENTITY VERIFICATION BEFORE TRADING
# ==============================================================================


def test_coin_trader_cannot_trade_without_verification(db_session: Session) -> None:
    """Coin traders must be verified before quoting rates, accepting orders, or trading."""
    user = _make_user(
        db_session,
        user_id="trader-unverified-1",
        email="unverified_trader@example.com",
        account_type=PublicAccountType.COIN_TRADER,
    )
    trader_service = CoinTraderService(db_session)
    profile_view = trader_service.create_or_update_profile(
        CoinTraderProfileCreateRequest(
            display_name="Unverified Desk",
            country_code="NG",
            terms={"same_name_account_only": True},
            payment_methods=[{"type": "bank_transfer", "label": "Bank"}],
            bank_accounts=[{"bank": "GTBank", "account_number": "1234567890"}],
        ),
        actor=user,
    )
    assert profile_view.status == CoinTraderProfileStatus.APPLIED.value
    assert profile_view.verified_at is None

    # Quoting rates must fail because profile is not approved/verified
    with pytest.raises(CoinTraderPermissionError):
        trader_service.upsert_rate(
            CoinTraderRateUpsertRequest(
                coin_unit=LedgerUnit.COIN,
                fiat_currency="NGN",
                buy_rate_fiat=Decimal("850"),
                sell_rate_fiat=Decimal("900"),
                min_coin_amount=Decimal("100"),
                max_coin_amount=Decimal("10000"),
                available_liquidity=Decimal("5000"),
                is_active=True,
            ),
            actor=user,
        )

    # Operating coin trader eligibility check must fail
    with pytest.raises(TradingEligibilityError) as exc:
        AccountEligibilityService.assert_can_operate_coin_trader(user, db_session)
    assert "pending identity verification" in str(exc.value).lower() or "must complete" in str(exc.value).lower()


def test_coin_trader_provider_adapters_and_webhook_activation(db_session: Session) -> None:
    """Authoritative provider webhook automatically activates trader with idempotency."""
    user = _make_user(
        db_session,
        user_id="trader-verify-1",
        email="verify_trader@example.com",
        account_type=PublicAccountType.COIN_TRADER,
    )
    trader_service = CoinTraderService(db_session)
    profile_view = trader_service.create_or_update_profile(
        CoinTraderProfileCreateRequest(
            display_name="Auto Verified Desk",
            country_code="NG",
            terms={"same_name_account_only": True},
            payment_methods=[{"type": "bank_transfer", "label": "Bank"}],
            bank_accounts=[{"bank": "Access Bank", "account_number": "9876543210"}],
        ),
        actor=user,
    )
    db_session.commit()

    # 1. Test supported provider adapters
    didit_adapter = get_identity_provider("didit")
    smile_adapter = get_identity_provider("smile_id")
    sandbox_adapter = get_identity_provider("sandbox")
    assert isinstance(didit_adapter, DIDitAdapter)
    assert isinstance(smile_adapter, SmileIdAdapter)
    assert isinstance(sandbox_adapter, SandboxAdapter)

    # 2. Initiate trader verification session
    identity_service = IdentityVerificationService(db_session)
    init_res = identity_service.initiate_trader_verification(
        actor=user,
        provider_name="sandbox",
        verification_type="government_id",
    )
    assert init_res.provider_session_id is not None
    assert init_res.status in {"initiated", "pending"}

    # 3. Simulate authoritative successful provider webhook
    webhook_payload = {
        "event": "verification.completed",
        "session_id": init_res.provider_session_id,
        "reference": "PROV-REF-9999",
        "status": "approved",
        "checks": {
            "document": "pass",
            "face_match": "pass",
            "liveness": "pass",
        },
    }
    raw_payload = json.dumps(webhook_payload).encode("utf-8")
    secret = b"sandbox-secret"
    signature = hmac.new(secret, raw_payload, sha256).hexdigest()
    headers = {"X-Sandbox-Signature": signature}

    # Process authoritative webhook
    result_dict = identity_service.process_provider_webhook(
        provider_name="sandbox",
        payload_bytes=raw_payload,
        headers=headers,
    )
    assert result_dict["status"] in {"success", "verified"}
    assert result_dict["reference"] == "PROV-REF-9999"

    # Profile automatically activated
    profile = db_session.get(CoinTraderProfile, profile_view.id)
    assert profile.status == CoinTraderProfileStatus.APPROVED.value
    assert profile.verified_at is not None
    assert profile.verification_provider == "sandbox"
    assert profile.verification_reference == "PROV-REF-9999"

    # Trader is now eligible to operate
    AccountEligibilityService.assert_can_operate_coin_trader(user, db_session)

    # 4. Idempotency test: repeating the same webhook does not fail or duplicate
    dup_dict = identity_service.process_provider_webhook(
        provider_name="sandbox",
        payload_bytes=raw_payload,
        headers=headers,
    )
    assert dup_dict["status"] == "idempotent_duplicate"

    # 5. Invalid signature rejected
    with pytest.raises(IdentityWebhookSignatureError):
        identity_service.process_provider_webhook(
            provider_name="sandbox",
            payload_bytes=raw_payload,
            headers={"X-Sandbox-Signature": "invalid-fake-signature"},
        )


def test_verified_coin_trader_withdrawal_no_repeat_kyc(db_session: Session) -> None:
    """An already verified accredited coin trader is not forced through routine repeat KYC on withdrawal."""
    user = _make_user(
        db_session,
        user_id="trader-with-1",
        email="trader_withdraw@example.com",
        account_type=PublicAccountType.COIN_TRADER,
        kyc_status=KycStatus.VERIFIED,
    )
    # Set up approved and verified trader profile
    profile = CoinTraderProfile(
        id="profile-with-1",
        user_id=user.id,
        display_name="Accredited Desk",
        country_code="NG",
        status=CoinTraderProfileStatus.APPROVED.value,
        verified_at=datetime.now(timezone.utc),
        verification_provider="smile_id",
        verification_reference="SMILE-REF-101",
        terms_json={"same_name_account_only": True},
        payment_methods_json=[{"type": "bank_transfer", "label": "Bank"}],
        bank_accounts_json=[{"bank": "GTBank", "account_number": "0011223344"}],
    )
    db_session.add(profile)
    wallet_service = WalletService()
    wallet_service.credit_trade_proceeds(
        db_session,
        user=user,
        amount=Decimal("100000.0000"),
        unit=LedgerUnit.COIN,
        reference="seed:trader-with-1",
        description="Seed balance",
        external_reference="seed-trader",
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
    )
    db_session.commit()

    # Treasury eligibility check reports requires_kyc = False
    treasury = TreasuryService(wallet_service=wallet_service)
    eligibility = treasury.get_withdrawal_eligibility(db_session, user)
    assert eligibility.requires_kyc is False

    # AccountEligibilityService confirms trader withdrawal is allowed
    AccountEligibilityService.assert_can_withdraw(user, db_session, Decimal("5000"))

    # Unverified trader requires KYC
    profile.verified_at = None
    profile.status = CoinTraderProfileStatus.APPLIED.value
    db_session.commit()

    eligibility_unverified = treasury.get_withdrawal_eligibility(db_session, user)
    assert eligibility_unverified.requires_kyc is True


def test_admin_suspend_and_reinstate_coin_trader(db_session: Session) -> None:
    """Administrators can suspend or reinstate coin traders for compliance or fraud reasons."""
    admin = _make_user(db_session, user_id="admin-susp", email="admin_susp@gtex.local", role=UserRole.ADMIN)
    user = _make_user(
        db_session,
        user_id="trader-susp-1",
        email="susp_trader@example.com",
        account_type=PublicAccountType.COIN_TRADER,
        kyc_status=KycStatus.VERIFIED,
    )
    profile = CoinTraderProfile(
        id="profile-susp-1",
        user_id=user.id,
        display_name="Susp Desk",
        country_code="NG",
        status=CoinTraderProfileStatus.APPROVED.value,
        verified_at=datetime.now(timezone.utc),
        terms_json={},
        payment_methods_json=[],
        bank_accounts_json=[],
    )
    db_session.add(profile)
    db_session.commit()

    trader_service = CoinTraderService(db_session)

    # Suspend trader
    suspended = trader_service.suspend_trader(
        profile.id,
        admin=admin,
        note="Suspicious OTC transaction activity detected",
    )
    assert suspended.status == CoinTraderProfileStatus.SUSPENDED.value
    assert suspended.suspended_at is not None

    # Suspended trader cannot operate
    with pytest.raises(TradingEligibilityError) as exc:
        AccountEligibilityService.assert_can_operate_coin_trader(user, db_session)
    assert "suspended" in str(exc.value).lower()

    # Reinstate trader
    reinstated = trader_service.reinstate_trader(
        profile.id,
        admin=admin,
        note="Compliance review completed and cleared.",
    )
    assert reinstated.status == CoinTraderProfileStatus.APPROVED.value
    assert reinstated.suspended_at is None

    # Now eligible again
    AccountEligibilityService.assert_can_operate_coin_trader(user, db_session)


# ==============================================================================
# 4. ACCOUNT-TYPE EXCLUSIVITY
# ==============================================================================


def test_account_type_exclusivity_rules(db_session: Session) -> None:
    """Coin Traders cannot trade player shares, own clubs, or switch to Creator."""
    coin_trader_user = _make_user(
        db_session,
        user_id="lane-trader-1",
        email="lane_trader@example.com",
        account_type=PublicAccountType.COIN_TRADER,
    )
    creator_user = _make_user(
        db_session,
        user_id="lane-creator-1",
        email="lane_creator@example.com",
        account_type=PublicAccountType.CREATOR,
    )
    ordinary_user = _make_user(
        db_session,
        user_id="lane-ord-1",
        email="lane_ord@example.com",
        account_type=PublicAccountType.USER,
    )

    # 1. Player shares: Coin Trader cannot trade; USER and CREATOR can
    with pytest.raises(AccountTypeConflictError) as exc:
        AccountEligibilityService.assert_can_trade_player_shares(coin_trader_user)
    assert "player share trading" in str(exc.value).lower()

    AccountEligibilityService.assert_can_trade_player_shares(creator_user)
    AccountEligibilityService.assert_can_trade_player_shares(ordinary_user)

    # 2. Club ownership: Coin Trader cannot own club; USER can
    with pytest.raises(AccountTypeConflictError) as exc:
        AccountEligibilityService.assert_can_own_club(coin_trader_user)
    assert "cannot own football clubs" in str(exc.value).lower()

    AccountEligibilityService.assert_can_own_club(ordinary_user)

    # 3. Creator promotion: Coin Trader cannot apply for Creator
    with pytest.raises(AccountTypeConflictError) as exc:
        AccountEligibilityService.assert_can_apply_for_creator(coin_trader_user, db_session)
    assert "cannot be promoted to creator" in str(exc.value).lower()

    # Creator cannot apply again
    with pytest.raises(AccountTypeConflictError):
        AccountEligibilityService.assert_can_apply_for_creator(creator_user, db_session)

    # Ordinary user without active club can apply
    AccountEligibilityService.assert_can_apply_for_creator(ordinary_user, db_session)


# ==============================================================================
# 5. TRADING ELIGIBILITY & TRANSACTION LIMITS (₦200,000 MINIMUM BUYER ORDER)
# ==============================================================================


def test_coin_trader_200k_minimum_buyer_order_enforced(db_session: Session) -> None:
    """Enforces ₦200,000 minimum buyer order value per trader transaction on NGN buy orders."""
    trader_user = _make_user(
        db_session,
        user_id="limit-trader-1",
        email="limit_trader@example.com",
        account_type=PublicAccountType.COIN_TRADER,
        kyc_status=KycStatus.VERIFIED,
    )
    buyer_user = _make_user(
        db_session,
        user_id="limit-buyer-1",
        email="limit_buyer@example.com",
        account_type=PublicAccountType.USER,
    )
    seller_user = _make_user(
        db_session,
        user_id="limit-seller-1",
        email="limit_seller@example.com",
        account_type=PublicAccountType.USER,
    )

    profile = CoinTraderProfile(
        id="profile-limit-1",
        user_id=trader_user.id,
        display_name="Limit OTC Desk",
        country_code="NG",
        status=CoinTraderProfileStatus.APPROVED.value,
        verified_at=datetime.now(timezone.utc),
        terms_json={"same_name_account_only": True},
        payment_methods_json=[{"type": "bank_transfer", "label": "Bank"}],
        bank_accounts_json=[{"bank": "Zenith", "account_number": "1234567890"}],
    )
    rate = CoinTraderRate(
        id="rate-limit-1",
        trader_profile_id=profile.id,
        coin_unit=LedgerUnit.COIN,
        fiat_currency="NGN",
        buy_rate_fiat=Decimal("860"),  # Desk buys coin from user at ₦860
        sell_rate_fiat=Decimal("920"),  # Desk sells coin to user at ₦920
        min_coin_amount=Decimal("10"),
        max_coin_amount=Decimal("50000"),
        available_liquidity=Decimal("100000"),
        is_active=True,
    )
    db_session.add_all([profile, rate])

    # Fund trader with coin for escrow
    wallet_service = WalletService()
    wallet_service.credit_trade_proceeds(
        db_session,
        user=trader_user,
        amount=Decimal("100000.0000"),
        unit=LedgerUnit.COIN,
        reference="seed:limit-trader",
        description="Seed balance",
        external_reference="seed-trader",
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
    )
    # Fund seller user with coin
    wallet_service.credit_trade_proceeds(
        db_session,
        user=seller_user,
        amount=Decimal("5000.0000"),
        unit=LedgerUnit.COIN,
        reference="seed:limit-seller",
        description="Seed balance",
        external_reference="seed-seller",
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
    )
    db_session.commit()

    trader_service = CoinTraderService(db_session, wallet_service=wallet_service)

    # 1. Buyer order below ₦200,000: 100 coin * ₦1,000 = ₦100,000 -> REJECTED
    with pytest.raises(CoinTraderValidationError) as exc:
        trader_service.create_order(
            CoinTradeOrderCreateRequest(
                trader_profile_id=profile.id,
                direction="user_buys",
                coin_unit=LedgerUnit.COIN,
                coin_amount=Decimal("100"),
                fiat_currency="NGN",
                payment_method="bank_transfer",
                idempotency_key="order-key-low-001",
            ),
            actor=buyer_user,
        )
    # ₦200,000 threshold enforced
    assert "200,000" in str(exc.value)

    # 2. Buyer order at or above ₦200,000: 250 coin * ₦920 = ₦230,000 -> ACCEPTED
    order_ok = trader_service.create_order(
        CoinTradeOrderCreateRequest(
            trader_profile_id=profile.id,
            direction="user_buys",
            coin_unit=LedgerUnit.COIN,
            coin_amount=Decimal("250"),
            fiat_currency="NGN",
            payment_method="bank_transfer",
            idempotency_key="order-key-ok-001",
        ),
        actor=buyer_user,
    )
    assert order_ok.id is not None
    assert order_ok.fiat_total == Decimal("230000")
    assert order_ok.status == CoinTradeOrderStatus.CREATED.value

    # 3. User sells coin to desk: 50 coin * ₦860 = ₦43,000 -> ACCEPTED (limit only applies to buyer orders)
    sell_order = trader_service.create_order(
        CoinTradeOrderCreateRequest(
            trader_profile_id=profile.id,
            direction="user_sells",
            coin_unit=LedgerUnit.COIN,
            coin_amount=Decimal("50"),
            fiat_currency="NGN",
            payment_method="bank_transfer",
            idempotency_key="order-key-sell-001",
        ),
        actor=seller_user,
    )
    assert sell_order.id is not None
    assert sell_order.fiat_total == Decimal("43000")
