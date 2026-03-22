from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.club_sale_market.service import ClubSaleMarketError, ClubSaleMarketService
from app.models.base import Base
from app.models.calendar_engine import CalendarEvent
from app.models.club_profile import ClubProfile
from app.models.club_sale_market import (
    ClubSaleInquiry,
    ClubSaleInquiryStatus,
    ClubSaleListing,
    ClubSaleListingStatus,
    ClubSaleOffer,
    ClubSaleOfferStatus,
    ClubSaleTransfer,
    ClubSaleTransferStatus,
    ClubValuationSnapshot,
)
from app.models.creator_share_market import CreatorClubShareHolding, CreatorClubShareMarket
from app.models.story_feed import StoryFeedItem
from app.models.user import User
from app.models.wallet import LedgerEntry, LedgerEntryReason, LedgerSourceTag, LedgerUnit
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


def _create_user(session, *, user_id: str, email: str, username: str) -> User:
    user = User(id=user_id, email=email, username=username, password_hash="hashed")
    session.add(user)
    session.flush()
    return user


def _create_club(session, *, club_id: str, owner_user_id: str) -> ClubProfile:
    club = ClubProfile(
        id=club_id,
        owner_user_id=owner_user_id,
        club_name="Lagos Comets FC",
        short_name="LCFC",
        slug=f"lagos-comets-{club_id}",
        crest_asset_ref=None,
        primary_color="#112233",
        secondary_color="#ddeeff",
        accent_color="#44aa66",
        home_venue_name="Comet Park",
        country_code="NG",
        region_name="Lagos",
        city_name="Lagos",
        description="Test creator club",
        visibility="public",
        founded_at=None,
    )
    session.add(club)
    session.flush()
    return club


def _seed_wallet(session, wallet: WalletService, user: User, *, amount: Decimal) -> None:
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
        description="seed funds",
        actor=user,
    )


def _attach_shareholders(session, *, club_id: str, owner: User, fan: User) -> CreatorClubShareMarket:
    market = CreatorClubShareMarket(
        id=f"market-{club_id}",
        club_id=club_id,
        creator_user_id=owner.id,
        issued_by_user_id=owner.id,
        status="active",
        share_price_coin=Decimal("5.0000"),
        max_shares_issued=1000,
        shares_sold=25,
        max_shares_per_fan=250,
        creator_controlled_shares=1001,
        shareholder_revenue_share_bps=2000,
        total_purchase_volume_coin=Decimal("125.0000"),
        total_revenue_distributed_coin=Decimal("0.0000"),
        metadata_json={},
    )
    holding = CreatorClubShareHolding(
        id=f"holding-{club_id}",
        market_id=market.id,
        club_id=club_id,
        user_id=fan.id,
        share_count=25,
        total_spent_coin=Decimal("125.0000"),
        revenue_earned_coin=Decimal("0.0000"),
        metadata_json={},
    )
    session.add_all([market, holding])
    session.flush()
    return market


def _prepare_market_sale(session):
    seller = _create_user(session, user_id="seller", email="seller@example.com", username="seller")
    buyer = _create_user(session, user_id="buyer", email="buyer@example.com", username="buyer")
    fan = _create_user(session, user_id="fan", email="fan@example.com", username="fan")
    club = _create_club(session, club_id="club-sale", owner_user_id=seller.id)
    share_market = _attach_shareholders(session, club_id=club.id, owner=seller, fan=fan)
    wallet = WalletService()
    _seed_wallet(session, wallet, buyer, amount=Decimal("200.0000"))
    service = ClubSaleMarketService(session=session, wallet_service=wallet)
    return {
        "buyer": buyer,
        "club": club,
        "fan": fan,
        "seller": seller,
        "service": service,
        "share_market": share_market,
        "wallet": wallet,
    }


