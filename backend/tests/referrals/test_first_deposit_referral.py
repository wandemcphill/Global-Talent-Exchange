from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import Thread

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.auth.dependencies import get_current_user, get_session
from app.auth.schemas import CreatorSignupRequest, TraderSignupRequest, UserClubSignupRequest
from app.common.enums.referral_reward_status import ReferralRewardStatus
from app.common.enums.referral_reward_type import ReferralRewardType
from app.models.base import Base
from app.models.fancoin_purchase_order import FancoinPurchaseOrder, PurchaseOrderStatus
from app.models.referral_affiliate import ReferralClick, ReferralRecoveryCase
from app.models.referral_attribution import ReferralAttribution
from app.models.referral_reward import ReferralReward
from app.models.share_code import ShareCode
from app.models.referral_reward_ledger import ReferralRewardLedger
from app.models.treasury import RateDirection, TreasurySettings
from app.models.user import PublicAccountType, User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit
from app.routes.admin_referrals import router as admin_referrals_router
from app.services.first_deposit_referral_service import (
    FirstDepositReferralError,
    FirstDepositReferralService,
    fiat_to_wallet,
)
from app.wallets.rail_service import WalletRailError, WalletRailService
from app.wallets.service import LedgerPosting, WalletService


def _engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def _user(
    email: str,
    username: str,
    *,
    role: UserRole = UserRole.USER,
    account_type: PublicAccountType = PublicAccountType.USER,
) -> User:
    return User(
        email=email,
        username=username,
        password_hash="test-hash",  # pragma: allowlist secret
        full_name=username,
        role=role,
        account_type=account_type,
    )


def _order(
    user: User,
    *,
    amount_fiat: str,
    currency: str = "NGN",
    rate: str = "100",
    direction: RateDirection = RateDirection.FIAT_PER_COIN,
    unit: LedgerUnit = LedgerUnit.COIN,
    status: PurchaseOrderStatus = PurchaseOrderStatus.PROCESSING,
    reference: str = "PO-1",
) -> FancoinPurchaseOrder:
    fiat = Decimal(amount_fiat)
    coins = fiat_to_wallet(fiat, Decimal(rate), direction)
    return FancoinPurchaseOrder(
        user_id=user.id,
        reference=reference,
        status=status,
        provider_key="manual",
        provider_reference=f"provider-{reference}",
        unit=unit,
        amount_fiat=fiat,
        gross_amount=coins,
        fee_amount=Decimal("0.0000"),
        processor_fee=Decimal("0.0000"),
        net_amount=coins,
        currency_code=currency,
        rate_value=Decimal(rate),
        rate_direction=direction,
        account_type_snapshot=str(
            user.account_type.value if hasattr(user.account_type, "value") else user.account_type
        ),
        raw_payload={},
    )


@pytest.fixture()
def db():
    engine = _engine()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    admin = _user("admin@gtex.test", "admin", role=UserRole.ADMIN)
    referrer = _user("referrer@gtex.test", "referrer")
    session.add_all([admin, referrer])
    session.commit()
    yield session, SessionLocal, admin, referrer
    session.close()
    engine.dispose()


def _service(session) -> FirstDepositReferralService:
    return FirstDepositReferralService(session, WalletService())


def test_signup_schemas_accept_referral_codes() -> None:
    user = UserClubSignupRequest.model_validate(
        {
            "full_name": "Club Owner",
            "username": "club_owner",
            "email": "club@gtex.test",
            "password": "ValidPassword123!",  # pragma: allowlist secret
            "is_over_18": True,
            "country": "Nigeria",
            "referral_code": " creator10 ",
            "club_name": "Northside",
            "club_short_tag": "NOR",
            "club_type": "community",
        }
    )
    creator = CreatorSignupRequest.model_validate(
        {
            "creator_name": "Creator",
            "username": "creator_one",
            "email": "creator@gtex.test",
            "password": "ValidPassword123!",  # pragma: allowlist secret
            "country": "NG",
            "category": "football",
            "primary_language": "en",
            "referral_code": "creator10",
        }
    )
    trader = TraderSignupRequest.model_validate(
        {
            "full_name": "Trader",
            "trading_alias": "Desk",
            "email": "trader@gtex.test",
            "password": "ValidPassword123!",  # pragma: allowlist secret
            "phone_number": "+2348012345678",
            "country": "NG",
            "preferred_currency": "NGN",
            "trading_experience": "beginner",
            "totp_secret": "JBSWY3DPEHPK3PXP",  # pragma: allowlist secret
            "totp_code": "123456",
            "referral_code": "creator10",
        }
    )
    assert user.referral_code == "creator10"
    assert user.creates_club is True
    assert creator.referral_code == "creator10"
    assert trader.referral_code == "creator10"


