"""Comprehensive acceptance tests for GTEX first-club grant, player purchase restrictions,
funding provenance, and 22-player club formation.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4
import pytest
from sqlalchemy import select

from app.ingestion.models import Player
from app.models.club_profile import ClubProfile, ClubType
from app.models.first_club_entitlement import FirstClubEntitlement
from app.models.user import User
from app.owner_console import competitions as comps, ledger, money, service
from app.owner_console.first_club_entitlement import (
    award_first_club_launch_grant,
    get_first_club_entitlement,
    has_received_first_club_grant,
)
from app.owner_console.models import LedgerEvent, OwnerCompetition, OwnerSquadPlayer
from app.owner_console.player_classification import classify_player_for_acquisition
from app.owner_console.service import OwnerError
from app.services.player_lifecycle_service import PlayerLifecycleService, PlayerLifecycleValidationError
from app.transfer_market.service import TransferMarketService
from sqlalchemy import create_engine


@pytest.fixture(scope="module")
def app(test_settings):
    from alembic import command
    from app.core.database import build_alembic_config, load_model_modules
    from app.main import create_app
    from app.models import Base

    engine = create_engine(test_settings.database_url, connect_args={"check_same_thread": False})
    load_model_modules()
    Base.metadata.create_all(engine)
    config = build_alembic_config(engine.url.render_as_string(hide_password=False))
    command.stamp(config, "head")
    application = create_app(settings=test_settings, engine=engine, run_migration_check=False)
    yield application
    engine.dispose()


def _create_player(
    session,
    *,
    player_id: str | None = None,
    name: str = "Test Player",
    overall: int = 75,
    is_real: bool = True,
    is_regen: bool = False,
    is_legend: bool = False,
    position: str = "Midfielder",
    market_value_eur: float = 1_000_000.0,
) -> Player:
    pid = player_id or f"test-p-{uuid4().hex[:8]}"
    dna = {
        "overall": overall,
        "current_rating": overall,
        "potential": overall + 5,
        "is_regen": is_regen,
        "is_legend": is_legend,
    }
    if is_regen:
        dna["origin"] = "regen"
    player = Player(
        id=pid,
        source_provider="gtex_legend_prime" if is_legend else ("gtex_regen_engine" if is_regen else "sofifa_real"),
        provider_external_id=f"ext_{pid}",
        full_name=name,
        is_real_player=is_real and not is_regen and not is_legend,
        real_player_tier="legend" if is_legend else ("first_team" if is_real else None),
        position=position,
        normalized_position=position.lower(),
        market_value_eur=market_value_eur,
        is_tradable=True,
        dna_profile=dna,
    )
    session.add(player)
    session.flush()
    return player


def _create_club_profile(
    session,
    owner_user_id: str,
    club_name: str | None = None,
    short_name: str = "TFC",
) -> ClubProfile:
    from app.models.club_profile import ClubLifecycleStatus
    name = club_name or f"Test Club {uuid4().hex[:6]} FC"
    club = ClubProfile(
        owner_user_id=owner_user_id,
        club_name=name,
        short_name=short_name,
        slug=f"club-{uuid4().hex[:8]}",
        club_type=ClubType.COMMUNITY,
        lifecycle_status=ClubLifecycleStatus.ACTIVE,
        visibility="public",
        primary_color="#0F766E",
        secondary_color="#FFFFFF",
        accent_color="#EA580C",
        country_code="NG",
        continent_code="AF",
        city_name="Lagos",
    )
    session.add(club)
    session.flush()
    return club


# =========================================================================
# 1. FIRST-CLUB LAUNCH GRANT — ONE-TIME ENTITLEMENT TESTS (Tests 1 - 11)
# =========================================================================

def test_first_club_receives_100k_gtex_promotional_grant(client, auth_user_factory, app_session_factory):
    """Test 1: User's first club receives exactly 100,000 GTEX Coin classified as promotional."""
    user = auth_user_factory(suffix="first-club-100k")
    claimed = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]

    with app_session_factory() as session:
        funding = ledger.get_club_funding(session, club_id)
        assert funding["total_cash"] == Decimal("100000")
        assert funding["available_promotional"] == Decimal("100000")
        assert funding["available_deposited"] == Decimal("0")
        assert funding["available_earned"] == Decimal("0")


