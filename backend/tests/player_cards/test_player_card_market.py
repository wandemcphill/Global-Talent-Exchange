from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.ingestion.models  # noqa: F401
import backend.app.models.player_cards  # noqa: F401
from backend.app.ingestion.models import Player
from backend.app.integrity_engine.service import IntegrityEngineService
from backend.app.models.base import Base
from backend.app.models.player_cards import PlayerCard, PlayerCardHolding, PlayerCardOwnerHistory, PlayerCardTier
from backend.app.models.user import User, UserRole
from backend.app.models.wallet import LedgerEntryReason, LedgerUnit
from backend.app.player_cards.service import PlayerCardMarketService, PlayerCardValidationError
from backend.app.player_import_engine.service import PlayerImportService
from backend.app.wallets.service import LedgerPosting, WalletService


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


def _create_user(session, *, user_id: str, email: str, username: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        id=user_id,
        email=email,
        username=username,
        password_hash="hashed",
        role=role,
    )
    session.add(user)
    session.flush()
    return user


def _create_player(session, *, player_id: str, name: str) -> Player:
    player = Player(
        id=player_id,
        source_provider="test",
        provider_external_id=player_id,
        full_name=name,
        is_tradable=True,
    )
    session.add(player)
    session.flush()
    return player


def _create_tier(session) -> PlayerCardTier:
    tier = PlayerCardTier(
        id="tier-elite",
        code="elite",
        name="Elite",
        rarity_rank=1,
        max_supply=1000,
        supply_multiplier=1.0,
        base_mint_price_credits=Decimal("10.0"),
        color_hex="#FFD700",
        is_active=True,
        metadata_json={},
    )
    session.add(tier)
    session.flush()
    return tier


def _create_card(session, *, player: Player, tier: PlayerCardTier) -> PlayerCard:
    card = PlayerCard(
        id="card-1",
        player_id=player.id,
        tier_id=tier.id,
        edition_code="base",
        display_name=f"{player.full_name} {tier.name}",
        season_label="2026",
        card_variant="base",
        supply_total=10,
        supply_available=10,
        is_active=True,
        metadata_json={},
    )
    session.add(card)
    session.flush()
    return card


def _seed_credits(session, wallet: WalletService, user: User, amount: Decimal) -> None:
    account = wallet.get_user_account(session, user, LedgerUnit.CREDIT)
    platform = wallet.ensure_platform_account(session, LedgerUnit.CREDIT)
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=platform, amount=-amount),
            LedgerPosting(account=account, amount=amount),
        ],
        reason=LedgerEntryReason.DEPOSIT,
        reference=f"seed-{user.id}",
        description="seed credits",
        actor=user,
    )


def test_create_listing_reserves_holdings(session):
    seller = _create_user(session, user_id="user-seller", email="seller@example.com", username="seller")
    player = _create_player(session, player_id="player-1", name="Ayo Striker")
    tier = _create_tier(session)
    card = _create_card(session, player=player, tier=tier)
    holding = PlayerCardHolding(player_card_id=card.id, owner_user_id=seller.id, quantity_total=5, quantity_reserved=0, metadata_json={})
    session.add(holding)
    session.flush()

    service = PlayerCardMarketService(session=session)
    listing = service.create_listing(actor=seller, player_card_id=card.id, quantity=2, price_per_card_credits=Decimal("15"))

    refreshed = session.get(PlayerCardHolding, holding.id)
    assert refreshed.quantity_reserved == 2
    assert listing["status"] == "open"


def test_invalid_ownership_rejected(session):
    seller = _create_user(session, user_id="user-seller", email="seller2@example.com", username="seller2")
    player = _create_player(session, player_id="player-2", name="Bola Mid")
    tier = _create_tier(session)
    card = _create_card(session, player=player, tier=tier)

    service = PlayerCardMarketService(session=session)
    with pytest.raises(PlayerCardValidationError):
        service.create_listing(actor=seller, player_card_id=card.id, quantity=1, price_per_card_credits=Decimal("10"))


