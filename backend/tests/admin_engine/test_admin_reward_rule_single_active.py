"""Exactly one Admin economic policy must stay active through any upsert.

resolve_economic_policy() fails closed on zero active rules as well as on more
than one, so a write path that deactivates every row takes gifting, competition
settlement and withdrawals offline. Activating a policy must leave that policy
active.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.admin_engine.schemas import AdminRewardRuleUpsertRequest
from app.admin_engine.service import AdminEngineService
from app.auth.service import AuthService
from app.economy.economic_policy import resolve_economic_policy
from app.models import AdminRewardRule, Base


def _make_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=True, expire_on_commit=False)()


def _admin(session):
    user = AuthService().register_user(
        session,
        email="policy-admin@example.com",
        username="policy-admin",
        password="SuperSecret1",  # pragma: allowlist secret
    )
    session.commit()
    return user


def _payload(rule_key: str, *, competition_bps: int, active: bool = True) -> AdminRewardRuleUpsertRequest:
    return AdminRewardRuleUpsertRequest(
        rule_key=rule_key,
        title="Economic Policy",
        description=None,
        trading_fee_bps=2000,
        gift_platform_rake_bps=3000,
        withdrawal_fee_bps=1000,
        minimum_withdrawal_fee_credits=Decimal("5.0000"),
        competition_platform_fee_bps=competition_bps,
        active=active,
    )


def _active_keys(session) -> list[str]:
    return sorted(session.scalars(select(AdminRewardRule.rule_key).where(AdminRewardRule.active.is_(True))).all())


def test_activating_a_brand_new_rule_leaves_exactly_that_rule_active() -> None:
    session = _make_session()
    try:
        actor = _admin(session)
        service = AdminEngineService(session)
        service.seed_defaults()
        session.flush()
        assert _active_keys(session) == ["platform-economy-defaults"]

        service.upsert_reward_rule(actor=actor, payload=_payload("promo-season-policy", competition_bps=1500))
        session.flush()

        assert _active_keys(session) == ["promo-season-policy"]
        policy = resolve_economic_policy(session)
        assert policy.rule.rule_key == "promo-season-policy"
        assert policy.competition_platform_fee_bps == 1500
    finally:
        session.close()


def test_updating_the_existing_rule_keeps_it_active() -> None:
    session = _make_session()
    try:
        actor = _admin(session)
        service = AdminEngineService(session)
        service.seed_defaults()
        session.flush()

        service.upsert_reward_rule(actor=actor, payload=_payload("platform-economy-defaults", competition_bps=2500))
        session.flush()

        assert _active_keys(session) == ["platform-economy-defaults"]
        assert resolve_economic_policy(session).competition_platform_fee_bps == 2500
    finally:
        session.close()


def test_policy_version_changes_when_the_rate_changes() -> None:
    session = _make_session()
    try:
        actor = _admin(session)
        service = AdminEngineService(session)
        service.seed_defaults()
        session.flush()
        before = resolve_economic_policy(session).policy_version

        service.upsert_reward_rule(actor=actor, payload=_payload("platform-economy-defaults", competition_bps=2200))
        session.flush()

        assert resolve_economic_policy(session).policy_version != before
    finally:
        session.close()


def test_successive_replacements_never_leave_more_or_less_than_one_active() -> None:
    session = _make_session()
    try:
        actor = _admin(session)
        service = AdminEngineService(session)
        service.seed_defaults()
        session.commit()

        for rule_key, bps in (("policy-a", 1100), ("policy-b", 1900), ("policy-c", 2700)):
            service.upsert_reward_rule(actor=actor, payload=_payload(rule_key, competition_bps=bps))
            session.commit()
            assert _active_keys(session) == [rule_key]
            policy = resolve_economic_policy(session)
            assert policy.rule.rule_key == rule_key
            assert policy.competition_platform_fee_bps == bps
    finally:
        session.close()


def test_failed_replacement_rolls_back_and_leaves_the_previous_policy_active() -> None:
    session = _make_session()
    try:
        actor = _admin(session)
        service = AdminEngineService(session)
        service.seed_defaults()
        session.commit()
        before = resolve_economic_policy(session).policy_version

        # A rule_key longer than the column allows fails during the write.
        with pytest.raises(Exception):
            service.upsert_reward_rule(actor=actor, payload=_payload("x" * 400, competition_bps=1234))
            session.commit()
        session.rollback()

        assert _active_keys(session) == ["platform-economy-defaults"]
        assert resolve_economic_policy(session).policy_version == before
    finally:
        session.close()


def test_two_active_rules_still_fail_closed() -> None:
    session = _make_session()
    try:
        service = AdminEngineService(session)
        service.seed_defaults()
        session.flush()
        # Bypass the lifecycle guard deliberately: the resolver must not trust
        # that every writer went through upsert_reward_rule().
        session.add(
            AdminRewardRule(
                rule_key="rogue-second-policy",
                title="Rogue Second Policy",
                description=None,
                trading_fee_bps=2000,
                gift_platform_rake_bps=3000,
                withdrawal_fee_bps=1000,
                minimum_withdrawal_fee_credits=Decimal("5.0000"),
                competition_platform_fee_bps=3000,
                stability_controls_json={},
                active=True,
            )
        )
        session.flush()
        assert len(_active_keys(session)) == 2

        with pytest.raises(Exception) as excinfo:
            resolve_economic_policy(session)
        assert "Exactly one active Admin economic policy" in str(excinfo.value)
    finally:
        session.close()


def test_deactivating_the_only_rule_fails_closed_rather_than_guessing() -> None:
    session = _make_session()
    try:
        actor = _admin(session)
        service = AdminEngineService(session)
        service.seed_defaults()
        session.flush()

        service.upsert_reward_rule(
            actor=actor,
            payload=_payload("platform-economy-defaults", competition_bps=3000, active=False),
        )
        session.flush()

        assert _active_keys(session) == []
        try:
            resolve_economic_policy(session)
        except Exception as exc:  # EconomicPolicyUnavailableError
            assert "No active Admin economic policy" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("resolve_economic_policy must fail closed with no active rule.")
    finally:
        session.close()
