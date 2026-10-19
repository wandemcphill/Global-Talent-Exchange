"""Exit gates for Club Legacy phases 2 through 9."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.admin_engine.service import AdminEngineService
from app.club_legacy.delegation import PRESEASON_RESPONSE, set_task
from app.club_legacy.operations import (
    showroom,
    appeal_case,
    approve_sponsor,
    assert_staff_can_spend,
    buy_listing,
    club_page,
    club_valuation,
    decide_manager_offer,
    economic_interest,
    hire_executive,
    invite_preseason,
    list_asset,
    make_promise,
    metrics,
    offer_gift,
    offer_score,
    offer_sponsor,
    open_case,
    open_window,
    owner_net_worth,
    publish_kit,
    purchase_asset,
    recruitment_report,
    resolve_gift,
    resolve_promise,
    respond_preseason,
    rule_case,
    seed_catalogue,
    set_stake,
    settle_preseason,
    simulate_season,
)
from app.club_legacy.ratings import development_score
from app.club_legacy.delegation import LegacyError
from app.models.admin_rules import AdminFeatureFlag
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.user import User
from app.models.wallet import LedgerTransaction
from app.owner_console.models import OwnerClubState


def _enable(app) -> None:
    with app.state.session_factory() as session:
        AdminEngineService(session).seed_defaults()
        flag = session.scalar(select(AdminFeatureFlag).where(AdminFeatureFlag.feature_key == "club_legacy"))
        flag.enabled = True
        session.commit()


def _admin(session) -> User:
    return session.scalar(select(User).where(User.email == "admin@test.gtex.local"))


def _claim(client, headers) -> str:
    response = client.post(
        "/api/owner/clubs/claim",
        headers=headers,
        json={"city_name": "Lagos", "country_code": "NG"},
    )
    assert response.status_code == 200, response.text
    return response.json()["club_id"]


def test_phase2_executives_report_and_limits(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        page = club_page(session, club_id)
        assert page["staff"] == []
        assert page["city"] == "Lagos"
        hire_executive(session, club_id, admin.id, role="gm", name="Ada Okonkwo", personality="cautious", wage="4000")
        hire_executive(
            session, club_id, admin.id, role="hoyd", name="Ifeanyi Bello", personality="youth-focused", wage="3000"
        )
        report = recruitment_report(session, club_id, admin.id)
        assert "Not a guaranteed star" in report.summary
        assert "-" in report.summary
        assert report.confidence < 100
        set_task(
            session, club_id, "operating_spend", mode="automatic", max_amount=Decimal("100"), actor_user_id=admin.id
        )
        set_task(
            session, club_id, PRESEASON_RESPONSE, mode="automatic", max_amount=Decimal("1000"), actor_user_id=admin.id
        )
        with pytest.raises(LegacyError) as spent:
            assert_staff_can_spend(session, club_id, "operating_spend", Decimal("500"))
        assert spent.value.code == "over_threshold"
        with pytest.raises(LegacyError) as cheap:
            assert_staff_can_spend(session, club_id, PRESEASON_RESPONSE, Decimal("100"))
        assert cheap.value.code == "below_minimum_fee"
        session.commit()
    opened = client.get("/api/owner/control-center", headers=bootstrap_admin_headers)
    assert opened.status_code == 200


def test_phase3_net_worth_uses_equity_not_the_whole_club(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        set_stake(session, club_id=club_id, holder_user_id=admin.id, percentage="60")
        valuation = club_valuation(session, club_id)
        interest = economic_interest(session, club_id=club_id, holder_user_id=admin.id)
        assert interest == (valuation * Decimal("0.60")).quantize(Decimal("0.01"))
        assert interest != valuation
        worth = owner_net_worth(session, admin.id)
        assert Decimal(worth["equity"]) == interest
        page = club_page(session, club_id)
        assert page["showroom_fallback"] == "static-card"
        assert page["continent_code"] == "AF"
        assert "personal_assets" not in page
        session.commit()


def test_phase4_purchase_gift_and_resale_cannot_double(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
        before = development_score(state.facilities_json)
        first = purchase_asset(
            session,
            club_id=club_id,
            user_id=admin.id,
            sku="gtex-jet-harbour",
            owner_class="club",
            idempotency_key="jet-1",
        )
        second = purchase_asset(
            session,
            club_id=club_id,
            user_id=admin.id,
            sku="gtex-jet-harbour",
            owner_class="club",
            idempotency_key="jet-1",
        )
        assert first.id == second.id
        assert (
            session.scalar(
                select(func.count())
                .select_from(LedgerTransaction)
                .where(LedgerTransaction.idempotency_key == "asset:jet-1")
            )
            == 1
        )
        session.refresh(state)
        assert development_score(state.facilities_json) == before
        seed_catalogue(session)
        from app.club_legacy.models import ClubLegacyCatalogueItem

        watch = session.scalar(select(ClubLegacyCatalogueItem).where(ClubLegacyCatalogueItem.sku == "gtex-watch-icon"))
        watch.minted_count = watch.supply_cap
        session.flush()
        with pytest.raises(LegacyError) as sold:
            purchase_asset(
                session,
                club_id=club_id,
                user_id=admin.id,
                sku="gtex-watch-icon",
                owner_class="owner",
                idempotency_key="watch-2",
            )
        assert sold.value.code == "sold_out"
        watch.minted_count = 0
        session.flush()
        owned = purchase_asset(
            session,
            club_id=club_id,
            user_id=admin.id,
            sku="gtex-watch-icon",
            owner_class="owner",
            idempotency_key="watch-1",
        )
        gift = offer_gift(session, asset_id=owned.id, user_id=admin.id, recipient_ref="player-1")
        assert owned.status == "offered"
        resolve_gift(session, gift_id=gift.id, accept=False, actor_user_id=admin.id)
        session.refresh(owned)
        assert owned.owner_class == "owner"
        gift = offer_gift(session, asset_id=owned.id, user_id=admin.id, recipient_ref="player-1")
        resolve_gift(session, gift_id=gift.id, accept=True, actor_user_id=admin.id)
        session.refresh(owned)
        assert owned.owner_class == "player"
        assert owned.owner_ref == "player-1"
        jet = session.scalar(select(type(first)).where(type(first).id == first.id))
        listing = list_asset(session, asset_id=jet.id, user_id=admin.id, price="1000")
        bought = buy_listing(
            session, listing_id=listing.id, buyer_user_id=admin.id, buyer_club_id=club_id, idempotency_key="sale-1"
        )
        again = buy_listing(
            session, listing_id=listing.id, buyer_user_id=admin.id, buyer_club_id=club_id, idempotency_key="sale-1"
        )
        assert bought.id == again.id
        with pytest.raises(LegacyError):
            buy_listing(
                session, listing_id=listing.id, buyer_user_id=admin.id, buyer_club_id=club_id, idempotency_key="sale-2"
            )
        session.commit()


def test_phase5_preseason_allocates_100_percent_once(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        rival = User(email="rival-owner@gte.local", username="rival_owner", password_hash="hash", display_name="Rival")
        session.add(rival)
        session.flush()
        other = ClubProfile(
            owner_user_id=rival.id,
            club_name="Opposite FC",
            short_name="OPP",
            club_type=ClubType.COMMUNITY,
            lifecycle_status=ClubLifecycleStatus.ACTIVE,
            slug="opposite-fc-phase5",
            primary_color="#111111",
            secondary_color="#eeeeee",
            accent_color="#EA580C",
            country_code="NG",
            continent_code="AF",
            city_name="Abuja",
            visibility="public",
        )
        session.add(other)
        session.flush()
        window = open_window(session, name="June window", starts_on="2026-06-01", ends_on="2026-06-30")
        with pytest.raises(LegacyError) as outside:
            invite_preseason(
                session,
                window_id=window.id,
                from_club_id=club_id,
                to_club_id=other.id,
                match_on="2026-07-01",
                appearance_fee="500",
                user_id=admin.id,
            )
        assert outside.value.code == "outside_window"
        invite = invite_preseason(
            session,
            window_id=window.id,
            from_club_id=club_id,
            to_club_id=other.id,
            match_on="2026-06-12",
            appearance_fee="500",
            user_id=admin.id,
        )
        respond_preseason(session, invite_id=invite.id, user_id=rival.id, decision="accept")
        first = settle_preseason(session, invite_id=invite.id, tv_pool="1000")
        second = settle_preseason(session, invite_id=invite.id, tv_pool="1000")
        assert first.id == second.id
        assert first.platform_amount + first.host_amount + first.participant_amount == Decimal("1000.00")
        invite_preseason(
            session,
            window_id=window.id,
            from_club_id=club_id,
            to_club_id=other.id,
            match_on="2026-06-20",
            appearance_fee="500",
            user_id=admin.id,
        )
        # date conflict is for accepted matches; 12 June is accepted, 20 June is free
        later = session.scalar(select(type(invite)).where(type(invite).match_on == "2026-06-20"))
        respond_preseason(session, invite_id=later.id, user_id=rival.id, decision="accept")
        repeat = settle_preseason(session, invite_id=later.id, tv_pool="1000")
        assert repeat.reputation_delta < first.reputation_delta
        session.commit()


def test_phase6_published_kit_matches_the_contract(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        contract = offer_sponsor(
            session, club_id=club_id, user_id=admin.id, sponsor_name="Harbour Trust", placement="front", fee="2500"
        )
        with pytest.raises(LegacyError):
            publish_kit(
                session,
                club_id=club_id,
                user_id=admin.id,
                contract_id=contract.id,
                template_name="Home",
                zones={"front": "sleeve"},
            )
        approve_sponsor(session, contract_id=contract.id, user_id=admin.id)
        with pytest.raises(LegacyError) as mismatch:
            publish_kit(
                session,
                club_id=club_id,
                user_id=admin.id,
                contract_id=contract.id,
                template_name="Home",
                zones={"front": "sleeve"},
            )
        assert mismatch.value.code == "placement_mismatch"
        kit = publish_kit(
            session,
            club_id=club_id,
            user_id=admin.id,
            contract_id=contract.id,
            template_name="Home",
            zones={"front": "front"},
        )
        assert kit.status == "published"
        assert kit.zones_json["front"] == contract.placement
        session.commit()


def test_phase7_money_does_not_decide_every_offer(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    rich_decline = [seed for seed in range(40) if offer_score(100000, 0, 20, seed)[2] < 70]
    modest_accept = [seed for seed in range(40) if offer_score(1000, 80, 1, seed)[2] >= 70]
    assert rich_decline
    assert modest_accept
    with app.state.session_factory() as session:
        admin = _admin(session)
        declined = decide_manager_offer(
            session,
            club_id=club_id,
            user_id=admin.id,
            candidate_name="Rich Miss",
            wage="100000",
            prestige=0,
            ambition=20,
            seed=rich_decline[0],
        )
        accepted = decide_manager_offer(
            session,
            club_id=club_id,
            user_id=admin.id,
            candidate_name="Project Hit",
            wage="1000",
            prestige=80,
            ambition=1,
            seed=modest_accept[0],
        )
        assert declined.outcome == "declined"
        assert accepted.outcome == "accepted"
        assert accepted.wage < declined.wage
        promise = make_promise(session, club_id=club_id, user_id=admin.id, subject="New training ground")
        resolve_promise(session, promise_id=promise.id, kept=False)
        assert promise.trust < 50
        session.commit()


def test_phase8_cases_are_appealable_and_stakes_are_proportional(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        with pytest.raises(LegacyError) as luxury:
            open_case(
                session,
                club_id=club_id,
                rule_code="luxury_possession",
                allegation="Bought a jet",
                evidence="Catalogue receipt",
            )
        assert luxury.value.code == "not_misconduct"
        case = open_case(
            session,
            club_id=club_id,
            rule_code="related_party_transfer",
            allegation="Sold an asset to a sister club",
            evidence="Listing 44",
        )
        rule_case(
            session, case_id=case.id, sanction="warning", reason="First related-party sale, logged and reviewable."
        )
        appeal_case(session, case_id=case.id, outcome="Warning stands. No points deduction.")
        assert case.status == "appealed"
        assert case.evidence
        assert case.reason
        set_stake(session, club_id=club_id, holder_user_id=admin.id, percentage="10")
        interest = economic_interest(session, club_id=club_id, holder_user_id=admin.id)
        assert interest == (club_valuation(session, club_id) * Decimal("0.10")).quantize(Decimal("0.01"))
        session.commit()


def test_showroom_labels_club_ownership_and_keeps_a_static_fallback(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        preview = showroom(session, club_id)
        owned_jet = any(
            item["name"] == "Harbour Jet" and item["ownership_label"] == "Club" for item in preview["exhibits"]
        )
        if not owned_jet:
            purchase_asset(
                session,
                club_id=club_id,
                user_id=admin.id,
                sku="gtex-jet-harbour",
                owner_class="club",
                idempotency_key="showroom-jet",
            )
        room = showroom(session, club_id)
        assert room["fallback"] == "static-card"
        assert room["mode"] == "lightweight-preview"
        labels = {item["name"]: item["ownership_label"] for item in room["exhibits"]}
        assert labels["Harbour Jet"] == "Club"
        assert labels["Lagoon Coach"] == "Not owned"
        models = {item["name"]: item["model_file"] for item in room["exhibits"]}
        assert models["Harbour Jet"] == "assets/showroom/sovereign_900x_jet.glb"
        assert models["Lagoon Coach"] == "assets/showroom/vanguard_xii_coach.glb"
        assert models["Legacy Arena"] == "assets/showroom/arena_imperiale_stadium.glb"
        assert models["Performance Campus"] == "assets/showroom/apex_performance_campus.glb"
        assert all(item["category"] != "vehicle" for item in room["exhibits"])
        arena = next(item for item in room["exhibits"] if item["name"] == "Legacy Arena")
        assert arena["ownership_label"] == "Club"
        assert arena["status"] == "facility"
        assert "price" not in arena
        from app.club_legacy.models import ClubLegacyAsset, ClubLegacyCatalogueItem

        watch = session.scalar(select(ClubLegacyCatalogueItem).where(ClubLegacyCatalogueItem.sku == "gtex-watch-icon"))
        session.add(
            ClubLegacyAsset(
                catalogue_id=watch.id,
                edition_number=99,
                owner_class="owner",
                owner_ref=admin.id,
                club_id=None,
                status="owned",
            )
        )
        session.flush()
        again = showroom(session, club_id)
        personal = [
            item for item in again["exhibits"] if item["name"] == "Icon Watch" and item["ownership_label"] == "Owner"
        ]
        assert personal
        assert personal[0]["owner_class"] == "owner"
        assert personal[0]["model_file"] == "assets/showroom/chronos_tourbillon_watch.glb"
        assert personal[0]["preview_file"] == "assets/showroom/chronos_tourbillon_watch.png"
        assert all(
            item["ownership_label"] == "Club"
            for item in room["exhibits"]
            if item["owned"] and item["owner_class"] == "club"
        )


def test_phase9_small_club_progress_and_flag_rollback(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        small = session.scalar(select(ClubProfile).where(ClubProfile.slug == "opposite-fc-phase5"))
        snapshot = simulate_season(session, small.id)
        assert snapshot["jets"] == 0
        assert snapshot["development"] >= 20
        assert snapshot["can_progress_without_jets"] is True
        funded = simulate_season(session, club_id)
        assert funded["financial_strength"] != funded["prestige"]
        report = metrics(session)
        assert "rollback" in report
    visible = client.get(f"/api/owner/legacy/{club_id}/page", headers=bootstrap_admin_headers)
    assert visible.status_code == 200, visible.text
    with app.state.session_factory() as session:
        flag = session.scalar(select(AdminFeatureFlag).where(AdminFeatureFlag.feature_key == "club_legacy"))
        flag.enabled = False
        session.commit()
    hidden = client.get(f"/api/owner/legacy/{club_id}/page", headers=bootstrap_admin_headers)
    assert hidden.status_code == 404
