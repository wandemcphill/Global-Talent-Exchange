"""Club Legacy phase 1: geography, ownership cap, ledger idempotency, and delegation."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select

from app.auth.service import AuthError, AuthService
from app.club_legacy.geography import backfill_missing_continents, continent_for_country, continent_name
from app.club_legacy.ledger import post_club_legacy_transfer
from app.models.admin_rules import AdminFeatureFlag
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.user import PublicAccountType, User
from app.models.wallet import LedgerTransaction
from app.owner_console import ledger as owner_ledger
from app.owner_console.service import OwnerError, _create_starter_profile


def test_continent_for_nigeria_is_africa_and_unknown_stays_blank() -> None:
    assert continent_for_country("ng") == "AF"
    assert continent_name("AF") == "Africa"
    assert continent_for_country(None) is None
    assert continent_for_country("ZZ") is None


def test_claim_sets_continent_and_blank_country_stays_blank(client, bootstrap_admin_headers, app):
    claimed = client.post(
        "/api/owner/clubs/claim",
        headers=bootstrap_admin_headers,
        json={"city_name": "Lagos", "country_code": "NG"},
    )
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]

    with app.state.session_factory() as session:
        club = session.get(ClubProfile, club_id)
        assert club.country_code == "NG"
        assert club.city_name == "Lagos"
        assert club.continent_code == "AF"
        blank = ClubProfile(
            owner_user_id=club.owner_user_id,
            club_name="Unplaced Club",
            short_name="UNPL",
            club_type=ClubType.COMMUNITY,
            lifecycle_status=ClubLifecycleStatus.ACTIVE,
            slug="unplaced-club-phase1",
            primary_color="#0F766E",
            secondary_color="#F8FAFC",
            accent_color="#EA580C",
            country_code=None,
            continent_code=None,
            visibility="public",
        )
        session.add(blank)
        session.commit()
        assert backfill_missing_continents(session) == 0
        session.refresh(blank)
        assert blank.continent_code is None
        assert session.get(ClubProfile, blank.id) is not None

    opened = client.get("/api/owner/control-center", headers=bootstrap_admin_headers)
    assert opened.status_code == 200, opened.text
    assert opened.json()["clubs"]
    assert opened.json()["legacy"] is None

    missing = client.get(f"/api/owner/legacy/{club_id}", headers=bootstrap_admin_headers)
    assert missing.status_code == 404


def test_fourth_club_is_rejected_on_create_and_claim(client, app):
    del client
    with app.state.session_factory() as session:
        user = User(
            email="legacy-cap@gte.local",
            username="legacy_cap",
            password_hash="hash",
            display_name="Legacy Cap",
            account_type=PublicAccountType.USER,
        )
        session.add(user)
        session.flush()
        service = AuthService()
        for index in range(3):
            service.create_explicit_club_profile(
                session,
                user,
                club_name=f"Cap Club {index}",
                short_name=f"C{index}",
                club_type=ClubType.COMMUNITY,
                country_code="NG",
                region_name=None,
                city_name="Lagos",
                crest_asset_ref=None,
                primary_color="#0F766E",
                secondary_color="#F8FAFC",
            )
        session.commit()
        try:
            service.create_explicit_club_profile(
                session,
                user,
                club_name="Cap Club 4",
                short_name="C4",
                club_type=ClubType.COMMUNITY,
                country_code="NG",
                region_name=None,
                city_name="Lagos",
                crest_asset_ref=None,
                primary_color="#0F766E",
                secondary_color="#F8FAFC",
            )
            raised = False
        except AuthError:
            raised = True
        assert raised
        try:
            _create_starter_profile(session, user, city_name="Abuja", country_code="NG")
            claim_raised = False
        except OwnerError as exc:
            claim_raised = True
            assert exc.code == "club_ownership_cap_reached"
        assert claim_raised
        assert (
            session.scalar(
                select(func.count())
                .select_from(ClubProfile)
                .where(
                    ClubProfile.owner_user_id == user.id,
                    ClubProfile.lifecycle_status != ClubLifecycleStatus.ARCHIVED_GENERATED,
                )
            )
            == 3
        )


def test_legacy_transfer_posts_once(client, bootstrap_admin_headers, app):
    claimed = client.post(
        "/api/owner/clubs/claim",
        headers=bootstrap_admin_headers,
        json={"city_name": "Lagos", "country_code": "NG"},
    )
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]
    with app.state.session_factory() as session:
        source = owner_ledger.wallet_account(session, owner_ledger.club_account(club_id), owner_ledger.GTEX)
        destination = owner_ledger.wallet_account(session, owner_ledger.PLATFORM_FEES, owner_ledger.GTEX)
        first = post_club_legacy_transfer(
            session,
            idempotency_key="club-legacy-phase1-once",
            source=source,
            destination=destination,
            amount=Decimal("10.0000"),
            description="Phase 1 idempotency",
        )
        session.commit()
        second = post_club_legacy_transfer(
            session,
            idempotency_key="club-legacy-phase1-once",
            source=source,
            destination=destination,
            amount=Decimal("10.0000"),
            description="Phase 1 idempotency",
        )
        session.commit()
        assert first[0].transaction_id == second[0].transaction_id
        assert (
            session.scalar(
                select(func.count())
                .select_from(LedgerTransaction)
                .where(LedgerTransaction.idempotency_key == "club-legacy-phase1-once")
            )
            == 1
        )


def _enable_legacy(app) -> None:
    from app.admin_engine.service import AdminEngineService

    with app.state.session_factory() as session:
        AdminEngineService(session).seed_defaults()
        flag = session.scalar(select(AdminFeatureFlag).where(AdminFeatureFlag.feature_key == "club_legacy"))
        assert flag is not None
        flag.enabled = True
        session.commit()


def test_delegation_rechecks_policy_and_blocks_over_threshold(client, bootstrap_admin_headers, app):
    claimed = client.post("/api/owner/clubs/claim", headers=bootstrap_admin_headers)
    assert claimed.status_code == 200, claimed.text
    club_id = claimed.json()["club_id"]
    _enable_legacy(app)
    headers = bootstrap_admin_headers

    opened = client.get(f"/api/owner/legacy/{club_id}", headers=headers)
    assert opened.status_code == 200, opened.text
    ratings = opened.json()
    assert set(ratings) >= {"prestige", "development", "financial_strength"}
    assert ratings["prestige"] != ratings["financial_strength"]
    assert ratings["continent_name"] == "Africa"

    wide = client.put(
        f"/api/owner/legacy/{club_id}/policies/operating_spend",
        headers=headers,
        json={"mode": "automatic", "max_amount": "1000"},
    )
    assert wide.status_code == 200, wide.text
    recommended = client.post(
        f"/api/owner/legacy/{club_id}/recommendations",
        headers=headers,
        json={"task_key": "operating_spend", "amount": "500"},
    )
    assert recommended.status_code == 200, recommended.text
    recommendation_id = recommended.json()["id"]
    tight = client.put(
        f"/api/owner/legacy/{club_id}/policies/operating_spend",
        headers=headers,
        json={"mode": "automatic", "max_amount": "100"},
    )
    assert tight.status_code == 200, tight.text
    blocked = client.post(f"/api/owner/legacy/recommendations/{recommendation_id}/execute", headers=headers)
    assert blocked.status_code == 200, blocked.text
    assert blocked.json()["status"] == "blocked"
    assert "exceeds the current automatic limit" in blocked.json()["outcome"]

    over = client.post(
        f"/api/owner/legacy/{club_id}/recommendations",
        headers=headers,
        json={"task_key": "operating_spend", "amount": "250"},
    )
    assert over.status_code == 200, over.text
    refused = client.post(f"/api/owner/legacy/recommendations/{over.json()['id']}/execute", headers=headers)
    assert refused.json()["status"] == "blocked"

    approval = client.put(
        f"/api/owner/legacy/{club_id}/policies/operating_spend",
        headers=headers,
        json={"mode": "approval_required", "max_amount": "1000"},
    )
    assert approval.status_code == 200, approval.text
    waiting = client.post(
        f"/api/owner/legacy/{club_id}/recommendations",
        headers=headers,
        json={"task_key": "operating_spend", "amount": "40"},
    )
    assert waiting.status_code == 200, waiting.text
    center = client.get("/api/owner/control-center", headers=headers)
    assert center.status_code == 200, center.text
    kinds = [item["kind"] for item in center.json()["decisions"]]
    assert "legacy_approval" in kinds
    assert center.json()["legacy"]
