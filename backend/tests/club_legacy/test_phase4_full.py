"""Exit gate for Club Legacy phase 4."""

from __future__ import annotations

from decimal import Decimal
import threading

import pytest
from sqlalchemy import delete, func, select

from app.admin_engine.service import AdminEngineService
from app.club_legacy.delegation import LegacyError
from app.club_legacy.full.phase4 import (
    RELATIONSHIP_LOYALTY,
    RELATIONSHIP_MORALE,
    market_limits,
    transfer_asset,
)
from app.club_legacy.models import (
    ClubLegacyAsset,
    ClubLegacyAuditEvent,
    ClubLegacyCatalogueItem,
    ClubLegacyMarketSettings,
    ClubLegacyProvenance,
    ClubLegacyRelationshipEvent,
)
from app.club_legacy.operations import (
    buy_listing,
    list_asset,
    offer_gift,
    place_bid,
    purchase_asset,
    resolve_gift,
    seed_catalogue,
)
from app.models.admin_rules import AdminFeatureFlag
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.user import User
from app.models.wallet import LedgerAccount, LedgerEntry, LedgerTransaction
from app.owner_console import ledger
from app.owner_console.models import OwnerSquadPlayer


def _enable(app, enabled: bool = True) -> None:
    with app.state.session_factory() as session:
        AdminEngineService(session).seed_defaults()
        flag = session.scalar(select(AdminFeatureFlag).where(AdminFeatureFlag.feature_key == "club_legacy"))
        flag.enabled = enabled
        session.commit()


def _claim(client, headers) -> str:
    response = client.post("/api/owner/clubs/claim", headers=headers, json={"city_name": "Lagos", "country_code": "NG"})
    assert response.status_code == 200, response.text
    return response.json()["club_id"]


def _admin(session) -> User:
    return session.scalar(select(User).where(User.email == "admin@test.gtex.local"))


def _club(session, owner_id: str, name: str, slug: str) -> ClubProfile:
    club = ClubProfile(
        owner_user_id=owner_id,
        club_name=name,
        short_name=name[:3].upper(),
        club_type=ClubType.COMMUNITY,
        lifecycle_status=ClubLifecycleStatus.ACTIVE,
        slug=slug,
        primary_color="#111111",
        secondary_color="#eeeeee",
        accent_color="#EA580C",
        country_code="NG",
        visibility="public",
    )
    session.add(club)
    session.flush()
    return club


def _user(session, email: str, username: str) -> User:
    user = User(email=email, username=username, password_hash="hash", display_name=username)
    session.add(user)
    session.flush()
    return user


def _cheap(session, sku: str, price: str = "100", supply: int = 20) -> None:
    seed_catalogue(session)
    item = session.scalar(select(ClubLegacyCatalogueItem).where(ClubLegacyCatalogueItem.sku == sku))
    item.price = Decimal(price)
    item.supply_cap = supply
    session.flush()


def _debit_account_id(session, idempotency_key: str) -> str:
    transaction = session.scalar(select(LedgerTransaction).where(LedgerTransaction.idempotency_key == idempotency_key))
    assert transaction is not None
    debits = session.scalars(
        select(LedgerEntry).where(LedgerEntry.transaction_id == transaction.id, LedgerEntry.amount < 0)
    ).all()
    assert len(debits) == 1
    return debits[0].account_id


def test_purchase_debits_the_club_once_and_reuses_the_idempotency_key(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        _cheap(session, "gtex-jet-harbour")
        treasury = ledger.wallet_account(session, ledger.club_account(club_id), ledger.GTEX)
        first = purchase_asset(
            session,
            club_id=club_id,
            user_id=admin.id,
            sku="gtex-jet-harbour",
            owner_class="club",
            idempotency_key="p4-jet-once",
        )
        second = purchase_asset(
            session,
            club_id=club_id,
            user_id=admin.id,
            sku="gtex-jet-harbour",
            owner_class="club",
            idempotency_key="p4-jet-once",
        )
        assert first.id == second.id
        assert first.status == "owned"
        assert (
            session.scalar(
                select(func.count())
                .select_from(LedgerTransaction)
                .where(LedgerTransaction.idempotency_key == "asset:p4-jet-once")
            )
            == 1
        )
        assert _debit_account_id(session, "asset:p4-jet-once") == treasury.id
        assert (
            session.scalar(
                select(func.count())
                .select_from(ClubLegacyAsset)
                .where(ClubLegacyAsset.idempotency_key == "p4-jet-once")
            )
            == 1
        )
        session.commit()
    closed = client.post(
        f"/api/owner/legacy/{club_id}/market/purchases",
        headers=bootstrap_admin_headers,
        json={"sku": "gtex-jet-harbour", "owner_class": "club", "idempotency_key": "p4-jet-once"},
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["id"] == first.id
    with app.state.session_factory() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(LedgerTransaction)
                .where(LedgerTransaction.idempotency_key == "asset:p4-jet-once")
            )
            == 1
        )


