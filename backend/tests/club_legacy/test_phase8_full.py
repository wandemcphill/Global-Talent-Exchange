"""Phase 8 exit gate: cases, reviews, stakes, distributions, and net worth."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.admin_engine.service import AdminEngineService
from app.club_legacy.delegation import LegacyError
from app.club_legacy.full import phase8
from app.club_legacy.models import ClubLegacyCase
from app.club_legacy.operations import buy_listing, list_asset, owner_net_worth, place_bid, purchase_asset
from app.models.admin_rules import AdminFeatureFlag
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.user import User
from app.models.wallet import LedgerTransaction
from app.owner_console import ledger


def _enable(app, *keys: str) -> None:
    with app.state.session_factory() as session:
        AdminEngineService(session).seed_defaults()
        for key in keys or ("club_legacy", "club_legacy_governance"):
            flag = session.scalar(select(AdminFeatureFlag).where(AdminFeatureFlag.feature_key == key))
            assert flag is not None
            assert flag.enabled is False
            flag.enabled = True
        session.commit()


def _claim(client, headers) -> str:
    response = client.post(
        "/api/owner/clubs/claim", headers=headers, json={"city_name": "Lagos", "country_code": "NG"}
    )
    assert response.status_code == 200, response.text
    return response.json()["club_id"]


def _admin(session) -> User:
    return session.scalar(select(User).where(User.email == "admin@test.gtex.local"))


def _user(session, slug: str) -> User:
    user = User(email=f"{slug}@gte.local", username=slug, password_hash="hash", display_name=slug)
    session.add(user)
    session.flush()
    return user


def _club(session, owner: User, slug: str) -> ClubProfile:
    club = ClubProfile(
        owner_user_id=owner.id,
        club_name=slug,
        short_name=slug[:4].upper(),
        club_type=ClubType.COMMUNITY,
        lifecycle_status=ClubLifecycleStatus.ACTIVE,
        slug=slug,
        primary_color="#111111",
        secondary_color="#eeeeee",
        accent_color="#EA580C",
        country_code="NG",
        continent_code="AF",
        city_name="Ibadan",
        visibility="public",
    )
    session.add(club)
    session.flush()
    return club


def test_cases_store_the_ruling_and_luxury_does_not_open_one(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        before = session.scalar(
            select(func.count()).select_from(ClubLegacyCase).where(ClubLegacyCase.club_id == club_id)
        )
        purchase_asset(
            session,
            club_id=club_id,
            user_id=admin.id,
            sku="gtex-coach-lagoon",
            owner_class="club",
            idempotency_key="phase8-coach",
        )
        assert (
            session.scalar(select(func.count()).select_from(ClubLegacyCase).where(ClubLegacyCase.club_id == club_id))
            == before
        )
        with pytest.raises(LegacyError) as luxury:
            phase8.open_case(
                session,
                club_id=club_id,
                rule_code="luxury_possession",
                allegation="Bought a coach",
                evidence="Catalogue receipt",
            )
        assert luxury.value.code == "not_misconduct"
        case = phase8.open_case(
            session,
            club_id=club_id,
            rule_code="related_party_transfer",
            allegation="Sold an asset to a sister club",
            evidence="Listing 44",
        )
        assert case.rule_code == "related_party_transfer"
        assert case.allegation
        assert case.evidence
        assert case.status == "open"
        phase8.rule_case(session, case_id=case.id, sanction="warning", reason="First related-party sale, logged.")
        assert case.sanction == "warning"
        assert case.reason.startswith("First related-party")
        phase8.appeal_case(session, case_id=case.id, outcome="Warning stands. No points deduction.")
        assert case.status == "appealed"
        assert case.appeal_outcome == "Warning stands. No points deduction."
        session.commit()
    listed = client.get(f"/api/owner/legacy/{club_id}/governance/cases", headers=bootstrap_admin_headers)
    assert listed.status_code == 200, listed.text
    assert any(row["appeal_outcome"] for row in listed.json()["cases"])


def test_related_party_and_sister_club_trades_are_reviewable(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        sister = _club(session, admin, "phase8-sister")
        jet = purchase_asset(
            session,
            club_id=club_id,
            user_id=admin.id,
            sku="gtex-jet-harbour",
            owner_class="club",
            idempotency_key="phase8-jet",
        )
        listing = list_asset(session, asset_id=jet.id, user_id=admin.id, price="1000")
        with pytest.raises(LegacyError) as blocked:
            buy_listing(
                session,
                listing_id=listing.id,
                buyer_user_id=admin.id,
                buyer_club_id=sister.id,
                idempotency_key="phase8-sister-buy",
            )
        assert blocked.value.code == "wash_trade"
        coach = purchase_asset(
            session,
            club_id=club_id,
            user_id=admin.id,
            sku="gtex-coach-lagoon",
            owner_class="club",
            idempotency_key="phase8-auction-coach",
        )
        auction = list_asset(session, asset_id=coach.id, user_id=admin.id, price="1500", kind="auction")
        with pytest.raises(LegacyError) as own_bid:
            place_bid(session, listing_id=auction.id, bidder_user_id=admin.id, amount="1600")
        assert own_bid.value.code == "wash_trade"
        reviews = phase8.list_trade_reviews(session, club_id)
        kinds = {row.kind for row in reviews}
        assert "sister_club" in kinds
        assert "related_party" in kinds
        assert all(row.status == "reviewable" for row in reviews)
        session.commit()
    payload = client.get(f"/api/owner/legacy/{club_id}/governance/trades", headers=bootstrap_admin_headers)
    assert payload.status_code == 200, payload.text
    assert {row["kind"] for row in payload.json()["trades"]} >= {"sister_club", "related_party"}


def test_stakes_cap_voting_and_distributions_pay_once(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        phase8.set_stake(session, club_id=club_id, holder_user_id=admin.id, percentage="60")
        with pytest.raises(LegacyError) as overflow:
            phase8.set_stake(session, club_id=club_id, holder_user_id="not-used", percentage="50")
        assert overflow.value.code == "stake_total"
        holder = _user(session, "phase8-holder")
        majority = phase8.set_stake(
            session, club_id=club_id, holder_user_id=admin.id, percentage="75", voting_rights="10"
        )
        minority = phase8.set_stake(
            session, club_id=club_id, holder_user_id=holder.id, percentage="25", voting_rights="90"
        )
        assert majority.percentage == Decimal("75.00")
        assert majority.voting_rights == Decimal("10.00")
        assert minority.voting_rights != minority.percentage
        interest = phase8.economic_interest(session, club_id=club_id, holder_user_id=admin.id)
        valuation_share = (phase8._valuation(session, club_id) * Decimal("0.75")).quantize(Decimal("0.01"))
        voting_share = (phase8._valuation(session, club_id) * Decimal("0.10")).quantize(Decimal("0.01"))
        assert interest == valuation_share
        assert interest != voting_share
        before = ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)
        first = phase8.distribute(
            session, club_id=club_id, user_id=admin.id, amount="100.00", idempotency_key="phase8-dist"
        )
        lines = phase8.distribution_lines(session, first.id)
        paid = sum((Decimal(line.amount) for line in lines), Decimal("0"))
        assert paid == Decimal("100.00")
        amounts = {line.holder_user_id: Decimal(line.amount) for line in lines}
        assert amounts[admin.id] == Decimal("75.00")
        assert amounts[holder.id] == Decimal("25.00")
        assert ledger.balance(session, ledger.club_account(club_id), ledger.GTEX) == before - Decimal("100.00")
        keys = session.scalar(
            select(func.count())
            .select_from(LedgerTransaction)
            .where(LedgerTransaction.idempotency_key.in_([f"distribution:phase8-dist:{admin.id}", f"distribution:phase8-dist:{holder.id}"]))
        )
        assert keys == 2
        second = phase8.distribute(
            session, club_id=club_id, user_id=admin.id, amount="100.00", idempotency_key="phase8-dist"
        )
        assert second.id == first.id
        assert ledger.balance(session, ledger.club_account(club_id), ledger.GTEX) == before - Decimal("100.00")
        assert (
            session.scalar(
                select(func.count())
                .select_from(LedgerTransaction)
                .where(
                    LedgerTransaction.idempotency_key.in_(
                        [f"distribution:phase8-dist:{admin.id}", f"distribution:phase8-dist:{holder.id}"]
                    )
                )
            )
            == 2
        )
        third = _user(session, "phase8-third")
        round_club = _club(session, admin, "phase8-round")
        ledger.record(
            session,
            event_type="launch_grant",
            source=ledger.PLATFORM_GRANTS,
            destination=ledger.club_account(round_club.id),
            currency=ledger.GTEX,
            gross=5000,
            user_id=admin.id,
            club_id=round_club.id,
            memo="Rounding float",
        )
        phase8.set_stake(session, club_id=round_club.id, holder_user_id=admin.id, percentage="33.33", voting_rights="10")
        phase8.set_stake(session, club_id=round_club.id, holder_user_id=holder.id, percentage="33.33", voting_rights="20")
        phase8.set_stake(session, club_id=round_club.id, holder_user_id=third.id, percentage="33.34", voting_rights="70")
        rounded = phase8.distribute(
            session, club_id=round_club.id, user_id=admin.id, amount="10.00", idempotency_key="phase8-round"
        )
        rounded_lines = phase8.distribution_lines(session, rounded.id)
        assert sum((Decimal(line.amount) for line in rounded_lines), Decimal("0")) == Decimal("10.00")
        session.commit()


def test_net_worth_keeps_personal_club_and_minority_distinct(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    with app.state.session_factory() as session:
        admin = _admin(session)
        purchase_asset(
            session,
            club_id=club_id,
            user_id=admin.id,
            sku="gtex-watch-icon",
            owner_class="owner",
            idempotency_key="phase8-watch",
        )
        purchase_asset(
            session,
            club_id=club_id,
            user_id=admin.id,
            sku="gtex-jet-harbour",
            owner_class="club",
            idempotency_key="phase8-worth-jet",
        )
        other_owner = _user(session, "phase8-other-owner")
        other = _club(session, other_owner, "phase8-minority-club")
        ledger.record(
            session,
            event_type="launch_grant",
            source=ledger.PLATFORM_GRANTS,
            destination=ledger.club_account(other.id),
            currency=ledger.GTEX,
            gross=80000,
            user_id=other_owner.id,
            club_id=other.id,
            memo="Minority club float",
        )
        phase8.set_stake(session, club_id=other.id, holder_user_id=admin.id, percentage="20", voting_rights="5")
        worth = owner_net_worth(session, admin.id)
        personal = Decimal(worth["personal_assets"])
        club_assets = Decimal(worth["club_assets"])
        minority = Decimal(worth["minority_stakes"])
        assert personal == Decimal("20000.00")
        assert club_assets == Decimal("50000.00")
        assert minority == Decimal("16000.00")
        assert len({personal, club_assets, minority}) == 3
        assert Decimal(worth["net_worth"]) == Decimal(worth["personal_cash"]) + personal + Decimal(worth["equity"])
        assert Decimal(worth["equity"]) == minority
        session.commit()