def test_first_club_receives_1k_fan_coin_grant_once(client, auth_user_factory, app_session_factory):
    """Test 2: User receives 1,000 Fan Coin welcome grant on first club creation."""
    user = auth_user_factory(suffix="first-club-1k-fan")
    claimed = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed.status_code == 200, claimed.text

    with app_session_factory() as session:
        db_user = session.scalar(select(User).where(User.id == user["user_id"]))
        assert db_user is not None
        fan_balance = ledger.balance(session, ledger.user_account(db_user.id), ledger.FAN)
        assert fan_balance >= Decimal("1000")


def test_second_club_receives_no_gtex_grant(client, auth_user_factory, app_session_factory):
    """Test 3: Second club created by the same user receives NO GTEX Coin launch grant."""
    user = auth_user_factory(suffix="second-club-no-gtex")
    # First club
    claimed1 = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed1.status_code == 200, claimed1.text
    club1_id = claimed1.json()["club_id"]

    # Second club created via service / onboarding
    with app_session_factory() as session:
        club2 = _create_club_profile(session, user["user_id"], club_name=f"Second Club {uuid4().hex[:6]} FC")
        club2_id = club2.id

        # Attempt to activate or award launch grant
        entitlement, awarded = award_first_club_launch_grant(session, user_id=user["user_id"], club_id=club2_id)
        assert awarded is False, "Second club must not receive a new entitlement"

        funding2 = ledger.get_club_funding(session, club2_id)
        assert funding2["total_cash"] == Decimal("0"), "Second club treasury must receive 0 launch grant"
        assert funding2["available_promotional"] == Decimal("0")


def test_second_club_receives_no_fan_coin_grant(client, auth_user_factory, app_session_factory):
    """Test 4: User does NOT receive a second 1,000 Fan Coin welcome grant when creating a second club."""
    user = auth_user_factory(suffix="second-club-no-fan")
    claimed1 = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed1.status_code == 200, claimed1.text

    with app_session_factory() as session:
        fan_before = ledger.balance(session, ledger.user_account(user["user_id"]), ledger.FAN)
        assert fan_before == Decimal("1000")

        # Second club
        club2 = _create_club_profile(session, user["user_id"], club_name=f"Club Two {uuid4().hex[:6]} FC")

        _, awarded = award_first_club_launch_grant(session, user_id=user["user_id"], club_id=club2.id)
        assert awarded is False
        session.commit()

        fan_after = ledger.balance(session, ledger.user_account(user["user_id"]), ledger.FAN)
        assert fan_after == fan_before, "Fan Coin balance must not increase on second club creation"


def test_third_club_receives_no_gtex_grant(client, auth_user_factory, app_session_factory):
    """Test 5: Third club receives NO GTEX Coin launch grant."""
    user = auth_user_factory(suffix="third-club-no-gtex")
    claimed1 = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed1.status_code == 200, claimed1.text

    with app_session_factory() as session:
        club2 = _create_club_profile(session, user["user_id"], club_name=f"Club 2 {uuid4().hex[:6]} FC")
        club3 = _create_club_profile(session, user["user_id"], club_name=f"Club 3 {uuid4().hex[:6]} FC")

        grant3, awarded = award_first_club_launch_grant(session, user_id=user["user_id"], club_id=club3.id)
        assert awarded is False

        funding3 = ledger.get_club_funding(session, club3.id)
        assert funding3["total_cash"] == Decimal("0")


def test_third_club_receives_no_fan_coin_grant(client, auth_user_factory, app_session_factory):
    """Test 6: User does NOT receive Fan Coin welcome grant on third club creation."""
    user = auth_user_factory(suffix="third-club-no-fan")
    claimed1 = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed1.status_code == 200, claimed1.text

    with app_session_factory() as session:
        club3 = _create_club_profile(session, user["user_id"], club_name=f"Club 3 {uuid4().hex[:6]} FC")

        _, awarded = award_first_club_launch_grant(session, user_id=user["user_id"], club_id=club3.id)
        assert awarded is False
        session.commit()

        fan_balance = ledger.balance(session, ledger.user_account(user["user_id"]), ledger.FAN)
        assert fan_balance == Decimal("1000")