def test_transfer_is_atomic_and_writes_provenance(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        _cheap(session, "gtex-coach-lagoon", price="100", supply=20)
        asset = purchase_asset(
            session,
            club_id=club_id,
            user_id=admin.id,
            sku="gtex-coach-lagoon",
            owner_class="club",
            idempotency_key="p4-transfer-asset",
        )
        holder = asset
        for owner_class, owner_ref, key in (
            ("owner", admin.id, "p4-to-owner"),
            ("player", "player-9", "p4-to-player"),
            ("manager", "manager-9", "p4-to-manager"),
            ("club", club_id, "p4-to-club"),
        ):
            row = transfer_asset(
                session,
                asset_id=holder.id,
                user_id=admin.id,
                to_owner_class=owner_class,
                to_owner_ref=owner_ref,
                price="0",
                idempotency_key=key,
            )
            session.refresh(holder)
            assert holder.owner_class == owner_class
            assert holder.owner_ref == owner_ref
            assert row.from_owner_class
            assert row.to_owner_class == owner_class
            assert row.to_owner_ref == owner_ref
            assert row.price == Decimal("0.00")
            assert row.actor_user_id == admin.id
            assert row.created_at is not None
        again = transfer_asset(
            session,
            asset_id=holder.id,
            user_id=admin.id,
            to_owner_class="player",
            to_owner_ref="someone-else",
            price="0",
            idempotency_key="p4-to-club",
        )
        session.refresh(holder)
        assert holder.owner_class == "club"
        assert again.to_owner_ref == club_id
        rival = _user(session, "p4-rival@gte.local", "p4_rival")
        rival_club = _club(session, rival.id, "Phase4 Rival", "phase4-rival")
        ledger.record(
            session,
            event_type="launch_grant",
            source=ledger.PLATFORM_GRANTS,
            destination=ledger.club_account(rival_club.id),
            currency=ledger.GTEX,
            gross=5000,
            user_id=rival.id,
            club_id=rival_club.id,
            memo="Rival float",
        )
        session.add(
            ClubLegacyMarketSettings(
                settings_key="club_legacy_market", transfer_fee_rate=Decimal("0.1000"), jet_cap=5, coach_cap=10
            )
        )
        session.flush()
        priced = transfer_asset(
            session,
            asset_id=holder.id,
            user_id=admin.id,
            to_owner_class="club",
            to_owner_ref=rival_club.id,
            price="1000",
            idempotency_key="p4-priced",
            payer_club_id=rival_club.id,
        )
        assert priced.price == Decimal("1000.00")
        assert priced.from_owner_ref == club_id
        assert priced.to_owner_ref == rival_club.id
        fee_tx = session.scalar(
            select(LedgerTransaction).where(LedgerTransaction.idempotency_key == "transfer-fee:p4-priced")
        )
        assert fee_tx is not None
        assert "fee" in (fee_tx.description or "").lower()
        fee_entries = session.scalars(select(LedgerEntry).where(LedgerEntry.transaction_id == fee_tx.id)).all()
        assert any(abs(entry.amount) == Decimal("100.0000") for entry in fee_entries)
        before_class = holder.owner_class
        with pytest.raises(Exception):
            transfer_asset(
                session,
                asset_id=holder.id,
                user_id=rival.id,
                to_owner_class="club",
                to_owner_ref=club_id,
                price="99999999",
                idempotency_key="p4-priced-fail",
                payer_club_id=club_id,
            )
        session.refresh(holder)
        assert holder.owner_class == before_class
        assert (
            session.scalar(select(ClubLegacyProvenance).where(ClubLegacyProvenance.idempotency_key == "p4-priced-fail"))
            is None
        )
        session.execute(delete(ClubLegacyMarketSettings))
        session.commit()


def test_gift_waits_for_acceptance_and_does_not_max_loyalty(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        _cheap(session, "gtex-watch-icon", price="100", supply=5)
        morale = [
            (player.id, player.morale)
            for player in session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id)).all()
        ]
        owned = purchase_asset(
            session,
            club_id=club_id,
            user_id=admin.id,
            sku="gtex-watch-icon",
            owner_class="owner",
            idempotency_key="p4-gift-watch",
        )
        owner_class = owned.owner_class
        gift = offer_gift(session, asset_id=owned.id, user_id=admin.id, recipient_ref="player-1")
        session.refresh(owned)
        assert owned.status == "offered"
        assert owned.owner_class == owner_class
        assert owned.owner_ref == admin.id
        resolve_gift(session, gift_id=gift.id, accept=False)
        session.refresh(owned)
        assert owned.owner_class == "owner"
        gift = offer_gift(session, asset_id=owned.id, user_id=admin.id, recipient_ref="player-1")
        assert (
            session.scalar(select(func.count()).select_from(ClubLegacyRelationshipEvent)) == 0
            or session.scalar(
                select(func.count())
                .select_from(ClubLegacyRelationshipEvent)
                .where(ClubLegacyRelationshipEvent.gift_id == gift.id)
            )
            == 0
        )
        resolve_gift(session, gift_id=gift.id, accept=True, actor_user_id=admin.id)
        session.refresh(owned)
        assert owned.owner_class == "player"
        assert owned.owner_ref == "player-1"
        event = session.scalar(
            select(ClubLegacyRelationshipEvent).where(ClubLegacyRelationshipEvent.gift_id == gift.id)
        )
        assert event is not None
        assert event.kind == "accepted"
        assert event.loyalty == RELATIONSHIP_LOYALTY
        assert event.morale == RELATIONSHIP_MORALE
        assert event.loyalty < 100
        assert event.morale < 100
        assert event.loyalty != 100
        assert event.morale != 100
        after = [
            (player.id, player.morale)
            for player in session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id)).all()
        ]
        assert after == morale
        session.commit()


