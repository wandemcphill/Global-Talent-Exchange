from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.coin_traders.schemas import (
    CoinTraderAdminLiquidityRequest,
    CoinTradeAdminResolutionRequest,
    CoinTradeDisputeRequest,
    CoinTradeOrderCreateRequest,
    CoinTradeProofRequest,
    CoinTraderAdminDecisionRequest,
    CoinTraderAdminRejectRequest,
    CoinTraderProfileCreateRequest,
    CoinTraderRateUpsertRequest,
)
from app.coin_traders.service import CoinTraderPermissionError, CoinTraderService, CoinTraderValidationError
from app.models.base import Base
from app.models.coin_trader import CoinTradeOrderStatus, CoinTraderProfileStatus, CoinTraderRate
from app.models.notification_record import NotificationRecord
from app.models.risk_ops import SystemEvent
from app.models.user import KycStatus, User, UserRole
from app.models.wallet import LedgerSourceTag, LedgerUnit
from app.wallets.service import WalletService


@pytest.fixture()
def coin_trader_session() -> Session:
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


def _seed_users(session: Session) -> dict[str, User]:
    admin = User(
        id="admin-1",
        email="admin@example.com",
        username="admin",
        display_name="Admin",
        password_hash="x",
        role=UserRole.ADMIN,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    trader = User(
        id="trader-1",
        email="trader@example.com",
        username="trader",
        display_name="Trader",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    buyer = User(
        id="buyer-1",
        email="buyer@example.com",
        username="buyer",
        display_name="Buyer",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    second_buyer = User(
        id="buyer-2",
        email="buyer2@example.com",
        username="buyer2",
        display_name="Buyer Two",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    session.add_all([admin, trader, buyer, second_buyer])
    session.commit()
    return {"admin": admin, "trader": trader, "buyer": buyer, "second_buyer": second_buyer}


def _approve_trader_with_rate(
    service: CoinTraderService,
    users: dict[str, User],
    *,
    coin_unit: LedgerUnit = LedgerUnit.COIN,
    available_liquidity: Decimal = Decimal("100000"),
):
    profile = service.create_or_update_profile(
        CoinTraderProfileCreateRequest(
            display_name="Lagos Desk",
            country_code="NG",
            terms={"same_name_only": True, "escrow": True},
            payment_methods=[{"type": "bank_transfer"}],
            bank_accounts=[{"bank": "GTBank"}],
        ),
        actor=users["trader"],
    )
    service.approve_trader(
        profile.id,
        CoinTraderAdminDecisionRequest(tier="gold", note="verified liquidity"),
        admin=users["admin"],
    )
    buy_rate = Decimal("860") if coin_unit == LedgerUnit.COIN else Decimal("0.90")
    sell_rate = Decimal("920") if coin_unit == LedgerUnit.COIN else Decimal("1.05")
    service.upsert_rate(
        CoinTraderRateUpsertRequest(
            coin_unit=coin_unit,
            fiat_currency="NGN",
            buy_rate_fiat=buy_rate,
            sell_rate_fiat=sell_rate,
            min_coin_amount=Decimal("1000"),
            max_coin_amount=Decimal("50000"),
            available_liquidity=available_liquidity,
        ),
        actor=users["trader"],
    )
    return profile


def test_coin_trader_buy_order_locks_and_releases_escrow(coin_trader_session: Session) -> None:
    users = _seed_users(coin_trader_session)
    wallet_service = WalletService()
    service = CoinTraderService(coin_trader_session, wallet_service=wallet_service)
    wallet_service.credit_trade_proceeds(
        coin_trader_session,
        user=users["trader"],
        amount=Decimal("100000.0000"),
        unit=LedgerUnit.COIN,
        reference="seed:trader-liquidity",
        description="Seed trader liquidity",
        external_reference="seed",
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
    )
    coin_trader_session.commit()

    profile = _approve_trader_with_rate(service, users)
    assert users["trader"].role == UserRole.COIN_TRADER
    assert service.get_my_profile(users["trader"]).status == CoinTraderProfileStatus.APPROVED.value

    order = service.create_order(
        CoinTradeOrderCreateRequest(
            trader_profile_id=profile.id,
            direction="user_buys",
            coin_unit=LedgerUnit.COIN,
            coin_amount=Decimal("5000"),
            fiat_currency="NGN",
            payment_method="bank_transfer",
            idempotency_key="order-key-123",
        ),
        actor=users["buyer"],
    )
    assert order.fiat_total == Decimal("4600000")

    accepted = service.accept_order(order.id, actor=users["trader"])
    assert accepted.status == CoinTradeOrderStatus.PAYMENT_PENDING.value
    trader_summary = wallet_service.get_wallet_summary(coin_trader_session, users["trader"], currency=LedgerUnit.COIN)
    assert trader_summary.reserved_balance == Decimal("5000.0000")

    with pytest.raises(CoinTraderValidationError):
        service.confirm_and_release(order.id, actor=users["trader"])
    with pytest.raises(CoinTraderPermissionError):
        service.submit_proof(
            order.id,
            CoinTradeProofRequest(proof_reference="wrong-side"),
            actor=users["trader"],
        )
    proof = service.submit_proof(
        order.id,
        CoinTradeProofRequest(proof_reference="buyer-receipt"),
        actor=users["buyer"],
    )
    assert proof.status == CoinTradeOrderStatus.PROOF_SUBMITTED.value

    released = service.confirm_and_release(order.id, actor=users["trader"])
    assert released.status == CoinTradeOrderStatus.RELEASED.value
    buyer_summary = wallet_service.get_wallet_summary(coin_trader_session, users["buyer"], currency=LedgerUnit.COIN)
    assert buyer_summary.available_balance == Decimal("5000.0000")
    trader_summary = wallet_service.get_wallet_summary(coin_trader_session, users["trader"], currency=LedgerUnit.COIN)
    assert trader_summary.reserved_balance == Decimal("0.0000")
    template_keys = {
        item.template_key
        for item in coin_trader_session.scalars(
            select(NotificationRecord).where(NotificationRecord.resource_id == order.id)
        ).all()
    }
    assert {
        "coin_trader.order.accepted",
        "escrow.locked",
        "payment.confirmed",
        "coins.released",
    }.issubset(template_keys)
    profile_view = service.get_my_profile(users["trader"])
    assert profile_view.completed_volume_fiat == Decimal("4600000.0000")
    assert profile_view.completion_rate == 100.0
    assert profile_view.average_release_minutes > 0


def test_admin_issues_and_redeems_coin_trader_liquidity_idempotently(coin_trader_session: Session) -> None:
    users = _seed_users(coin_trader_session)
    wallet_service = WalletService()
    service = CoinTraderService(coin_trader_session, wallet_service=wallet_service)
    profile = _approve_trader_with_rate(service, users, available_liquidity=Decimal("5000"))

    issued = service.admin_issue_liquidity(
        profile.id,
        CoinTraderAdminLiquidityRequest(
            coin_unit=LedgerUnit.COIN,
            amount=Decimal("2500"),
            reference="admin-liquidity-issue-001",
            idempotency_key="admin-issue-key-001",
            note="operator sold inventory to trader",
        ),
        admin=users["admin"],
    )
    assert issued.flow == "issue"
    assert issued.available_balance == Decimal("2500.0000")
    assert issued.ledger_entry_ids
    repeated = service.admin_issue_liquidity(
        profile.id,
        CoinTraderAdminLiquidityRequest(
            coin_unit=LedgerUnit.COIN,
            amount=Decimal("2500"),
            reference="admin-liquidity-issue-001",
            idempotency_key="admin-issue-key-001",
        ),
        admin=users["admin"],
    )
    assert repeated.transaction_id == issued.transaction_id
    trader_summary = wallet_service.get_wallet_summary(coin_trader_session, users["trader"], currency=LedgerUnit.COIN)
    assert trader_summary.available_balance == Decimal("2500.0000")
    with pytest.raises(CoinTraderValidationError, match="idempotency key"):
        service.admin_issue_liquidity(
            profile.id,
            CoinTraderAdminLiquidityRequest(
                coin_unit=LedgerUnit.COIN,
                amount=Decimal("2600"),
                reference="admin-liquidity-issue-001",
                idempotency_key="admin-issue-key-001",
            ),
            admin=users["admin"],
        )

    redeemed = service.admin_redeem_liquidity(
        profile.id,
        CoinTraderAdminLiquidityRequest(
            coin_unit=LedgerUnit.COIN,
            amount=Decimal("1000"),
            reference="admin-liquidity-redeem-001",
            idempotency_key="admin-redeem-key-001",
            note="operator bought back inventory",
        ),
        admin=users["admin"],
    )
    assert redeemed.flow == "redeem"
    assert redeemed.available_balance == Decimal("1500.0000")
    trader_summary = wallet_service.get_wallet_summary(coin_trader_session, users["trader"], currency=LedgerUnit.COIN)
    assert trader_summary.available_balance == Decimal("1500.0000")

    with pytest.raises(CoinTraderValidationError, match="below redemption amount"):
        service.admin_redeem_liquidity(
            profile.id,
            CoinTraderAdminLiquidityRequest(coin_unit=LedgerUnit.COIN, amount=Decimal("2000")),
            admin=users["admin"],
        )


def test_admin_liquidity_keeps_gtex_coin_and_fan_coin_balances_distinct(coin_trader_session: Session) -> None:
    users = _seed_users(coin_trader_session)
    wallet_service = WalletService()
    service = CoinTraderService(coin_trader_session, wallet_service=wallet_service)
    profile = _approve_trader_with_rate(service, users, coin_unit=LedgerUnit.COIN, available_liquidity=Decimal("5000"))
    service.upsert_rate(
        CoinTraderRateUpsertRequest(
            coin_unit=LedgerUnit.CREDIT,
            fiat_currency="NGN",
            buy_rate_fiat=Decimal("0.90"),
            sell_rate_fiat=Decimal("1.05"),
            min_coin_amount=Decimal("100"),
            max_coin_amount=Decimal("50000"),
            available_liquidity=Decimal("9000"),
        ),
        actor=users["trader"],
    )

    service.admin_issue_liquidity(
        profile.id,
        CoinTraderAdminLiquidityRequest(coin_unit=LedgerUnit.COIN, amount=Decimal("1200")),
        admin=users["admin"],
    )
    service.admin_issue_liquidity(
        profile.id,
        CoinTraderAdminLiquidityRequest(coin_unit=LedgerUnit.CREDIT, amount=Decimal("3400")),
        admin=users["admin"],
    )

    coin_summary = wallet_service.get_wallet_summary(coin_trader_session, users["trader"], currency=LedgerUnit.COIN)
    credit_summary = wallet_service.get_wallet_summary(coin_trader_session, users["trader"], currency=LedgerUnit.CREDIT)
    assert coin_summary.available_balance == Decimal("1200.0000")
    assert credit_summary.available_balance == Decimal("3400.0000")
    profile_view = service.get_my_profile(users["trader"])
    liquidity_by_unit = {rate.coin_unit: rate.available_liquidity for rate in profile_view.rates}
    assert liquidity_by_unit[LedgerUnit.COIN] == Decimal("1200.0000")
    assert liquidity_by_unit[LedgerUnit.CREDIT] == Decimal("3400.0000")


def test_coin_trader_displayed_liquidity_is_capped_by_wallet_balance(coin_trader_session: Session) -> None:
    users = _seed_users(coin_trader_session)
    wallet_service = WalletService()
    service = CoinTraderService(coin_trader_session, wallet_service=wallet_service)
    wallet_service.credit_trade_proceeds(
        coin_trader_session,
        user=users["trader"],
        amount=Decimal("1000.0000"),
        unit=LedgerUnit.COIN,
        reference="seed:stale-liquidity-wallet",
        description="Seed limited trader liquidity",
        external_reference="seed",
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
    )
    coin_trader_session.commit()
    profile = _approve_trader_with_rate(service, users, available_liquidity=Decimal("50000"))

    profile_view = service.get_profile(profile.id)
    assert profile_view.rates[0].available_liquidity == Decimal("1000.0000")
    assert profile_view.liquidity_snapshot["coin:NGN"]["available_liquidity"] == "1000.0000"
    assert profile_view.liquidity_snapshot["coin:NGN"]["claimed_available_liquidity"] == "50000.0000"

    with pytest.raises(CoinTraderValidationError, match="liquidity"):
        service.create_order(
            CoinTradeOrderCreateRequest(
                trader_profile_id=profile.id,
                direction="user_buys",
                coin_unit=LedgerUnit.COIN,
                coin_amount=Decimal("1500"),
                fiat_currency="NGN",
                payment_method="bank_transfer",
                idempotency_key="stale-liquidity-order-key",
            ),
            actor=users["buyer"],
        )


def test_coin_trade_order_idempotency_is_scoped_to_actor(coin_trader_session: Session) -> None:
    users = _seed_users(coin_trader_session)
    wallet_service = WalletService()
    service = CoinTraderService(coin_trader_session, wallet_service=wallet_service)
    wallet_service.credit_trade_proceeds(
        coin_trader_session,
        user=users["trader"],
        amount=Decimal("100000.0000"),
        unit=LedgerUnit.COIN,
        reference="seed:trader-idempotency-liquidity",
        description="Seed trader liquidity",
        external_reference="seed",
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
    )
    coin_trader_session.commit()
    profile = _approve_trader_with_rate(service, users)

    payload = CoinTradeOrderCreateRequest(
        trader_profile_id=profile.id,
        direction="user_buys",
        coin_unit=LedgerUnit.COIN,
        coin_amount=Decimal("5000"),
        fiat_currency="NGN",
        payment_method="bank_transfer",
        idempotency_key="shared-order-key-123",
    )
    first = service.create_order(payload, actor=users["buyer"])
    retried = service.create_order(payload, actor=users["buyer"])
    assert retried.id == first.id

    with pytest.raises(CoinTraderValidationError):
        service.create_order(payload, actor=users["second_buyer"])


def test_coin_trade_cancel_active_escrow_refunds_locked_party(coin_trader_session: Session) -> None:
    users = _seed_users(coin_trader_session)
    wallet_service = WalletService()
    service = CoinTraderService(coin_trader_session, wallet_service=wallet_service)
    wallet_service.credit_trade_proceeds(
        coin_trader_session,
        user=users["trader"],
        amount=Decimal("100000.0000"),
        unit=LedgerUnit.COIN,
        reference="seed:trader-cancel-liquidity",
        description="Seed trader liquidity",
        external_reference="seed",
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
    )
    coin_trader_session.commit()
    profile = _approve_trader_with_rate(service, users)
    order = service.create_order(
        CoinTradeOrderCreateRequest(
            trader_profile_id=profile.id,
            direction="user_buys",
            coin_unit=LedgerUnit.COIN,
            coin_amount=Decimal("5000"),
            fiat_currency="NGN",
            payment_method="bank_transfer",
            idempotency_key="cancel-order-key-123",
        ),
        actor=users["buyer"],
    )
    service.accept_order(order.id, actor=users["trader"])
    trader_summary = wallet_service.get_wallet_summary(coin_trader_session, users["trader"], currency=LedgerUnit.COIN)
    assert trader_summary.reserved_balance == Decimal("5000.0000")

    cancelled = service.cancel_order(order.id, actor=users["buyer"])
    assert cancelled.status == CoinTradeOrderStatus.REFUNDED.value
    trader_summary = wallet_service.get_wallet_summary(coin_trader_session, users["trader"], currency=LedgerUnit.COIN)
    buyer_summary = wallet_service.get_wallet_summary(coin_trader_session, users["buyer"], currency=LedgerUnit.COIN)
    assert trader_summary.reserved_balance == Decimal("0.0000")
    assert trader_summary.available_balance == Decimal("100000.0000")
    assert buyer_summary.available_balance == Decimal("0.0000")


def test_coin_trader_sell_order_locks_user_coin_and_releases_to_trader(coin_trader_session: Session) -> None:
    users = _seed_users(coin_trader_session)
    wallet_service = WalletService()
    service = CoinTraderService(coin_trader_session, wallet_service=wallet_service)
    wallet_service.credit_trade_proceeds(
        coin_trader_session,
        user=users["buyer"],
        amount=Decimal("20000.0000"),
        unit=LedgerUnit.CREDIT,
        reference="seed:user-fan-coin",
        description="Seed user fan coin",
        external_reference="seed",
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
    )
    coin_trader_session.commit()
    profile = _approve_trader_with_rate(
        service,
        users,
        coin_unit=LedgerUnit.CREDIT,
        available_liquidity=Decimal("0"),
    )

    order = service.create_order(
        CoinTradeOrderCreateRequest(
            trader_profile_id=profile.id,
            direction="user_sells",
            coin_unit=LedgerUnit.CREDIT,
            coin_amount=Decimal("4000"),
            fiat_currency="NGN",
            payment_method="bank_transfer",
            idempotency_key="sell-order-key-123",
        ),
        actor=users["buyer"],
    )
    assert order.fiat_total == Decimal("3600.0000")

    accepted = service.accept_order(order.id, actor=users["trader"])
    assert accepted.escrow_owner_user_id == users["buyer"].id
    seller_summary = wallet_service.get_wallet_summary(coin_trader_session, users["buyer"], currency=LedgerUnit.CREDIT)
    assert seller_summary.reserved_balance == Decimal("4000.0000")

    with pytest.raises(CoinTraderPermissionError):
        service.submit_proof(
            order.id,
            CoinTradeProofRequest(proof_reference="wrong-side"),
            actor=users["buyer"],
        )
    service.submit_proof(
        order.id,
        CoinTradeProofRequest(proof_reference="trader-fiat-transfer"),
        actor=users["trader"],
    )
    released = service.confirm_and_release(order.id, actor=users["buyer"])
    assert released.status == CoinTradeOrderStatus.RELEASED.value
    seller_summary = wallet_service.get_wallet_summary(coin_trader_session, users["buyer"], currency=LedgerUnit.CREDIT)
    trader_summary = wallet_service.get_wallet_summary(coin_trader_session, users["trader"], currency=LedgerUnit.CREDIT)
    assert seller_summary.reserved_balance == Decimal("0.0000")
    assert trader_summary.available_balance == Decimal("4000.0000")


def test_coin_trader_rate_view_includes_governance_status(coin_trader_session: Session) -> None:
    users = _seed_users(coin_trader_session)
    service = CoinTraderService(coin_trader_session, wallet_service=WalletService())
    profile = _approve_trader_with_rate(service, users)

    profile_view = service.get_my_profile(users["trader"])
    rate_view = profile_view.rates[0]

    assert profile_view.verification_level == "standard"
    assert profile_view.completed_volume_fiat == Decimal("0.0000")
    assert profile.id == rate_view.trader_profile_id
    assert rate_view.buy_rate_fiat == Decimal("860")
    assert rate_view.sell_rate_fiat == Decimal("920")
    assert rate_view.spread_fiat == Decimal("60.0000")
    assert rate_view.treasury_deposit_rate_fiat == Decimal("900.0000")
    assert rate_view.treasury_withdrawal_rate_fiat == Decimal("880.0000")
    assert rate_view.min_trader_buy_rate_fiat == Decimal("820.0000")
    assert rate_view.max_trader_buy_rate_fiat == Decimal("890.0000")
    assert rate_view.min_trader_sell_rate_fiat == Decimal("900.0000")
    assert rate_view.max_trader_sell_rate_fiat == Decimal("980.0000")
    assert rate_view.max_trader_spread_fiat == Decimal("120.0000")
    assert rate_view.governance_status == "compliant"
    assert rate_view.governance_reasons == []


def test_coin_trader_invalid_sell_rate_is_blocked_and_risk_flagged(coin_trader_session: Session) -> None:
    users = _seed_users(coin_trader_session)
    service = CoinTraderService(coin_trader_session, wallet_service=WalletService())
    _approve_trader_with_rate(service, users)

    with pytest.raises(CoinTraderValidationError, match="undercuts treasury deposit"):
        service.upsert_rate(
            CoinTraderRateUpsertRequest(
                coin_unit=LedgerUnit.COIN,
                fiat_currency="NGN",
                buy_rate_fiat=Decimal("860"),
                sell_rate_fiat=Decimal("890"),
                min_coin_amount=Decimal("1000"),
                max_coin_amount=Decimal("50000"),
                available_liquidity=Decimal("50000"),
            ),
            actor=users["trader"],
        )

    event = coin_trader_session.scalar(
        select(SystemEvent).where(SystemEvent.event_type == "coin_trader_pricing_governance")
    )
    assert event is not None
    assert event.subject_type == "coin_trader_profile"
    assert event.metadata_json["action"] == "upsert"
    assert event.metadata_json["status"] == "arbitrage_risk"
    assert "undercuts treasury deposit" in " ".join(event.metadata_json["reasons"])


def test_coin_trader_invalid_buy_rate_and_spread_are_blocked(coin_trader_session: Session) -> None:
    users = _seed_users(coin_trader_session)
    service = CoinTraderService(coin_trader_session, wallet_service=WalletService())
    _approve_trader_with_rate(service, users)

    with pytest.raises(CoinTraderValidationError, match="exceeds treasury withdrawal"):
        service.upsert_rate(
            CoinTraderRateUpsertRequest(
                coin_unit=LedgerUnit.COIN,
                fiat_currency="NGN",
                buy_rate_fiat=Decimal("900"),
                sell_rate_fiat=Decimal("960"),
                min_coin_amount=Decimal("1000"),
                max_coin_amount=Decimal("50000"),
                available_liquidity=Decimal("50000"),
            ),
            actor=users["trader"],
        )

    with pytest.raises(CoinTraderValidationError, match="exceeds maximum"):
        service.upsert_rate(
            CoinTraderRateUpsertRequest(
                coin_unit=LedgerUnit.COIN,
                fiat_currency="NGN",
                buy_rate_fiat=Decimal("820"),
                sell_rate_fiat=Decimal("980"),
                min_coin_amount=Decimal("1000"),
                max_coin_amount=Decimal("50000"),
                available_liquidity=Decimal("50000"),
            ),
            actor=users["trader"],
        )


def test_existing_out_of_bounds_coin_trader_rate_is_readable_but_cannot_order(
    coin_trader_session: Session,
) -> None:
    users = _seed_users(coin_trader_session)
    wallet_service = WalletService()
    service = CoinTraderService(coin_trader_session, wallet_service=wallet_service)
    wallet_service.credit_trade_proceeds(
        coin_trader_session,
        user=users["trader"],
        amount=Decimal("100000.0000"),
        unit=LedgerUnit.COIN,
        reference="seed:trader-invalid-rate-liquidity",
        description="Seed trader liquidity",
        external_reference="seed",
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
    )
    coin_trader_session.commit()
    profile = _approve_trader_with_rate(service, users)
    rate = coin_trader_session.scalar(select(CoinTraderRate).where(CoinTraderRate.trader_profile_id == profile.id))
    assert rate is not None
    rate.sell_rate_fiat = Decimal("700")
    coin_trader_session.commit()

    profile_view = service.get_my_profile(users["trader"])
    assert profile_view.rates[0].governance_status == "arbitrage_risk"
    assert profile_view.rates[0].governance_reasons

    with pytest.raises(CoinTraderValidationError, match="undercuts treasury deposit"):
        service.create_order(
            CoinTradeOrderCreateRequest(
                trader_profile_id=profile.id,
                direction="user_buys",
                coin_unit=LedgerUnit.COIN,
                coin_amount=Decimal("5000"),
                fiat_currency="NGN",
                payment_method="bank_transfer",
                idempotency_key="invalid-rate-order-key-123",
            ),
            actor=users["buyer"],
        )


def test_fan_coin_rates_stay_separate_from_gtex_coin_guardrails(coin_trader_session: Session) -> None:
    users = _seed_users(coin_trader_session)
    service = CoinTraderService(coin_trader_session, wallet_service=WalletService())
    _approve_trader_with_rate(
        service,
        users,
        coin_unit=LedgerUnit.CREDIT,
        available_liquidity=Decimal("0"),
    )

    rate_view = service.get_my_profile(users["trader"]).rates[0]
    assert rate_view.coin_unit == LedgerUnit.CREDIT
    assert rate_view.governance_status == "compliant"
    assert rate_view.treasury_deposit_rate_fiat is None
    assert rate_view.treasury_withdrawal_rate_fiat is None


def test_disputed_coin_trade_requires_admin_resolution(coin_trader_session: Session) -> None:
    users = _seed_users(coin_trader_session)
    wallet_service = WalletService()
    service = CoinTraderService(coin_trader_session, wallet_service=wallet_service)
    wallet_service.credit_trade_proceeds(
        coin_trader_session,
        user=users["trader"],
        amount=Decimal("100000.0000"),
        unit=LedgerUnit.COIN,
        reference="seed:trader-liquidity",
        description="Seed trader liquidity",
        external_reference="seed",
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
    )
    coin_trader_session.commit()
    profile = _approve_trader_with_rate(service, users)
    order = service.create_order(
        CoinTradeOrderCreateRequest(
            trader_profile_id=profile.id,
            direction="user_buys",
            coin_unit=LedgerUnit.COIN,
            coin_amount=Decimal("5000"),
            fiat_currency="NGN",
            payment_method="bank_transfer",
            idempotency_key="disputed-order-key-123",
        ),
        actor=users["buyer"],
    )

    service.accept_order(order.id, actor=users["trader"])
    disputed = service.dispute_order(
        order.id,
        payload=CoinTradeDisputeRequest(reason="payment mismatch"),
        actor=users["buyer"],
    )
    assert disputed.status == CoinTradeOrderStatus.DISPUTED.value
    assert service.get_my_profile(users["trader"]).dispute_score == 100.0

    with pytest.raises(CoinTraderValidationError):
        service.confirm_and_release(order.id, actor=users["trader"])

    resolved = service.admin_resolve_order(
        order.id,
        payload=CoinTradeAdminResolutionRequest(resolution="release"),
        admin=users["admin"],
    )
    assert resolved.status == CoinTradeOrderStatus.ADMIN_RELEASED.value
    buyer_summary = wallet_service.get_wallet_summary(coin_trader_session, users["buyer"], currency=LedgerUnit.COIN)
    assert buyer_summary.available_balance == Decimal("5000.0000")
    profile_view = service.get_my_profile(users["trader"])
    assert profile_view.completed_volume_fiat == Decimal("4600000.0000")
    assert profile_view.dispute_score == 100.0


def test_frozen_or_rejected_coin_trader_cannot_trade(coin_trader_session: Session) -> None:
    users = _seed_users(coin_trader_session)
    wallet_service = WalletService()
    service = CoinTraderService(coin_trader_session, wallet_service=wallet_service)
    wallet_service.credit_trade_proceeds(
        coin_trader_session,
        user=users["trader"],
        amount=Decimal("100000.0000"),
        unit=LedgerUnit.COIN,
        reference="seed:trader-frozen-liquidity",
        description="Seed trader liquidity",
        external_reference="seed",
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
    )
    coin_trader_session.commit()
    profile = _approve_trader_with_rate(service, users)
    service.freeze_trader(profile.id, admin=users["admin"], note="risk review")

    with pytest.raises(CoinTraderValidationError):
        service.create_order(
            CoinTradeOrderCreateRequest(
                trader_profile_id=profile.id,
                direction="user_buys",
                coin_unit=LedgerUnit.COIN,
                coin_amount=Decimal("5000"),
                fiat_currency="NGN",
                payment_method="bank_transfer",
                idempotency_key="frozen-order-key-123",
            ),
            actor=users["buyer"],
        )
    with pytest.raises(CoinTraderPermissionError):
        service.upsert_rate(
            CoinTraderRateUpsertRequest(
                coin_unit=LedgerUnit.COIN,
                fiat_currency="NGN",
                buy_rate_fiat=Decimal("0.80"),
                sell_rate_fiat=Decimal("1.10"),
                min_coin_amount=Decimal("1000"),
                max_coin_amount=Decimal("50000"),
                available_liquidity=Decimal("50000"),
            ),
            actor=users["trader"],
        )

    service.reject_trader(profile.id, CoinTraderAdminRejectRequest(note="compliance failed"), admin=users["admin"])
    assert service.get_my_profile(users["trader"]).status == CoinTraderProfileStatus.REJECTED.value

    with pytest.raises(CoinTraderValidationError):
        service.create_order(
            CoinTradeOrderCreateRequest(
                trader_profile_id=profile.id,
                direction="user_buys",
                coin_unit=LedgerUnit.COIN,
                coin_amount=Decimal("5000"),
                fiat_currency="NGN",
                payment_method="bank_transfer",
                idempotency_key="rejected-order-key-123",
            ),
            actor=users["buyer"],
        )


def test_admin_cannot_approve_own_coin_trader_profile(coin_trader_session: Session) -> None:
    users = _seed_users(coin_trader_session)
    service = CoinTraderService(coin_trader_session)
    profile = service.create_or_update_profile(
        CoinTraderProfileCreateRequest(display_name="Admin Desk", country_code="NG"),
        actor=users["admin"],
    )

    with pytest.raises(CoinTraderValidationError):
        service.approve_trader(profile.id, CoinTraderAdminDecisionRequest(tier="gold"), admin=users["admin"])