def test_canonical_sale_flow_exposes_public_values_and_settles_on_executed_price(session) -> None:
    prepared = _prepare_market_sale(session)
    seller = prepared["seller"]
    buyer = prepared["buyer"]
    fan = prepared["fan"]
    club = prepared["club"]
    share_market = prepared["share_market"]
    service = prepared["service"]
    wallet = prepared["wallet"]

    valuation = service.get_valuation(club_id=club.id)
    listing = service.create_listing(
        actor=seller,
        club_id=club.id,
        asking_price=Decimal("100.0000"),
        visibility="public",
        note="Public asking price is visible.",
        metadata_json={"channel": "open-market"},
    )
    public_listing = service.get_public_listing(club_id=club.id)

    inquiry = service.create_inquiry(
        actor=buyer,
        club_id=club.id,
        message="Interested buyer ready to talk.",
        metadata_json={"origin": "public-profile"},
    )
    inquiry_response = service.respond_inquiry(
        actor=seller,
        club_id=club.id,
        inquiry_id=inquiry["inquiry_id"],
        response_message="Still available.",
        close_thread=False,
        metadata_json={"reply": "owner-response"},
    )
    offer = service.create_offer(
        actor=buyer,
        club_id=club.id,
        offer_price=Decimal("95.0000"),
        inquiry_id=inquiry["inquiry_id"],
        message="Cash buyer, ready to settle.",
        expires_at=None,
        metadata_json={"path": "direct-offer"},
    )
    accepted_offer = service.accept_offer(
        actor=seller,
        club_id=club.id,
        offer_id=offer["offer_id"],
        message="Accepted pending settlement.",
        metadata_json={"owner": "accepted"},
    )

    seller_account = wallet.get_user_account(session, seller, LedgerUnit.COIN)
    buyer_account = wallet.get_user_account(session, buyer, LedgerUnit.COIN)
    platform_account = wallet.ensure_platform_account(session, LedgerUnit.COIN)
    seller_before = wallet.get_balance(session, seller_account)
    buyer_before = wallet.get_balance(session, buyer_account)
    platform_before = wallet.get_balance(session, platform_account)

    transfer = service.execute_transfer(
        actor=seller,
        club_id=club.id,
        offer_id=offer["offer_id"],
        executed_sale_price=Decimal("80.0000"),
        metadata_json={"settlement": "manual-execution"},
    )
    history = service.history_for_club(actor=buyer, club_id=club.id)
    session.flush()

    listing_row = session.scalar(select(ClubSaleListing).where(ClubSaleListing.listing_id == listing["listing_id"]))
    inquiry_row = session.scalar(select(ClubSaleInquiry).where(ClubSaleInquiry.inquiry_id == inquiry["inquiry_id"]))
    offer_row = session.scalar(select(ClubSaleOffer).where(ClubSaleOffer.offer_id == offer["offer_id"]))
    transfer_row = session.scalar(select(ClubSaleTransfer).where(ClubSaleTransfer.transfer_id == transfer["transfer_id"]))
    transfer_row_id = transfer_row.id if transfer_row is not None else ""
    transfer_story = session.scalar(
        select(StoryFeedItem).where(
            StoryFeedItem.subject_type == "club_sale_transfer",
            StoryFeedItem.subject_id == transfer["transfer_id"],
        )
    )
    transfer_calendar_event = session.scalar(
        select(CalendarEvent).where(
            CalendarEvent.source_type == "club_sale_transfer",
            CalendarEvent.source_id == transfer_row_id,
        )
    )
    valuation_snapshots = session.scalars(
        select(ClubValuationSnapshot)
        .where(ClubValuationSnapshot.club_id == club.id)
        .order_by(ClubValuationSnapshot.created_at.asc(), ClubValuationSnapshot.id.asc())
    ).all()
    shareholder_holding = session.scalar(
        select(CreatorClubShareHolding).where(
            CreatorClubShareHolding.club_id == club.id,
            CreatorClubShareHolding.user_id == fan.id,
        )
    )
    ledger_entries = session.scalars(
        select(LedgerEntry)
        .where(LedgerEntry.reference == transfer["settlement_reference"])
        .order_by(LedgerEntry.created_at.asc(), LedgerEntry.id.asc())
    ).all()

    assert valuation["currency"] == LedgerUnit.COIN.value
    assert valuation["system_valuation"] == (
        valuation["breakdown"]["first_team_value"]
        + valuation["breakdown"]["reserve_squad_value"]
        + valuation["breakdown"]["u19_squad_value"]
        + valuation["breakdown"]["academy_value"]
        + valuation["breakdown"]["stadium_value"]
        + valuation["breakdown"]["paid_enhancements_value"]
    )
    assert listing["asking_price"] == Decimal("100.0000")
    assert public_listing["asking_price"] == Decimal("100.0000")
    assert "system_valuation" in public_listing
    assert public_listing["system_valuation"] == listing["system_valuation"]

    assert inquiry_response["status"] == ClubSaleInquiryStatus.RESPONDED
    assert accepted_offer["status"] == ClubSaleOfferStatus.ACCEPTED

    assert transfer["executed_sale_price"] == Decimal("80.0000")
    assert transfer["platform_fee_amount"] == Decimal("8.0000")
    assert transfer["seller_net_amount"] == Decimal("72.0000")
    assert transfer["platform_fee_bps"] == 1000
    assert transfer["status"] == ClubSaleTransferStatus.SETTLED
    assert transfer["story_feed_item_id"]
    assert transfer["calendar_event_id"]
    assert transfer["ownership_transition"]["previous_owner_user_id"] == seller.id
    assert transfer["ownership_transition"]["new_owner_user_id"] == buyer.id
    assert transfer["ownership_transition"]["shareholder_rights_preserved"] is True

    assert listing_row is not None
    assert inquiry_row is not None
    assert offer_row is not None
    assert transfer_row is not None
    assert transfer_story is not None
    assert transfer_calendar_event is not None
    assert listing_row.status == ClubSaleListingStatus.TRANSFERRED
    assert inquiry_row.status == ClubSaleInquiryStatus.CLOSED_ON_TRANSFER
    assert offer_row.status == ClubSaleOfferStatus.EXECUTED
    assert transfer_row.status == ClubSaleTransferStatus.SETTLED
    assert transfer_row.executed_sale_price == Decimal("80.0000")
    assert transfer_row.platform_fee_amount == Decimal("8.0000")
    assert transfer_row.seller_net_amount == Decimal("72.0000")
    assert transfer_row.platform_fee_bps == 1000
    assert transfer_row.metadata_json["story_feed_item_id"] == transfer["story_feed_item_id"]
    assert transfer_row.metadata_json["calendar_event_id"] == transfer["calendar_event_id"]
    assert listing_row.valuation_snapshot_id is not None
    assert transfer_row.valuation_snapshot_id is not None
    assert len(valuation_snapshots) == 2
    assert club.owner_user_id == buyer.id
    assert transfer_story.story_type == "club_sale_transfer"
    assert transfer_calendar_event.event_key == f"club-sale-transfer:{transfer_row.id}"

    assert shareholder_holding is not None
    assert shareholder_holding.share_count == 25
    assert shareholder_holding.club_id == club.id
    assert share_market.creator_user_id == buyer.id
    assert shareholder_holding.metadata_json["club_sale_shareholders_preserved"] is True
    assert history["ownership_history"]["transfer_count"] == 1
    assert history["ownership_history"]["current_owner_user_id"] == buyer.id
    assert history["ownership_history"]["shareholder_count"] == 1
    assert history["ownership_history"]["active_governance_proposal_count"] == 0
    assert history["dynasty_snapshot"]["ownership_eras"] == 2
    assert history["dynasty_snapshot"]["shareholder_continuity_transfers"] == 1
    assert history["transfers"][0]["ownership_transition"]["ownership_lineage_index"] == 1

    assert wallet.get_balance(session, seller_account) - seller_before == Decimal("72.0000")
    assert wallet.get_balance(session, buyer_account) - buyer_before == Decimal("-80.0000")
    assert wallet.get_balance(session, platform_account) - platform_before == Decimal("8.0000")

    assert len(ledger_entries) == 3
    assert {entry.reason for entry in ledger_entries} == {LedgerEntryReason.TRADE_SETTLEMENT}
    assert {entry.source_tag for entry in ledger_entries} == {
        LedgerSourceTag.CLUB_SALE_PLATFORM_FEE,
        LedgerSourceTag.CLUB_SALE_PURCHASE,
        LedgerSourceTag.CLUB_SALE_SALE,
    }

    with pytest.raises(ClubSaleMarketError, match="current club owner"):
        service.create_listing(
            actor=seller,
            club_id=club.id,
            asking_price=Decimal("90.0000"),
            visibility="public",
            note="Old owner should not relist.",
        )

    relisted = service.create_listing(
        actor=buyer,
        club_id=club.id,
        asking_price=Decimal("105.0000"),
        visibility="public",
        note="New owner relisted the club.",
    )
    updated = service.update_listing(
        actor=buyer,
        club_id=club.id,
        asking_price=Decimal("110.0000"),
        visibility="private",
        note="New owner can still manage the club.",
    )
    assert relisted["seller_user_id"] == buyer.id
    assert updated["asking_price"] == Decimal("110.0000")
    assert updated["visibility"] == "private"