def test_fourth_club_creation_rejected_by_ownership_cap(client, auth_user_factory, app_session_factory):
    """Test 7: Fourth club creation is rejected due to max 3 clubs ownership cap."""
    from app.clubs.ownership_cap import ClubOwnershipCapError, assert_can_acquire_club

    user = auth_user_factory(suffix="fourth-club-cap")
    claimed1 = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed1.status_code == 200, claimed1.text

    with app_session_factory() as session:
        club2 = _create_club_profile(session, user["user_id"], club_name=f"Club 2 {uuid4().hex[:6]} FC")
        club3 = _create_club_profile(session, user["user_id"], club_name=f"Club 3 {uuid4().hex[:6]} FC")
        session.commit()

        # At 3 clubs, assert_can_acquire_club should raise ClubOwnershipCapError
        with pytest.raises(ClubOwnershipCapError):
            assert_can_acquire_club(session, user["user_id"])


def test_concurrent_first_club_claims_award_grant_exactly_once(client, auth_user_factory, app_session_factory):
    """Test 8: Concurrent / repeated first-club grant awards are atomic and idempotent."""
    with app_session_factory() as session:
        fresh_user = User(
            id=str(uuid4()),
            email=f"concurrent-{uuid4().hex[:6]}@example.com",
            username=f"conc_{uuid4().hex[:6]}",
            password_hash="test-hash",
            account_type="user",
        )
        session.add(fresh_user)
        session.flush()

        club = _create_club_profile(session, fresh_user.id, club_name=f"Concurrent Club {uuid4().hex[:6]} FC")

        # Call 1
        grant1, awarded1 = award_first_club_launch_grant(session, user_id=fresh_user.id, club_id=club.id)
        assert grant1 is not None
        assert awarded1 is True

        # Call 2 (simulating race or retry)
        grant2, awarded2 = award_first_club_launch_grant(session, user_id=fresh_user.id, club_id=club.id)
        assert grant2 is not None
        assert awarded2 is False
        assert grant2.id == grant1.id

        session.commit()

        # Verify only 1 entitlement row in database
        entitlements = list(
            session.scalars(
                select(FirstClubEntitlement).where(FirstClubEntitlement.user_id == fresh_user.id)
            ).all()
        )
        assert len(entitlements) == 1

        # Verify treasury only credited 100k once
        funding = ledger.get_club_funding(session, club.id)
        assert funding["total_cash"] == Decimal("100000")


def test_first_club_entitlement_recorded_with_ledger_tx_ids(client, auth_user_factory, app_session_factory):
    """Test 9: FirstClubEntitlement record stores non-null user_id, club_id, amounts, and ledger tx IDs."""
    user = auth_user_factory(suffix="entitlement-record")
    claimed = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]

    with app_session_factory() as session:
        entitlement = get_first_club_entitlement(session, user["user_id"])
        assert entitlement is not None
        assert entitlement.user_id == user["user_id"]
        assert entitlement.club_id == club_id
        assert entitlement.gtex_grant_amount == Decimal("100000")
        assert entitlement.fan_grant_amount == Decimal("1000")
        assert entitlement.gtex_ledger_event_id is not None
        assert entitlement.fan_ledger_event_id is not None

        # Verify ledger events exist
        gtex_tx = session.get(LedgerEvent, entitlement.gtex_ledger_event_id)
        assert gtex_tx is not None
        assert gtex_tx.currency == ledger.GTEX
        assert gtex_tx.balance_class == "promotional"

        fan_tx = session.get(LedgerEvent, entitlement.fan_ledger_event_id)
        assert fan_tx is not None
        assert fan_tx.currency == ledger.FAN


