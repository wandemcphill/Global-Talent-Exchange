from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
import app.ingestion.models  # noqa: F401
import app.models.card_access  # noqa: F401
import app.models.player_cards  # noqa: F401
import app.players.read_models  # noqa: F401
from app.ingestion.models import Player
from app.integrity_engine.service import IntegrityEngineService
from app.models.base import Base
from app.models.notification_record import NotificationRecord
from app.models.player_cards import PlayerCard, PlayerCardHolding, PlayerCardOwnerHistory, PlayerCardTier
from app.player_cards.collectibles_service import PlayerCardCollectiblesService
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.player_cards.marketplace_service import PlayerCardMarketplaceService
from app.player_cards.service import PlayerCardMarketService, PlayerCardValidationError
from app.player_import_engine.service import PlayerImportService
from app.players.read_models import PlayerSummaryReadModel
from app.wallets.service import LedgerPosting, WalletService


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


def _create_summary(session, *, player: Player, value_credits: float = 20.0) -> None:
    session.add(
        PlayerSummaryReadModel(
            player_id=player.id,
            player_name=player.full_name,
            current_club_name="GTEX FC",
            last_snapshot_at=datetime.now(timezone.utc),
            current_value_credits=value_credits,
            previous_value_credits=value_credits,
            movement_pct=0.0,
            average_rating=7.0,
            market_interest_score=0,
            summary_json={},
        )
    )
    session.flush()


def _seed_credits(session, wallet: WalletService, user: User, amount: Decimal) -> None:
    account = wallet.get_user_account(session, user, LedgerUnit.COIN)
    platform = wallet.ensure_platform_account(session, LedgerUnit.COIN)
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
    holding = PlayerCardHolding(
        player_card_id=card.id, owner_user_id=seller.id, quantity_total=5, quantity_reserved=0, metadata_json={}
    )
    session.add(holding)
    session.flush()

    service = PlayerCardMarketService(session=session)
    listing = service.create_listing(
        actor=seller, player_card_id=card.id, quantity=2, price_per_card_credits=Decimal("15")
    )

    refreshed = session.get(PlayerCardHolding, holding.id)
    assert refreshed.quantity_reserved == 2
    assert listing["status"] == "open"


def test_marketplace_loan_offer_publishes_notification(session):
    owner = _create_user(session, user_id="loan-owner", email="loan-owner@example.com", username="loan-owner")
    borrower = _create_user(
        session,
        user_id="loan-borrower",
        email="loan-borrower@example.com",
        username="loan-borrower",
    )
    player = _create_player(session, player_id="loan-player", name="Notify Loan Target")
    tier = _create_tier(session)
    card = _create_card(session, player=player, tier=tier)
    session.add(
        PlayerCardHolding(
            player_card_id=card.id,
            owner_user_id=owner.id,
            quantity_total=2,
            quantity_reserved=0,
            metadata_json={},
        )
    )
    session.flush()

    service = PlayerCardMarketplaceService(session=session)
    listing = service.create_loan_listing(
        actor=owner,
        player_card_id=card.id,
        total_slots=1,
        duration_days=7,
        loan_fee_credits=Decimal("4.0000"),
        is_negotiable=True,
    )
    negotiation = service.create_loan_negotiation(
        actor=borrower,
        listing_id=listing["listing_id"],
        proposed_duration_days=5,
        proposed_loan_fee_credits=Decimal("3.0000"),
        note="Can we do five days?",
    )

    notification = session.scalar(
        select(NotificationRecord).where(
            NotificationRecord.user_id == owner.id,
            NotificationRecord.resource_id == negotiation["negotiation_id"],
        )
    )
    assert notification is not None
    assert notification.template_key == "card.offer.received"
    assert notification.resource_type == "card_offer_received"
    assert notification.metadata_json["listing_id"] == listing["listing_id"]


