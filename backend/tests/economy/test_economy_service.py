from __future__ import annotations

from decimal import Decimal
from shutil import copyfile

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
import pytest

import app.models.admin_rules  # noqa: F401
import app.models.economy_config  # noqa: F401
import app.models.wallet  # noqa: F401
from app.core.database import ensure_database_schema_current
from app.economy.governor_service import EconomyGovernorService
from app.economy.economy_service import EconomyService
from app.economy.pricing_engine import PricingEngine
from app.models.admin_rules import AdminRewardRule
from app.models.economy_config import ServicePricingRule
from app.models.user import User, UserRole
from app.models.wallet import (
    LedgerAccount,
    LedgerAccountKind,
    LedgerEntry,
    LedgerSourceTag,
    LedgerTransactionType,
    LedgerUnit,
)
from app.reward_engine.service import RewardEngineService
from app.wallets.service import LedgerPosting, WalletService
from backend.tests.support.economic_policy import seed_economic_policy


@pytest.fixture(scope="session")
def migrated_economy_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("economy-service-db") / "template.db"
    engine = create_engine(
        f"sqlite+pysqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    ensure_database_schema_current(engine)
    engine.dispose()
    return db_path


@pytest.fixture()
def session(tmp_path, migrated_economy_db):
    db_path = tmp_path / "economy-service.db"
    copyfile(migrated_economy_db, db_path)
    engine = create_engine(
        f"sqlite+pysqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session
    engine.dispose()


def _create_user(
    session,
    *,
    user_id: str,
    email: str,
    username: str,
    role: UserRole = UserRole.USER,
) -> User:
    user = User(
        id=user_id,
        email=email,
        username=username,
        password_hash="hashed",
        role=role,
    )
    session.add(user)
    session.flush()
    WalletService().ensure_default_accounts(session, user)
    session.flush()
    return user


def _seed_balance(session, wallet: WalletService, *, user: User, unit: LedgerUnit, amount: Decimal) -> None:
    user_account = wallet.get_user_account(session, user, unit)
    platform_account = wallet.ensure_platform_account(session, unit)
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=amount),
            LedgerPosting(account=platform_account, amount=-amount),
        ],
        reason=wallet.trade_settlement_reason,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        reference=f"seed:{user.id}:{unit.value}",
        actor=user,
    )


def _create_escrow_account(session, *, code: str, label: str, unit: LedgerUnit) -> LedgerAccount:
    account = LedgerAccount(
        code=code,
        label=label,
        unit=unit,
        kind=LedgerAccountKind.ESCROW,
    )
    session.add(account)
    session.flush()
    return account


def _seed_system_balance(
    session,
    wallet: WalletService,
    *,
    account: LedgerAccount,
    unit: LedgerUnit,
    amount: Decimal,
    actor: User,
) -> None:
    operations_account = wallet.ensure_operations_account(session, unit)
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=account, amount=amount),
            LedgerPosting(account=operations_account, amount=-amount),
        ],
        reason=wallet.trade_settlement_reason,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        reference=f"seed-system:{account.code}",
        actor=actor,
    )


def _create_reward_rule(
    session,
    *,
    trading_fee_bps: int = 2000,
    competition_platform_fee_bps: int = 1000,
) -> AdminRewardRule:
    # migrated_economy_db runs the full migration chain, which now seeds
    # 'platform-economy-defaults' itself (0113/0114). A raw insert here
    # collided with that row on rule_key; upsert onto it instead.
    return seed_economic_policy(
        session,
        title="Platform defaults",
        description="Default configurable fee envelope.",
        trading_fee_bps=trading_fee_bps,
        competition_platform_fee_bps=competition_platform_fee_bps,
    )


def _create_service_pricing_rule(
    session,
    *,
    service_key: str,
    price_coin: Decimal,
    price_fancoin_equivalent: Decimal,
) -> ServicePricingRule:
    rule = ServicePricingRule(
        service_key=service_key,
        title=service_key.replace("-", " ").title(),
        description="Economy test rule",
        price_coin=price_coin,
        price_fancoin_equivalent=price_fancoin_equivalent,
        active=True,
    )
    session.add(rule)
    session.flush()
    return rule


def test_pricing_engine_quotes_dual_currency_service_amounts(session) -> None:
    _create_service_pricing_rule(
        session,
        service_key="competitive-match-entry",
        price_coin=Decimal("1.0000"),
        price_fancoin_equivalent=Decimal("100.0000"),
    )

    quote = PricingEngine(session).quote_service("competitive-match-entry", quantity=2)

    assert quote.gtex_amount == Decimal("2.0000")
    assert quote.fancoin_amount == Decimal("200.0000")
    assert quote.amount_for_unit(LedgerUnit.COIN) == Decimal("2.0000")
    assert quote.amount_for_unit(LedgerUnit.CREDIT) == Decimal("200.0000")