def test_historical_club_owner_backfill_does_not_reaward_grant(client, auth_user_factory, app_session_factory):
    """Test 10: Backfilled historical owner cannot receive another grant."""
    with app_session_factory() as session:
        hist_user = User(
            id=str(uuid4()),
            email=f"historical-{uuid4().hex[:6]}@example.com",
            username=f"hist_{uuid4().hex[:6]}",
            password_hash="test-hash",
            account_type="user",
        )
        session.add(hist_user)
        session.flush()

        club = _create_club_profile(session, hist_user.id, club_name=f"Historical FC {uuid4().hex[:6]}")

        # Simulate historical entitlement backfill record
        historical_entitlement = FirstClubEntitlement(
            user_id=hist_user.id,
            club_id=club.id,
            gtex_grant_amount=Decimal("100000"),
            fan_grant_amount=Decimal("1000"),
            gtex_ledger_event_id="historical_migration_tx_gtex",
            fan_ledger_event_id="historical_migration_tx_fan",
        )
        session.add(historical_entitlement)
        session.commit()

        assert has_received_first_club_grant(session, hist_user.id) is True

        # Attempt to award grant again
        result, awarded = award_first_club_launch_grant(session, user_id=hist_user.id, club_id=club.id)
        assert awarded is False
        assert result.id == historical_entitlement.id
        # No new money should be added
        funding = ledger.get_club_funding(session, club.id)
        assert funding["total_cash"] == Decimal("0")


def test_trader_and_creator_accounts_denied_first_club_grant(client, auth_user_factory, app_session_factory):
    """Test 11: Trader and Creator accounts cannot claim clubs or receive club launch grants."""
    from backend.tests.support.signup_payloads import creator_signup_payload

    # 1. Creator
    creator_res = client.post(
        "/auth/signup/creator",
        json=creator_signup_payload(
            email=f"creator-{uuid4().hex[:6]}@example.com",
            username=f"creator_{uuid4().hex[:6]}",
            creator_name="Test Creator",
            password="SuperSecret1",
        ),
    )
    assert creator_res.status_code == 201
    creator_token = creator_res.json()["access_token"]
    creator_headers = {"Authorization": f"Bearer {creator_token}"}

    claim_res = client.post("/api/owner/clubs/claim", headers=creator_headers)
    assert claim_res.status_code == 403
    assert claim_res.json()["detail"]["code"] == "club_owner_account_type_required"

    # 2. Trader
    trader = auth_user_factory(suffix="trader-guard", account_type="coin_trader")
    claim_trader = client.post("/api/owner/clubs/claim", headers=trader["headers"])
    assert claim_trader.status_code == 403
    assert claim_trader.json()["detail"]["code"] == "club_owner_account_type_required"


# =========================================================================
# 2. PROMOTIONAL-CREDIT PLAYER PURCHASE RESTRICTIONS (Tests 12 - 24)
# =========================================================================

def test_real_player_gsi_79_purchasable_with_promotional_credit(client, auth_user_factory, app_session_factory):
    """Test 12: Ordinary real player with GSI 79 is eligible and purchasable using promotional credit."""
    user = auth_user_factory(suffix="p-gsi-79")
    claimed = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]

    with app_session_factory() as session:
        player_79 = _create_player(session, name="Player SeventyNine", overall=79, is_real=True)
        # Classify authoritative
        classification = classify_player_for_acquisition(session, player_79)
        assert classification.is_eligible_for_promotional is True
        assert classification.requires_deposited_funds is False

        # Sign player into squad
        signed = service.sign_market_player(session, user["user_id"], club_id, player_79.id)
        assert signed is not None
        assert signed.player_ref == player_79.id

        # Promotional credit was consumed
        funding = ledger.get_club_funding(session, club_id)
        assert funding["available_promotional"] < Decimal("100000")


def test_real_player_gsi_80_rejected_with_promotional_credit(client, auth_user_factory, app_session_factory):
    """Test 13: Real player with GSI 80 cannot be purchased with promotional launch credit."""
    user = auth_user_factory(suffix="p-gsi-80-fail")
    claimed = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]

    with app_session_factory() as session:
        player_80 = _create_player(session, name="Player Eighty", overall=80, is_real=True)
        classification = classify_player_for_acquisition(session, player_80)
        assert classification.is_eligible_for_promotional is False
        assert classification.requires_deposited_funds is True

        with pytest.raises(OwnerError) as exc_info:
            service.sign_market_player(session, user["user_id"], club_id, player_80.id)
        assert exc_info.value.code == "restricted_player_requires_deposited_funds"