def test_only_current_owner_can_create_one_active_listing(session) -> None:
    owner = _create_user(session, user_id="owner", email="owner@example.com", username="owner")
    intruder = _create_user(session, user_id="intruder", email="intruder@example.com", username="intruder")
    club = _create_club(session, club_id="club-owner-check", owner_user_id=owner.id)
    service = ClubSaleMarketService(session=session, wallet_service=WalletService())

    with pytest.raises(ClubSaleMarketError, match="current club owner"):
        service.create_listing(
            actor=intruder,
            club_id=club.id,
            asking_price=Decimal("50.0000"),
            visibility="public",
            note=None,
        )

    service.create_listing(
        actor=owner,
        club_id=club.id,
        asking_price=Decimal("50.0000"),
        visibility="public",
        note=None,
    )

    with pytest.raises(ClubSaleMarketError, match="active club sale listing already exists"):
        service.create_listing(
            actor=owner,
            club_id=club.id,
            asking_price=Decimal("60.0000"),
            visibility="public",
            note=None,
        )


def test_offer_counterparty_switches_to_buyer_on_seller_counter(session) -> None:
    seller = _create_user(session, user_id="seller-counter", email="seller-counter@example.com", username="seller-counter")
    buyer = _create_user(session, user_id="buyer-counter", email="buyer-counter@example.com", username="buyer-counter")
    club = _create_club(session, club_id="club-counter", owner_user_id=seller.id)
    wallet = WalletService()
    _seed_wallet(session, wallet, buyer, amount=Decimal("250.0000"))
    service = ClubSaleMarketService(session=session, wallet_service=wallet)

    listing = service.create_listing(
        actor=seller,
        club_id=club.id,
        asking_price=Decimal("120.0000"),
        visibility="public",
        note=None,
    )
    initial_offer = service.create_offer(
        actor=buyer,
        club_id=club.id,
        offer_price=Decimal("100.0000"),
        inquiry_id=None,
        message="Initial buyer offer.",
        expires_at=None,
    )
    counter = service.counter_offer(
        actor=seller,
        club_id=club.id,
        offer_id=initial_offer["offer_id"],
        offer_price=Decimal("112.0000"),
        message="Seller counter.",
        expires_at=None,
    )

    assert counter["proposer_user_id"] == seller.id
    assert counter["counterparty_user_id"] == buyer.id
    assert counter["offer_type"] == "counter"

    with pytest.raises(ClubSaleMarketError, match="current counterparty can reject"):
        service.reject_offer(
            actor=seller,
            club_id=club.id,
            offer_id=counter["offer_id"],
            message="Seller cannot reject own counter.",
        )

    accepted_counter = service.accept_offer(
        actor=buyer,
        club_id=club.id,
        offer_id=counter["offer_id"],
        message="Buyer accepts seller counter.",
    )
    listing_row = session.scalar(select(ClubSaleListing).where(ClubSaleListing.listing_id == listing["listing_id"]))

    assert accepted_counter["status"] == ClubSaleOfferStatus.ACCEPTED
    assert listing_row is not None
    assert listing_row.status == ClubSaleListingStatus.UNDER_OFFER


