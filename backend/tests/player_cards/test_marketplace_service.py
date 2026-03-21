from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
import app.players.read_models  # noqa: F401
from app.core.config import get_settings
from app.ingestion.models import Player
from app.models.integrity import IntegrityIncident
from app.models.base import Base
from app.models.card_access import CardSwapExecution
from app.models.player_cards import PlayerCard, PlayerCardHolding, PlayerCardListing, PlayerCardSale, PlayerCardTier
from app.models.risk_ops import SystemEvent
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.player_cards.marketplace_service import PlayerCardMarketplaceService
from app.player_cards.service import PlayerCardValidationError
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
    user = User(id=user_id, email=email, username=username, password_hash="hashed", role=role)
    session.add(user)
    session.flush()
    return user


def _create_player(session, *, player_id: str, name: str, position: str = "forward", value_eur: float = 2_000_000) -> Player:
    player = Player(
        id=player_id,
        source_provider="test",
        provider_external_id=player_id,
        full_name=name,
        position=position.upper(),
        normalized_position=position.lower(),
        market_value_eur=value_eur,
        is_tradable=True,
    )
    session.add(player)
    session.flush()
    return player


def _create_summary(session, *, player: Player, club_name: str = "GTEX FC", rating: float = 7.5, value_credits: float = 20.0) -> None:
    summary = PlayerSummaryReadModel(
        player_id=player.id,
        player_name=player.full_name,
        current_club_name=club_name,
        last_snapshot_at=player.last_synced_at,
        current_value_credits=value_credits,
        previous_value_credits=value_credits,
        movement_pct=0.0,
        average_rating=rating,
        market_interest_score=0,
        summary_json={},
    )
    session.add(summary)
    session.flush()


def _create_tier(session, *, tier_id: str, code: str) -> PlayerCardTier:
    tier = PlayerCardTier(
        id=tier_id,
        code=code,
        name=code.title(),
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


def _create_card(session, *, card_id: str, player: Player, tier: PlayerCardTier, variant: str = "base") -> PlayerCard:
    card = PlayerCard(
        id=card_id,
        player_id=player.id,
        tier_id=tier.id,
        edition_code="base",
        display_name=f"{player.full_name} {tier.name}",
        season_label="2026",
        card_variant=variant,
        supply_total=10,
        supply_available=10,
        is_active=True,
        metadata_json={},
    )
    session.add(card)
    session.flush()
    return card


def _seed_wallet(session, wallet: WalletService, user: User, *, amount: Decimal) -> None:
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
        description="seed funds",
        actor=user,
    )


def test_free_regen_loan_floor_and_settlement(session) -> None:
    lender = _create_user(session, user_id="lender", email="lender@example.com", username="lender")
    borrower = _create_user(session, user_id="borrower", email="borrower@example.com", username="borrower")
    player = _create_player(session, player_id="player-regen", name="Regen Star", position="forward", value_eur=2_000_000)
    _create_summary(session, player=player, rating=8.1, value_credits=20.0)
    tier = _create_tier(session, tier_id="tier-regen", code="elite")
    card = _create_card(session, card_id="card-regen", player=player, tier=tier, variant="regen_unique")
    session.add(PlayerCardHolding(player_card_id=card.id, owner_user_id=lender.id, quantity_total=1, quantity_reserved=0, metadata_json={}))
    session.flush()

    wallet = WalletService()
    _seed_wallet(session, wallet, borrower, amount=Decimal("10.0000"))
    service = PlayerCardMarketplaceService(session=session, wallet_service=wallet)
    platform_account = wallet.ensure_platform_account(session, LedgerUnit.CREDIT)
    platform_balance_before = wallet.get_balance(session, platform_account)

    listing = service.create_loan_listing(actor=lender, player_card_id=card.id, total_slots=1, duration_days=7, loan_fee_credits=Decimal("0.0000"))
    negotiation = service.create_loan_negotiation(
        actor=borrower,
        listing_id=listing["listing_id"],
        proposed_duration_days=7,
        proposed_loan_fee_credits=Decimal("0.0000"),
    )
    contract = service.accept_loan_negotiation(actor=lender, negotiation_id=negotiation["negotiation_id"])
    settled = service.settle_loan_contract(actor=borrower, contract_id=contract["loan_contract_id"])

    lender_balance = wallet.get_balance(session, wallet.get_user_account(session, lender, LedgerUnit.CREDIT))
    borrower_balance = wallet.get_balance(session, wallet.get_user_account(session, borrower, LedgerUnit.CREDIT))
    platform_balance = wallet.get_balance(session, platform_account)

    assert settled["fee_floor_applied"] is True
    assert settled["effective_loan_fee_credits"] == Decimal("1.0000")
    assert settled["platform_fee_credits"] == Decimal("0.4000")
    assert settled["lender_net_credits"] == Decimal("0.6000")
    assert lender_balance == Decimal("0.6000")
    assert borrower_balance == Decimal("9.0000")
    assert platform_balance - platform_balance_before == Decimal("0.4000")

    returned = service.return_loan_contract(actor=borrower, contract_id=contract["loan_contract_id"])
    assert returned["status"] == "returned"