def test_real_player_gsi_80_purchasable_with_deposited_funds(client, auth_user_factory, app_session_factory):
    """Test 14: Real player with GSI 80 can be purchased when club treasury has deposited funds."""
    user = auth_user_factory(suffix="p-gsi-80-pass")
    claimed = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]

    with app_session_factory() as session:
        player_80 = _create_player(session, name="Player Eighty Paid", overall=80, is_real=True)
        # Credit deposited funds
        ledger.record(
            session,
            event_type="owner_capital_injection",
            currency=ledger.GTEX,
            gross=Decimal("50000"),
            source=ledger.WORLD_MARKET,
            destination=ledger.club_account(club_id),
            user_id=user["user_id"],
            club_id=club_id,
            balance_class="deposited",
        )
        session.commit()

        signed = service.sign_market_player(session, user["user_id"], club_id, player_80.id)
        assert signed is not None
        assert signed.player_ref == player_80.id


def test_regen_player_rejected_with_promotional_credit(client, auth_user_factory, app_session_factory):
    """Test 15: Regen player (regardless of GSI, e.g. GSI 65) rejected with promotional credit."""
    user = auth_user_factory(suffix="regen-fail")
    claimed = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]

    with app_session_factory() as session:
        regen_low_gsi = _create_player(session, name="Regen Kid", overall=65, is_real=False, is_regen=True)
        classification = classify_player_for_acquisition(session, regen_low_gsi)
        assert classification.requires_deposited_funds is True

        with pytest.raises(OwnerError) as exc_info:
            service.sign_market_player(session, user["user_id"], club_id, regen_low_gsi.id)
        assert exc_info.value.code == "restricted_player_requires_deposited_funds"


def test_regen_player_purchasable_with_deposited_funds(client, auth_user_factory, app_session_factory):
    """Test 16: Regen player can be purchased when club has deposited funds."""
    user = auth_user_factory(suffix="regen-pass")
    claimed = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]

    with app_session_factory() as session:
        regen = _create_player(session, name="Regen Star", overall=78, is_real=False, is_regen=True)
        ledger.record(
            session,
            event_type="owner_capital_injection",
            currency=ledger.GTEX,
            gross=Decimal("50000"),
            source=ledger.WORLD_MARKET,
            destination=ledger.club_account(club_id),
            user_id=user["user_id"],
            club_id=club_id,
            balance_class="deposited",
        )
        session.commit()

        signed = service.sign_market_player(session, user["user_id"], club_id, regen.id)
        assert signed is not None
        assert signed.player_ref == regen.id


def test_legend_player_rejected_with_promotional_credit(client, auth_user_factory, app_session_factory):
    """Test 17: Legend player rejected with promotional credit."""
    user = auth_user_factory(suffix="legend-fail")
    claimed = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]

    with app_session_factory() as session:
        legend = _create_player(session, name="Legend King", overall=94, is_legend=True)
        classification = classify_player_for_acquisition(session, legend)
        assert classification.requires_deposited_funds is True

        with pytest.raises(OwnerError) as exc_info:
            service.sign_market_player(session, user["user_id"], club_id, legend.id)
        assert exc_info.value.code == "restricted_player_requires_deposited_funds"


def test_legend_player_purchasable_with_deposited_funds(client, auth_user_factory, app_session_factory):
    """Test 18: Legend player can be purchased when club has deposited funds."""
    user = auth_user_factory(suffix="legend-pass")
    claimed = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]

    with app_session_factory() as session:
        legend = _create_player(session, name="Legend Hero", overall=92, is_legend=True)
        ledger.record(
            session,
            event_type="owner_capital_injection",
            currency=ledger.GTEX,
            gross=Decimal("100000"),
            source=ledger.WORLD_MARKET,
            destination=ledger.club_account(club_id),
            user_id=user["user_id"],
            club_id=club_id,
            balance_class="deposited",
        )
        session.commit()

        signed = service.sign_market_player(session, user["user_id"], club_id, legend.id)
        assert signed is not None
        assert signed.player_ref == legend.id