def test_pricing_engine_backfills_missing_fancoin_price_from_wallet_conversion(session) -> None:
    _create_service_pricing_rule(
        session,
        service_key="fast-match-entry",
        price_coin=Decimal("0.2500"),
        price_fancoin_equivalent=Decimal("0.0000"),
    )

    quote = PricingEngine(session).quote_service("fast-match-entry")

    assert quote.gtex_amount == Decimal("0.2500")
    assert quote.fancoin_amount == Decimal("25.0000")


def test_collect_match_entry_supports_coin_and_fancoin_payments(session) -> None:
    wallet = WalletService()
    user = _create_user(session, user_id="entry-user", email="entry@example.com", username="entry-user")
    _create_reward_rule(session, competition_platform_fee_bps=1000)
    _create_service_pricing_rule(
        session,
        service_key="tournament-entry",
        price_coin=Decimal("1.0000"),
        price_fancoin_equivalent=Decimal("100.0000"),
    )
    _seed_balance(session, wallet, user=user, unit=LedgerUnit.COIN, amount=Decimal("5.0000"))
    _seed_balance(session, wallet, user=user, unit=LedgerUnit.CREDIT, amount=Decimal("500.0000"))

    economy = EconomyService(session=session, wallet_service=wallet)

    coin_escrow = _create_escrow_account(
        session,
        code="match:coin:escrow",
        label="Coin Match Escrow",
        unit=LedgerUnit.COIN,
    )
    coin_platform = wallet.ensure_platform_account(session, LedgerUnit.COIN)
    coin_result = economy.collect_match_entry(
        user=user,
        payment_unit=LedgerUnit.COIN,
        service_key="tournament-entry",
        destination_account=coin_escrow,
        fee_account=coin_platform,
        reference="coin-entry",
        actor=user,
    )

    credit_escrow = _create_escrow_account(
        session,
        code="match:credit:escrow",
        label="Credit Match Escrow",
        unit=LedgerUnit.CREDIT,
    )
    credit_platform = wallet.ensure_platform_account(session, LedgerUnit.CREDIT)
    credit_result = economy.collect_match_entry(
        user=user,
        payment_unit=LedgerUnit.CREDIT,
        service_key="tournament-entry",
        destination_account=credit_escrow,
        fee_account=credit_platform,
        reference="credit-entry",
        actor=user,
    )
    coin_entry_types = {
        entry.transaction_type
        for entry in session.scalars(select(LedgerEntry).where(LedgerEntry.reference == "coin-entry")).all()
    }
    credit_entry_types = {
        entry.transaction_type
        for entry in session.scalars(select(LedgerEntry).where(LedgerEntry.reference == "credit-entry")).all()
    }

    assert coin_result.gross_amount == Decimal("1.0000")
    assert coin_result.fee_amount == Decimal("0.1000")
    assert coin_result.net_amount == Decimal("0.9000")
    assert coin_entry_types == {LedgerTransactionType.MATCH_ENTRY_FEE}
    assert wallet.get_balance(session, wallet.get_user_account(session, user, LedgerUnit.COIN)) == Decimal("4.0000")
    assert wallet.get_balance(session, coin_escrow) == Decimal("0.9000")
    assert wallet.get_balance(session, coin_platform) == Decimal("-4.9000")

    assert credit_result.gross_amount == Decimal("100.0000")
    assert credit_result.fee_amount == Decimal("10.0000")
    assert credit_result.net_amount == Decimal("90.0000")
    assert credit_entry_types == {LedgerTransactionType.MATCH_ENTRY_FEE}
    assert wallet.get_balance(session, wallet.get_user_account(session, user, LedgerUnit.CREDIT)) == Decimal("400.0000")
    assert wallet.get_balance(session, credit_escrow) == Decimal("90.0000")
    assert wallet.get_balance(session, credit_platform) == Decimal("-490.0000")


