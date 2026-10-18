"""Exit gate for Club Legacy phase 5."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.admin_engine.service import AdminEngineService
from app.club_legacy.delegation import PRESEASON_RESPONSE, LegacyError, set_task
from app.club_legacy.full.phase5 import host_tournament, set_revenue_rule, settle_tournament
from app.club_legacy.models import (
    ClubLegacyAuditEvent,
    ClubLegacyManagerCommitment,
    ClubLegacyPreseasonEvent,
    ClubLegacyPreseasonOffer,
    ClubLegacyRevenueRule,
)
from app.club_legacy.operations import hire_executive, invite_preseason, open_window, respond_preseason, settle_preseason
from app.models.admin_rules import AdminCalendarRule, AdminFeatureFlag
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.gtex_economy import GtexLeagueStanding
from app.models.hosted_competition import HostedCompetitionStanding
from app.models.projections import CompetitionStandingProjection
from app.models.user import User
from app.models.wallet import LedgerTransaction
from app.models.world_super_cup_authority import WorldSuperCupStanding
from app.owner_console.models import OwnerMatch


def _enable(app) -> None:
    with app.state.session_factory() as session:
        AdminEngineService(session).seed_defaults()
        flag = session.scalar(select(AdminFeatureFlag).where(AdminFeatureFlag.feature_key == "club_legacy"))
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


def _outsider(session, email: str, username: str, club_name: str, slug: str) -> tuple[User, ClubProfile]:
    user = User(email=email, username=username, password_hash="hash", display_name=username)
    session.add(user)
    session.flush()
    club = ClubProfile(
        owner_user_id=user.id,
        club_name=club_name,
        short_name=club_name[:3].upper(),
        club_type=ClubType.COMMUNITY,
        lifecycle_status=ClubLifecycleStatus.ACTIVE,
        slug=slug,
        primary_color="#111111",
        secondary_color="#eeeeee",
        accent_color="#EA580C",
        country_code="GH",
        visibility="public",
    )
    session.add(club)
    session.flush()
    return user, club


def _standings(session) -> dict[str, int]:
    def count(model) -> int:
        return int(session.scalar(select(func.count()).select_from(model)) or 0)

    return {
        "gtex": count(GtexLeagueStanding),
        "hosted": count(HostedCompetitionStanding),
        "projection": count(CompetitionStandingProjection),
        "world": count(WorldSuperCupStanding),
    }


def test_offer_history_keeps_the_previous_terms(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        rival, other = _outsider(session, "p5-rival@gte.local", "p5_rival", "Opposite FC", "p5-opposite")
        window = open_window(session, name="June window", starts_on="2026-06-01", ends_on="2026-06-30")
        with pytest.raises(LegacyError) as outside:
            invite_preseason(
                session,
                window_id=window.id,
                from_club_id=club_id,
                to_club_id=other.id,
                match_on="2026-07-02",
                appearance_fee="400",
                user_id=admin.id,
            )
        assert outside.value.code == "outside_window"
        invite = invite_preseason(
            session,
            window_id=window.id,
            from_club_id=club_id,
            to_club_id=other.id,
            match_on="2026-06-12",
            appearance_fee="400",
            user_id=admin.id,
        )
        respond_preseason(
            session,
            invite_id=invite.id,
            user_id=rival.id,
            decision="counter",
            appearance_fee="650",
            match_on="2026-06-18",
        )
        session.refresh(invite)
        assert invite.appearance_fee == Decimal("650.00")
        assert invite.match_on == "2026-06-18"
        assert invite.status == "countered"
        offers = session.scalars(
            select(ClubLegacyPreseasonOffer)
            .where(ClubLegacyPreseasonOffer.invite_id == invite.id)
            .order_by(ClubLegacyPreseasonOffer.sequence.asc())
        ).all()
        assert [(row.appearance_fee, row.match_on, row.status) for row in offers] == [
            (Decimal("400.00"), "2026-06-12", "superseded"),
            (Decimal("650.00"), "2026-06-18", "open"),
        ]
        respond_preseason(session, invite_id=invite.id, user_id=admin.id, decision="accept")
        session.refresh(invite)
        assert invite.status == "accepted"
        rejected = invite_preseason(
            session,
            window_id=window.id,
            from_club_id=club_id,
            to_club_id=other.id,
            match_on="2026-06-21",
            appearance_fee="300",
            user_id=admin.id,
        )
        respond_preseason(session, invite_id=rejected.id, user_id=rival.id, decision="reject")
        first_history = session.scalars(
            select(ClubLegacyPreseasonEvent.status)
            .where(ClubLegacyPreseasonEvent.invite_id == invite.id)
            .order_by(ClubLegacyPreseasonEvent.sequence.asc())
        ).all()
        second_history = session.scalars(
            select(ClubLegacyPreseasonEvent.status)
            .where(ClubLegacyPreseasonEvent.invite_id == rejected.id)
            .order_by(ClubLegacyPreseasonEvent.sequence.asc())
        ).all()
        assert first_history == ["pending", "countered", "accepted"]
        assert second_history == ["pending", "rejected"]
        session.commit()
    answered = client.post(
        f"/api/owner/legacy/{club_id}/preseason/invites/{invite.id}/respond",
        headers=bootstrap_admin_headers,
        json={"decision": "reject"},
    )
    assert answered.status_code == 409


def test_tournament_shares_come_from_the_rule_and_settle_once(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        _, alpha = _outsider(session, "p5-alpha@gte.local", "p5_alpha", "Alpha FC", "p5-alpha")
        _, beta = _outsider(session, "p5-beta@gte.local", "p5_beta", "Beta FC", "p5-beta")
        window = open_window(session, name="Rule window", starts_on="2026-06-01", ends_on="2026-06-30")
        rule = set_revenue_rule(session, platform_share="0.20", host_share="0.50", participant_share="0.30")
        assert rule.version >= 1
        before = _standings(session)
        tournament = host_tournament(
            session,
            window_id=window.id,
            host_club_id=club_id,
            name="Harbour Cup",
            match_on="2026-06-11",
            user_id=admin.id,
            participant_club_ids=[alpha.id, beta.id],
        )
        first = settle_tournament(session, tournament_id=tournament.id, tv_pool="1000")
        second = settle_tournament(session, tournament_id=tournament.id, tv_pool="1000")
        assert first.id == second.id
        assert first.rule_version == rule.version
        assert first.platform_amount + first.host_amount + first.participant_amount == Decimal("1000.00")
        assert first.platform_amount == Decimal("200.00")
        assert first.host_amount == Decimal("500.00")
        assert first.participant_amount == Decimal("300.00")
        assert first.reputation_delta == 10
        assert first.audience == 200
        assert first.reputation_delta != first.audience
        assert _standings(session) == before
        host_payments = session.scalar(
            select(func.count())
            .select_from(LedgerTransaction)
            .where(LedgerTransaction.idempotency_key == f"tournament:{tournament.id}:host")
        )
        assert host_payments == 1
        session.commit()


def test_blocks_repeat_fixtures_and_gm_policy(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        rival, other = _outsider(session, "p5-block@gte.local", "p5_block", "Block FC", "p5-block")
        sister = ClubProfile(
            owner_user_id=admin.id,
            club_name="Sister FC",
            short_name="SIS",
            club_type=ClubType.COMMUNITY,
            lifecycle_status=ClubLifecycleStatus.ACTIVE,
            slug="p5-sister",
            primary_color="#111111",
            secondary_color="#eeeeee",
            accent_color="#EA580C",
            country_code="NG",
            visibility="public",
        )
        session.add(sister)
        session.flush()
        window = open_window(session, name="Block window", starts_on="2026-06-01", ends_on="2026-06-30")
        with pytest.raises(LegacyError) as related:
            invite_preseason(
                session,
                window_id=window.id,
                from_club_id=club_id,
                to_club_id=sister.id,
                match_on="2026-06-08",
                appearance_fee="400",
                user_id=admin.id,
            )
        assert related.value.code == "related_club_blocked"
        assert (
            session.scalar(
                select(func.count())
                .select_from(ClubLegacyAuditEvent)
                .where(ClubLegacyAuditEvent.action == "related_club_refused")
            )
            >= 1
        )
        session.add(
            AdminCalendarRule(
                rule_key="p5-block-june",
                title="Block",
                description="",
                world_cup_exclusive=True,
                active=True,
                priority=1,
                config_json={"blocked_ranges": [{"start": "2026-06-14", "end": "2026-06-16"}]},
            )
        )
        session.flush()
        with pytest.raises(LegacyError) as blocked:
            invite_preseason(
                session,
                window_id=window.id,
                from_club_id=club_id,
                to_club_id=other.id,
                match_on="2026-06-15",
                appearance_fee="400",
                user_id=admin.id,
            )
        assert blocked.value.code == "calendar_blocked"
        session.add(
            OwnerMatch(
                competition_id="p5-comp",
                round_number=1,
                home_club_id=club_id,
                away_club_id=other.id,
                home_name="Home",
                away_name="Away",
                status="scheduled",
                played_at=datetime(2026, 6, 19, tzinfo=timezone.utc),
            )
        )
        session.flush()
        with pytest.raises(LegacyError) as manager:
            invite_preseason(
                session,
                window_id=window.id,
                from_club_id=club_id,
                to_club_id=other.id,
                match_on="2026-06-19",
                appearance_fee="400",
                user_id=admin.id,
            )
        assert manager.value.code == "manager_unavailable"
        first = invite_preseason(
            session,
            window_id=window.id,
            from_club_id=club_id,
            to_club_id=other.id,
            match_on="2026-06-10",
            appearance_fee="500",
            user_id=admin.id,
        )
        respond_preseason(session, invite_id=first.id, user_id=rival.id, decision="accept")
        assert (
            session.scalar(
                select(func.count())
                .select_from(ClubLegacyManagerCommitment)
                .where(ClubLegacyManagerCommitment.match_on == "2026-06-10")
            )
            == 2
        )
        with pytest.raises(LegacyError) as committed:
            invite_preseason(
                session,
                window_id=window.id,
                from_club_id=club_id,
                to_club_id=other.id,
                match_on="2026-06-10",
                appearance_fee="500",
                user_id=admin.id,
            )
        assert committed.value.code == "manager_unavailable"
        paid = settle_preseason(session, invite_id=first.id, tv_pool="1000")
        again = settle_preseason(session, invite_id=first.id, tv_pool="1000")
        assert paid.id == again.id
        assert paid.platform_amount + paid.host_amount + paid.participant_amount == Decimal("1000.00")
        repeat_invite = invite_preseason(
            session,
            window_id=window.id,
            from_club_id=club_id,
            to_club_id=other.id,
            match_on="2026-06-22",
            appearance_fee="500",
            user_id=admin.id,
        )
        respond_preseason(session, invite_id=repeat_invite.id, user_id=rival.id, decision="accept")
        repeat = settle_preseason(session, invite_id=repeat_invite.id, tv_pool="1000")
        assert repeat.reputation_delta == 0
        assert repeat.reputation_delta < paid.reputation_delta
        assert repeat.audience == 100
        payments = session.scalar(
            select(func.count())
            .select_from(LedgerTransaction)
            .where(LedgerTransaction.idempotency_key == f"preseason:{first.id}:host")
        )
        assert payments == 1

        hire_executive(session, other.id, rival.id, role="gm", name="Ada Okonkwo", personality="cautious", wage="4000")
        set_task(session, other.id, PRESEASON_RESPONSE, mode="automatic", max_amount=Decimal("800"), actor_user_id=rival.id)
        inside = invite_preseason(
            session,
            window_id=window.id,
            from_club_id=club_id,
            to_club_id=other.id,
            match_on="2026-06-24",
            appearance_fee="700",
            user_id=admin.id,
        )
        staff = User(email="p5-gm@gte.local", username="p5_gm", password_hash="hash", display_name="GM")
        session.add(staff)
        session.flush()
        respond_preseason(session, invite_id=inside.id, user_id=staff.id, decision="accept", as_staff=True)
        session.refresh(inside)
        assert inside.status == "accepted"
        set_task(session, other.id, PRESEASON_RESPONSE, mode="owner_only", max_amount=None, actor_user_id=rival.id)
        owner_only = invite_preseason(
            session,
            window_id=window.id,
            from_club_id=club_id,
            to_club_id=other.id,
            match_on="2026-06-25",
            appearance_fee="300",
            user_id=admin.id,
        )
        with pytest.raises(LegacyError) as gm_blocked:
            respond_preseason(session, invite_id=owner_only.id, user_id=staff.id, decision="accept", as_staff=True)
        assert gm_blocked.value.code == "manual_only"
        set_task(session, other.id, PRESEASON_RESPONSE, mode="automatic", max_amount=Decimal("100"), actor_user_id=rival.id)
        over = invite_preseason(
            session,
            window_id=window.id,
            from_club_id=club_id,
            to_club_id=other.id,
            match_on="2026-06-26",
            appearance_fee="900",
            user_id=admin.id,
        )
        with pytest.raises(LegacyError) as over_cap:
            respond_preseason(session, invite_id=over.id, user_id=staff.id, decision="accept", as_staff=True)
        assert over_cap.value.code == "over_threshold"
        respond_preseason(session, invite_id=over.id, user_id=rival.id, decision="accept")
        session.refresh(over)
        assert over.status == "accepted"
        active = session.scalar(select(ClubLegacyRevenueRule).where(ClubLegacyRevenueRule.active.is_(True)))
        assert active is not None
        session.commit()