def test_earned_funds_cannot_purchase_restricted_players(client, auth_user_factory, app_session_factory):
    """Test 19: Earned funds (competition prizes, player sales) cannot purchase restricted players."""
    user = auth_user_factory(suffix="earned-restricted-fail")
    claimed = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]

    with app_session_factory() as session:
        # Credit 50,000 GTEX as earned rewards
        ledger.record(
            session,
            event_type="match_reward",
            currency=ledger.GTEX,
            gross=Decimal("50000"),
            source=ledger.WORLD_MARKET,
            destination=ledger.club_account(club_id),
            user_id=user["user_id"],
            club_id=club_id,
            balance_class="earned",
        )
        session.commit()

        player_85 = _create_player(session, name="Player EightyFive", overall=85, is_real=True)
        with pytest.raises(OwnerError) as exc_info:
            service.sign_market_player(session, user["user_id"], club_id, player_85.id)
        assert exc_info.value.code == "restricted_player_requires_deposited_funds"


def test_mixed_promotional_and_deposited_insufficient_deposited_fails(client, auth_user_factory, app_session_factory):
    """Test 20: When purchasing a restricted player, deposited funds must cover the ENTIRE price."""
    user = auth_user_factory(suffix="mixed-insufficient-fail")
    claimed = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]

    with app_session_factory() as session:
        # Restricted player costs > 0 GTEX Coin
        player_82 = _create_player(session, name="Player EightyTwo", overall=82, is_real=True, market_value_eur=5000000.0)
        price, _ = service.player_quotes(session, [player_82])[player_82.id]
        assert price > 0

        # Club has 100,000 promotional from launch grant.
        # Credit deposited GTEX Coin that is strictly less than price (e.g. half of price)
        deposited_amount = max(Decimal("1"), Decimal(str(price // 2)))
        ledger.record(
            session,
            event_type="owner_capital_injection",
            currency=ledger.GTEX,
            gross=deposited_amount,
            source=ledger.WORLD_MARKET,
            destination=ledger.club_account(club_id),
            user_id=user["user_id"],
            club_id=club_id,
            balance_class="deposited",
        )
        session.commit()

        with pytest.raises(OwnerError) as exc_info:
            service.sign_market_player(session, user["user_id"], club_id, player_82.id)
        assert exc_info.value.code == "restricted_player_requires_deposited_funds"


def test_eligible_purchase_consumes_promotional_before_deposited(client, auth_user_factory, app_session_factory):
    """Test 21: Purchasing an eligible player (GSI <= 79) consumes promotional credit first."""
    user = auth_user_factory(suffix="promo-priority")
    claimed = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]

    with app_session_factory() as session:
        # Inject 20,000 deposited funds
        ledger.record(
            session,
            event_type="owner_capital_injection",
            currency=ledger.GTEX,
            gross=Decimal("20000"),
            source=ledger.WORLD_MARKET,
            destination=ledger.club_account(club_id),
            user_id=user["user_id"],
            club_id=club_id,
            balance_class="deposited",
        )
        session.commit()

        funding_before = ledger.get_club_funding(session, club_id)
        assert funding_before["available_promotional"] == Decimal("100000")
        assert funding_before["available_deposited"] == Decimal("20000")

        # Sign eligible GSI 75 player
        player_75 = _create_player(session, name="Player SeventyFive", overall=75, is_real=True)
        signed = service.sign_market_player(session, user["user_id"], club_id, player_75.id)
        assert signed is not None

        funding_after = ledger.get_club_funding(session, club_id)
        # Promotional balance decreased
        assert funding_after["available_promotional"] < Decimal("100000")
        # Deposited balance remains completely intact!
        assert funding_after["available_deposited"] == Decimal("20000")


def test_user_wallet_deposit_transfers_provenance_to_club_treasury(client, auth_user_factory, app_session_factory):
    """Test 22: Injecting capital from user wallet preserves funding provenance."""
    user = auth_user_factory(suffix="provenance-injection", funded_coin=Decimal("15000"))
    claimed = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]

    with app_session_factory() as session:
        # Record verified deposit into user's wallet account in owner ledger
        ledger.record(
            session,
            event_type="deposit",
            source=ledger.PAYSTACK,
            destination=ledger.user_account(user["user_id"]),
            currency=ledger.GTEX,
            gross=Decimal("15000"),
            balance_class="deposited",
            user_id=user["user_id"],
            memo="Test wallet deposit",
        )
        session.commit()

        # Inject 10,000 into club treasury
        event = money.inject_capital(session, user["user_id"], club_id, Decimal("10000"))
        assert event is not None
        assert event.balance_class == "deposited"

        funding = ledger.get_club_funding(session, club_id)
        assert funding["available_deposited"] == Decimal("10000")


def test_formal_transfer_bid_enforces_funding_provenance_at_bid_and_settlement(client, auth_user_factory, app_session_factory):
    """Test 23: Formal transfer bid enforces funding provenance for restricted players."""
    user = auth_user_factory(suffix="formal-bid-enforcement")
    claimed = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]

    with app_session_factory() as session:
        player_88 = _create_player(session, name="Player EightyEight", overall=88, is_real=True)
        lifecycle = PlayerLifecycleService(session)

        # Club only has promotional credit -> assertion must fail for restricted player
        with pytest.raises(PlayerLifecycleValidationError) as exc_info:
            lifecycle._assert_buying_club_can_fund(club_id, Decimal("25000"), player_id=player_88.id)
        assert "restricted" in str(exc_info.value).lower()


