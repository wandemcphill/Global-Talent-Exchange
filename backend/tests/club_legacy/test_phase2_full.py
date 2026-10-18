"""Full phase 2 exit gate: staff contracts, delegation, academy, and pre-season."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.admin_engine.service import AdminEngineService
from app.club_legacy.delegation import PRESEASON_RESPONSE, LegacyError, execute, recommend, set_task
from app.club_legacy.full.phase2 import (
    academy_plan,
    execute_as_executive,
    gm_respond_preseason,
    good_prospect_chance,
    hire_executive,
    pathway_recommendation,
    recruitment_report,
    roll_prospect,
    star_chance,
)
from app.club_legacy.models import ClubLegacyExecutive, ClubLegacyPolicy
from app.club_legacy.operations import invite_preseason, open_window, respond_preseason
from app.models.admin_rules import AdminFeatureFlag
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.user import User
from app.owner_console.models import OwnerSquadPlayer


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


def _rival(session) -> tuple[User, ClubProfile]:
    rival = User(email="phase2-rival@gte.local", username="phase2_rival", password_hash="hash", display_name="Rival")
    session.add(rival)
    session.flush()
    club = ClubProfile(
        owner_user_id=rival.id,
        club_name="Phase2 Rival",
        short_name="P2R",
        club_type=ClubType.COMMUNITY,
        lifecycle_status=ClubLifecycleStatus.ACTIVE,
        slug="phase2-rival",
        primary_color="#111111",
        secondary_color="#eeeeee",
        accent_color="#EA580C",
        country_code="GH",
        continent_code="AF",
        city_name="Accra",
        visibility="public",
    )
    session.add(club)
    session.flush()
    return rival, club


def test_quality_raises_the_odds_and_never_guarantees_a_star() -> None:
    assert star_chance(100) < 0.2
    assert good_prospect_chance(95) > good_prospect_chance(10)
    assert good_prospect_chance(100) < 1
    high = [roll_prospect(quality=95, prestige=40, seed=seed)["potential"] >= 75 for seed in range(250)]
    low = [roll_prospect(quality=10, prestige=40, seed=seed)["potential"] >= 75 for seed in range(250)]
    assert sum(high) > sum(low)
    assert sum(high) < 250
    stars = [roll_prospect(quality=100, prestige=90, seed=seed) for seed in range(300)]
    assert any(item["potential"] < 86 for item in stars)
    assert any(item["band"] == "high" for item in stars)
    assert all(item["guaranteed_star"] is False for item in stars)
    small = [roll_prospect(quality=20, prestige=0, seed=seed)["potential"] for seed in range(400)]
    assert any(item >= 80 for item in small)


def test_executives_presets_and_policy_recheck(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    hired = client.post(
        f"/api/owner/legacy/full/phase2/{club_id}/executives",
        headers=bootstrap_admin_headers,
        json={
            "role": "gm",
            "name": "Ada Okonkwo",
            "personality": "cautious",
            "wage": "4000",
            "contract_months": 36,
            "authority": "operations",
        },
    )
    assert hired.status_code == 200, hired.text
    body = hired.json()
    assert body["personality"] == "cautious"
    assert body["contract_months"] == 36
    assert body["authority"] == "operations"
    assert body["attributes"]["city_bonus"] == 10
    assert body["attributes"]["facility_level"] >= 20
    assert "owner_trust" in body["attributes"]
    again = client.post(
        f"/api/owner/legacy/full/phase2/{club_id}/executives",
        headers=bootstrap_admin_headers,
        json={"role": "gm", "name": "Second GM", "personality": "bold", "wage": "1000"},
    )
    assert again.status_code == 409
    assert again.json()["code"] == "role_filled"

    preset = client.post(
        f"/api/owner/legacy/full/phase2/{club_id}/presets/executive_led",
        headers=bootstrap_admin_headers,
    )
    assert preset.status_code == 200, preset.text
    override = client.put(
        f"/api/owner/legacy/full/phase2/{club_id}/tasks/operating_spend",
        headers=bootstrap_admin_headers,
        json={"mode": "owner_only", "max_amount": None},
    )
    assert override.status_code == 200, override.text
    with app.state.session_factory() as session:
        modes = {
            row.task_key: row.mode
            for row in session.scalars(select(ClubLegacyPolicy).where(ClubLegacyPolicy.club_id == club_id)).all()
        }
        assert modes["operating_spend"] == "owner_only"
        assert modes["recruitment"] == "automatic"
        assert modes["preseason_response"] == "automatic"
        admin = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        set_task(
            session, club_id, "operating_spend", mode="automatic", max_amount=Decimal("1000"), actor_user_id=admin.id
        )
        pending = recommend(
            session,
            club_id=club_id,
            user_id=admin.id,
            task_key="operating_spend",
            amount=Decimal("800"),
            reason="The GM wants this operating spend.",
            confidence=64,
            consequence="Cash falls by 800 if the current policy still allows it.",
        )
        assert pending.reason and pending.consequence
        assert pending.confidence < 100
        set_task(
            session, club_id, "operating_spend", mode="automatic", max_amount=Decimal("100"), actor_user_id=admin.id
        )
        with pytest.raises(LegacyError) as blocked:
            execute_as_executive(session, recommendation_id=pending.id, actor_user_id=admin.id)
        assert blocked.value.code == "over_threshold"
        assert pending.status == "recommended"
        owner = execute(session, recommendation_id=pending.id, actor_user_id=admin.id)
        assert owner.status == "blocked"
        session.commit()


def test_academy_and_pathways_do_not_bypass_the_owner(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        owner_run = academy_plan(session, club_id, admin.id, seed=7)
        assert owner_run["report"].role == "owner"
        assert "Not a guaranteed star" in owner_run["report"].summary
        assert owner_run["report"].confidence < 100
        assert str(owner_run["cost"]) in owner_run["report"].consequence
        assert owner_run["recommendation"].status == "recommended"
        assert (
            "suit" in owner_run["recommendation"].reason.lower()
            or "quality" in owner_run["recommendation"].reason.lower()
        )
        hire_executive(
            session, club_id, admin.id, role="hoyd", name="Ifeanyi Bello", personality="youth-focused", wage="3000"
        )
        hoyd_run = recruitment_report(session, club_id, admin.id)
        assert hoyd_run.role == "hoyd"
        assert hoyd_run.confidence < 100
        player = session.scalar(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id))
        before = player.status
        pathway = pathway_recommendation(
            session,
            club_id,
            admin.id,
            kind="promotion",
            player_id=player.id,
            amount="500",
            note="Ready for the first team, with uncertainty on minutes.",
        )
        session.refresh(player)
        assert player.status == before
        assert pathway.status == "recommended"
        assert pathway.confidence < 100
        for kind in ("loan", "sale"):
            other = pathway_recommendation(session, club_id, admin.id, kind=kind, player_id=player.id, amount="200")
            assert other.status == "recommended"
        session.refresh(player)
        assert player.status == before
        set_task(session, club_id, "academy_promotion", mode="owner_only", max_amount=None, actor_user_id=admin.id)
        with pytest.raises(LegacyError) as refused:
            execute_as_executive(session, recommendation_id=pathway.id, actor_user_id=admin.id)
        assert refused.value.code == "manual_only"
        assert pathway.status == "recommended"
        session.commit()


def test_gm_preseason_stays_inside_the_current_policy(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        rival, rival_club = _rival(session)
        window = open_window(session, name="Phase2 window", starts_on="2026-06-01", ends_on="2026-06-30")
        owner_invite = invite_preseason(
            session,
            window_id=window.id,
            from_club_id=rival_club.id,
            to_club_id=club_id,
            match_on="2026-06-04",
            appearance_fee="400",
            user_id=rival.id,
        )
        responded = respond_preseason(session, invite_id=owner_invite.id, user_id=admin.id, decision="accept")
        assert responded.status == "accepted"
        delegated = invite_preseason(
            session,
            window_id=window.id,
            from_club_id=rival_club.id,
            to_club_id=club_id,
            match_on="2026-06-11",
            appearance_fee="400",
            user_id=rival.id,
        )
        current_gm = session.scalar(
            select(ClubLegacyExecutive).where(ClubLegacyExecutive.club_id == club_id, ClubLegacyExecutive.role == "gm")
        )
        if current_gm is not None:
            session.delete(current_gm)
            session.flush()
        with pytest.raises(LegacyError) as missing_gm:
            gm_respond_preseason(session, invite_id=delegated.id, user_id=admin.id, decision="accept")
        assert missing_gm.value.code == "gm_required"
        hire_executive(session, club_id, admin.id, role="gm", name="Ada Okonkwo", personality="cautious", wage="4000")
        set_task(
            session, club_id, PRESEASON_RESPONSE, mode="automatic", max_amount=Decimal("1000"), actor_user_id=admin.id
        )
        with pytest.raises(LegacyError) as cheap:
            gm_respond_preseason(session, invite_id=delegated.id, user_id=admin.id, decision="accept")
        assert cheap.value.code == "below_minimum_fee"
        set_task(
            session, club_id, PRESEASON_RESPONSE, mode="automatic", max_amount=Decimal("100"), actor_user_id=admin.id
        )
        set_task(session, club_id, PRESEASON_RESPONSE, mode="owner_only", max_amount=None, actor_user_id=admin.id)
        with pytest.raises(LegacyError) as owner_only:
            gm_respond_preseason(session, invite_id=delegated.id, user_id=admin.id, decision="accept")
        assert owner_only.value.code == "manual_only"
        session.refresh(delegated)
        assert delegated.status == "pending"
        set_task(
            session, club_id, PRESEASON_RESPONSE, mode="automatic", max_amount=Decimal("100"), actor_user_id=admin.id
        )
        acted = gm_respond_preseason(session, invite_id=delegated.id, user_id=admin.id, decision="accept")
        assert acted["acted"] is True
        assert acted["invite_status"] == "accepted"
        session.commit()
