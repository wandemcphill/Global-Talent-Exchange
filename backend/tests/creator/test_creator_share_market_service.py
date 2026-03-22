from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.creator_profile import CreatorProfile
from app.models.creator_provisioning import CreatorSquad
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.services.creator_share_market_service import CreatorClubShareMarketError, CreatorClubShareMarketService
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


def test_creator_share_market_enforces_anti_takeover_cap_and_enriches_ledger(session) -> None:
    owner = _create_user(session, user_id="owner-share", email="owner-share@example.com", username="owner-share")
    fan = _create_user(session, user_id="fan-share", email="fan-share@example.com", username="fan-share")
    session.add(
        ClubProfile(
            id="club-share",
            owner_user_id=owner.id,
            club_name="Share Club FC",
            short_name="SCF",
            slug="share-club-fc",
            crest_asset_ref=None,
            primary_color="#112233",
            secondary_color="#ddeeff",
            accent_color="#44aa66",
            home_venue_name="Share Arena",
            country_code="NG",
            region_name="Lagos",
            city_name="Lagos",
            description="Creator share test club",
            visibility="public",
            founded_at=None,
        )
    )
    session.add(
        CreatorProfile(
            id="creator-profile",
            user_id=owner.id,
            handle="owner-share",
            display_name="Owner Share",
            status="active",
        )
    )
    session.add(
        CreatorSquad(
            id="creator-squad",
            club_id="club-share",
            creator_profile_id="creator-profile",
            metadata_json={},
        )
    )
    wallet = WalletService()
    _seed_wallet(session, wallet, fan, amount=Decimal("500.0000"))

    service = CreatorClubShareMarketService(session=session, wallet_service=wallet)
    market = service.issue_market(
        actor=owner,
        club_id="club-share",
        share_price_coin=Decimal("5.0000"),
        max_shares_issued=100,
        max_shares_per_fan=100,
        metadata_json={"governance_policy": {"max_holder_bps": 1000}},
    )
    purchase = service.purchase_shares(actor=fan, club_id="club-share", share_count=20)
    serialized_market = service.serialize_market(market, viewer=fan)

    assert purchase.metadata_json["post_purchase_share_count"] == 20
    assert serialized_market["governance_policy"]["max_holder_bps"] == 1000
    assert serialized_market["ownership_ledger"]["recent_entries"][0]["entry_type"] == "share_purchase"
    assert serialized_market["ownership_ledger"]["recent_entries"][0]["entry_reference_id"] == purchase.id
    assert serialized_market["viewer_holding"]["share_count"] == 20

    with pytest.raises(CreatorClubShareMarketError) as exc_info:
        service.purchase_shares(actor=fan, club_id="club-share", share_count=1)

    assert exc_info.value.reason == "shareholder_anti_takeover_cap_exceeded"
