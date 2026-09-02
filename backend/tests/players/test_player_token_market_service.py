from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from app.core.database import load_model_modules
from app.core.events import InMemoryEventPublisher
from app.economy.governor_service import EconomyGovernorService
from app.ingestion.models import Player
from app.models.base import Base
from app.models.regen_ecosystem import NationalRegenSeed
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
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


def _create_player(session, *, player_id: str, is_tradable: bool | None = None) -> Player:
    player = Player(
        id=player_id,
        source_provider="test",
        provider_external_id=f"provider-{player_id}",
        full_name="Token Test Player",
        canonical_display_name="Token Test Player",
        **({"is_tradable": is_tradable} if is_tradable is not None else {}),
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
    assert purchase["fee_amount_coin"] == Decimal("0.1500")
    assert purchase["net_amount_coin"] == Decimal("0.9000")
    assert purchase["transaction_id"]
    assert purchase["market"]["share_price_coin"] == Decimal("0.0769")
    assert repriced.share_price_coin == Decimal("0.0807")
    assert dividend["gross_amount_coin"] == Decimal("7.5000")
    assert holding is not None
    assert holding.share_count == 10
    assert holding.average_cost_coin == Decimal("0.0900")
    assert holding.dividends_earned_coin == Decimal("7.5000")
    assert len(events) >= 4


def test_player_share_market_read_does_not_auto_create_or_fund_new_players(session) -> None:
    player = _create_player(session, player_id="player-token-auto")

    service = PlayerTokenMarketService(session=session)
    with pytest.raises(PlayerTokenMarketError, match="market was not found"):
        service.get_market_view(player_id=player.id)

    from app.models.player_token_market import PlayerShareMarket

    assert session.query(PlayerShareMarket).filter_by(player_id=player.id).first() is None


def test_ineligible_new_player_does_not_auto_create_share_market(session) -> None:
    player = _create_player(session, player_id="player-token-blocked", is_tradable=False)

    assert player.share_market is None
    from app.models.player_token_market import PlayerShareMarket

    assert session.query(PlayerShareMarket).filter_by(player_id=player.id).first() is None

    service = PlayerTokenMarketService(session=session)
    with pytest.raises(PlayerTokenMarketError, match="not eligible for the share market"):
        service.get_market_view(player_id=player.id)

    assert session.query(PlayerShareMarket).filter_by(player_id=player.id).first() is None


def test_player_share_market_sell_flow_updates_holding_and_price(session) -> None:
    wallet = WalletService()
    admin = _create_user(session, user_id="token-sell-admin", role=UserRole.ADMIN)
    fan = _create_user(session, user_id="token-sell-fan")
    player = _create_player(session, player_id="player-token-sell")
    _seed_coin_balance(session, wallet, user=fan, amount=Decimal("50.0000"))

    service = PlayerTokenMarketService(session=session, wallet_service=wallet)
    service.issue_market(
        actor=admin,
        player_id=player.id,
        total_shares=1000,
        share_price_coin=Decimal("0.5000"),
        liquidity_coin=Decimal("20.0000"),
    )
    service.buy_shares(actor=fan, player_id=player.id, share_count=10)
    sale = service.sell_shares(actor=fan, player_id=player.id, share_count=4)
    holding = service.get_holding(user_id=fan.id, player_id=player.id)
    events = service.list_events(player_id=player.id)

    assert sale["transaction_id"]
    assert sale["gross_amount_coin"] > Decimal("0.0000")
    assert sale["fee_amount_coin"] > Decimal("0.0000")
    assert sale["net_amount_coin"] < sale["gross_amount_coin"]
    assert sale["market"]["circulating_shares"] == 6
    assert Decimal(str(sale["market"]["share_price_coin"])) < Decimal("0.5125")
    assert holding is not None
    assert holding.share_count == 6
    assert events[0].event_type == "sell"


def test_player_share_market_trade_publishes_realtime_event_after_commit(session) -> None:
    publisher = InMemoryEventPublisher()
    wallet = WalletService(event_publisher=publisher)
    admin = _create_user(session, user_id="token-publish-admin", role=UserRole.ADMIN)
    fan = _create_user(session, user_id="token-publish-fan")
    player = _create_player(session, player_id="player-token-publish")
    _seed_coin_balance(session, wallet, user=fan, amount=Decimal("50.0000"))

    service = PlayerTokenMarketService(
        session=session,
        wallet_service=wallet,
        event_publisher=publisher,
    )
    service.issue_market(
        actor=admin,
        player_id=player.id,
        total_shares=1000,
        share_price_coin=Decimal("0.1250"),
    )
    service.buy_shares(actor=fan, player_id=player.id, share_count=4)
    session.commit()

    market_events = [event for event in publisher.published_events if event.name == "market.trade.executed"]
    assert len(market_events) == 1
    assert market_events[0].payload["player_id"] == player.id
    assert market_events[0].payload["side"] == "buy"
    assert market_events[0].payload["shares"] == 4


def test_player_share_market_respects_governor_price_caps(session) -> None:
    admin = _create_user(session, user_id="token-cap-admin", role=UserRole.ADMIN)
    player = _create_player(session, player_id="player-token-cap")

    EconomyGovernorService(session).update_policy(
        actor=admin,
        price_change_limit=Decimal("0.0500"),
    )

    service = PlayerTokenMarketService(session=session)
    service.issue_market(
        actor=admin,
        player_id=player.id,
        total_shares=1000,
        share_price_coin=Decimal("0.0750"),
    )
    repriced = service.apply_performance_adjustment(
        actor=admin,
        player_id=player.id,
        multiplier=Decimal("1.5000"),
        reason="viral_breakout",
    )

    assert repriced.share_price_coin == Decimal("0.0788")


def test_preseeded_national_regens_cannot_issue_player_share_markets(session) -> None:
    admin = _create_user(session, user_id="token-seed-admin", role=UserRole.ADMIN)
    seed = NationalRegenSeed(
        seed_key="seed:share-market:block",
        display_name="Pape Ndiaye",
        age=18,
        age_band="u20",
        country_code="SN",
        country_name="Senegal",
        seed_type="preseeded_national_pool",
        primary_position="AM",
        current_rating=72,
        potential_rating=86,
        growth_curve=0.74,
        rarity_tier="rare",
        status="available",
        metadata_json={},
    )
    session.add(seed)
    session.flush()

    service = PlayerTokenMarketService(session=session)
    with pytest.raises(
        PlayerTokenMarketError,
        match="national-pool-only and cannot be issued to the share market",
    ) as exc_info:
        service.issue_market(
            actor=admin,
            player_id=seed.id,
            total_shares=1000,
            share_price_coin=Decimal("0.1250"),
        )

    assert exc_info.value.reason == "preseeded_national_regen_share_market_ineligible"
