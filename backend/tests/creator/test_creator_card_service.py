from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.club_identity.models.reputation  # noqa: F401
import backend.app.ingestion.models  # noqa: F401
import backend.app.models  # noqa: F401
from backend.app.common.enums.creator_profile_status import CreatorProfileStatus
from backend.app.ingestion.models import Player
from backend.app.models.base import Base
from backend.app.models.creator_profile import CreatorProfile
from backend.app.models.user import User
from backend.app.models.wallet import LedgerEntryReason, LedgerUnit
from backend.app.services.creator_card_service import (
    CreatorCardPermissionError,
    CreatorCardService,
    CreatorCardValidationError,
)
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


def _create_user(session, *, user_id: str, email: str, username: str) -> User:
    user = User(id=user_id, email=email, username=username, password_hash="hashed", phone_number="1234567890")
    session.add(user)
    session.flush()
    return user


def _create_creator_profile(session, *, profile_id: str, user: User, handle: str) -> CreatorProfile:
    profile = CreatorProfile(
        id=profile_id,
        user_id=user.id,
        handle=handle,
        display_name=handle.title(),
        tier="emerging",
        status=CreatorProfileStatus.ACTIVE,
    )
    session.add(profile)
    session.flush()
    return profile


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


def _seed_wallet(session, wallet: WalletService, user: User, amount: Decimal) -> None:
    user_account = wallet.get_user_account(session, user, LedgerUnit.CREDIT)
    platform_account = wallet.ensure_platform_account(session, LedgerUnit.CREDIT)
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=platform_account, amount=-amount),
            LedgerPosting(account=user_account, amount=amount),
        ],
        reason=LedgerEntryReason.DEPOSIT,
        reference=f"seed-{user.id}",
        description="seed credits",
        actor=user,
    )


def test_creator_card_uniqueness_and_creator_only_buy_sell_swap_loan_constraints(session) -> None:
    creator_one = _create_user(session, user_id="creator-1", email="creator1@example.com", username="creator1")
    creator_two = _create_user(session, user_id="creator-2", email="creator2@example.com", username="creator2")
    regular_user = _create_user(session, user_id="user-3", email="user3@example.com", username="user3")
    _create_creator_profile(session, profile_id="profile-1", user=creator_one, handle="creator.one")
    _create_creator_profile(session, profile_id="profile-2", user=creator_two, handle="creator.two")

    player_one = _create_player(session, player_id="player-1", name="Alpha Striker")
    player_two = _create_player(session, player_id="player-2", name="Bravo Midfielder")
    player_three = _create_player(session, player_id="player-3", name="Charlie Defender")

    wallet = WalletService()
    _seed_wallet(session, wallet, creator_one, Decimal("50.0000"))
    _seed_wallet(session, wallet, creator_two, Decimal("50.0000"))
    service = CreatorCardService(session=session, wallet_service=wallet)

    card_one = service.assign_card(player_id=player_one.id, owner_user_id=creator_one.id)
    card_two = service.assign_card(player_id=player_two.id, owner_user_id=creator_two.id)
    card_three = service.assign_card(player_id=player_three.id, owner_user_id=creator_one.id)

    with pytest.raises(CreatorCardValidationError):
        service.assign_card(player_id=player_one.id, owner_user_id=creator_two.id)

    listing = service.create_listing(
        actor=creator_one,
        creator_card_id=card_one["creator_card_id"],
        price_credits=Decimal("10.0000"),
    )

    with pytest.raises(CreatorCardPermissionError):
        service.buy_listing(actor=regular_user, listing_id=listing["listing_id"])

    sale = service.buy_listing(actor=creator_two, listing_id=listing["listing_id"])
    assert sale["buyer_user_id"] == creator_two.id
    inventory_two = service.list_inventory(actor=creator_two)
    assert {item["player_id"] for item in inventory_two} >= {player_one.id, player_two.id}

    swap = service.swap_cards(
        actor=creator_one,
        offered_card_id=card_three["creator_card_id"],
        requested_card_id=card_two["creator_card_id"],
    )
    assert swap["status"] == "executed"
    inventory_one = service.list_inventory(actor=creator_one)
    assert {item["player_id"] for item in inventory_one} == {player_two.id}

    with pytest.raises(CreatorCardPermissionError):
        service.loan_card(
            actor=creator_two,
            creator_card_id=card_one["creator_card_id"],
            borrower_user_id=regular_user.id,
            duration_days=7,
            loan_fee_credits=Decimal("2.0000"),
        )

    loan = service.loan_card(
        actor=creator_two,
        creator_card_id=card_one["creator_card_id"],
        borrower_user_id=creator_one.id,
        duration_days=7,
        loan_fee_credits=Decimal("2.0000"),
    )
    assert loan["status"] == "active"
    returned = service.return_loan(actor=creator_one, loan_id=loan["loan_id"])
    assert returned["status"] == "returned"
