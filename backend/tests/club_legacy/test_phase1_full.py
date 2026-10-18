"""Full phase 1 exit gate: location, cap, ledger, audit, settings, separate ratings."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.admin_engine.service import DEFAULT_FEATURE_FLAGS, AdminEngineService
from app.auth.service import AuthError, AuthService
from app.club_legacy.delegation import LegacyError, set_task
from app.club_legacy.full.phase1 import (
    backfill_locations,
    current_settings,
    post_economic,
    preseason_split,
    resolve_location,
    transfer_fee,
    update_settings,
)
from app.club_legacy.models import ClubLegacyAuditEvent, ClubLegacySettings
from app.club_legacy.operations import purchase_asset
from app.club_legacy.ratings import development_score, prestige_score
from app.clubs.ownership_cap import MAX_OWNED_CLUBS, assert_can_acquire_club, count_owned_clubs
from app.models.admin_rules import AdminFeatureFlag
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.user import PublicAccountType, User
from app.models.wallet import LedgerTransaction
from app.owner_console import ledger as owner_ledger
from app.owner_console.models import OwnerClubState
from app.owner_console.service import OwnerError, _create_starter_profile


def _enable(app) -> None:
    with app.state.session_factory() as session:
        AdminEngineService(session).seed_defaults()
        flag = session.scalar(select(AdminFeatureFlag).where(AdminFeatureFlag.feature_key == "club_legacy"))
        flag.enabled = True
        session.commit()


def _claim(client, headers) -> str:
    response = client.post(
        "/api/owner/clubs/claim",
        headers=headers,
        json={"city_name": "Lagos", "country_code": "NG"},
    )
    assert response.status_code == 200, response.text
    return response.json()["club_id"]


def test_flag_stays_off_until_enabled() -> None:
    seed = next(item for item in DEFAULT_FEATURE_FLAGS if item["feature_key"] == "club_legacy")
    assert seed["enabled"] is False


def test_city_country_and_continent_are_validated_together(client, app):
    del client
    city, country, continent = resolve_location(city_name="Lagos", country_code="ng")
    assert (city, country, continent) == ("Lagos", "NG", "AF")
    assert resolve_location(city_name="Nowhere", country_code="ZZ")[2] is None
    with pytest.raises(LegacyError) as mismatch:
        resolve_location(city_name="Lagos", country_code="NG", continent_code="EU")
    assert mismatch.value.code == "location_mismatch"
    with pytest.raises(LegacyError):
        resolve_location(city_name="Nowhere", country_code="ZZ", continent_code="AF")

    with app.state.session_factory() as session:
        user = User(
            email="legacy-location@gte.local",
            username="legacy_location",
            password_hash="hash",
            display_name="Legacy Location",
            account_type=PublicAccountType.USER,
        )
        session.add(user)
        session.flush()
        created = AuthService().create_explicit_club_profile(
            session,
            user,
            club_name="Located FC",
            short_name="LOC",
            club_type=ClubType.COMMUNITY,
            country_code="NG",
            region_name=None,
            city_name="Lagos",
            crest_asset_ref=None,
            primary_color="#0F766E",
            secondary_color="#F8FAFC",
        )
        assert created.city_name == "Lagos"
        assert created.country_code == "NG"
        assert created.continent_code == "AF"
        with pytest.raises(AuthError) as created_mismatch:
            AuthService().create_explicit_club_profile(
                session,
                user,
                club_name="Wrong Continent FC",
                short_name="WRNG",
                club_type=ClubType.COMMUNITY,
                country_code="NG",
                region_name=None,
                city_name="Lagos",
                crest_asset_ref=None,
                primary_color="#0F766E",
                secondary_color="#F8FAFC",
                continent_code="EU",
            )
        assert "continent" in str(created_mismatch.value).lower()
        with pytest.raises(OwnerError) as claimed:
            _create_starter_profile(session, user, city_name="Lagos", country_code="NG", continent_code="EU")
        assert claimed.value.code == "location_mismatch"
        unknown = _create_starter_profile(session, user, city_name="Nowhere", country_code="ZZ")
        profile = session.get(ClubProfile, unknown.id)
        assert profile.continent_code is None
        assert profile.city_name == "Nowhere"
        session.commit()


def test_existing_clubs_backfill_without_inventing_a_continent(client, app):
    del client
    with app.state.session_factory() as session:
        user = User(
            email="legacy-backfill@gte.local",
            username="legacy_backfill",
            password_hash="hash",
            display_name="Backfill",
            account_type=PublicAccountType.USER,
        )
        session.add(user)
        session.flush()

        def club(slug: str, country: str | None, continent: str | None) -> ClubProfile:
            row = ClubProfile(
                owner_user_id=user.id,
                club_name=slug,
                short_name=slug[:4].upper(),
                club_type=ClubType.COMMUNITY,
                lifecycle_status=ClubLifecycleStatus.ACTIVE,
                slug=slug,
                primary_color="#111111",
                secondary_color="#eeeeee",
                accent_color="#EA580C",
                country_code=country,
                continent_code=continent,
                visibility="public",
            )
            session.add(row)
            return row

        germany = club("backfill-germany", "DE", None)
        unknown = club("backfill-unknown", "ZZ", None)
        already = club("backfill-kept", "FR", "AF")
        session.flush()
        updated = backfill_locations(session)
        assert updated >= 1
        session.refresh(germany)
        session.refresh(unknown)
        session.refresh(already)
        assert germany.continent_code == "EU"
        assert unknown.continent_code is None
        assert already.continent_code == "AF"
        assert backfill_locations(session) == 0
        session.commit()


def test_three_club_cap_stays_on_the_server(client, app):
    del client
    with app.state.session_factory() as session:
        user = User(
            email="legacy-full-cap@gte.local",
            username="legacy_full_cap",
            password_hash="hash",
            display_name="Full Cap",
            account_type=PublicAccountType.USER,
        )
        session.add(user)
        session.flush()
        service = AuthService()
        for index in range(MAX_OWNED_CLUBS):
            service.create_explicit_club_profile(
                session,
                user,
                club_name=f"Full Cap {index}",
                short_name=f"F{index}",
                club_type=ClubType.COMMUNITY,
                country_code="NG",
                region_name=None,
                city_name="Lagos",
                crest_asset_ref=None,
                primary_color="#0F766E",
                secondary_color="#F8FAFC",
            )
        assert count_owned_clubs(session, user.id) == 3
        with pytest.raises(Exception):
            assert_can_acquire_club(session, user.id)
        with pytest.raises(AuthError):
            service.create_explicit_club_profile(
                session,
                user,
                club_name="Full Cap 4",
                short_name="F4",
                club_type=ClubType.COMMUNITY,
                country_code="NG",
                region_name=None,
                city_name="Lagos",
                crest_asset_ref=None,
                primary_color="#0F766E",
                secondary_color="#F8FAFC",
            )
        session.commit()


def test_economic_post_and_audit_happen_once(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        source = owner_ledger.wallet_account(session, owner_ledger.club_account(club_id), owner_ledger.GTEX)
        destination = owner_ledger.wallet_account(session, owner_ledger.PLATFORM_FEES, owner_ledger.GTEX)
        post_economic(
            session,
            idempotency_key="phase1-full-once",
            source=source,
            destination=destination,
            amount=Decimal("15.00"),
            actor_user_id=admin.id,
            club_id=club_id,
            action="economic_action",
            description="Phase 1 full idempotency",
        )
        post_economic(
            session,
            idempotency_key="phase1-full-once",
            source=source,
            destination=destination,
            amount=Decimal("15.00"),
            actor_user_id=admin.id,
            club_id=club_id,
            action="economic_action",
            description="Phase 1 full idempotency",
        )
        session.commit()
        assert (
            session.scalar(
                select(func.count())
                .select_from(LedgerTransaction)
                .where(LedgerTransaction.idempotency_key == "phase1-full-once")
            )
            == 1
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(ClubLegacyAuditEvent)
                .where(ClubLegacyAuditEvent.idempotency_key == "audit:phase1-full-once")
            )
            == 1
        )
        set_task(session, club_id, "operating_spend", mode="owner_only", max_amount=None, actor_user_id=admin.id)
        session.commit()
        assert (
            session.scalar(
                select(func.count())
                .select_from(ClubLegacyAuditEvent)
                .where(ClubLegacyAuditEvent.club_id == club_id, ClubLegacyAuditEvent.action == "policy_set")
            )
            >= 1
        )


def test_settings_row_drives_fee_caps_and_preseason_shares(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    headers = bootstrap_admin_headers
    updated = client.put(
        "/api/owner/legacy/full/phase1/settings",
        headers=headers,
        json={
            "transfer_fee_rate": "0.10",
            "inventory_caps": {"jet": 1, "coach": 2},
            "preseason_shares": {
                "foundation": "0.30",
                "growing": "0.10",
                "established": "0.50",
                "elite": "0.60",
                "legacy": "0.70",
                "host_cut_of_club_pool": "0.40",
                "gift_foundation": "0.40",
            },
        },
    )
    assert updated.status_code == 200, updated.text
    with app.state.session_factory() as session:
        assert transfer_fee(session, "1000") == Decimal("100.00")
        split = preseason_split(session, stage="growing", tv_pool="1000", gift_pool="0")
        assert split["club_rate"] == Decimal("0.1000")
        assert split["platform"] + split["host"] + split["participants"] == Decimal("1000.00")
        assert split["platform"] == Decimal("900.00")
        admin = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
        before_prestige = prestige_score(session, club_id)
        before_development = development_score(state.facilities_json)
        purchase_asset(
            session,
            club_id=club_id,
            user_id=admin.id,
            sku="gtex-jet-harbour",
            owner_class="club",
            idempotency_key="settings-jet",
        )
        with pytest.raises(LegacyError) as capped:
            purchase_asset(
                session,
                club_id=club_id,
                user_id=admin.id,
                sku="gtex-jet-harbour",
                owner_class="club",
                idempotency_key="settings-jet-2",
            )
        assert capped.value.code == "inventory_cap"
        session.refresh(state)
        assert prestige_score(session, club_id) == before_prestige
        assert development_score(state.facilities_json) == before_development
        ratings = client.get(f"/api/owner/legacy/full/phase1/{club_id}/ratings", headers=headers)
        assert ratings.status_code == 200, ratings.text
        body = ratings.json()
        assert body["prestige"] == before_prestige
        assert body["development"] == before_development
        assert body["financial_strength"] != body["prestige"]
        update_settings(
            session,
            actor_user_id=admin.id,
            transfer_fee_rate="0.05",
            inventory_caps={"jet": 5, "coach": 10},
            preseason_shares={
                "foundation": "0.30",
                "growing": "0.40",
                "established": "0.50",
                "elite": "0.60",
                "legacy": "0.70",
                "host_cut_of_club_pool": "0.40",
                "gift_foundation": "0.40",
            },
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(ClubLegacyAuditEvent)
                .where(ClubLegacyAuditEvent.action == "settings_updated")
            )
            >= 1
        )
        assert session.scalar(select(func.count()).select_from(ClubLegacySettings)) == 1
        assert current_settings(session).transfer_fee_rate == Decimal("0.0500")
        session.commit()


def test_migration_upgrade_can_run_twice(app):
    import importlib

    from alembic.operations import Operations
    from alembic.runtime.migration import MigrationContext

    migration = importlib.import_module("migrations.versions.20261018_0141_club_legacy_full_p123")
    with app.state.session_factory() as session:
        connection = session.connection()
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.upgrade()
            migration.upgrade()
        session.commit()
        assert (
            session.scalar(select(ClubLegacySettings).where(ClubLegacySettings.settings_key == "current")) is not None
        )
