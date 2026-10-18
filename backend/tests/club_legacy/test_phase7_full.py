"""Phase 7 exit gate: terms, seeds, promises, gifts, poaching, and retention."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select

from app.admin_engine.service import AdminEngineService
from app.club_legacy.full import phase7
from app.club_legacy.operations import decide_manager_offer, offer_score
from app.models.admin_rules import AdminFeatureFlag
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.user import User
from app.models.wallet import LedgerTransaction
from app.owner_console import ledger


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


def _rival(session, slug: str) -> tuple[User, ClubProfile]:
    user = User(email=f"{slug}@gte.local", username=slug, password_hash="hash", display_name=slug)
    session.add(user)
    session.flush()
    club = ClubProfile(
        owner_user_id=user.id,
        club_name=slug,
        short_name=slug[:4].upper(),
        club_type=ClubType.COMMUNITY,
        lifecycle_status=ClubLifecycleStatus.ACTIVE,
        slug=slug,
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
    return user, club


def test_terms_can_be_accepted_rejected_or_countered_and_history_keeps_both(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        manager = phase7.register_manager(
            session,
            name="Tunde Bakare",
            personality="demanding",
            ambition=14,
            wage_expectation="8000",
            seed=3,
        )
        assert manager.personality == "demanding"
        assert manager.ambition == 14
        assert manager.wage_expectation == Decimal("8000.00")
        accepted = phase7.present_offer(
            session,
            club_id=club_id,
            user_id=admin.id,
            manager_id=manager.id,
            wage="9000",
            contract_length=3,
            role="head_coach",
            prestige=30,
            seed=1,
        )
        assert accepted.contract_length == 3
        assert accepted.role == "head_coach"
        phase7.respond_to_offer(session, offer_id=accepted.id, decision="accept")
        rejected = phase7.present_offer(
            session,
            club_id=club_id,
            user_id=admin.id,
            manager_id=manager.id,
            wage="4000",
            contract_length=1,
            role="assistant",
            prestige=10,
            seed=2,
        )
        phase7.respond_to_offer(session, offer_id=rejected.id, decision="reject")
        original = phase7.present_offer(
            session,
            club_id=club_id,
            user_id=admin.id,
            manager_id=manager.id,
            wage="6000",
            contract_length=2,
            role="head_coach",
            prestige=20,
            seed=4,
        )
        counter = phase7.respond_to_offer(
            session,
            offer_id=original.id,
            decision="counter",
            wage="7500",
            contract_length=4,
            role="director",
        )
        history = phase7.offer_history(session, manager.id)
        identities = {item.id for item in history}
        assert original.id in identities
        assert counter.id in identities
        assert counter.parent_offer_id == original.id
        assert counter.id != original.id
        assert Decimal(counter.wage) != Decimal(original.wage)
        assert counter.contract_length != original.contract_length
        assert counter.role != original.role
        assert {item.outcome for item in history} >= {"accepted", "rejected", "countered", "counter"}
        session.commit()

    created = client.post(
        f"/api/owner/legacy/{club_id}/managers",
        headers=bootstrap_admin_headers,
        json={"name": "Ada Okonkwo", "personality": "cautious", "ambition": 8, "wage_expectation": "5000"},
    )
    assert created.status_code == 200, created.text
    assert created.json()["personality"] == "cautious"
    offered = client.post(
        f"/api/owner/legacy/{club_id}/managers/{created.json()['id']}/offers",
        headers=bootstrap_admin_headers,
        json={"wage": "5500", "contract_length": 2, "role": "head_coach", "prestige": 12, "seed": 1},
    )
    assert offered.status_code == 200, offered.text
    assert offered.json()["outcome"] == "pending"


def test_the_same_rich_wage_is_accepted_for_one_seed_and_rejected_for_another(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    wage = "80000"
    accepted_seeds = []
    rejected_seeds = []
    money_scores = set()
    for seed in range(60):
        money, _project, total = offer_score(wage, 30, 12, seed)
        money_scores.add(money)
        (accepted_seeds if total >= 70 else rejected_seeds).append(seed)
    assert accepted_seeds
    assert rejected_seeds
    assert len(money_scores) == 1
    assert money_scores.pop() > offer_score("1000", 30, 12, accepted_seeds[0])[0]
    with app.state.session_factory() as session:
        admin = _admin(session)
        accepted = decide_manager_offer(
            session,
            club_id=club_id,
            user_id=admin.id,
            candidate_name="Same Wage",
            wage=wage,
            prestige=30,
            ambition=12,
            seed=accepted_seeds[0],
        )
        rejected = decide_manager_offer(
            session,
            club_id=club_id,
            user_id=admin.id,
            candidate_name="Same Wage",
            wage=wage,
            prestige=30,
            ambition=12,
            seed=rejected_seeds[0],
        )
        assert accepted.outcome == "accepted"
        assert rejected.outcome == "declined"
        assert accepted.wage == rejected.wage
        assert accepted.money_score == rejected.money_score
        assert accepted.money_score > 0
        assert phase7.offer_score(wage, 30, 12, accepted_seeds[0]) == offer_score(wage, 30, 12, accepted_seeds[0])
        session.commit()


def test_a_broken_promise_lowers_the_score_the_next_offer_reads(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    with app.state.session_factory() as session:
        admin = _admin(session)
        manager = phase7.register_manager(
            session, name="Ife Bello", personality="loyal", ambition=8, wage_expectation="4000"
        )
        before = phase7.present_offer(
            session,
            club_id=club_id,
            user_id=admin.id,
            manager_id=manager.id,
            wage="7000",
            contract_length=2,
            role="head_coach",
            prestige=24,
            seed=6,
        )
        promise = phase7.make_promise(
            session, club_id=club_id, user_id=admin.id, subject="Training ground", manager_id=manager.id
        )
        phase7.resolve_promise(session, promise_id=promise.id, kept=False)
        session.refresh(manager)
        assert manager.relationship_score == 35
        assert promise.trust < 50
        after = phase7.present_offer(
            session,
            club_id=club_id,
            user_id=admin.id,
            manager_id=manager.id,
            wage="7000",
            contract_length=2,
            role="head_coach",
            prestige=24,
            seed=6,
        )
        assert after.relationship_score == manager.relationship_score
        assert after.total_score < before.total_score
        assert after.money_score == before.money_score
        session.commit()


def test_a_gift_moves_the_relationship_by_a_capped_step_below_the_maximum(client, bootstrap_admin_headers, app):
    _claim(client, bootstrap_admin_headers)
    with app.state.session_factory() as session:
        manager = phase7.register_manager(
            session, name="Ngozi Ade", personality="warm", ambition=6, wage_expectation="3000"
        )
        manager.relationship_score = 40
        session.flush()
        modest = phase7.record_gift(session, manager_id=manager.id)
        assert modest.delta == phase7.GIFT_DELTA_CAP
        assert modest.score_after == 44
        assert modest.score_after < 100
        manager.relationship_score = 98
        session.flush()
        near_max = phase7.record_gift(session, manager_id=manager.id)
        assert near_max.delta <= phase7.GIFT_DELTA_CAP
        assert near_max.score_after == 99
        assert near_max.score_after < 100
        session.commit()


def test_poaching_an_employed_manager_posts_twenty_percent_once(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    with app.state.session_factory() as session:
        admin = _admin(session)
        rival_user, rival = _rival(session, "phase7-employer")
        manager = phase7.register_manager(
            session, name="Sena Boateng", personality="ambitious", ambition=11, wage_expectation="2000"
        )
        hired = phase7.present_offer(
            session,
            club_id=rival.id,
            user_id=rival_user.id,
            manager_id=manager.id,
            wage="5000",
            contract_length=3,
            role="head_coach",
            prestige=15,
            seed=1,
        )
        phase7.respond_to_offer(session, offer_id=hired.id, decision="accept")
        session.refresh(manager)
        assert manager.status == "employed"
        before = ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)
        phase7.poach_manager(session, manager_id=manager.id, from_club_id=club_id, user_id=admin.id)
        after = ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)
        expected = phase7.poach_compensation(manager.wage)
        assert expected == (Decimal(manager.wage) * phase7.POACH_SHARE).quantize(Decimal("0.01"))
        assert before - after == expected
        key = f"compensation:manager:{manager.id}:{club_id}"
        count = session.scalar(
            select(func.count()).select_from(LedgerTransaction).where(LedgerTransaction.idempotency_key == key)
        )
        assert count == 1
        phase7.poach_manager(session, manager_id=manager.id, from_club_id=club_id, user_id=admin.id)
        assert ledger.balance(session, ledger.club_account(club_id), ledger.GTEX) == after
        assert (
            session.scalar(
                select(func.count()).select_from(LedgerTransaction).where(LedgerTransaction.idempotency_key == key)
            )
            == 1
        )
        session.commit()


def test_retention_uses_the_appointment_score_and_a_happy_manager_can_refuse(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    with app.state.session_factory() as session:
        admin = _admin(session)
        manager = phase7.register_manager(
            session, name="Kwame Mensah", personality="settled", ambition=10, wage_expectation="1000"
        )
        hired = phase7.present_offer(
            session,
            club_id=club_id,
            user_id=admin.id,
            manager_id=manager.id,
            wage="35000",
            contract_length=4,
            role="head_coach",
            prestige=40,
            seed=3,
        )
        phase7.respond_to_offer(session, offer_id=hired.id, decision="accept")
        manager.relationship_score = 90
        session.flush()
        happy = phase7.consider_retention(
            session, manager_id=manager.id, rival_wage="50000", rival_prestige=40, seed=3
        )
        money, project, base = offer_score(manager.wage, 40, manager.ambition, 3)
        assert happy["stay"]["money"] == money
        assert happy["stay"]["project"] == project
        assert happy["stay"]["base_total"] == base
        assert happy["rival"]["money"] == offer_score("50000", 40, manager.ambition, 3)[0]
        assert happy["refused_richer"] is True
        assert Decimal("50000") > Decimal(manager.wage)
        manager.relationship_score = 20
        session.flush()
        unhappy = phase7.consider_retention(
            session, manager_id=manager.id, rival_wage="50000", rival_prestige=40, seed=3
        )
        assert unhappy["decision"] == "leave"
        assert unhappy["refused_richer"] is False
        assert unhappy["stay"]["base_total"] == happy["stay"]["base_total"]
        session.commit()
