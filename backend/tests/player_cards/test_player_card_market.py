from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

import app.ingestion.models  # noqa: F401
import app.models.player_cards  # noqa: F401
import app.players.read_models  # noqa: F401
from app.ingestion.models import Player
from app.integrity_engine.service import IntegrityEngineService
from app.models.player_cards import PlayerCard, PlayerCardHolding, PlayerCardOwnerHistory, PlayerCardTier
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.player_cards.service import PlayerCardMarketService, PlayerCardValidationError
from app.player_import_engine.service import PlayerImportService
from app.players.read_models import PlayerSummaryReadModel
from app.wallets.service import LedgerPosting, WalletService


@pytest.fixture()
def session(gtex_db_session):
    # Shared session-scoped schema (tests/conftest.py::gtex_db_engine) with
    # per-test rollback, instead of rebuilding all ~567 tables per test.
    yield gtex_db_session


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


def _create_player(
    session,
    *,
    player_id: str,
    name: str,
    position: str | None = None,
    normalized_position: str | None = None,
) -> Player:
    player = Player(
        id=player_id,
        source_provider="test",
        provider_external_id=player_id,
        full_name=name,
        position=position,
        normalized_position=normalized_position,
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


def _create_summary(
    session,
    *,
    player: Player,
    value_credits: float = 20.0,
    summary_json: dict[str, object] | None = None,
) -> None:
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
            summary_json=summary_json or {},
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


def test_player_payloads_expose_dynamic_gsi(session):
    player = _create_player(
        session,
        player_id="player-gsi",
        name="GSI Striker",
        position="Striker",
        normalized_position="ST",
    )
    player.dna_profile = {
        "finishing": 92,
        "shooting": 88,
        "movement": 90,
        "pace": 86,
        "composure": 91,
        "physical": 78,
        "mentality": 84,
    }
    _create_summary(session, player=player, summary_json={"global_scouting_index": 75})

    service = PlayerCardMarketService(session=session)
    summary = service.list_players()[0]
    detail = service.get_player_detail(player_id=player.id)

    assert summary["global_scouting_index"] == detail["global_scouting_index"]
    assert summary["global_scouting_index"] not in {65, 75, 85}
    assert summary["gsi_band"] in {"Elite", "World Class"}


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


def test_player_card_player_views_emit_canonical_position_code(session):
    player = _create_player(
        session,
        player_id="position-player",
        name="Loose Forward",
        position="FORWARD",
        normalized_position="forward",
    )
    _create_summary(session, player=player, value_credits=25.0)

    service = PlayerCardMarketService(session=session)

    players = service.list_players()
    detail = service.get_player_detail(player_id=player.id)

    assert players[0]["position"] == "ST"
    assert detail["position"] == "ST"