def test_registration_lanes_and_code_guards(db) -> None:
    session, _, admin, _referrer = db
    service = _service(session)
    partner = service.create_partner(
        admin,
        {
            "display_name": "External Creator",
            "campaign_name": "Launch",
            "code": "CREATOR10",
            "contact_email": "promoter@outside.test",
            "social_handle": "@promoter",
            "payout_destination_label": "External bank",
        },
    )
    session.commit()
    assert partner["owner_user_id"] is None
    code = partner["campaigns"][0]["code"]

    lanes = [
        ("member@gtex.test", "member", "user", PublicAccountType.USER, False, "user"),
        ("owner@gtex.test", "clubboss", "user", PublicAccountType.USER, True, "club_owner"),
        ("creator@gtex.test", "creator", "creator", PublicAccountType.CREATOR, False, "creator"),
        ("trader@gtex.test", "trader", "coin_trader", PublicAccountType.COIN_TRADER, False, "coin_trader"),
    ]
    for email, username, account_type, public_type, creates_club, snapshot in lanes:
        person = _user(email, username, account_type=public_type)
        session.add(person)
        session.flush()
        attribution = service.attribute_signup(person, code, account_type=account_type, creates_club=creates_club)
        assert attribution.referral_partner_id == partner["id"]
        assert attribution.account_type_snapshot == snapshot
        assert attribution.referrer_user_id is None
    session.commit()

    stranger = _user("nobody@gtex.test", "nobody")
    session.add(stranger)
    session.flush()
    with pytest.raises(FirstDepositReferralError) as invalid:
        service.attribute_signup(stranger, "NO-SUCH", account_type="user")
    assert invalid.value.code == "referral_code_invalid"

    share = session.scalar(select(ShareCode).where(ShareCode.code == code))
    share.ends_at = datetime.now(timezone.utc) - timedelta(days=1)
    session.flush()
    with pytest.raises(FirstDepositReferralError) as expired:
        service.attribute_signup(stranger, code, account_type="user")
    assert expired.value.code == "referral_code_expired"
    share.ends_at = None
    session.flush()

    service.set_partner_status(admin, partner["id"], active=False, reason="Pause the campaign")
    with pytest.raises(FirstDepositReferralError) as disabled:
        service.attribute_signup(stranger, code, account_type="user")
    assert disabled.value.code == "referral_code_inactive"
    service.set_partner_status(admin, partner["id"], active=True, reason="Campaign restored")

    self_user = _user("promoter@outside.test", "promoter")
    session.add(self_user)
    session.flush()
    with pytest.raises(FirstDepositReferralError) as blocked:
        service.attribute_signup(self_user, code, account_type="user")
    assert blocked.value.code == "self_referral_blocked"


