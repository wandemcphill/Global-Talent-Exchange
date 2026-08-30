"""Behavioral proof for PS-P0-1: a player-share trade replay with the same
idempotency key must execute exactly once, and reusing a key for a different
trade (different player, side, or share count) must be rejected as a conflict
rather than silently executing as an unrelated trade.

These tests exercise the real PlayerTokenMarketService.buy_shares/sell_shares
methods end to end (real ledger, real holdings, real market state) - not an
AST/source scan of the service's method bodies.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from app.core.database import load_model_modules
from app.ingestion.models import Player
from app.models.base import Base
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransaction, LedgerUnit
from app.players.token_service import PlayerTokenMarketError, PlayerTokenMarketService
from app.wallets.service import LedgerPosting, WalletService


@pytest.fixture()
def session():
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


def _create_user(session, *, user_id: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        id=user_id,
        email=f"{user_id}@example.com",
        username=user_id,
        password_hash="hashed",
        role=role,
    )
    session.add(user)
    session.flush()
    WalletService().ensure_default_accounts(session, user)
    session.flush()
    return user


def _create_player(session, *, player_id: str) -> Player:
    player = Player(
        id=player_id,
        source_provider="test",
        provider_external_id=f"provider-{player_id}",
        full_name="Idempotency Test Player",
        canonical_display_name="Idempotency Test Player",
    )
    session.add(player)
    session.flush()
    return player


def _seed_coin_balance(session, wallet: WalletService, *, user: User, amount: Decimal) -> None:
    user_account = wallet.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = wallet.ensure_platform_account(session, LedgerUnit.COIN)
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=amount),
            LedgerPosting(account=platform_account, amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        reference=f"seed:{user.id}",
        actor=user,
    )


def _setup_service(session, *, admin_id: str) -> tuple[PlayerTokenMarketService, WalletService, User]:
    wallet = WalletService()
    admin = _create_user(session, user_id=admin_id, role=UserRole.ADMIN)
    service = PlayerTokenMarketService(session=session, wallet_service=wallet)
    return service, wallet, admin


def _issue_market(
    session,
    service: PlayerTokenMarketService,
    admin: User,
    *,
    player_id: str,
    share_price: Decimal = Decimal("0.5000"),
    liquidity: Decimal = Decimal("20.0000"),
) -> Player:
    player = _create_player(session, player_id=player_id)
    service.issue_market(
        actor=admin,
        player_id=player.id,
        total_shares=1000,
        share_price_coin=share_price,
        liquidity_coin=liquidity,
    )
    return player


def _ledger_transaction_count(session) -> int:
    return len(session.scalars(select(LedgerTransaction)).all())


def test_buy_replay_with_same_idempotency_key_executes_once(session):
    service, wallet, admin = _setup_service(session, admin_id="admin-buy-replay")
    player = _issue_market(session, service, admin, player_id="p-buy-replay")
    fan = _create_user(session, user_id="fan-buy-replay")
    _seed_coin_balance(session, wallet, user=fan, amount=Decimal("50.0000"))
    fan_account = wallet.get_user_account(session, fan, LedgerUnit.COIN)

    first = service.buy_shares(actor=fan, player_id=player.id, share_count=10, idempotency_key="buy-key-1")
    balance_after_first = wallet.get_balance(session, fan_account)
    holding_after_first = service.get_holding(user_id=fan.id, player_id=player.id)
    market_after_first = service.get_market_view(player_id=player.id)
    tx_count_after_first = _ledger_transaction_count(session)

    second = service.buy_shares(actor=fan, player_id=player.id, share_count=10, idempotency_key="buy-key-1")
    balance_after_second = wallet.get_balance(session, fan_account)
    holding_after_second = service.get_holding(user_id=fan.id, player_id=player.id)
    market_after_second = service.get_market_view(player_id=player.id)
    tx_count_after_second = _ledger_transaction_count(session)

    assert second["transaction_id"] == first["transaction_id"]
    assert second["gross_amount_coin"] == first["gross_amount_coin"]
    assert balance_after_second == balance_after_first
    assert holding_after_second.share_count == holding_after_first.share_count == 10
    assert market_after_second["circulating_shares"] == market_after_first["circulating_shares"]
    assert tx_count_after_second == tx_count_after_first


def test_sell_replay_with_same_idempotency_key_executes_once(session):
    service, wallet, admin = _setup_service(session, admin_id="admin-sell-replay")
    player = _issue_market(session, service, admin, player_id="p-sell-replay")
    fan = _create_user(session, user_id="fan-sell-replay")
    _seed_coin_balance(session, wallet, user=fan, amount=Decimal("50.0000"))
    fan_account = wallet.get_user_account(session, fan, LedgerUnit.COIN)
    service.buy_shares(actor=fan, player_id=player.id, share_count=10, idempotency_key="buy-before-sell")

    first = service.sell_shares(actor=fan, player_id=player.id, share_count=4, idempotency_key="sell-key-1")
    balance_after_first = wallet.get_balance(session, fan_account)
    holding_after_first = service.get_holding(user_id=fan.id, player_id=player.id)
    market_after_first = service.get_market_view(player_id=player.id)
    tx_count_after_first = _ledger_transaction_count(session)

    second = service.sell_shares(actor=fan, player_id=player.id, share_count=4, idempotency_key="sell-key-1")
    balance_after_second = wallet.get_balance(session, fan_account)
    holding_after_second = service.get_holding(user_id=fan.id, player_id=player.id)
    market_after_second = service.get_market_view(player_id=player.id)
    tx_count_after_second = _ledger_transaction_count(session)

    assert second["transaction_id"] == first["transaction_id"]
    assert second["gross_amount_coin"] == first["gross_amount_coin"]
    assert balance_after_second == balance_after_first
    assert holding_after_second.share_count == holding_after_first.share_count == 6
    assert market_after_second["circulating_shares"] == market_after_first["circulating_shares"]
    assert tx_count_after_second == tx_count_after_first


def test_same_key_different_user_does_not_conflict(session):
    service, wallet, admin = _setup_service(session, admin_id="admin-multi-user")
    player = _issue_market(session, service, admin, player_id="p-multi-user")
    fan_a = _create_user(session, user_id="fan-a-key")
    fan_b = _create_user(session, user_id="fan-b-key")
    _seed_coin_balance(session, wallet, user=fan_a, amount=Decimal("50.0000"))
    _seed_coin_balance(session, wallet, user=fan_b, amount=Decimal("50.0000"))

    result_a = service.buy_shares(actor=fan_a, player_id=player.id, share_count=5, idempotency_key="shared-key")
    result_b = service.buy_shares(actor=fan_b, player_id=player.id, share_count=5, idempotency_key="shared-key")

    assert result_a["transaction_id"] != result_b["transaction_id"]
    assert service.get_holding(user_id=fan_a.id, player_id=player.id).share_count == 5
    assert service.get_holding(user_id=fan_b.id, player_id=player.id).share_count == 5


def test_same_key_different_player_is_rejected_as_conflict(session):
    service, wallet, admin = _setup_service(session, admin_id="admin-player-conflict")
    player_one = _issue_market(session, service, admin, player_id="p-conflict-1")
    player_two = _issue_market(session, service, admin, player_id="p-conflict-2")
    fan = _create_user(session, user_id="fan-player-conflict")
    _seed_coin_balance(session, wallet, user=fan, amount=Decimal("50.0000"))

    service.buy_shares(actor=fan, player_id=player_one.id, share_count=5, idempotency_key="reused-key")

    with pytest.raises(PlayerTokenMarketError, match="already used for a different player-share trade") as exc_info:
        service.buy_shares(actor=fan, player_id=player_two.id, share_count=5, idempotency_key="reused-key")
    assert exc_info.value.reason == "trade_idempotency_conflict"
    assert service.get_holding(user_id=fan.id, player_id=player_two.id) is None


def test_same_key_different_side_is_rejected_as_conflict(session):
    service, wallet, admin = _setup_service(session, admin_id="admin-side-conflict")
    player = _issue_market(session, service, admin, player_id="p-side-conflict")
    fan = _create_user(session, user_id="fan-side-conflict")
    _seed_coin_balance(session, wallet, user=fan, amount=Decimal("50.0000"))

    service.buy_shares(actor=fan, player_id=player.id, share_count=5, idempotency_key="side-key")

    with pytest.raises(PlayerTokenMarketError, match="already used for a different player-share trade") as exc_info:
        service.sell_shares(actor=fan, player_id=player.id, share_count=5, idempotency_key="side-key")
    assert exc_info.value.reason == "trade_idempotency_conflict"
    assert service.get_holding(user_id=fan.id, player_id=player.id).share_count == 5


def test_same_key_different_share_count_is_rejected_as_conflict(session):
    service, wallet, admin = _setup_service(session, admin_id="admin-count-conflict")
    player = _issue_market(session, service, admin, player_id="p-count-conflict")
    fan = _create_user(session, user_id="fan-count-conflict")
    _seed_coin_balance(session, wallet, user=fan, amount=Decimal("50.0000"))

    service.buy_shares(actor=fan, player_id=player.id, share_count=5, idempotency_key="count-key")

    with pytest.raises(PlayerTokenMarketError, match="already used for a different player-share trade") as exc_info:
        service.buy_shares(actor=fan, player_id=player.id, share_count=6, idempotency_key="count-key")
    assert exc_info.value.reason == "trade_idempotency_conflict"
    assert service.get_holding(user_id=fan.id, player_id=player.id).share_count == 5


def test_ledger_transaction_idempotency_key_has_database_unique_constraint(session):
    """Proves the final backstop for genuinely concurrent duplicate trades.

    Two independent DB connections racing the replay check so that both decide
    to execute before either commits cannot be reproduced with the single
    shared-connection SQLite StaticPool harness used across this test suite
    (see test_player_token_market_service.py's `session` fixture, which this
    file mirrors). What guarantees only one trade survives such a race in
    production is that LedgerTransaction.idempotency_key is DB-unique: the
    loser's flush in _bind_trade_idempotency raises IntegrityError, aborting
    its whole transaction - trade, holding, and balance mutations all revert -
    before it can commit, leaving exactly one committed trade for the key.
    """
    service, wallet, admin = _setup_service(session, admin_id="admin-race-backstop")
    player = _issue_market(session, service, admin, player_id="p-race-backstop")
    fan = _create_user(session, user_id="fan-race-backstop")
    _seed_coin_balance(session, wallet, user=fan, amount=Decimal("50.0000"))

    service.buy_shares(actor=fan, player_id=player.id, share_count=5, idempotency_key="race-key")
    session.commit()

    # Simulate the loser of a race: an independent trade that already executed
    # (e.g. because it read the market before the winner's commit was visible)
    # and now tries to bind the SAME idempotency key the winner already holds.
    loser = service.buy_shares(actor=fan, player_id=player.id, share_count=5, idempotency_key="throwaway-key")

    with pytest.raises(IntegrityError):
        service._bind_trade_idempotency(
            transaction_id=str(loser["transaction_id"]),
            reference=service._idempotency_reference(actor_id=fan.id, key="race-key"),
            actor=fan,
            player_id=player.id,
            side="buy",
            share_count=5,
        )
    session.rollback()
