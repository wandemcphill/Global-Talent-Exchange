from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.auth.service import AuthService
from app.models.market_topup import MarketTopupStatus
from app.models.risk_ops import RiskActionType
from app.models.risk_ops import AuditLog
from app.models.trader import TraderMarket, TraderOrderSide
from app.models.user import KycStatus, PublicAccountType
from app.risk_ops_engine.service import RiskOpsService
from app.trader.service import (
    TraderAccessError,
    TraderFinancialBalanceUnavailableError,
    TraderMarketNotFoundError,
    TraderService,
)
from backend.tests.support.secrets import TEST_PASSWORD


@pytest.fixture()
def session(gtex_db_session):
    # Shared session-scoped schema (tests/conftest.py::gtex_db_engine) with
    # per-test rollback, instead of rebuilding all ~567 tables per test.
    yield gtex_db_session


def _create_trader(session):
    return AuthService().register_user(
        session,
        email="trader@example.com",
        username="trader",
        password=TEST_PASSWORD,
        display_name="Trader",
        account_type=PublicAccountType.COIN_TRADER,
    )


def _create_market(session) -> TraderMarket:
    market = TraderMarket(
        symbol="GTEX",
        display_name="GTEX Coin",
        asset_type="gtex_coin",
        price=Decimal("1.0000"),
        daily_change_percent=Decimal("0.0000"),
        market_cap=Decimal("1000000.0000"),
        volume_24h=Decimal("10000.0000"),
        liquidity_score=90,
    )
    session.add(market)
    session.flush()
    return market


def _verify_trader(session, trader):
    trader.kyc_status = KycStatus.VERIFIED
    service = TraderService(session)
    service.ensure_profile(
        trader,
        trading_alias="gtex-trader",
        preferred_currency="USD",
        trading_experience="beginner",
        interests=["GTEX"],
        wallet_label="GTEX Trading Wallet",
    )
    session.flush()
    return trader


def test_trader_orders_require_existing_market(session) -> None:
    trader = _create_trader(session)
    _verify_trader(session, trader)
    service = TraderService(session)

    with pytest.raises(TraderMarketNotFoundError, match="Trader market not found"):
        service.place_order(
            trader,
            market_id="missing-market",
            side=TraderOrderSide.BUY,
            quantity=Decimal("1"),
            limit_price=Decimal("1.25"),
        )


def test_trader_order_creation_stays_in_coin_trader_lane(session) -> None:
    football_user = AuthService().register_user(
        session,
        email="football@example.com",
        username="football",
        password=TEST_PASSWORD,
        display_name="Football User",
        account_type=PublicAccountType.USER,
    )
    market = _create_market(session)

    with pytest.raises(TraderAccessError, match="Coin trader account access is required"):
        TraderService(session).place_order(
            football_user,
            market_id=market.id,
            side=TraderOrderSide.BUY,
            quantity=Decimal("1"),
            limit_price=Decimal("1.25"),
        )


def test_trader_order_requires_kyc_before_trading(session) -> None:
    trader = _create_trader(session)
    service = TraderService(session)
    service.ensure_profile(
        trader,
        trading_alias="pending-trader",
        preferred_currency="USD",
        trading_experience="beginner",
        interests=["GTEX"],
        wallet_label="GTEX Trading Wallet",
    )
    market = _create_market(session)

    with pytest.raises(TraderAccessError, match="KYC verification is required"):
        service.place_order(
            trader,
            market_id=market.id,
            side=TraderOrderSide.BUY,
            quantity=Decimal("1"),
            limit_price=Decimal("1.25"),
        )


def test_trader_overview_blocks_null_financial_balance_without_zero_fallback(session) -> None:
    trader = _create_trader(session)
    _verify_trader(session, trader)
    _create_market(session)
    service = TraderService(session, wallet_service=_NullBalanceWalletService())

    with pytest.raises(TraderFinancialBalanceUnavailableError, match="Balance data unavailable"):
        service.overview(trader)


def test_trader_metrics_block_null_reserved_balance_without_zero_fallback(session) -> None:
    trader = _create_trader(session)
    _verify_trader(session, trader)
    service = TraderService(session, wallet_service=_NullReservedBalanceWalletService())

    with pytest.raises(TraderFinancialBalanceUnavailableError, match="Balance data unavailable"):
        service.sync_trader_metrics(trader)


def test_trader_order_creation_records_audit_reference(session) -> None:
    trader = _create_trader(session)
    _verify_trader(session, trader)
    market = _create_market(session)
    service = TraderService(session)

    order = service.place_order(
        trader,
        market_id=market.id,
        side=TraderOrderSide.BUY,
        quantity=Decimal("1"),
        limit_price=Decimal("1.25"),
    )

    audit_ref = getattr(order, "audit_ref", None)
    audit = session.get(AuditLog, audit_ref)
    assert audit is not None
    assert audit.action_key == "trader.order.placed"
    assert audit.actor_user_id == trader.id
    assert audit.resource_id == order.id
    assert audit.metadata_json["market_id"] == market.id
    assert audit.metadata_json["quantity"] == "1"