def test_settled_deposit_pays_ten_percent_once_and_replays_do_not_duplicate(db) -> None:
    session, _, admin, _referrer = db
    service = _service(session)
    partner = service.create_partner(
        admin,
        {
            "display_name": "External Creator",
            "campaign_name": "Launch",
            "code": "CREATOR10",
        },
    )
    member = _user("member@gtex.test", "member")
    session.add(member)
    session.flush()
    service.attribute_signup(member, "CREATOR10", account_type="user")
    service.record_click("CREATOR10", ip_address="203.0.113.10")
    order = _order(member, amount_fiat="100000.00", reference="PO-FIRST")
    session.add(order)
    session.commit()

    rail = WalletRailService(session=session)
    rail.settle_purchase_order(order=order, actor=member)
    rail.settle_purchase_order(order=order, actor=member)
    session.commit()

    rewards = list(session.scalars(select(ReferralReward).where(ReferralReward.referred_user_id == member.id)).all())
    bonus = next(item for item in rewards if item.reward_type == ReferralRewardType.FIRST_DEPOSIT_BONUS)
    commission = next(item for item in rewards if item.reward_type == ReferralRewardType.FIRST_DEPOSIT_COMMISSION)
    assert len(rewards) == 2
    assert commission.reward_amount == Decimal("10000.00")
    assert commission.qualifying_amount == Decimal("100000.0000")
    assert bonus.qualifying_amount == commission.qualifying_amount
    assert bonus.reward_amount == fiat_to_wallet(Decimal("10000.00"), Decimal("100"), RateDirection.FIAT_PER_COIN)
    assert bonus.status == ReferralRewardStatus.PAID
    assert commission.status == ReferralRewardStatus.PENDING
    assert commission.referral_partner_id == partner["id"]
    assert commission.beneficiary_user_id is None
    assert bonus.applied_rate_bps == 1000
    assert commission.applied_rate_bps == 1000
    wallet = WalletService().get_balance(session, WalletService().get_user_account(session, member, LedgerUnit.COIN))
    deposit_credit = fiat_to_wallet(Decimal("100000.00"), Decimal("100"), RateDirection.FIAT_PER_COIN)
    assert wallet == deposit_credit + bonus.reward_amount

    second = _order(member, amount_fiat="50000.00", reference="PO-SECOND")
    session.add(second)
    session.commit()
    rail.settle_purchase_order(order=second, actor=member)
    session.commit()
    again = list(session.scalars(select(ReferralReward).where(ReferralReward.referred_user_id == member.id)).all())
    assert len(again) == 2

    pending = _order(member, amount_fiat="100000.00", reference="PO-PENDING", status=PurchaseOrderStatus.PROCESSING)
    failed = _order(member, amount_fiat="100000.00", reference="PO-FAILED", status=PurchaseOrderStatus.FAILED)
    session.add_all([pending, failed])
    session.flush()
    assert service.on_purchase_order_settled(pending) == []
    assert service.on_purchase_order_settled(failed) == []

    analytics = service.analytics()
    clicks = session.scalar(select(func.count()).select_from(ReferralClick).where(ReferralClick.succeeded.is_(True)))
    registrations = session.scalar(select(func.count()).select_from(ReferralAttribution))
    deposits = session.scalar(
        select(func.count())
        .select_from(ReferralReward)
        .where(ReferralReward.reward_type == ReferralRewardType.FIRST_DEPOSIT_BONUS)
    )
    assert analytics["clicks"] == clicks
    assert analytics["registrations"] == registrations
    assert analytics["first_deposits"] == deposits

    old_amount = commission.reward_amount
    old_rate = commission.applied_rate_bps
    service.update_settings(
        admin, {"user_bonus_bps": 1500, "referrer_commission_bps": 1500, "reason": "Future campaigns only"}
    )
    session.refresh(commission)
    assert commission.reward_amount == old_amount
    assert commission.applied_rate_bps == old_rate


def test_coin_per_fiat_and_non_ngn_use_the_same_base(db) -> None:
    session, _, admin, _referrer = db
    service = _service(session)
    service.create_partner(admin, {"display_name": "USD Partner", "campaign_name": "USD", "code": "USDCODE"})
    person = _user("usd@gtex.test", "usduser")
    session.add(person)
    session.flush()
    service.attribute_signup(person, "USDCODE", account_type="user")
    order = _order(
        person,
        amount_fiat="100.00",
        currency="USD",
        rate="0.02",
        direction=RateDirection.COIN_PER_FIAT,
        reference="PO-USD",
    )
    session.add(order)
    session.commit()
    WalletRailService(session=session).settle_purchase_order(order=order, actor=person)
    session.commit()
    rewards = list(session.scalars(select(ReferralReward).where(ReferralReward.referred_user_id == person.id)).all())
    bonus = next(item for item in rewards if item.reward_type == ReferralRewardType.FIRST_DEPOSIT_BONUS)
    commission = next(item for item in rewards if item.reward_type == ReferralRewardType.FIRST_DEPOSIT_COMMISSION)
    assert commission.reward_amount == Decimal("10.00")
    assert commission.qualifying_currency == "USD"
    assert bonus.reward_amount == fiat_to_wallet(Decimal("10.00"), Decimal("0.02"), RateDirection.COIN_PER_FIAT)
    assert bonus.qualifying_amount == commission.qualifying_amount


