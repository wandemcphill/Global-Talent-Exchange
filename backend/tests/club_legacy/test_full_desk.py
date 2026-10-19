"""Owner desk, marketplace safeguards, calendar, and stake totals."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.admin_engine.service import AdminEngineService
from app.club_legacy.delegation import LegacyError
from app.club_legacy.operations import (
    approach_manager,
    buy_listing,
    close_auction,
    desk_snapshot,
    hire_executive,
    invite_preseason,
    list_asset,
    load_catalogue,
    open_window,
    perform_desk_action,
    place_bid,
    purchase_asset,
    renew_sponsor,
    report_delivery,
    seed_catalogue,
    set_stake,
    settle_preseason,
    showroom,
)
from app.club_legacy.operations import approve_sponsor, offer_sponsor, respond_preseason
from app.models.admin_rules import AdminCalendarRule, AdminFeatureFlag
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.user import User
from app.owner_console import ledger


def _enable(app) -> None:
    with app.state.session_factory() as session:
        AdminEngineService(session).seed_defaults()
        flag = session.scalar(select(AdminFeatureFlag).where(AdminFeatureFlag.feature_key == "club_legacy"))
        flag.enabled = True
        session.commit()


def _claim(client, headers) -> str:
    response = client.post("/api/owner/clubs/claim", headers=headers, json={"city_name": "Lagos", "country_code": "NG"})
    assert response.status_code == 200, response.text
    return response.json()["club_id"]


def test_full_desk_rules(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        hired = hire_executive(
            session, club_id, admin.id, role="gm", name="Ada Okonkwo", personality="cautious", wage="4000"
        )
        assert hired.attributes_json["city_bonus"] == 10
        assert hired.attributes_json["facility_level"] >= 20
        set_stake(session, club_id=club_id, holder_user_id=admin.id, percentage="60")
        with pytest.raises(LegacyError) as stakes:
            set_stake(session, club_id=club_id, holder_user_id="someone-else", percentage="50")
        assert stakes.value.code == "stake_total"

        sister = ClubProfile(
            owner_user_id=admin.id,
            club_name="Sister FC",
            short_name="SIS",
            club_type=ClubType.COMMUNITY,
            lifecycle_status=ClubLifecycleStatus.ACTIVE,
            slug="sister-fc-desk",
            primary_color="#111111",
            secondary_color="#eeeeee",
            accent_color="#EA580C",
            country_code="NG",
            visibility="public",
        )
        session.add(sister)
        session.flush()
        window = open_window(session, name="Desk window", starts_on="2026-06-01", ends_on="2026-06-30")
        with pytest.raises(LegacyError) as related:
            invite_preseason(
                session,
                window_id=window.id,
                from_club_id=club_id,
                to_club_id=sister.id,
                match_on="2026-06-10",
                appearance_fee="400",
                user_id=admin.id,
            )
        assert related.value.code == "related_club_blocked"

        session.add(
            AdminCalendarRule(
                rule_key="test-block-june-15",
                title="Block",
                description="",
                world_cup_exclusive=True,
                active=True,
                priority=1,
                config_json={"blocked_ranges": [{"start": "2026-06-14", "end": "2026-06-16"}]},
            )
        )
        session.flush()
        rival = User(email="desk-rival@gte.local", username="desk_rival", password_hash="hash")
        session.add(rival)
        session.flush()
        rival_club = ClubProfile(
            owner_user_id=rival.id,
            club_name="Rival FC",
            short_name="RIV",
            club_type=ClubType.COMMUNITY,
            lifecycle_status=ClubLifecycleStatus.ACTIVE,
            slug="rival-fc-desk",
            primary_color="#222222",
            secondary_color="#dddddd",
            accent_color="#EA580C",
            country_code="GH",
            visibility="public",
        )
        session.add(rival_club)
        session.flush()
        with pytest.raises(LegacyError) as blocked:
            invite_preseason(
                session,
                window_id=window.id,
                from_club_id=club_id,
                to_club_id=rival_club.id,
                match_on="2026-06-15",
                appearance_fee="400",
                user_id=admin.id,
            )
        assert blocked.value.code == "calendar_blocked"

        seed_catalogue(session)
        jet = purchase_asset(
            session,
            club_id=club_id,
            user_id=admin.id,
            sku="gtex-jet-harbour",
            owner_class="club",
            idempotency_key="desk-jet",
        )
        listing = list_asset(session, asset_id=jet.id, user_id=admin.id, price="1000", kind="auction")
        with pytest.raises(LegacyError) as wash:
            place_bid(session, listing_id=listing.id, bidder_user_id=admin.id, amount="1500")
        assert wash.value.code == "wash_trade"
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
        bid = place_bid(session, listing_id=listing.id, bidder_user_id=rival.id, amount="1500")
        assert bid.status == "leading"
        closed = close_auction(session, listing_id=listing.id, buyer_club_id=rival_club.id)
        assert closed.status == "sold"

        huge = list_asset(
            session,
            asset_id=purchase_asset(
                session,
                club_id=club_id,
                user_id=admin.id,
                sku="gtex-coach-lagoon",
                owner_class="club",
                idempotency_key="desk-coach",
            ).id,
            user_id=admin.id,
            price="99999999",
        )
        with pytest.raises(Exception):
            buy_listing(
                session,
                listing_id=huge.id,
                buyer_user_id=rival.id,
                buyer_club_id=rival_club.id,
                idempotency_key="too-poor",
            )
        session.refresh(huge)
        assert huge.status == "open"

        contract = offer_sponsor(
            session, club_id=club_id, user_id=admin.id, sponsor_name="Harbour Trust", placement="front", fee="100"
        )
        approve_sponsor(session, contract_id=contract.id, user_id=admin.id)
        report_delivery(
            session,
            contract_id=contract.id,
            user_id=admin.id,
            impressions=12,
            note="Boards ran the agreed front placement.",
        )
        assert contract.status == "completed"
        renewed = renew_sponsor(session, contract_id=contract.id, user_id=admin.id)
        assert renewed.renewed_from_id == contract.id

        manager = hire_executive(
            session,
            club_id,
            admin.id,
            role="football_manager",
            name="Tunde Bakare",
            personality="demanding",
            wage="5000",
        )
        approached = approach_manager(session, executive_id=manager.id, from_club_id=rival_club.id, user_id=rival.id)
        assert approached.status == "in_talks"

        invite = invite_preseason(
            session,
            window_id=window.id,
            from_club_id=club_id,
            to_club_id=rival_club.id,
            match_on="2026-06-18",
            appearance_fee="300",
            user_id=admin.id,
        )
        respond_preseason(session, invite_id=invite.id, user_id=rival.id, decision="accept")
        settled = settle_preseason(session, invite_id=invite.id, tv_pool="100", gift_pool="50")
        assert settled.gift_platform_amount + settled.gift_club_amount == Decimal("50.00")
        assert settled.platform_amount + settled.host_amount + settled.participant_amount == Decimal("100.00")

        room = showroom(session, club_id)
        assert room["within_budget"] is True
        assert load_catalogue(session)["within_budget"] is True
        desk = desk_snapshot(session, club_id, admin.id)
        assert any(item["role"] == "gm" for item in desk["staff"])
        assert any(row["name"] == "Lagoon Coach" and row["status"] == "open" for row in desk["market"])
        with pytest.raises(LegacyError) as missing_asset:
            perform_desk_action(session, rival_club.id, rival.id, "list_auction", {"price": "1800"})
        assert missing_asset.value.code == "asset_required"
        with pytest.raises(LegacyError) as missing_listing:
            perform_desk_action(session, club_id, admin.id, "place_bid", {"amount": "2000"})
        assert missing_listing.value.code == "listing_required"
        auction = perform_desk_action(
            session,
            rival_club.id,
            rival.id,
            "list_auction",
            {"asset_id": jet.id, "price": "1800"},
        )
        assert auction["status"] == "auction"
        bid_action = perform_desk_action(
            session,
            club_id,
            admin.id,
            "place_bid",
            {"listing_id": auction["id"], "amount": "2000"},
        )
        assert bid_action["status"] == "leading"
        market = desk_snapshot(session, club_id, admin.id)["market"]
        assert any(row["id"] == auction["id"] and row["leading_bid"] == "2000.00" for row in market)
        acted = perform_desk_action(
            session,
            club_id,
            admin.id,
            "open_case",
            {"rule_code": "late_wages", "allegation": "Wages slipped", "evidence": "Ledger"},
        )
        assert acted["status"] == "open"

        # Give club GTEX funds to test purchase
        ledger.record(
            session,
            event_type="test_fund",
            source=ledger.PLATFORM_GRANTS,
            destination=ledger.club_account(club_id),
            currency=ledger.GTEX,
            gross=100000,
            user_id=admin.id,
            club_id=club_id,
            memo="Prestige fund",
        )

        # 1. Idempotent purchase debits GTEX once, returns same asset
        balance_before = ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)
        purchased_watch = perform_desk_action(
            session,
            club_id,
            admin.id,
            "purchase",
            {"sku": "gtex-watch-icon", "idempotency_key": "desk-watch-1"},
        )
        balance_after = ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)
        assert Decimal(balance_before) - Decimal(balance_after) == Decimal("20000.00")

        repeat_watch = perform_desk_action(
            session,
            club_id,
            admin.id,
            "purchase",
            {"sku": "gtex-watch-icon", "idempotency_key": "desk-watch-1"},
        )
        assert repeat_watch["id"] == purchased_watch["id"]
        assert ledger.balance(session, ledger.club_account(club_id), ledger.GTEX) == balance_after

        # 2. Sold out cap test (Icon watch supply cap is 1)
        with pytest.raises(LegacyError) as sold_out_exc:
            perform_desk_action(
                session,
                club_id,
                admin.id,
                "purchase",
                {"sku": "gtex-watch-icon", "idempotency_key": "desk-watch-2"},
            )
        assert sold_out_exc.value.code == "sold_out"

        # 3. Gift of unowned asset rejected
        with pytest.raises(LegacyError) as unowned_gift:
            perform_desk_action(
                session,
                club_id,
                rival.id,
                "gift",
                {"asset_id": purchased_watch["id"], "recipient_ref": "player-1"},
            )
        assert unowned_gift.value.code in {"not_asset_owner", "not_club_owner", "club_owner_required"}

        # 4. Gifting owned asset & resolving gift
        gift_res = perform_desk_action(
            session,
            club_id,
            admin.id,
            "gift",
            {"asset_id": purchased_watch["id"], "recipient_ref": rival.id},
        )
        assert gift_res["status"] == "offered"

        accept_res = perform_desk_action(
            session,
            rival_club.id,
            rival.id,
            "accept_gift",
            {"gift_id": gift_res["id"]},
        )
        assert accept_res["status"] == "accepted"

        with pytest.raises(LegacyError) as second_accept:
            perform_desk_action(
                session,
                rival_club.id,
                rival.id,
                "accept_gift",
                {"gift_id": gift_res["id"]},
            )
        assert second_accept.value.code == "gift_not_open"

        session.commit()

    page = client.get(f"/api/owner/legacy/{club_id}/desk", headers=bootstrap_admin_headers)
    assert page.status_code == 200, page.text
    assert page.json()["finance"]["club_valuation"] != page.json()["finance"]["equity"]