def test_sale_listing_guardrails_reject_price_outside_reference_band(session) -> None:
    seller = _create_user(session, user_id="guard-seller", email="guard-seller@example.com", username="guard-seller")
    player = _create_player(session, player_id="guard-player", name="Guarded Price")
    _create_summary(session, player=player, value_credits=20.0)
    tier = _create_tier(session, tier_id="tier-guard", code="elite")
    card = _create_card(session, card_id="card-guard", player=player, tier=tier)
    session.add(PlayerCardHolding(player_card_id=card.id, owner_user_id=seller.id, quantity_total=1, quantity_reserved=0, metadata_json={}))
    session.flush()

    service = PlayerCardMarketplaceService(session=session, wallet_service=WalletService())

    with pytest.raises(PlayerCardValidationError, match="Listing price must stay between"):
        service.create_sale_listing(
            actor=seller,
            player_card_id=card.id,
            quantity=1,
            price_per_card_credits=Decimal("50.0000"),
        )

    assert session.scalar(select(func.count(PlayerCardListing.id))) == 0


def test_sale_listing_relist_cooldown_persists_integrity_snapshot(session) -> None:
    seller = _create_user(session, user_id="cooldown-seller", email="cooldown-seller@example.com", username="cooldown-seller")
    player = _create_player(session, player_id="cooldown-player", name="Cooldown Seller")
    _create_summary(session, player=player, value_credits=20.0)
    tier = _create_tier(session, tier_id="tier-cooldown", code="gold")
    card = _create_card(session, card_id="card-cooldown", player=player, tier=tier)
    session.add(PlayerCardHolding(player_card_id=card.id, owner_user_id=seller.id, quantity_total=2, quantity_reserved=0, metadata_json={}))
    session.flush()

    service = PlayerCardMarketplaceService(session=session, wallet_service=WalletService())
    listing = service.create_sale_listing(
        actor=seller,
        player_card_id=card.id,
        quantity=1,
        price_per_card_credits=Decimal("18.0000"),
    )
    stored_listing = session.scalar(select(PlayerCardListing).where(PlayerCardListing.listing_id == listing["listing_id"]))

    assert stored_listing is not None
    assert stored_listing.integrity_context_json["reference_source"] == "player_summary.current_value"
    assert stored_listing.integrity_context_json["relist_cooldown_active"] is False

    service.cancel_sale_listing(actor=seller, listing_id=listing["listing_id"])
    with pytest.raises(PlayerCardValidationError, match="relist cooldown"):
        service.create_sale_listing(
            actor=seller,
            player_card_id=card.id,
            quantity=1,
            price_per_card_credits=Decimal("18.0000"),
        )


def test_sale_integrity_signals_repeated_pair_and_price_anomaly(session) -> None:
    seller = _create_user(session, user_id="signal-seller", email="signal-seller@example.com", username="signal-seller")
    buyer = _create_user(session, user_id="signal-buyer", email="signal-buyer@example.com", username="signal-buyer")
    player = _create_player(session, player_id="signal-player", name="Signal Player")
    _create_summary(session, player=player, value_credits=12.0)
    tier = _create_tier(session, tier_id="tier-signal", code="elite")
    card = _create_card(session, card_id="card-signal", player=player, tier=tier)
    session.add(PlayerCardHolding(player_card_id=card.id, owner_user_id=seller.id, quantity_total=3, quantity_reserved=0, metadata_json={}))
    session.flush()

    wallet = WalletService()
    _seed_wallet(session, wallet, buyer, amount=Decimal("100.0000"))
    base_settings = get_settings()
    integrity_config = replace(
        base_settings.player_card_market_integrity,
        listing_price_ceiling_ratio=3.50,
        price_spike_alert_ratio=2.00,
    )
    service = PlayerCardMarketplaceService(
        session=session,
        wallet_service=wallet,
        settings=replace(base_settings, player_card_market_integrity=integrity_config),
    )

    for price in (Decimal("10.0000"), Decimal("10.0000"), Decimal("30.0000")):
        listing = service.create_sale_listing(actor=seller, player_card_id=card.id, quantity=1, price_per_card_credits=price)
        service.buy_sale_listing(actor=buyer, listing_id=listing["listing_id"])

    incidents = session.scalars(
        select(IntegrityIncident).where(IntegrityIncident.incident_type == "repeated_card_trade_pair")
    ).all()
    latest_sale = session.scalar(
        select(PlayerCardSale).where(PlayerCardSale.player_card_id == card.id).order_by(PlayerCardSale.created_at.desc())
    )
    anomaly_event = session.scalar(
        select(SystemEvent).where(SystemEvent.event_type == "player_card_price_anomaly")
    )

    assert len(incidents) == 2
    assert latest_sale is not None
    assert "repeated_pair_trade" in latest_sale.integrity_flags_json["signals"]
    assert "price_anomaly" in latest_sale.integrity_flags_json["signals"]
    assert anomaly_event is not None
    assert anomaly_event.metadata_json["sale_id"] == latest_sale.sale_id