def test_settle_marketplace_transaction_applies_fee_destination_and_overrides(session) -> None:
    wallet = WalletService()
    buyer = _create_user(session, user_id="buyer", email="buyer@example.com", username="buyer")
    seller = _create_user(session, user_id="seller", email="seller@example.com", username="seller")
    _create_reward_rule(session, trading_fee_bps=2500)
    _seed_balance(session, wallet, user=buyer, unit=LedgerUnit.COIN, amount=Decimal("10.0000"))
    _seed_balance(session, wallet, user=buyer, unit=LedgerUnit.CREDIT, amount=Decimal("50.0000"))

    economy = EconomyService(session=session, wallet_service=wallet)

    coin_result = economy.settle_marketplace_transaction(
        buyer=buyer,
        seller=seller,
        gross_amount=Decimal("4.0000"),
        unit=LedgerUnit.COIN,
        reference="manager-sale",
        buyer_source_tag=LedgerSourceTag.PLAYER_CARD_PURCHASE,
        seller_source_tag=LedgerSourceTag.PLAYER_CARD_SALE,
        burn_fee=False,
        actor=buyer,
    )

    credit_result = economy.settle_marketplace_transaction(
        buyer=buyer,
        seller=seller,
        gross_amount=Decimal("20.0000"),
        unit=LedgerUnit.CREDIT,
        reference="card-sale",
        buyer_source_tag=LedgerSourceTag.PLAYER_CARD_PURCHASE,
        seller_source_tag=LedgerSourceTag.PLAYER_CARD_SALE,
        fee_bps=500,
        burn_fee=True,
        actor=buyer,
    )

    assert coin_result.fee_amount == Decimal("1.0000")
    assert coin_result.seller_net_amount == Decimal("3.0000")
    assert wallet.get_balance(session, wallet.get_user_account(session, buyer, LedgerUnit.COIN)) == Decimal("6.0000")
    assert wallet.get_balance(session, wallet.get_user_account(session, seller, LedgerUnit.COIN)) == Decimal("3.0000")
    assert wallet.get_balance(session, wallet.ensure_platform_account(session, LedgerUnit.COIN)) == Decimal("-10.0000")
    assert wallet.get_balance(session, wallet.ensure_trade_fee_account(session, LedgerUnit.COIN)) == Decimal("1.0000")

    assert credit_result.fee_amount == Decimal("1.0000")
    assert credit_result.seller_net_amount == Decimal("19.0000")
    assert wallet.get_balance(session, wallet.get_user_account(session, buyer, LedgerUnit.CREDIT)) == Decimal("30.0000")
    assert wallet.get_balance(session, wallet.get_user_account(session, seller, LedgerUnit.CREDIT)) == Decimal(
        "19.0000"
    )
    assert wallet.get_balance(session, wallet.ensure_platform_burn_account(session, LedgerUnit.CREDIT)) == Decimal(
        "1.0000"
    )
    assert {
        entry.transaction_type
        for entry in session.scalars(select(LedgerEntry).where(LedgerEntry.reference == "manager-sale")).all()
    } == {LedgerTransactionType.TRADE_BUY, LedgerTransactionType.TRADE_SELL}


def test_governor_adjusts_pricing_conversion_and_rewards(session) -> None:
    wallet = WalletService()
    admin = _create_user(
        session,
        user_id="governor-admin",
        email="governor-admin@example.com",
        username="governor-admin",
        role=UserRole.ADMIN,
    )
    user = _create_user(
        session,
        user_id="governor-user",
        email="governor-user@example.com",
        username="governor-user",
    )
    _create_reward_rule(session, competition_platform_fee_bps=1000)
    _create_service_pricing_rule(
        session,
        service_key="tournament-entry",
        price_coin=Decimal("1.0000"),
        price_fancoin_equivalent=Decimal("100.0000"),
    )

    governor = EconomyGovernorService(session=session, wallet_service=wallet)
    governor.apply_actions(
        actor=admin,
        actions=[
            {"type": "increase_entry_fee", "value": "0.1000"},
            {"type": "boost_conversion_incentive", "value": 250},
            {"type": "reduce_rewards", "value": "0.1500"},
        ],
    )

    quote = PricingEngine(session, wallet_service=wallet).quote_service("tournament-entry")
    conversion = governor.quote_conversion(source_unit=LedgerUnit.COIN, amount=Decimal("1.0000"))

    reward_engine = RewardEngineService(session=session, wallet_service=wallet)
    reward_engine.credit_promo_pool(actor=admin, amount=Decimal("10.0000"))
    settlement = reward_engine.settle_reward(
        actor=admin,
        user_id=user.id,
        competition_key="governor-cup",
        title="Governor Cup Reward",
        gross_amount=Decimal("1.0000"),
    )

    assert quote.gtex_amount == Decimal("1.1000")
    assert quote.fancoin_amount == Decimal("110.0000")
    assert conversion.target_amount == Decimal("102.5000")
    assert settlement.gross_amount == Decimal("0.8500")
    assert settlement.net_amount == Decimal("0.7650")


def test_governor_enforces_treasury_buffer_and_dynamic_reward_scaling(session) -> None:
    wallet = WalletService()
    admin = _create_user(
        session,
        user_id="treasury-governor-admin",
        email="treasury-governor-admin@example.com",
        username="treasury-governor-admin",
        role=UserRole.ADMIN,
    )
    treasury_account = wallet.ensure_treasury_account(session, LedgerUnit.COIN)
    _seed_system_balance(
        session,
        wallet,
        account=treasury_account,
        unit=LedgerUnit.COIN,
        amount=Decimal("20.0000"),
        actor=admin,
    )

    governor = EconomyGovernorService(session=session, wallet_service=wallet)

    assert governor.can_fund_match(amount=Decimal("6.0000"))
    assert not governor.can_fund_match(amount=Decimal("7.0000"))
    assert governor.reward_multiplier() == Decimal("0.8000")
    assert governor.scale_reward_amount(amount=Decimal("10.0000")) == Decimal("6.6666")