def test_transfer_hub_offer_enforces_funding_provenance(client, auth_user_factory, app_session_factory):
    """Test 24: Transfer Hub cash offer enforces deposited funding provenance for restricted players."""
    user = auth_user_factory(suffix="transfer-hub-enforcement")
    claimed = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]

    with app_session_factory() as session:
        player_82 = _create_player(session, name="Player EightyTwo Hub", overall=82, is_real=True)
        hub = TransferMarketService(session)

        # Transfer market offer assertion on restricted player must reject promotional-only club
        with pytest.raises(Exception) as exc_info:
            hub._assert_bidder_can_fund(club_id, Decimal("30000"), subject="transfer_hub_offer", player_or_id=player_82)
        assert "Restricted players" in str(exc_info.value) or "restricted_player_requires_deposited_funds" in str(exc_info.value)


# =========================================================================
# 3. CLUB FORMATION — MINIMUM 22 REGISTERED PLAYERS (Tests 25 - 28)
# =========================================================================

def test_club_formation_fails_with_21_distinct_players(client, auth_user_factory, app_session_factory):
    """Test 25: A club with only 21 distinct registered players fails formation and cannot enter competitions."""
    user = auth_user_factory(suffix="formation-21-fail")
    claimed = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]

    with app_session_factory() as session:
        # Clear squad and contracts
        from app.models.player_contract import PlayerContract
        session.query(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id).delete()
        session.query(PlayerContract).where(PlayerContract.club_id == club_id).delete()
        session.flush()

        # Add 1 GK and 20 outfield players = 21 players
        for i in range(21):
            pos = "goalkeeper" if i == 0 else "midfielder"
            p = OwnerSquadPlayer(
                club_id=club_id,
                player_ref=f"p21_{i}",
                name=f"Player {i}",
                position=pos,
                status="active",
                rating=65,
                morale=70,
                potential=75,
                is_regen=True,
                personality_json={"squad_status": "first_team" if i < 11 else ("reserve" if i < 16 else "academy")},
            )
            session.add(p)
        session.commit()

        formation = service.get_club_formation_status(session, club_id)
        assert formation["total_registered_players"] == 21
        assert formation["is_formed"] is False
        assert formation["remaining_to_form"] == 1

        # Attempt to enter competition must fail
        comp = session.scalar(select(OwnerCompetition).where(OwnerCompetition.status == "open"))
        if not comp:
            comp = OwnerCompetition(
                id="test_open_comp_21",
                name="Test Open Cup 21",
                host_type="community",
                status="open",
                max_clubs=16,
                entry_fee=0,
                prize_pool=1000,
            )
            session.add(comp)
            session.flush()

        with pytest.raises(OwnerError) as exc_info:
            comps.enter_competition(session, user["user_id"], comp.id, club_id)
        assert exc_info.value.code == "minimum_squad_size_not_met"