def test_trader_minimum_stays_at_two_hundred_thousand(db) -> None:
    session, _, _admin, _referrer = db
    rail = WalletRailService(session=session)
    settings = TreasurySettings(
        currency_code="NGN",
        deposit_rate_value=Decimal("100"),
        trader_coin_purchase_rate_value=Decimal("100"),
        min_deposit=None,
        max_deposit=None,
    )
    with pytest.raises(WalletRailError, match="200,000"):
        rail.quote_purchase_order(
            settings=settings,
            amount=Decimal("100000"),
            input_unit="fiat",
            provider_key="manual",
            source_scope="trader_liquidity",
            unit=LedgerUnit.COIN,
            processor_mode="automatic_gateway",
            payout_channel="gateway",
        )
    try:
        rail.quote_purchase_order(
            settings=settings,
            amount=Decimal("200000"),
            input_unit="fiat",
            provider_key="manual",
            source_scope="trader_liquidity",
            unit=LedgerUnit.COIN,
            processor_mode="automatic_gateway",
            payout_channel="gateway",
        )
    except WalletRailError as exc:
        assert "200,000" not in str(exc)


def test_coin_trader_bulk_packages_grant_extra_gtex_coin(db) -> None:
    session, _, _admin, _referrer = db
    rail = WalletRailService(session=session)
    settings = TreasurySettings(
        currency_code="NGN",
        deposit_rate_value=Decimal("100"),
        deposit_rate_direction=RateDirection.FIAT_PER_COIN,
        trader_coin_purchase_rate_value=Decimal("50"),
        trader_fan_coin_purchase_rate_value=Decimal("2.50"),
        min_deposit=None,
        max_deposit=None,
    )

    def quote(amount: str, *, source_scope: str = "trader_liquidity", unit: LedgerUnit = LedgerUnit.COIN):
        return rail.quote_purchase_order(
            settings=settings,
            amount=Decimal(amount),
            input_unit="fiat",
            provider_key="manual",
            source_scope=source_scope,
            unit=unit,
            processor_mode="manual_review",
            payout_channel="manual",
        )

    half_million = quote("500000")
    assert half_million.amount_fiat == Decimal("500000.0000")
    assert half_million.gross_amount == Decimal("10000.0000")
    assert half_million.bulk_bonus_amount == Decimal("300.0000")
    assert half_million.net_amount == half_million.gross_amount - half_million.fee_amount + Decimal("300.0000")

    one_million = quote("1000000")
    assert one_million.gross_amount == Decimal("20000.0000")
    assert one_million.bulk_bonus_amount == Decimal("700.0000")
    assert one_million.net_amount == one_million.gross_amount - one_million.fee_amount + Decimal("700.0000")

    opening_inventory = quote("200000")
    assert opening_inventory.bulk_bonus_amount == Decimal("0.0000")
    assert opening_inventory.net_amount == opening_inventory.gross_amount - opening_inventory.fee_amount

    member_deposit = quote("500000", source_scope="wallet")
    assert member_deposit.bulk_bonus_amount == Decimal("0.0000")
    assert member_deposit.net_amount == member_deposit.gross_amount - member_deposit.fee_amount

    fan_inventory = quote("500000", unit=LedgerUnit.CREDIT)
    assert fan_inventory.bulk_bonus_amount == Decimal("0.0000")


