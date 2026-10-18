"""Phase 9 exit gate: seasons, subsystem flags, metrics, rollback, and catalogue reads."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select

from app.admin_engine.service import DEFAULT_FEATURE_FLAGS, AdminEngineService
from app.club_legacy.full import phase9
from app.club_legacy.ledger import post_club_legacy_transfer
from app.club_legacy.operations import (
    invite_preseason,
    load_catalogue,
    metrics,
    open_case,
    open_window,
    respond_preseason,
    seed_catalogue,
    settle_preseason,
)
from app.models.admin_rules import AdminFeatureFlag
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.user import User
from app.models.wallet import LedgerTransaction
from app.owner_console import ledger

SUBSYSTEMS = (
    "club_legacy_market",
    "club_legacy_preseason",
    "club_legacy_sponsors",
    "club_legacy_governance",
)


def _set_flags(app, enabled: dict[str, bool]) -> None:
    with app.state.session_factory() as session:
        AdminEngineService(session).seed_defaults()
        for key, is_on in enabled.items():
            flag = session.scalar(select(AdminFeatureFlag).where(AdminFeatureFlag.feature_key == key))
            assert flag is not None
            flag.enabled = is_on
        session.commit()


def _claim(client, headers, city: str = "Lagos") -> str:
    response = client.post(
        "/api/owner/clubs/claim", headers=headers, json={"city_name": city, "country_code": "NG"}
    )
    assert response.status_code == 200, response.text
    return response.json()["club_id"]


def _all_on() -> dict[str, bool]:
    return {"club_legacy": True, **{key: True for key in SUBSYSTEMS}}


def test_subsystem_flags_default_off() -> None:
    seeded = {item["feature_key"]: item for item in DEFAULT_FEATURE_FLAGS}
    for key in ("club_legacy", *SUBSYSTEMS):
        assert seeded[key]["enabled"] is False


def test_three_tiers_simulate_at_least_three_seasons(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    with app.state.session_factory() as session:
        ledger_before = session.scalar(select(func.count()).select_from(LedgerTransaction))
        runs = {
            tier: phase9.simulate_seasons(session, club_id, 3, tier, seed=1)
            for tier in ("small", "established", "elite")
        }
        for tier, result in runs.items():
            assert result["seasons_run"] == 3
            assert len(result["seasons"]) == 3
            assert result["reputation"] == result["seasons"][-1]["reputation"]
            assert "revenue" in result
            assert result["youth_intake"]
            assert isinstance(result["sanction_count"], int)
            assert sum(row["sanction_count"] for row in result["seasons"]) == result["sanction_count"]
            assert all("potential" in prospect for prospect in result["youth_intake"])
            assert tier == result["tier"]
        small = runs["small"]
        established = runs["established"]
        elite = runs["elite"]
        assert small["reputation"] > small["reputation_start"]
        assert Decimal(small["revenue"]) < Decimal(established["revenue"]) < Decimal(elite["revenue"])
        assert Decimal(small["revenue"]) < Decimal(elite["seasons"][0]["revenue"])
        other = phase9.simulate_seasons(session, club_id, 3, "small", seed=2)
        same = phase9.simulate_seasons(session, club_id, 3, "small", seed=2)
        assert [item["potential"] for item in other["youth_intake"]] == [
            item["potential"] for item in same["youth_intake"]
        ]
        assert [item["potential"] for item in other["youth_intake"]] != [
            item["potential"] for item in small["youth_intake"]
        ]
        high = False
        for seed in range(40):
            draw = phase9.simulate_seasons(session, club_id, 3, "small", seed=seed)
            if any(item["potential"] >= 85 for item in draw["youth_intake"]):
                high = True
                break
        assert high
        assert session.scalar(select(func.count()).select_from(LedgerTransaction)) == ledger_before
        session.commit()


def test_one_subsystem_flag_hides_only_that_subsystem(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _set_flags(app, _all_on())
    paths = {
        "club_legacy_market": f"/api/owner/legacy/{club_id}/market/supply",
        "club_legacy_preseason": f"/api/owner/legacy/{club_id}/preseason/invitations",
        "club_legacy_sponsors": f"/api/owner/legacy/{club_id}/sponsors/contracts",
        "club_legacy_governance": f"/api/owner/legacy/{club_id}/governance/cases",
    }
    for path in paths.values():
        opened = client.get(path, headers=bootstrap_admin_headers)
        assert opened.status_code == 200, opened.text
    manager = client.post(
        f"/api/owner/legacy/{club_id}/managers",
        headers=bootstrap_admin_headers,
        json={"name": "Flag Manager", "personality": "calm", "ambition": 5, "wage_expectation": "2000"},
    )
    assert manager.status_code == 200, manager.text
    for key, path in paths.items():
        enabled = _all_on()
        enabled[key] = False
        _set_flags(app, enabled)
        hidden = client.get(path, headers=bootstrap_admin_headers)
        assert hidden.status_code == 404, hidden.text
        for other_key, other_path in paths.items():
            if other_key == key:
                continue
            still = client.get(other_path, headers=bootstrap_admin_headers)
            assert still.status_code == 200, still.text
        page = client.get(f"/api/owner/legacy/{club_id}/page", headers=bootstrap_admin_headers)
        assert page.status_code == 200, page.text
    _set_flags(app, {"club_legacy": False, **{key: True for key in SUBSYSTEMS}})
    for path in (*paths.values(), f"/api/owner/legacy/{club_id}/page"):
        hidden = client.get(path, headers=bootstrap_admin_headers)
        assert hidden.status_code == 404, hidden.text
    seasons = client.post(
        f"/api/owner/legacy/{club_id}/seasons/simulate",
        headers=bootstrap_admin_headers,
        json={"seasons": 3, "tier": "small", "seed": 1},
    )
    assert seasons.status_code == 404, seasons.text


def test_metrics_cover_invitations_acceptance_settlements_supply_cases_and_failures(
    client, bootstrap_admin_headers, app
):
    club_id = _claim(client, bootstrap_admin_headers)
    with app.state.session_factory() as session:
        admin = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        rival = User(email="phase9-rival@gte.local", username="phase9_rival", password_hash="hash", display_name="Rival")
        session.add(rival)
        session.flush()
        other = ClubProfile(
            owner_user_id=rival.id,
            club_name="Phase9 Opposite",
            short_name="P9O",
            club_type=ClubType.COMMUNITY,
            lifecycle_status=ClubLifecycleStatus.ACTIVE,
            slug="phase9-opposite",
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
        before = metrics(session)
        window = open_window(session, name="Phase 9 window", starts_on="2026-06-01", ends_on="2026-06-30")
        invite = invite_preseason(
            session,
            window_id=window.id,
            from_club_id=club_id,
            to_club_id=other.id,
            match_on="2026-06-12",
            appearance_fee="400",
            user_id=admin.id,
        )
        respond_preseason(session, invite_id=invite.id, user_id=rival.id, decision="accept")
        settlement = settle_preseason(session, invite_id=invite.id, tv_pool="1000")
        open_case(
            session,
            club_id=club_id,
            rule_code="late_wages",
            allegation="Wages slipped",
            evidence="Payroll",
        )
        phase9.record_showroom_failure(session, club_id=club_id, reason="Preview file missing")
        report = metrics(session)
        assert report["invitation_count"] == before["invitation_count"] + 1
        assert report["acceptance"] == before["acceptance"] + 1
        assert report["open_cases"] == before["open_cases"] + 1
        assert report["showroom_failure_count"] == before["showroom_failure_count"] + 1
        totals = report["settlement_totals"]
        combined = Decimal(totals["platform"]) + Decimal(totals["host"]) + Decimal(totals["participant"])
        assert Decimal(totals["combined"]) == combined
        assert combined >= settlement.platform_amount + settlement.host_amount + settlement.participant_amount
        assert report["supply_remaining"]
        assert "rollback" in report
        session.commit()


def test_turning_the_flag_off_hides_routes_and_keeps_the_ledger_row(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _set_flags(app, _all_on())
    with app.state.session_factory() as session:
        source = ledger.wallet_account(session, ledger.PLATFORM_SPONSORS, ledger.GTEX)
        destination = ledger.wallet_account(session, ledger.club_account(club_id), ledger.GTEX)
        post_club_legacy_transfer(
            session,
            idempotency_key="club-legacy-rollback-stays",
            source=source,
            destination=destination,
            amount=Decimal("15.00"),
            description="Rollback must not delete this",
        )
        session.commit()
        before = session.scalar(
            select(func.count())
            .select_from(LedgerTransaction)
            .where(LedgerTransaction.idempotency_key == "club-legacy-rollback-stays")
        )
        assert before == 1
    _set_flags(app, {"club_legacy": False, **{key: True for key in SUBSYSTEMS}})
    for path in (
        f"/api/owner/legacy/{club_id}/page",
        f"/api/owner/legacy/{club_id}/market/supply",
        f"/api/owner/legacy/{club_id}/preseason/invitations",
        f"/api/owner/legacy/{club_id}/sponsors/contracts",
        f"/api/owner/legacy/{club_id}/governance/cases",
        f"/api/owner/legacy/{club_id}/metrics",
    ):
        hidden = client.get(path, headers=bootstrap_admin_headers)
        assert hidden.status_code == 404, hidden.text
    with app.state.session_factory() as session:
        row = session.scalar(
            select(LedgerTransaction).where(LedgerTransaction.idempotency_key == "club-legacy-rollback-stays")
        )
        assert row is not None
        assert (
            session.scalar(
                select(func.count())
                .select_from(LedgerTransaction)
                .where(LedgerTransaction.idempotency_key == "club-legacy-rollback-stays")
            )
            == 1
        )


def test_catalogue_reads_do_not_change_supply(client, bootstrap_admin_headers, app):
    _claim(client, bootstrap_admin_headers)
    with app.state.session_factory() as session:
        seed_catalogue(session)
        before = phase9.supply_snapshot(session)
        loaded = load_catalogue(session, 40)
        after = phase9.supply_snapshot(session)
        assert loaded["rounds"] == 40
        assert loaded["supply_unchanged"] is True
        assert loaded["supply"] == before == after
        assert before
        session.commit()
