from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.enums.contract_status import ContractStatus
from app.ingestion.models import Player
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.player_cards import PlayerCard, PlayerCardHolding, PlayerCardTier
from app.models.player_contract import PlayerContract
from app.models.user import KycStatus, User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.player_cards.marketplace_service import PlayerCardMarketplaceService
from app.wallets.service import LedgerPosting, WalletService


@pytest.fixture()
def card_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_player_card_purchase_does_not_affect_club_transfer_or_contract(card_session: Session) -> None:
    seller_user = User(
        id="user-card-seller",
        email="seller@example.com",
        username="seller",
        display_name="Seller",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    buyer_user = User(
        id="user-card-buyer",
        email="buyer@example.com",
        username="buyer",
        display_name="Buyer",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    seller_club = ClubProfile(
        id="club-seller",
        owner_user_id=seller_user.id,
        club_name="Seller FC",
        short_name="SFC",
        slug="seller-fc",
        primary_color="#111111",
        secondary_color="#222222",
        accent_color="#333333",
    )
    buyer_club = ClubProfile(
        id="club-buyer",
        owner_user_id=buyer_user.id,
        club_name="Buyer FC",
        short_name="BFC",
        slug="buyer-fc",
        primary_color="#444444",
        secondary_color="#555555",
        accent_color="#666666",
    )
    player = Player(
        id="player-card-test",
        source_provider="test",
        provider_external_id="player-card-test",
        current_club_profile_id=seller_club.id,
        full_name="Card Test Player",
        normalized_position="forward",
    )
    contract = PlayerContract(
        id="contract-test-1",
        player_id=player.id,
        club_id=seller_club.id,
        status=ContractStatus.ACTIVE.value,
        wage_amount=Decimal("50000.00"),
        signed_on=date(2026, 1, 1),
        starts_on=date(2026, 1, 1),
        ends_on=date(2028, 12, 31),
    )
    tier = PlayerCardTier(
        id="tier-gold",
        code="gold",
        name="Gold Tier",
        rarity_rank=1,
        max_supply=100,
        supply_multiplier=Decimal("1.0"),
        base_mint_price_credits=Decimal("10.0"),
        color_hex="#ffd700",
        is_active=True,
    )
    card = PlayerCard(
        id="card-test-1",
        player_id=player.id,
        tier_id=tier.id,
        edition_code="standard",
        display_name="Card Test Player Gold",
        season_label="2025/26",
        supply_total=10,
        supply_available=10,
    )
    holding = PlayerCardHolding(
        id="holding-seller-1",
        player_card_id=card.id,
        owner_user_id=seller_user.id,
        quantity_total=2,
        quantity_reserved=0,
    )
    card_session.add_all([seller_user, buyer_user, seller_club, buyer_club, player, contract, tier, card, holding])
    card_session.commit()

    wallet_service = WalletService()
    wallet_service.append_transaction(
        card_session,
        postings=[
            LedgerPosting(
                account=wallet_service.ensure_platform_account(card_session, LedgerUnit.COIN),
                amount=Decimal("-1000.00"),
                source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            ),
            LedgerPosting(
                account=wallet_service.get_user_account(card_session, buyer_user, LedgerUnit.COIN),
                amount=Decimal("1000.00"),
                source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            ),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        reference="fund-buyer-test",
        description="Fund buyer for card test",
        actor=buyer_user,
    )
    card_session.commit()

    mkt_service = PlayerCardMarketplaceService(session=card_session)
    listing = mkt_service.create_sale_listing(
        actor=seller_user,
        player_card_id=card.id,
        quantity=1,
        price_per_card_credits=Decimal("1.00"),
    )
    card_session.commit()

    contracts_before = card_session.query(PlayerContract).filter_by(player_id=player.id).count()
    club_before = player.current_club_profile_id

    sale_result = mkt_service.buy_sale_listing(
        actor=buyer_user,
        listing_id=listing["listing_id"],
        quantity=1,
    )
    card_session.commit()

    card_session.refresh(player)
    card_session.refresh(contract)
    contracts_after = card_session.query(PlayerContract).filter_by(player_id=player.id).count()

    assert sale_result["status"] == "settled"
    assert contracts_after == contracts_before == 1
    assert contract.status == ContractStatus.ACTIVE.value
    assert contract.club_id == seller_club.id
    assert player.current_club_profile_id == seller_club.id == club_before