def test_sale_execution_fee_and_owner_history(session):
    seller = _create_user(session, user_id="user-seller", email="seller3@example.com", username="seller3")
    buyer = _create_user(session, user_id="user-buyer", email="buyer@example.com", username="buyer")
    player = _create_player(session, player_id="player-3", name="Carlos Keeper")
    tier = _create_tier(session)
    card = _create_card(session, player=player, tier=tier)
    holding = PlayerCardHolding(player_card_id=card.id, owner_user_id=seller.id, quantity_total=4, quantity_reserved=0, metadata_json={})
    session.add(holding)
    session.flush()

    wallet = WalletService()
    _seed_credits(session, wallet, buyer, Decimal("100"))

    service = PlayerCardMarketService(session=session, wallet_service=wallet)
    listing = service.create_listing(actor=seller, player_card_id=card.id, quantity=2, price_per_card_credits=Decimal("10"))
    sale = service.buy_listing(actor=buyer, listing_id=listing["listing_id"], quantity=2)

    seller_account = wallet.get_user_account(session, seller, LedgerUnit.CREDIT)
    buyer_account = wallet.get_user_account(session, buyer, LedgerUnit.CREDIT)
    platform_account = wallet.ensure_platform_burn_account(session, LedgerUnit.CREDIT)

    seller_balance = wallet.get_balance(session, seller_account)
    buyer_balance = wallet.get_balance(session, buyer_account)
    platform_balance = wallet.get_balance(session, platform_account)

    assert seller_balance == Decimal("16.0000")
    assert buyer_balance == Decimal("80.0000")
    assert platform_balance == Decimal("4.0000")

    history = session.scalar(select(PlayerCardOwnerHistory).where(PlayerCardOwnerHistory.reference_id == sale["sale_id"]))
    assert history is not None


def test_watchlist_add_remove(session):
    user = _create_user(session, user_id="user-watch", email="watch@example.com", username="watcher")
    player = _create_player(session, player_id="player-4", name="Diego Defender")
    service = PlayerCardMarketService(session=session)

    watch = service.add_watchlist(actor=user, player_id=player.id, player_card_id=None, notes="Monitor")
    items = service.list_watchlist(actor=user)
    assert len(items) == 1
    assert items[0].id == watch.id

    service.remove_watchlist(actor=user, watchlist_id=watch.id)
    assert service.list_watchlist(actor=user) == []


def test_import_validation(session):
    admin = _create_user(session, user_id="admin", email="admin@example.com", username="admin", role=UserRole.ADMIN)
    service = PlayerImportService(session)
    job, items = service.create_card_supply_job(actor=admin, source_label="test", rows=[{"tier_code": "elite", "quantity": 5}], commit=False)
    assert job.failed_items == 1
    assert items[0].status.value if hasattr(items[0].status, "value") else items[0].status == "invalid"


def test_suspicious_trade_signal_emission(session):
    seller = _create_user(session, user_id="user-seller4", email="seller4@example.com", username="seller4")
    buyer = _create_user(session, user_id="user-buyer4", email="buyer4@example.com", username="buyer4")
    player = _create_player(session, player_id="player-5", name="Efe Forward")
    tier = _create_tier(session)
    card = _create_card(session, player=player, tier=tier)
    holding = PlayerCardHolding(player_card_id=card.id, owner_user_id=seller.id, quantity_total=6, quantity_reserved=0, metadata_json={})
    session.add(holding)
    session.flush()

    wallet = WalletService()
    _seed_credits(session, wallet, buyer, Decimal("200"))

    service = PlayerCardMarketService(session=session, wallet_service=wallet)
    for _ in range(3):
        listing = service.create_listing(actor=seller, player_card_id=card.id, quantity=2, price_per_card_credits=Decimal("12"))
        service.buy_listing(actor=buyer, listing_id=listing["listing_id"], quantity=2)

    integrity = IntegrityEngineService(session)
    incidents = integrity.list_incidents_for_user(user=seller)
    assert any(item.incident_type == "repeated_card_trade_pair" for item in incidents)