def test_hold_approval_and_beneficiary_currency_payout(db) -> None:
    session, _, admin, referrer = db
    service = _service(session)
    external = service.create_partner(
        admin,
        {
            "display_name": "External",
            "campaign_name": "External campaign",
            "code": "EXTCODE",
        },
    )
    internal = service.create_partner(
        admin,
        {
            "display_name": "Internal",
            "campaign_name": "Internal campaign",
            "code": "INTCODE",
            "owner_user_id": referrer.id,
        },
    )
    first = _user("one@gtex.test", "one")
    second = _user("two@gtex.test", "two")
    session.add_all([first, second])
    session.flush()
    service.attribute_signup(first, "EXTCODE", account_type="user")
    service.attribute_signup(second, "INTCODE", account_type="creator")
    orders = [
        _order(first, amount_fiat="100000.00", reference="PO-EXT"),
        _order(second, amount_fiat="100000.00", currency="USD", reference="PO-INT"),
    ]
    session.add_all(orders)
    session.commit()
    rail = WalletRailService(session=session)
    for order in orders:
        rail.settle_purchase_order(order=order, actor=session.get(User, order.user_id))
    session.commit()

    external_commission = session.scalar(
        select(ReferralReward).where(
            ReferralReward.referred_user_id == first.id,
            ReferralReward.reward_type == ReferralRewardType.FIRST_DEPOSIT_COMMISSION,
        )
    )
    internal_commission = session.scalar(
        select(ReferralReward).where(
            ReferralReward.referred_user_id == second.id,
            ReferralReward.reward_type == ReferralRewardType.FIRST_DEPOSIT_COMMISSION,
        )
    )
    assert internal_commission.beneficiary_user_id == referrer.id
    assert internal_commission.referral_partner_id == internal["id"]
    assert internal_commission.status == ReferralRewardStatus.PAID
    assert internal_commission.reward_unit == LedgerUnit.COIN.value
    assert internal_commission.reward_amount == Decimal("100.0000")
    referrer_wallet = WalletService()
    assert referrer_wallet.get_balance(
        session, referrer_wallet.get_user_account(session, referrer, LedgerUnit.COIN)
    ) == Decimal("100.0000")
    with pytest.raises(FirstDepositReferralError) as already_paid:
        service.decide_commission(admin, internal_commission.id, decision="approve", reason="Already in the wallet")
    assert already_paid.value.code == "reward_not_pending"
    with pytest.raises(FirstDepositReferralError) as early:
        service.decide_commission(admin, external_commission.id, decision="approve", reason="Too early")
    assert early.value.code == "hold_active"
    external_commission.hold_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    session.flush()
    service.decide_commission(admin, external_commission.id, decision="approve", reason="Hold elapsed")

    service.update_settings(admin, {"min_payout_thresholds": {"NGN": "10000.00", "USD": "10.00"}})
    batch = service.create_payout_batch(
        admin,
        reward_ids=[external_commission.id],
        payout_method="external_transfer",
        off_cycle_reason="Reconciliation",
    )
    with pytest.raises(FirstDepositReferralError) as missing_reference:
        service.confirm_payout_batch(admin, batch["id"], external_reference="")
    assert missing_reference.value.code == "payment_reference_required"
    confirmed = service.confirm_payout_batch(admin, batch["id"], external_reference="BANK-100")
    assert confirmed["transferred_by_gtex"] is False
    again = service.confirm_payout_batch(admin, batch["id"], external_reference="BANK-100")
    assert again["id"] == confirmed["id"]
    with pytest.raises(FirstDepositReferralError) as duplicate:
        service.confirm_payout_batch(admin, batch["id"], external_reference="BANK-999")
    assert duplicate.value.code == "duplicate_payout_confirmation"
    session.refresh(external_commission)
    assert external_commission.status == ReferralRewardStatus.PAID

    other = service.create_partner(admin, {"display_name": "Other", "campaign_name": "Other", "code": "OTHER1"})
    assert other["id"] != external["id"]


def test_reversal_preserves_history_and_opens_recovery(db) -> None:
    session, _, admin, _referrer = db
    service = _service(session)
    service.create_partner(admin, {"display_name": "External", "campaign_name": "Launch", "code": "REVCODE"})
    member = _user("reversal@gtex.test", "reversal")
    session.add(member)
    session.flush()
    service.attribute_signup(member, "REVCODE", account_type="user")
    order = _order(member, amount_fiat="100000.00", reference="PO-REV")
    session.add(order)
    session.commit()
    rail = WalletRailService(session=session)
    rail.settle_purchase_order(order=order, actor=member)
    commission = session.scalar(
        select(ReferralReward).where(
            ReferralReward.referred_user_id == member.id,
            ReferralReward.reward_type == ReferralRewardType.FIRST_DEPOSIT_COMMISSION,
        )
    )
    commission.hold_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    service.decide_commission(admin, commission.id, decision="approve", reason="Hold elapsed")
    batch = service.create_payout_batch(
        admin,
        reward_ids=[commission.id],
        payout_method="external_transfer",
        off_cycle_reason="Reconciliation",
    )
    service.confirm_payout_batch(admin, batch["id"], external_reference="BANK-REV")
    ledger_before = session.scalar(select(func.count()).select_from(ReferralRewardLedger))
    rail.reverse_purchase_order(order=order, status=PurchaseOrderStatus.REFUNDED, actor=admin, notes="Refund")
    session.commit()
    session.refresh(commission)
    assert commission.status == ReferralRewardStatus.PAID
    recovery = session.scalar(select(ReferralRecoveryCase).where(ReferralRecoveryCase.reward_id == commission.id))
    assert recovery is not None
    assert recovery.kind == "paid_commission_recovery"
    ledger_after = session.scalar(select(func.count()).select_from(ReferralRewardLedger))
    assert ledger_after > ledger_before