def test_marketplace_search_filters_and_exact_views(session) -> None:
    seller = _create_user(session, user_id="seller-search", email="seller-search@example.com", username="seller-search")
    loan_owner = _create_user(session, user_id="loan-owner", email="loan-owner@example.com", username="loan-owner")
    swap_owner = _create_user(session, user_id="swap-owner", email="swap-owner@example.com", username="swap-owner")

    sale_player = _create_player(session, player_id="player-sale", name="Ayo Seller", position="forward", value_eur=1_500_000)
    loan_player = _create_player(session, player_id="player-loan", name="Bola Lender", position="midfielder", value_eur=2_500_000)
    swap_player = _create_player(session, player_id="player-swap", name="Chika Swapper", position="defender", value_eur=1_000_000)
    _create_summary(session, player=sale_player, club_name="Red City", rating=7.2, value_credits=15.0)
    _create_summary(session, player=loan_player, club_name="Blue City", rating=8.4, value_credits=25.0)
    _create_summary(session, player=swap_player, club_name="Blue City", rating=6.8, value_credits=10.0)

    tier = _create_tier(session, tier_id="tier-search", code="gold")
    sale_card = _create_card(session, card_id="sale-card", player=sale_player, tier=tier)
    loan_card = _create_card(session, card_id="loan-card", player=loan_player, tier=tier, variant="regen_unique")
    swap_card = _create_card(session, card_id="swap-card", player=swap_player, tier=tier)

    session.add(PlayerCardHolding(player_card_id=sale_card.id, owner_user_id=seller.id, quantity_total=2, quantity_reserved=0, metadata_json={}))
    session.add(PlayerCardHolding(player_card_id=loan_card.id, owner_user_id=loan_owner.id, quantity_total=1, quantity_reserved=0, metadata_json={}))
    session.add(PlayerCardHolding(player_card_id=swap_card.id, owner_user_id=swap_owner.id, quantity_total=1, quantity_reserved=0, metadata_json={}))
    session.flush()

    service = PlayerCardMarketplaceService(session=session, wallet_service=WalletService())
    service.create_sale_listing(actor=seller, player_card_id=sale_card.id, quantity=1, price_per_card_credits=Decimal("12.0000"), is_negotiable=True)
    service.create_loan_listing(actor=loan_owner, player_card_id=loan_card.id, total_slots=1, duration_days=5, loan_fee_credits=Decimal("3.5000"))
    service.create_swap_listing(actor=swap_owner, player_card_id=swap_card.id)

    loan_results = service.search_marketplace(listing_type="loan", asset_origin="regen_newgen", sort="cheapest")
    all_results = service.search_marketplace(search="city", club="Blue", availability="available", sort="highest_rated")

    assert loan_results["total"] == 1
    assert loan_results["items"][0]["listing_type"] == "loan"
    assert loan_results["items"][0]["asset_origin"] == "regen_newgen"
    assert all(item["club_name"] == "Blue City" for item in all_results["items"])
    assert all_results["items"][0]["player_name"] == "Bola Lender"


def test_swap_execution_transfers_holdings(session) -> None:
    owner = _create_user(session, user_id="swap-lister", email="swap-lister@example.com", username="swap-lister")
    counterparty = _create_user(session, user_id="swap-counter", email="swap-counter@example.com", username="swap-counter")
    owner_player = _create_player(session, player_id="player-owner", name="Owner Card")
    counter_player = _create_player(session, player_id="player-counter", name="Counter Card")
    _create_summary(session, player=owner_player, value_credits=12.0)
    _create_summary(session, player=counter_player, value_credits=18.0)
    tier = _create_tier(session, tier_id="tier-swap", code="silver")
    owner_card = _create_card(session, card_id="owner-card", player=owner_player, tier=tier)
    counter_card = _create_card(session, card_id="counter-card", player=counter_player, tier=tier)

    session.add(PlayerCardHolding(player_card_id=owner_card.id, owner_user_id=owner.id, quantity_total=1, quantity_reserved=0, metadata_json={}))
    session.add(PlayerCardHolding(player_card_id=counter_card.id, owner_user_id=counterparty.id, quantity_total=1, quantity_reserved=0, metadata_json={}))
    session.flush()

    service = PlayerCardMarketplaceService(session=session, wallet_service=WalletService())
    listing = service.create_swap_listing(actor=owner, player_card_id=owner_card.id, requested_player_card_id=counter_card.id)
    execution = service.execute_swap_listing(actor=counterparty, listing_id=listing["listing_id"], counterparty_player_card_id=counter_card.id)

    owner_received = session.query(PlayerCardHolding).filter_by(owner_user_id=owner.id, player_card_id=counter_card.id).one()
    counter_received = session.query(PlayerCardHolding).filter_by(owner_user_id=counterparty.id, player_card_id=owner_card.id).one()

    assert execution["status"] == "executed"
    assert owner_received.quantity_total == 1
    assert counter_received.quantity_total == 1
    assert session.query(CardSwapExecution).count() == 1
