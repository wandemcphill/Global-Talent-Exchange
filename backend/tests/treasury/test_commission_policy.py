"""Withdrawal commission resolves from the Admin economic policy.

Before Phase A this read admin god-mode runtime state. The sweep made
``AdminRewardRule`` the single economic authority, so these tests assert the
current source of truth and prove the retired one can no longer influence it.
"""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.admin_rules import AdminRewardRule
from app.models.admin_runtime_state import AdminRuntimeState
from app.treasury.commission_policy import (
    CommissionPolicyUnavailableError,
    resolve_commission_policy,
)
from backend.tests.support.economic_policy import seed_economic_policy


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    AdminRuntimeState.__table__.create(engine)
    AdminRewardRule.__table__.create(engine)
    return Session(engine)


def test_withdrawal_fee_resolves_from_active_admin_economic_policy() -> None:
    with make_session() as session:
        seed_economic_policy(
            session,
            withdrawal_fee_bps=300,
            minimum_withdrawal_fee_credits=Decimal("7.5000"),
        )
        session.commit()

        policy = resolve_commission_policy(session)

    assert policy.withdrawal_fee_bps == 300
    assert policy.minimum_withdrawal_fee_credits == Decimal("7.5000")
    assert policy.policy_rule_key == "platform-economy-defaults"
    assert policy.policy_version


def test_admin_runtime_state_cannot_override_the_economic_policy() -> None:
    with make_session() as session:
        seed_economic_policy(
            session,
            withdrawal_fee_bps=300,
            minimum_withdrawal_fee_credits=Decimal("7.5000"),
        )
        session.add(
            AdminRuntimeState(
                state_key="admin_god_mode",
                payload_json={
                    "commissions": {
                        "withdrawal_fee_bps": 9000,
                        "minimum_withdrawal_fee_credits": "99.0000",
                    }
                },
            )
        )
        session.commit()

        policy = resolve_commission_policy(session)

    # The god-mode commission block is not the withdrawal fee authority.
    assert policy.withdrawal_fee_bps == 300
    assert policy.minimum_withdrawal_fee_credits == Decimal("7.5000")


def test_withdrawal_fee_resolution_fails_closed_when_admin_policy_missing() -> None:
    with make_session() as session:
        with pytest.raises(CommissionPolicyUnavailableError):
            resolve_commission_policy(session)


def test_withdrawal_fee_resolution_fails_closed_on_duplicate_active_policies() -> None:
    with make_session() as session:
        seed_economic_policy(session)
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
        session.commit()

        with pytest.raises(CommissionPolicyUnavailableError):
            resolve_commission_policy(session)
