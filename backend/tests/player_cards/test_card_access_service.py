from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.ingestion.models  # noqa: F401
import backend.app.models.card_access  # noqa: F401
import backend.app.models.player_cards  # noqa: F401
from backend.app.core.config import get_settings
from backend.app.ingestion.models import Player
from backend.app.models.base import Base
from backend.app.models.player_cards import PlayerCard, PlayerCardHolding, PlayerCardTier
from backend.app.models.user import User, UserRole
from backend.app.models.wallet import LedgerEntryReason, LedgerUnit
from backend.app.player_cards.access_service import CardLoanService, StarterSquadRentalService
from backend.app.player_cards.service import PlayerCardValidationError
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
    user = User(id=user_id, email=email, username=username, password_hash="hashed", role=role)
    session.add(user)
    session.flush()
    return user


def _create_player(session, *, player_id: str, name: str, club_id: str | None = None, value: float | None = None) -> Player:
    player = Player(
        id=player_id,
        source_provider="test",
        provider_external_id=player_id,
        full_name=name,
        current_club_profile_id=club_id,
        market_value_eur=value,
        is_tradable=True,
    )
    session.add(player)
    session.flush()
    return player


def _create_tier(session, *, tier_id: str = "tier-elite", code: str = "elite") -> PlayerCardTier:
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


def _create_card(session, *, card_id: str, player: Player, tier: PlayerCardTier) -> PlayerCard:
    card = PlayerCard(
        id=card_id,
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


def _seed_wallet(session, wallet: WalletService, user: User, *, amount: Decimal, unit: LedgerUnit) -> None:
    account = wallet.get_user_account(session, user, unit)
    platform = wallet.ensure_platform_account(session, unit)
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=platform, amount=-amount),
            LedgerPosting(account=account, amount=amount),
        ],
        reason=LedgerEntryReason.DEPOSIT,
        reference=f"seed-{user.id}-{unit.value}",
        description="seed funds",
        actor=user,
    )


def test_create_card_loan_listing_reserves_quantity(session) -> None:
    seller = _create_user(session, user_id="seller", email="seller@example.com", username="seller")
    player = _create_player(session, player_id="player-1", name="Loan Target")
    tier = _create_tier(session)
    card = _create_card(session, card_id="card-1", player=player, tier=tier)
    holding = PlayerCardHolding(player_card_id=card.id, owner_user_id=seller.id, quantity_total=3, quantity_reserved=0, metadata_json={})
    session.add(holding)
    session.flush()

    service = CardLoanService(session=session)
    listing = service.create_listing(
        actor=seller,
        player_card_id=card.id,
        total_slots=2,
        duration_days=5,
        loan_fee_credits=Decimal("4.5"),
        usage_restrictions={"allowed_squad_scopes": ["first_team"]},
        terms={"allow_early_return": True},
    )

    refreshed = session.get(PlayerCardHolding, holding.id)
    assert refreshed.quantity_reserved == 2
    assert listing["available_slots"] == 2
    assert listing["usage_restrictions_json"]["allowed_squad_scopes"] == ["first_team"]


def test_card_loan_borrow_and_return_transfers_fee_and_restores_access(session) -> None:
    seller = _create_user(session, user_id="seller-2", email="seller2@example.com", username="seller2")
    borrower = _create_user(session, user_id="borrower", email="borrower@example.com", username="borrower")
    player = _create_player(session, player_id="player-2", name="Borrow Target")
    tier = _create_tier(session, tier_id="tier-gold", code="gold")
    card = _create_card(session, card_id="card-2", player=player, tier=tier)
    holding = PlayerCardHolding(player_card_id=card.id, owner_user_id=seller.id, quantity_total=1, quantity_reserved=0, metadata_json={})
    session.add(holding)
    session.flush()

    wallet = WalletService()
    _seed_wallet(session, wallet, borrower, amount=Decimal("25.0000"), unit=LedgerUnit.COIN)

    service = CardLoanService(session=session, wallet_service=wallet)
    listing = service.create_listing(
        actor=seller,
        player_card_id=card.id,
        total_slots=1,
        duration_days=7,
        loan_fee_credits=Decimal("10.0000"),
        usage_restrictions={"allowed_competition_ids": ["cup-1"], "allowed_squad_scopes": ["first_team"]},
    )
    contract = service.borrow_listing(actor=borrower, listing_id=listing["loan_listing_id"], competition_id="cup-1", squad_scope="first_team")

    seller_balance = wallet.get_balance(session, wallet.get_user_account(session, seller, LedgerUnit.COIN))
    borrower_balance = wallet.get_balance(session, wallet.get_user_account(session, borrower, LedgerUnit.COIN))
    assert seller_balance == Decimal("10.0000")
    assert borrower_balance == Decimal("15.0000")
    assert contract["available_slots"] == 0
    assert service.validate_contract_usage(
        borrower_user_id=borrower.id,
        player_card_id=card.id,
        competition_id="cup-1",
        squad_scope="first_team",
    )

    returned = service.return_loan(actor=borrower, contract_id=contract["loan_contract_id"])
    assert returned["contract_status"] == "returned"
    assert returned["available_slots"] == 1


def test_starter_rental_generates_non_tradable_rosters_and_blocks_repeat_rental(session) -> None:
    user = _create_user(session, user_id="renter", email="renter@example.com", username="renter")
    wallet = WalletService()
    _seed_wallet(session, wallet, user, amount=Decimal("10.0000"), unit=LedgerUnit.CREDIT)

    service = StarterSquadRentalService(session=session, settings=get_settings(), wallet_service=wallet)
    rental = service.create_rental(actor=user, include_academy=True)

    assert rental["first_team_count"] == 18
    assert rental["academy_count"] == 18
    assert len(rental["roster"]) == 18
    assert len(rental["academy_roster"]) == 18
    assert all(item["non_tradable"] is True for item in rental["roster"])
    assert all(item["current_gsi"] == item["locked_gsi"] for item in rental["roster"])

    with pytest.raises(PlayerCardValidationError):
        service.create_rental(actor=user)


def test_starter_rental_rejects_users_with_permanent_holdings(session) -> None:
    user = _create_user(session, user_id="owner-user", email="owner@example.com", username="owner-user")
    player = _create_player(session, player_id="player-3", name="Owned Player")
    tier = _create_tier(session, tier_id="tier-owned", code="owned")
    card = _create_card(session, card_id="card-owned", player=player, tier=tier)
    session.add(PlayerCardHolding(player_card_id=card.id, owner_user_id=user.id, quantity_total=1, quantity_reserved=0, metadata_json={}))
    session.flush()

    service = StarterSquadRentalService(session=session, settings=get_settings(), wallet_service=WalletService())
    with pytest.raises(PlayerCardValidationError):
        service.create_rental(actor=user)
