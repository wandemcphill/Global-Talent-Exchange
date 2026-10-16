from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.access_control.service import AccessControlService
from app.core.database import load_model_modules
from app.ingestion.models import Player
from app.legend_layer.player_foundation import LegendaryPlayerFoundationService, LegendaryPlayerSeed
from app.market.service import MarketPlayerQueryService
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.player_token_market import PlayerShareMarket
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.players.legacy_token_service import PlayerTokenMarketService
from app.transfer_market.schemas import TransferHubOfferCreateRequest, TransferListingCreateRequest
from app.transfer_market.service import TransferMarketService
from app.wallets.service import LedgerPosting, WalletService


def _user(session, *, user_id: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        id=user_id,
        email=f"{user_id}@example.com",
        username=user_id,
        password_hash="hash",
        role=role,
    )
    session.add(user)
    session.flush()
    WalletService().ensure_default_accounts(session, user)
    return user


def _club(session, *, club_id: str, owner: User) -> ClubProfile:
    club = ClubProfile(
        id=club_id,
        owner_user_id=owner.id,
        club_name=club_id.replace("-", " ").title(),
        slug=club_id,
        primary_color="#111111",
        secondary_color="#eeeeee",
        accent_color="#00aa00",
        country_code="NG",
    )
    session.add(club)
    session.flush()
    AccessControlService(session).ensure_club_organization(club, owner_user_id=owner.id)
    session.flush()
    return club


def _fund_coin(session, *, user: User, amount: Decimal) -> None:
    wallet = WalletService()
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=wallet.get_user_account(session, user, LedgerUnit.COIN), amount=amount),
            LedgerPosting(account=wallet.ensure_platform_account(session, LedgerUnit.COIN), amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        reference=f"legendary-test-funding:{user.id}",
        actor=user,
    )


def test_legendary_player_uses_the_standard_search_market_and_transfer_lifecycle() -> None:
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with Session() as session:
        seller = _user(session, user_id="legendary-seller", role=UserRole.ADMIN)
        buyer = _user(session, user_id="legendary-buyer")
        seller_club = _club(session, club_id="legendary-seller-fc", owner=seller)
        buyer_club = _club(session, club_id="legendary-buyer-fc", owner=buyer)
        _fund_coin(session, user=buyer, amount=Decimal("100.0000"))

        ordinary = Player(
            id="ordinary-player",
            source_provider="ordinary-test",
            provider_external_id="ordinary-player",
            full_name="Ordinary Player",
            canonical_display_name="Ordinary Player",
            normalized_position="midfielder",
            is_tradable=True,
        )
        session.add(ordinary)
        session.flush()

        legend = LegendaryPlayerFoundationService(session).seed(
            actor=seller,
            seed=LegendaryPlayerSeed(
                key="jay-jay-okocha",
                full_name="Jay Jay Okocha",
                nationality_name="Nigeria",
                nationality_code="NG",
                position="forward",
                market_value_eur=12_000_000,
                current_club_profile_id=seller_club.id,
            ),
        )
        session.commit()

        # Exact/partial name, nationality, and position all use MarketPlayerQueryService.
        market_query = MarketPlayerQueryService(session)
        assert [item.player_id for item in market_query.list_players(search="Jay Jay Okocha").items] == [legend.id]
        assert [item.player_id for item in market_query.list_players(search="Okocha").items] == [legend.id]
        assert [item.player_id for item in market_query.list_players(nationality="Nigeria").items] == [legend.id]
        assert [item.player_id for item in market_query.list_players(position="forward").items] == [legend.id]
        assert market_query.get_player_detail(legend.id).identity.player_name == "Jay Jay Okocha"

        shares = PlayerTokenMarketService(session)
        active_market = shares.get_market_view(player_id=legend.id)
        assert active_market["status"] == "active"
        assert session.get(PlayerShareMarket, active_market["id"]) is not None

        # Existing acquisition and resale operations create and update normal holdings.
        purchase = shares.buy_shares(actor=buyer, player_id=legend.id, share_count=10)
        assert purchase["holding"].share_count == 10
        resale = shares.sell_shares(actor=buyer, player_id=legend.id, share_count=4)
        assert resale["holding"].share_count == 6

        # Existing transfer-listing and offer acceptance logic accepts the same player id.
        transfers = TransferMarketService(session)
        listing = transfers.create_listing(
            TransferListingCreateRequest(
                player_id=legend.id,
                selling_club_id=seller_club.id,
                base_price=Decimal("1000000.00"),
                expires_at=datetime.now(UTC) + timedelta(days=1),
            ),
            actor=seller,
        )
        offer = transfers.create_hub_offer(
            listing.id,
            TransferHubOfferCreateRequest(cash_amount=Decimal("1200000.00"), idempotency_key="legendary-offer-001"),
            actor=buyer,
            bidder_club_id=buyer_club.id,
        )
        accepted = transfers.accept_hub_offer(offer.id, actor=seller)
        assert accepted.status == "accepted"

        # An ordinary record remains discoverable and has no market created as a side effect.
        assert ordinary.id in {item.player_id for item in market_query.list_players(search="Ordinary").items}
        assert session.query(PlayerShareMarket).filter_by(player_id=ordinary.id).one_or_none() is None