def test_invalid_ownership_rejected(session):
    seller = _create_user(session, user_id="user-seller", email="seller2@example.com", username="seller2")
    player = _create_player(session, player_id="player-2", name="Bola Mid")
    tier = _create_tier(session)
    card = _create_card(session, player=player, tier=tier)

    service = PlayerCardMarketService(session=session)
    with pytest.raises(PlayerCardValidationError):
        service.create_listing(actor=seller, player_card_id=card.id, quantity=1, price_per_card_credits=Decimal("10"))


def test_collectible_packs_burns_and_upgrades_use_existing_card_supply(session):
    owner = _create_user(session, user_id="collector", email="collector@example.com", username="collector")
    player = _create_player(session, player_id="collectible-player", name="Collectible Ace")
    tiers = [
        PlayerCardTier(
            id="tier-bronze",
            code="bronze",
            name="Bronze",
            rarity_rank=4,
            max_supply=1000,
            supply_multiplier=1,
            base_mint_price_credits=0,
            is_active=True,
            metadata_json={},
        ),
        PlayerCardTier(
            id="tier-silver",
            code="silver",
            name="Silver",
            rarity_rank=3,
            max_supply=1000,
            supply_multiplier=1,
            base_mint_price_credits=0,
            is_active=True,
            metadata_json={},
        ),
        PlayerCardTier(
            id="tier-fusion-elite",
            code="elite",
            name="Elite",
            rarity_rank=1,
            max_supply=100,
            supply_multiplier=1,
            base_mint_price_credits=0,
            is_active=True,
            metadata_json={},
        ),
    ]
    session.add_all(tiers)
    session.flush()
    cards = [
        PlayerCard(
            id="collectible-card-bronze",
            player_id=player.id,
            tier_id=tiers[0].id,
            edition_code="base",
            display_name="Collectible Ace Bronze",
            supply_total=10,
            supply_available=10,
            is_active=True,
            metadata_json={},
        ),
        PlayerCard(
            id="collectible-card-silver",
            player_id=player.id,
            tier_id=tiers[1].id,
            edition_code="base",
            display_name="Collectible Ace Silver",
            supply_total=10,
            supply_available=10,
            is_active=True,
            metadata_json={},
        ),
        PlayerCard(
            id="collectible-card-elite",
            player_id=player.id,
            tier_id=tiers[2].id,
            edition_code="base",
            display_name="Collectible Ace Elite",
            supply_total=10,
            supply_available=10,
            is_active=True,
            metadata_json={},
        ),
    ]
    session.add_all(cards)
    session.add_all(
        [
            PlayerCardHolding(
                player_card_id=cards[0].id,
                owner_user_id=owner.id,
                quantity_total=2,
                quantity_reserved=0,
                metadata_json={},
            ),
            PlayerCardHolding(
                player_card_id=cards[1].id,
                owner_user_id=owner.id,
                quantity_total=2,
                quantity_reserved=0,
                metadata_json={},
            ),
        ]
    )
    session.flush()

    service = PlayerCardCollectiblesService(session=session)
    packs = service.list_packs()
    opening = service.open_pack(actor=owner, pack_key=packs[0]["pack_key"])
    burn = service.burn_card(actor=owner, player_card_id=cards[0].id, quantity=1, reason="test")
    upgrade = service.upgrade_cards(
        actor=owner,
        source_player_card_ids=[cards[0].id, cards[1].id],
        target_tier_code="elite",
    )

    assert packs[0]["pack_key"] == "starter-draft"
    assert len(opening["opened_cards"]) == 3
    assert burn["remaining_quantity"] >= 1
    assert upgrade["target_player_card_id"]
    assert session.get(PlayerCard, upgrade["target_player_card_id"]) is not None