def test_gift_resolution_authorization_checks(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        other_user = _user(session, "p4-other@gte.local", "p4_other")
        recipient_user = _user(session, "p4-recipient@gte.local", "p4_recipient")

        _cheap(session, "gtex-watch-icon", price="100", supply=5)
        owned_a = purchase_asset(
            session,
            club_id=club_id,
            user_id=admin.id,
            sku="gtex-watch-icon",
            owner_class="owner",
            idempotency_key="p4-gift-auth-a",
        )
        owned_b = purchase_asset(
            session,
            club_id=club_id,
            user_id=admin.id,
            sku="gtex-watch-icon",
            owner_class="owner",
            idempotency_key="p4-gift-auth-b",
        )

        gift_a = offer_gift(session, asset_id=owned_a.id, user_id=admin.id, recipient_ref=recipient_user.id)
        gift_b = offer_gift(session, asset_id=owned_b.id, user_id=admin.id, recipient_ref=recipient_user.id)

        # Unauthorized user receives 403 when resolving recipient_user's gift
        with pytest.raises(LegacyError) as exc_info:
            resolve_gift(session, gift_id=gift_a.id, accept=True, actor_user_id=other_user.id)
        assert exc_info.value.status == 403
        assert exc_info.value.code == "not_gift_recipient"

        # Intended recipient can accept directly (user id)
        resolved_a = resolve_gift(session, gift_id=gift_a.id, accept=True, actor_user_id=recipient_user.id)
        assert resolved_a.status == "accepted"

        # Gift sent to a player in recipient_user's club can be accepted by recipient_user
        recipient_club = _club(session, recipient_user.id, "Recipient FC", "recipient-fc")
        player = OwnerSquadPlayer(id="squad-player-1", club_id=recipient_club.id, name="Star Player", position="ST")
        session.add(player)
        session.flush()

        owned_c = purchase_asset(
            session,
            club_id=club_id,
            user_id=admin.id,
            sku="gtex-watch-icon",
            owner_class="owner",
            idempotency_key="p4-gift-auth-c",
        )
        gift_c = offer_gift(session, asset_id=owned_c.id, user_id=admin.id, recipient_ref=player.id)

        # Other user cannot resolve gift sent to squad player
        with pytest.raises(LegacyError) as exc_info:
            resolve_gift(session, gift_id=gift_c.id, accept=True, actor_user_id=other_user.id)
        assert exc_info.value.status == 403

        # Owner of the player's club can accept
        resolved_c = resolve_gift(session, gift_id=gift_c.id, accept=True, actor_user_id=recipient_user.id)
        assert resolved_c.status == "accepted"

        # Admin user can decline on behalf of recipient
        resolved_b = resolve_gift(session, gift_id=gift_b.id, accept=False, actor_user_id=admin.id)
        assert resolved_b.status == "declined"

        session.commit()


def test_supply_cap_holds_for_two_concurrent_purchases_and_club_caps_stay(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        admin_id = admin.id
        _cheap(session, "gtex-watch-icon", price="100", supply=20)
        item = session.scalar(select(ClubLegacyCatalogueItem).where(ClubLegacyCatalogueItem.sku == "gtex-watch-icon"))
        item.supply_cap = int(item.minted_count) + 1
        session.commit()

    barrier = threading.Barrier(2)
    results: list[str] = []
    errors: list[BaseException] = []

    def attempt(key: str) -> None:
        local = app.state.session_factory()
        try:
            barrier.wait(timeout=5)
            asset = purchase_asset(
                local,
                club_id=club_id,
                user_id=admin_id,
                sku="gtex-watch-icon",
                owner_class="owner",
                idempotency_key=key,
            )
            local.commit()
            results.append(asset.id)
        except Exception as exc:  # noqa: BLE001 - the losing purchase must fail closed
            local.rollback()
            errors.append(exc)
        finally:
            local.close()

    threads = [threading.Thread(target=attempt, args=(key,)) for key in ("p4-watch-a", "p4-watch-b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    with app.state.session_factory() as session:
        item = session.scalar(select(ClubLegacyCatalogueItem).where(ClubLegacyCatalogueItem.sku == "gtex-watch-icon"))
        minted_assets = session.scalar(
            select(func.count()).select_from(ClubLegacyAsset).where(ClubLegacyAsset.catalogue_id == item.id)
        )
        assert item.minted_count <= item.supply_cap
        assert minted_assets <= item.supply_cap
        assert len(results) == 1
        assert errors

    with app.state.session_factory() as session:
        admin = _admin(session)
        _cheap(session, "gtex-jet-harbour", price="100", supply=20)
        session.add(
            ClubLegacyMarketSettings(
                settings_key="club_legacy_market", transfer_fee_rate=Decimal("0.0500"), jet_cap=1, coach_cap=1
            )
        )
        session.flush()
        owned = session.scalar(
            select(func.count())
            .select_from(ClubLegacyAsset)
            .join(ClubLegacyCatalogueItem, ClubLegacyCatalogueItem.id == ClubLegacyAsset.catalogue_id)
            .where(
                ClubLegacyAsset.club_id == club_id,
                ClubLegacyAsset.owner_class == "club",
                ClubLegacyCatalogueItem.category == "jet",
                ClubLegacyAsset.status == "owned",
            )
        )
        if int(owned or 0) == 0:
            purchase_asset(
                session,
                club_id=club_id,
                user_id=admin.id,
                sku="gtex-jet-harbour",
                owner_class="club",
                idempotency_key="p4-jet-cap",
            )
        with pytest.raises(LegacyError) as capped:
            purchase_asset(
                session,
                club_id=club_id,
                user_id=admin.id,
                sku="gtex-jet-harbour",
                owner_class="club",
                idempotency_key="p4-jet-cap-over",
            )
        assert capped.value.code == "inventory_cap"
        session.execute(delete(ClubLegacyMarketSettings))
        session.commit()
        rate, jet_cap, coach_cap = market_limits(session)
        assert rate == Decimal("0.0500")
        assert jet_cap == 5
        assert coach_cap == 10


def test_listings_reject_wash_trades_and_a_failed_resale_stays_open(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        _cheap(session, "gtex-jet-harbour", price="100", supply=20)
        _cheap(session, "gtex-coach-lagoon", price="100", supply=20)
        jet = purchase_asset(
            session,
            club_id=club_id,
            user_id=admin.id,
            sku="gtex-jet-harbour",
            owner_class="club",
            idempotency_key="p4-auction-jet",
        )
        auction = list_asset(session, asset_id=jet.id, user_id=admin.id, price="1000", kind="auction")
        with pytest.raises(LegacyError) as seller_bid:
            place_bid(session, listing_id=auction.id, bidder_user_id=admin.id, amount="1500")
        assert seller_bid.value.code == "wash_trade"
        session.refresh(auction)
        assert auction.status == "auction"
        assert (
            session.scalar(
                select(func.count())
                .select_from(ClubLegacyAuditEvent)
                .where(ClubLegacyAuditEvent.action == "seller_bid_refused")
            )
            >= 1
        )
        sister = _club(session, admin.id, "Sister Phase4", "sister-phase4")
        coach = purchase_asset(
            session,
            club_id=club_id,
            user_id=admin.id,
            sku="gtex-coach-lagoon",
            owner_class="club",
            idempotency_key="p4-wash-coach",
        )
        listing = list_asset(session, asset_id=coach.id, user_id=admin.id, price="1000")
        with pytest.raises(LegacyError) as wash:
            buy_listing(
                session,
                listing_id=listing.id,
                buyer_user_id=admin.id,
                buyer_club_id=sister.id,
                idempotency_key="p4-wash",
            )
        assert wash.value.code == "wash_trade"
        session.refresh(listing)
        assert listing.status == "open"
        assert (
            session.scalar(
                select(func.count())
                .select_from(ClubLegacyAuditEvent)
                .where(ClubLegacyAuditEvent.action == "related_club_refused")
            )
            >= 1
        )
        rival = _user(session, "p4-buyer@gte.local", "p4_buyer")
        rival_club = _club(session, rival.id, "Buyer FC", "phase4-buyer")
        ledger.record(
            session,
            event_type="launch_grant",
            source=ledger.PLATFORM_GRANTS,
            destination=ledger.club_account(rival_club.id),
            currency=ledger.GTEX,
            gross=500,
            user_id=rival.id,
            club_id=rival_club.id,
            memo="Small float",
        )
        with pytest.raises(Exception):
            buy_listing(
                session,
                listing_id=listing.id,
                buyer_user_id=rival.id,
                buyer_club_id=rival_club.id,
                idempotency_key="p4-too-poor",
            )
        session.refresh(listing)
        assert listing.status == "open"
        session.commit()
    denied = client.post(
        f"/api/owner/legacy/{club_id}/market/listings/{auction.id}/bids",
        headers=bootstrap_admin_headers,
        json={"amount": "1600"},
    )
    assert denied.status_code == 409
    assert denied.json()["code"] == "wash_trade"
    with app.state.session_factory() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(ClubLegacyAuditEvent)
                .where(ClubLegacyAuditEvent.action == "seller_bid_refused")
            )
            >= 1
        )


def test_fee_comes_from_the_admin_row_or_the_documented_default(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        rate, jet_cap, coach_cap = market_limits(session)
        assert (rate, jet_cap, coach_cap) == (Decimal("0.0500"), 5, 10)
        _cheap(session, "gtex-coach-lagoon", price="100", supply=20)
        asset = purchase_asset(
            session,
            club_id=club_id,
            user_id=admin.id,
            sku="gtex-coach-lagoon",
            owner_class="club",
            idempotency_key="p4-fee-coach",
        )
        listing = list_asset(session, asset_id=asset.id, user_id=admin.id, price="1000")
        assert listing.fee == Decimal("50.00")
        session.add(
            ClubLegacyMarketSettings(
                settings_key="club_legacy_market", transfer_fee_rate=Decimal("0.2500"), jet_cap=4, coach_cap=8
            )
        )
        session.flush()
        assert market_limits(session)[0] == Decimal("0.2500")
        rival = _user(session, "p4-fee-buyer@gte.local", "p4_fee_buyer")
        rival_club = _club(session, rival.id, "Fee Buyer", "phase4-fee-buyer")
        ledger.record(
            session,
            event_type="launch_grant",
            source=ledger.PLATFORM_GRANTS,
            destination=ledger.club_account(rival_club.id),
            currency=ledger.GTEX,
            gross=5000,
            user_id=rival.id,
            club_id=rival_club.id,
            memo="Fee float",
        )
        bought = buy_listing(
            session,
            listing_id=listing.id,
            buyer_user_id=rival.id,
            buyer_club_id=rival_club.id,
            idempotency_key="p4-fee-sale",
        )
        assert bought.fee == Decimal("250.00")
        fee_tx = session.scalar(
            select(LedgerTransaction).where(LedgerTransaction.idempotency_key == "sale-fee:p4-fee-sale")
        )
        assert fee_tx is not None
        account = session.get(LedgerAccount, _debit_account_id(session, "sale-fee:p4-fee-sale"))
        assert account is not None
        session.execute(delete(ClubLegacyMarketSettings))
        session.commit()
    _enable(app, enabled=False)
    hidden = client.post(
        f"/api/owner/legacy/{club_id}/market/purchases",
        headers=bootstrap_admin_headers,
        json={"sku": "gtex-jet-harbour", "owner_class": "club", "idempotency_key": "p4-hidden"},
    )
    assert hidden.status_code == 404
    _enable(app, enabled=True)
