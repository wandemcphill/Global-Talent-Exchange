from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.coin_traders.schemas import (
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
from app.models.coin_trader import CoinTradeOrderStatus, CoinTraderProfileStatus
from app.models.notification_record import NotificationRecord
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
    service.upsert_rate(
        CoinTraderRateUpsertRequest(
            coin_unit=coin_unit,
            fiat_currency="NGN",
            buy_rate_fiat=Decimal("0.90"),
            sell_rate_fiat=Decimal("1.05"),
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
    assert order.fiat_total == Decimal("5250.0000")

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