def test_sale_execution_fee_and_owner_history(session):
    seller = _create_user(session, user_id="user-seller", email="seller3@example.com", username="seller3")
    buyer = _create_user(session, user_id="user-buyer", email="buyer@example.com", username="buyer")
    player = _create_player(session, player_id="player-3", name="Carlos Keeper")
    tier = _create_tier(session)
    card = _create_card(session, player=player, tier=tier)
    holding = PlayerCardHolding(
        player_card_id=card.id, owner_user_id=seller.id, quantity_total=4, quantity_reserved=0, metadata_json={}
    )
    session.add(holding)
    session.flush()

    wallet = WalletService()
    _seed_credits(session, wallet, buyer, Decimal("100"))

    service = PlayerCardMarketService(session=session, wallet_service=wallet)
    listing = service.create_listing(
        actor=seller, player_card_id=card.id, quantity=2, price_per_card_credits=Decimal("10")
    )
    sale = service.buy_listing(actor=buyer, listing_id=listing["listing_id"], quantity=2)

    seller_account = wallet.get_user_account(session, seller, LedgerUnit.COIN)
    buyer_account = wallet.get_user_account(session, buyer, LedgerUnit.COIN)
    platform_account = wallet.ensure_platform_burn_account(session, LedgerUnit.COIN)

    seller_balance = wallet.get_balance(session, seller_account)
    buyer_balance = wallet.get_balance(session, buyer_account)
    platform_balance = wallet.get_balance(session, platform_account)

    assert seller_balance == Decimal("16.0000")
    assert buyer_balance == Decimal("80.0000")
    assert platform_balance == Decimal("4.0000")

    history = session.scalar(
        select(PlayerCardOwnerHistory).where(PlayerCardOwnerHistory.reference_id == sale["sale_id"])
    )
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
    job, items = service.create_card_supply_job(
        actor=admin, source_label="test", rows=[{"tier_code": "elite", "quantity": 5}], commit=False
    )
    assert job.failed_items == 1
    assert items[0].status.value if hasattr(items[0].status, "value") else items[0].status == "invalid"


def test_suspicious_trade_signal_emission(session):
    seller = _create_user(session, user_id="user-seller4", email="seller4@example.com", username="seller4")
    buyer = _create_user(session, user_id="user-buyer4", email="buyer4@example.com", username="buyer4")
    player = _create_player(session, player_id="player-5", name="Efe Forward")
    tier = _create_tier(session)
    card = _create_card(session, player=player, tier=tier)
    holding = PlayerCardHolding(
        player_card_id=card.id, owner_user_id=seller.id, quantity_total=6, quantity_reserved=0, metadata_json={}
    )
    session.add(holding)
    session.flush()

    wallet = WalletService()
    _seed_credits(session, wallet, buyer, Decimal("200"))

    service = PlayerCardMarketService(session=session, wallet_service=wallet)
    for _ in range(3):
        listing = service.create_listing(
            actor=seller, player_card_id=card.id, quantity=2, price_per_card_credits=Decimal("12")
        )
        service.buy_listing(actor=buyer, listing_id=listing["listing_id"], quantity=2)

    integrity = IntegrityEngineService(session)
    incidents = integrity.list_incidents_for_user(user=seller)
    assert any(item.incident_type == "repeated_card_trade_pair" for item in incidents)


def test_inventory_and_listing_views_include_latest_value(session):
    seller = _create_user(session, user_id="value-seller", email="value-seller@example.com", username="value-seller")
    player = _create_player(session, player_id="value-player", name="Value Anchor")
    _create_summary(session, player=player, value_credits=33.0)
    tier = _create_tier(session)
    card = _create_card(session, player=player, tier=tier)
    session.add(
        PlayerCardHolding(
            player_card_id=card.id,
            owner_user_id=seller.id,
            quantity_total=2,
            quantity_reserved=0,
            metadata_json={},
        )
    )
    session.flush()

    service = PlayerCardMarketService(session=session)
    service.create_listing(
        actor=seller,
        player_card_id=card.id,
        quantity=1,
        price_per_card_credits=Decimal("12"),
    )

    inventory = service.list_inventory(actor=seller)
    listings = service.list_listings()

    assert inventory[0]["latest_value_credits"] == 33.0
    assert listings[0]["latest_value_credits"] == 33.0