def test_club_formation_succeeds_with_22_distinct_players_across_tiers(client, auth_user_factory, app_session_factory):
    """Test 26: Club with 22 distinct registered players across First Team, Reserve, and Academy satisfies formation."""
    user = auth_user_factory(suffix="formation-22-pass")
    claimed = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]

    with app_session_factory() as session:
        # Clear squad and add exactly 22 players: 11 first team, 6 reserve, 5 academy
        from app.models.player_contract import PlayerContract
        session.query(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id).delete()
        session.query(PlayerContract).where(PlayerContract.club_id == club_id).delete()
        session.flush()

        for i in range(22):
            pos = "goalkeeper" if i < 2 else "midfielder"
            squad_tier = "first_team" if i < 11 else ("reserve" if i < 17 else "academy")
            p = OwnerSquadPlayer(
                club_id=club_id,
                player_ref=f"p22_{i}",
                name=f"Squad Member {i}",
                position=pos,
                status="active",
                rating=68,
                morale=75,
                potential=80,
                is_regen=True,
                personality_json={"squad_status": squad_tier},
            )
            session.add(p)
        session.commit()

        formation = service.get_club_formation_status(session, club_id)
        assert formation["total_registered_players"] == 22
        assert formation["distinct_registered_count"] == 22
        assert formation["first_team_count"] == 11
        assert formation["reserve_count"] == 6
        assert formation["academy_count"] == 5
        assert formation["has_goalkeeper"] is True
        assert formation["is_formed"] is True
        assert formation["remaining_to_form"] == 0


def test_club_formation_requires_goalkeeper_among_22_players(client, auth_user_factory, app_session_factory):
    """Test 27: Formation requires at least one registered goalkeeper among the 22 players."""
    user = auth_user_factory(suffix="formation-no-gk")
    claimed = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]

    with app_session_factory() as session:
        from app.models.player_contract import PlayerContract
        session.query(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id).delete()
        session.query(PlayerContract).where(PlayerContract.club_id == club_id).delete()
        session.flush()

        # 22 players, all outfield (no GK)
        for i in range(22):
            p = OwnerSquadPlayer(
                club_id=club_id,
                player_ref=f"nogk_{i}",
                name=f"Outfield {i}",
                position="midfielder",
                status="active",
                rating=65,
                morale=70,
                potential=75,
                is_regen=True,
            )
            session.add(p)
        session.commit()

        formation = service.get_club_formation_status(session, club_id)
        assert formation["total_registered_players"] == 22
        assert formation["has_goalkeeper"] is False
        assert formation["is_formed"] is False


def test_starter_squad_bootstrap_generates_22_non_marketable_players(client, auth_user_factory, app_session_factory):
    """Test 28: Starter squad bootstrap creates 22 starter players with GK coverage across 3 tiers."""
    user = auth_user_factory(suffix="starter-bootstrap-22")
    claimed = client.post("/api/owner/clubs/claim", headers=user["headers"])
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]

    with app_session_factory() as session:
        squad_players = service.squad(session, club_id)
        assert len(squad_players) == 22, f"Expected 22 players, found {len(squad_players)}"

        gk_count = sum(1 for p in squad_players if "goalkeeper" in str(p.position).lower())
        assert gk_count >= 2, f"Expected at least 2 goalkeepers, found {gk_count}"

        # Check squad status distribution
        first_team = 0
        reserve = 0
        academy = 0
        for p in squad_players:
            tier = (p.personality_json or {}).get("squad_status")
            if tier == "first_team":
                first_team += 1
            elif tier == "reserve":
                reserve += 1
            elif tier == "academy":
                academy += 1

        assert first_team == 11, f"Expected 11 first team players, got {first_team}"
        assert reserve == 6, f"Expected 6 reserve players, got {reserve}"
        assert academy == 5, f"Expected 5 academy players, got {academy}"

        # Verify club formation is satisfied
        formation = service.get_club_formation_status(session, club_id)
        assert formation["is_formed"] is True