def test_listing_cancel_closes_open_threads_and_blocks_stale_transfer(session) -> None:
    prepared = _prepare_market_sale(session)
    seller = prepared["seller"]
    buyer = prepared["buyer"]
    club = prepared["club"]
    service = prepared["service"]

    listing = service.create_listing(
        actor=seller,
        club_id=club.id,
        asking_price=Decimal("90.0000"),
        visibility="public",
        note="Cancelable listing.",
    )
    inquiry = service.create_inquiry(
        actor=buyer,
        club_id=club.id,
        message="Please keep me posted.",
    )
    offer = service.create_offer(
        actor=buyer,
        club_id=club.id,
        offer_price=Decimal("82.0000"),
        inquiry_id=inquiry["inquiry_id"],
        message="Open offer before cancellation.",
        expires_at=None,
    )
    accepted = service.accept_offer(
        actor=seller,
        club_id=club.id,
        offer_id=offer["offer_id"],
        message="Accepted, pending next step.",
    )
    cancelled = service.cancel_listing(
        actor=seller,
        club_id=club.id,
        reason="Owner pulled the club from sale.",
    )

    listing_row = session.scalar(select(ClubSaleListing).where(ClubSaleListing.listing_id == listing["listing_id"]))
    inquiry_row = session.scalar(select(ClubSaleInquiry).where(ClubSaleInquiry.inquiry_id == inquiry["inquiry_id"]))
    offer_row = session.scalar(select(ClubSaleOffer).where(ClubSaleOffer.offer_id == offer["offer_id"]))

    assert accepted["status"] == ClubSaleOfferStatus.ACCEPTED
    assert cancelled["status"] == ClubSaleListingStatus.CANCELLED
    assert listing_row is not None
    assert inquiry_row is not None
    assert offer_row is not None
    assert listing_row.status == ClubSaleListingStatus.CANCELLED
    assert inquiry_row.status == ClubSaleInquiryStatus.CLOSED
    assert offer_row.status == ClubSaleOfferStatus.WITHDRAWN
    assert service.list_public_listings()["total"] == 0
    assert service.list_inquiries(actor=seller, club_id=club.id)["total"] == 1
    assert service.list_offers(actor=seller, club_id=club.id)["total"] == 1

    with pytest.raises(ClubSaleMarketError, match="Public club sale listing was not found"):
        service.get_public_listing(club_id=club.id)

    with pytest.raises(ClubSaleMarketError) as exc_info:
        service.execute_transfer(
            actor=seller,
            club_id=club.id,
            offer_id=offer["offer_id"],
            executed_sale_price=Decimal("82.0000"),
        )
    assert exc_info.value.reason == "club_sale_transfer_path_invalid"


def test_settled_transfer_amounts_are_immutable(session) -> None:
    prepared = _prepare_market_sale(session)
    seller = prepared["seller"]
    buyer = prepared["buyer"]
    club = prepared["club"]
    service = prepared["service"]

    service.create_listing(
        actor=seller,
        club_id=club.id,
        asking_price=Decimal("100.0000"),
        visibility="public",
        note=None,
    )
    offer = service.create_offer(
        actor=buyer,
        club_id=club.id,
        offer_price=Decimal("95.0000"),
        inquiry_id=None,
        message="Offer for immutable test.",
        expires_at=None,
    )
    service.accept_offer(
        actor=seller,
        club_id=club.id,
        offer_id=offer["offer_id"],
        message="Accepted for immutable test.",
    )
    transfer = service.execute_transfer(
        actor=seller,
        club_id=club.id,
        offer_id=offer["offer_id"],
        executed_sale_price=Decimal("80.0000"),
    )

    transfer_row = session.scalar(select(ClubSaleTransfer).where(ClubSaleTransfer.transfer_id == transfer["transfer_id"]))
    assert transfer_row is not None

    transfer_row.platform_fee_amount = Decimal("0.0000")
    with pytest.raises(ValueError, match="immutable"):
        session.flush()
