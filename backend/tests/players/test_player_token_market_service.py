from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from app.core.database import load_model_modules
from app.ingestion.models import Player
from app.models.base import Base
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.players.token_service import PlayerTokenMarketService
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
        full_name="Token Test Player",
        canonical_display_name="Token Test Player",
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


def test_player_share_market_lifecycle(session) -> None:
    wallet = WalletService()
    admin = _create_user(session, user_id="token-admin", role=UserRole.ADMIN)
    fan = _create_user(session, user_id="token-fan")
    player = _create_player(session, player_id="player-token-1")
    _seed_coin_balance(session, wallet, user=fan, amount=Decimal("50.0000"))

    service = PlayerTokenMarketService(session=session, wallet_service=wallet)
    market = service.issue_market(
        actor=admin,
        player_id=player.id,
        total_shares=1000,
        share_price_coin=Decimal("0.0750"),
    )
    purchase = service.buy_shares(actor=fan, player_id=player.id, share_count=10)
    repriced = service.apply_performance_adjustment(
        actor=admin,
        player_id=player.id,
        multiplier=Decimal("1.0500"),
        reason="player_scored",
    )
    dividend = service.distribute_dividend(
        actor=admin,
        player_id=player.id,
        gross_amount_coin=Decimal("7.5000"),
        note="tournament_winnings",
    )
    holding = service.get_holding(user_id=fan.id, player_id=player.id)
    events = service.list_events(player_id=player.id)

    assert market.total_shares == 1000
    assert purchase["gross_amount_coin"] == Decimal("0.7500")
    assert purchase["transaction_id"]
    assert repriced.share_price_coin == Decimal("0.0788")
    assert dividend["gross_amount_coin"] == Decimal("7.5000")
    assert holding is not None
    assert holding.share_count == 10
    assert holding.average_cost_coin == Decimal("0.0750")
    assert holding.dividends_earned_coin == Decimal("7.5000")
    assert len(events) >= 4