def test_trader_quote_uses_backend_lock_and_audit_reference(session) -> None:
    trader = _create_trader(session)
    _verify_trader(session, trader)
    market = _create_market(session)

    quote = TraderService(session).quote_order(
        trader,
        market_id=market.id,
        side=TraderOrderSide.BUY,
        amount=Decimal("10.0000"),
        currency="coin",
    )

    audit = session.get(AuditLog, quote["audit_ref"])
    assert audit is not None
    assert audit.action_key == "trader.quote.requested"
    assert quote["lock_seconds_remaining"] == 30
    assert quote["locked_until"] == quote["valid_until"]
    assert quote["id"] == audit.id


def test_trader_order_book_aggregates_open_orders_from_backend(session) -> None:
    trader = _create_trader(session)
    _verify_trader(session, trader)
    market = _create_market(session)
    service = TraderService(session)
    service.place_order(
        trader,
        market_id=market.id,
        side=TraderOrderSide.BUY,
        quantity=Decimal("2.0000"),
        limit_price=Decimal("1.2500"),
    )
    service.place_order(
        trader,
        market_id=market.id,
        side=TraderOrderSide.BUY,
        quantity=Decimal("3.0000"),
        limit_price=Decimal("1.2500"),
    )
    service.place_order(
        trader,
        market_id=market.id,
        side=TraderOrderSide.SELL,
        quantity=Decimal("1.0000"),
        limit_price=Decimal("1.5000"),
    )

    book = service.order_book(market.id)

    assert book["status"] == "live"
    assert book["bids"] == [{"price": Decimal("1.2500"), "quantity": Decimal("5.0000")}]
    assert book["asks"] == [{"price": Decimal("1.5000"), "quantity": Decimal("1.0000")}]


def test_trader_dispute_contract_is_audited_without_inventing_resolution(session) -> None:
    trader = _create_trader(session)
    _verify_trader(session, trader)
    market = _create_market(session)
    service = TraderService(session)
    order = service.place_order(
        trader,
        market_id=market.id,
        side=TraderOrderSide.BUY,
        quantity=Decimal("1.0000"),
        limit_price=Decimal("1.2500"),
    )

    dispute = service.file_dispute(trader, order_id=order.id, reason="Settlement proof mismatch.")

    assert dispute["order_id"] == order.id
    assert dispute["status"] == "pending_admin_review"
    assert dispute["resolved_at"] is None
    assert dispute["audit_ref"] == dispute["id"]
    assert service.list_disputes(trader)[0]["id"] == dispute["id"]
    assert service.get_dispute(trader, dispute_id=dispute["id"])["reason"] == "Settlement proof mismatch."


def test_trader_settlements_are_backed_by_market_topup_truth(session) -> None:
    trader = _create_trader(session)
    _verify_trader(session, trader)
    service = TraderService(session)
    topup = service.request_wholesale_procurement(
        trader,
        amount=Decimal("100.0000"),
        fee_bps=0,
        notes="Self-service wholesale buy",
    )

    settlements = service.list_settlements(trader)

    assert settlements[0]["id"] == topup.id
    assert settlements[0]["amount"] == topup.net_amount
    assert settlements[0]["status"] == topup.status.value
    assert settlements[0]["receipt_ref"] == topup.reference
    assert settlements[0]["audit_ref"]


def test_trader_korapay_withdrawal_is_blocked_and_audited(session) -> None:
    trader = _create_trader(session)
    service = TraderService(session)

    result = service.request_withdrawal(
        trader,
        amount=Decimal("25.0000"),
        currency="coin",
        method="korapay",
        destination_ref="bank-account-1",
    )

    audit = session.get(AuditLog, result["audit_ref"])
    assert result["status"] == "blocked"
    assert audit is not None
    assert audit.action_key == "trader.withdrawal.blocked"
    assert audit.metadata_json["method"] == "korapay"


def test_risk_block_prevents_coin_trader_p2p_offer(session) -> None:
    trader = _create_trader(session)
    _verify_trader(session, trader)
    market = _create_market(session)
    RiskOpsService(session).create_action(
        actor_user_id=None,
        user_id=trader.id,
        action_type=RiskActionType.BLOCK_TRADING,
        reason="Manual compliance review.",
    )

    with pytest.raises(TraderAccessError, match="Trading is temporarily blocked"):
        TraderService(session).create_p2p_offer(
            trader,
            market_id=market.id,
            side=TraderOrderSide.SELL,
            quantity=Decimal("10"),
            unit_price=Decimal("1.10"),
            preferred_currency="USD",
        )


def test_wholesale_procurement_updates_trader_liquidity_metrics(session) -> None:
    trader = _create_trader(session)
    _verify_trader(session, trader)
    service = TraderService(session)

    topup = service.request_wholesale_procurement(
        trader,
        amount=Decimal("100.0000"),
        fee_bps=0,
        notes="Self-service wholesale buy",
    )
    profile = service.sync_trader_metrics(trader)

    assert topup.status == MarketTopupStatus.REQUESTED
    assert topup.source_scope == "liquidity"
    assert topup.metadata_json["self_service"] is True
    assert profile.liquidity_snapshot_json["pending_procurements"] == 1


class _NullBalanceWalletService:
    def get_wallet_summary(self, session, user, *, currency):
        return SimpleNamespace(
            available_balance=None,
            reserved_balance=Decimal("0.0000"),
            total_balance=None,
            currency=currency,
        )


class _NullReservedBalanceWalletService:
    def get_wallet_summary(self, session, user, *, currency):
        return SimpleNamespace(
            available_balance=Decimal("10.0000"),
            reserved_balance=None,
            total_balance=Decimal("10.0000"),
            currency=currency,
        )