def test_governor_snapshot_surfaces_whale_decay_and_circuit_breaker_metrics(session) -> None:
    wallet = WalletService()
    whale = _create_user(session, user_id="whale-user", email="whale@example.com", username="whale-user")
    minnow = _create_user(session, user_id="minnow-user", email="minnow@example.com", username="minnow-user")
    _seed_balance(session, wallet, user=whale, unit=LedgerUnit.COIN, amount=Decimal("90.0000"))
    _seed_balance(session, wallet, user=minnow, unit=LedgerUnit.COIN, amount=Decimal("10.0000"))

    governor = EconomyGovernorService(session=session, wallet_service=wallet)

    assert governor.whale_concentration() == Decimal("0.9000")

    snapshot = governor.snapshot(
        metrics={
            "gtex_supply": Decimal("100.0000"),
            "daily_burn": Decimal("10.0000"),
            "daily_mint": Decimal("25.0000"),
            "inflation_rate": Decimal("0.2600"),
            "liquidity_pool_balance": Decimal("0.0000"),
            "treasury_balance": Decimal("100.0000"),
            "rewards_pool_balance": Decimal("30.0000"),
            "treasury_reward_threshold": Decimal("20.0000"),
        }
    )

    assert snapshot["metrics"]["whale_concentration"] == "0.9000"
    assert snapshot["metrics"]["reward_decay_factor"] == "0.6600"
    assert snapshot["metrics"]["effective_burn_bonus_bps"] == "600"
    assert snapshot["metrics"]["circuit_breaker_active"] == "1.0000"
    action_types = {item["type"] for item in snapshot["recommended_actions"]}
    assert "activate_circuit_breaker" in action_types
    assert "apply_reward_decay" in action_types


def test_governor_thread_c_cycle_sets_reward_agent_and_price_controls(session) -> None:
    wallet = WalletService()
    admin = _create_user(
        session,
        user_id="thread-c-admin",
        email="thread-c-admin@example.com",
        username="thread-c-admin",
        role=UserRole.ADMIN,
    )
    governor = EconomyGovernorService(session=session, wallet_service=wallet)
    metrics = {
        "gtex_supply": Decimal("1000.0000"),
        "fan_supply": Decimal("2000.0000"),
        "daily_burn": Decimal("40.0000"),
        "daily_mint": Decimal("40.0000"),
        "avg_user_spend": Decimal("30.0000"),
        "inflation_rate": Decimal("0.1200"),
        "treasury_balance": Decimal("10.0000"),
        "rewards_pool_balance": Decimal("50.0000"),
        "liquidity_pool_balance": Decimal("25.0000"),
        "treasury_reward_threshold": Decimal("25.0000"),
        "active_users": 4000,
        "market_volatility": Decimal("0.6000"),
    }

    analysis = governor.analyze(metrics=metrics)
    action_types = {item["type"] for item in analysis["actions"]}

    snapshot = governor.run_cycle(actor=admin, metrics=metrics)

    assert action_types >= {
        "set_reward_multiplier",
        "set_free_prize_multiplier",
        "set_agent_activity",
        "adjust_price_caps",
    }
    assert snapshot["reward_payout_multiplier"] == Decimal("0.8000")
    assert snapshot["free_prize_multiplier"] == Decimal("0.8000")
    assert snapshot["agent_activity_multiplier"] == Decimal("0.5000")
    assert snapshot["price_change_limit"] == Decimal("0.0500")


def test_governor_price_change_limit_caps_service_pricing(session) -> None:
    admin = _create_user(
        session,
        user_id="pricing-cap-admin",
        email="pricing-cap-admin@example.com",
        username="pricing-cap-admin",
        role=UserRole.ADMIN,
    )
    _create_service_pricing_rule(
        session,
        service_key="tournament-entry",
        price_coin=Decimal("1.0000"),
        price_fancoin_equivalent=Decimal("100.0000"),
    )

    governor = EconomyGovernorService(session=session)
    governor.update_policy(
        actor=admin,
        tournament_entry_multiplier=Decimal("1.2000"),
        price_change_limit=Decimal("0.0500"),
    )

    quote = PricingEngine(session).quote_service("tournament-entry")

    assert quote.gtex_amount == Decimal("1.0500")
    assert quote.fancoin_amount == Decimal("105.0000")