def test_spent_bonus_records_shortfall_without_editing_history(db) -> None:
    session, _, admin, _referrer = db
    service = _service(session)
    wallets = WalletService()
    service.create_partner(admin, {"display_name": "External", "campaign_name": "Launch", "code": "SPEND1"})
    member = _user("spent@gtex.test", "spent")
    session.add(member)
    session.flush()
    service.attribute_signup(member, "SPEND1", account_type="user")
    order = _order(member, amount_fiat="100000.00", reference="PO-SPENT")
    session.add(order)
    session.commit()
    rail = WalletRailService(session=session, wallet_service=wallets)
    rail.settle_purchase_order(order=order, actor=member)
    account = wallets.get_user_account(session, member, LedgerUnit.COIN)
    balance = wallets.get_balance(session, account)
    operations = wallets.ensure_operations_account(session, LedgerUnit.COIN)
    wallets.append_transaction(
        session,
        postings=[
            LedgerPosting(account=account, amount=-balance, transaction_type=LedgerTransactionType.ADJUSTMENT),
            LedgerPosting(account=operations, amount=balance, transaction_type=LedgerTransactionType.ADJUSTMENT),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        transaction_type=LedgerTransactionType.ADJUSTMENT,
        reference="spend-all",
        description="Spend the deposit and bonus",
        actor=member,
        idempotency_key="spend-all-bonus",
    )
    session.commit()
    rail.reverse_purchase_order(order=order, status=PurchaseOrderStatus.CHARGEBACK, actor=admin, notes="Chargeback")
    session.commit()
    bonus = session.scalar(
        select(ReferralReward).where(
            ReferralReward.referred_user_id == member.id,
            ReferralReward.reward_type == ReferralRewardType.FIRST_DEPOSIT_BONUS,
        )
    )
    shortfall = session.scalar(
        select(ReferralRecoveryCase).where(
            ReferralRecoveryCase.reward_id == bonus.id,
            ReferralRecoveryCase.kind == "spent_bonus_shortfall",
        )
    )
    assert shortfall is not None
    assert Decimal(shortfall.amount) == bonus.reward_amount
    assert session.scalar(select(func.count()).select_from(ReferralRewardLedger)) > 0


def test_concurrent_settlement_creates_one_reward_pair(db) -> None:
    session, SessionLocal, admin, _referrer = db
    service = _service(session)
    service.create_partner(admin, {"display_name": "External", "campaign_name": "Launch", "code": "RACE10"})
    member = _user("race@gtex.test", "race")
    session.add(member)
    session.flush()
    service.attribute_signup(member, "RACE10", account_type="coin_trader")
    order = _order(member, amount_fiat="200000.00", reference="PO-RACE")
    session.add(order)
    session.commit()

    def replay() -> None:
        local = SessionLocal()
        try:
            local_order = local.get(FancoinPurchaseOrder, order.id)
            WalletRailService(session=local).settle_purchase_order(order=local_order, actor=local.get(User, member.id))
            local.commit()
        except Exception:
            local.rollback()
        finally:
            local.close()

    threads = [Thread(target=replay) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    count = session.scalar(
        select(func.count()).select_from(ReferralReward).where(ReferralReward.referred_user_id == member.id)
    )
    assert count == 2


def test_app_accounts_share_a_link_and_creators_earn_25_percent_in_gtex_coin(db) -> None:
    session, _, _, referrer = db
    service = _service(session)
    share = service.ensure_personal_code(referrer)
    dashboard = service.my_affiliate(referrer)
    assert dashboard["link"] == f"https://playgtex.app/signup?ref={share.code}"
    assert dashboard["your_rate_percent"] == "10"
    assert dashboard["their_rate_percent"] == "10"

    member = _user("buyer@gtex.test", "buyer")
    session.add(member)
    session.flush()
    service.attribute_signup(member, share.code, account_type="user")
    order = _order(member, amount_fiat="6000.00", rate="60", reference="PO-APP")
    session.add(order)
    session.commit()
    WalletRailService(session=session).settle_purchase_order(order=order, actor=member)
    session.commit()

    rewards = list(session.scalars(select(ReferralReward).where(ReferralReward.referred_user_id == member.id)).all())
    bonus = next(item for item in rewards if item.reward_type == ReferralRewardType.FIRST_DEPOSIT_BONUS)
    commission = next(item for item in rewards if item.reward_type == ReferralRewardType.FIRST_DEPOSIT_COMMISSION)
    assert bonus.applied_rate_bps == 1000
    assert bonus.status == ReferralRewardStatus.PAID
    assert commission.applied_rate_bps == 1000
    assert commission.status == ReferralRewardStatus.PAID
    assert commission.reward_unit == LedgerUnit.COIN.value
    assert commission.reward_amount == Decimal("10.0000")
    wallet = WalletService()
    assert wallet.get_balance(session, wallet.get_user_account(session, referrer, LedgerUnit.COIN)) == Decimal(
        "10.0000"
    )

    creator = _user("creator-ref@gtex.test", "creatorref", account_type=PublicAccountType.CREATOR)
    trader = _user("trader-ref@gtex.test", "traderref", account_type=PublicAccountType.COIN_TRADER)
    session.add_all([creator, trader])
    session.flush()
    assert service.my_affiliate(trader)["your_rate_percent"] == "10"
    creator_share = service.ensure_personal_code(creator)
    assert service.my_affiliate(creator)["your_rate_percent"] == "25"
    assert service.my_affiliate(creator)["their_rate_percent"] == "10"
    referred = _user("referred-by-creator@gtex.test", "referredcreator")
    session.add(referred)
    session.flush()
    service.attribute_signup(referred, creator_share.code, account_type="coin_trader")
    creator_order = _order(referred, amount_fiat="6000.00", rate="60", reference="PO-CREATOR")
    session.add(creator_order)
    session.commit()
    WalletRailService(session=session).settle_purchase_order(order=creator_order, actor=referred)
    session.commit()

    creator_rewards = list(
        session.scalars(select(ReferralReward).where(ReferralReward.referred_user_id == referred.id)).all()
    )
    creator_bonus = next(item for item in creator_rewards if item.reward_type == ReferralRewardType.FIRST_DEPOSIT_BONUS)
    creator_commission = next(
        item for item in creator_rewards if item.reward_type == ReferralRewardType.FIRST_DEPOSIT_COMMISSION
    )
    assert creator_bonus.applied_rate_bps == 1000
    assert creator_commission.applied_rate_bps == 2500
    assert creator_commission.status == ReferralRewardStatus.PAID
    assert creator_commission.reward_amount == Decimal("25.0000")
    assert wallet.get_balance(session, wallet.get_user_account(session, creator, LedgerUnit.COIN)) == Decimal("25.0000")


def test_admin_routes_reject_non_admins_and_serve_records(db) -> None:
    session, _, admin, _referrer = db
    member = _user("plain@gtex.test", "plain")
    session.add(member)
    session.commit()
    app = FastAPI()
    app.include_router(admin_referrals_router)
    holder = {"user": member}

    def override_user():
        return holder["user"]

    def override_session():
        yield session

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as client:
        denied = client.get("/api/admin/referrals/affiliate/overview")
        assert denied.status_code == 403
        holder["user"] = admin
        created = client.post(
            "/api/admin/referrals/affiliate/partners",
            json={
                "display_name": "Partner",
                "campaign_name": "Campaign",
                "code": "ADMIN10",
                "contact_email": "partner@outside.test",
            },
        )
        assert created.status_code == 201, created.text
        assert created.json()["owner_user_id"] is None
        overview = client.get("/api/admin/referrals/affiliate/overview")
        assert overview.status_code == 200
        assert overview.json()["partners"] >= 1
        partner_id = created.json()["id"]
        suspended = client.post(
            f"/api/admin/referrals/affiliate/partners/{partner_id}/status",
            json={"active": False, "reason": "Suspended for review"},
        )
        assert suspended.status_code == 200
        assert suspended.json()["status"] == "suspended"
        restored = client.post(
            f"/api/admin/referrals/affiliate/partners/{partner_id}/status",
            json={"active": True, "reason": "Review cleared"},
        )
        assert restored.status_code == 200
        assert restored.json()["status"] == "active"
