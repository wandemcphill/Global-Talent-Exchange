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


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    AdminRuntimeState.__table__.create(engine)
    AdminRewardRule.__table__.create(engine)
    return Session(engine)


def test_withdrawal_fee_resolves_from_admin_runtime_state() -> None:
    with make_session() as session:
        session.add(
            AdminRewardRule(
                rule_key="commission-policy-test",
                title="Commission policy test rule",
                description="Explicit economic policy for treasury commission regression tests.",
                trading_fee_bps=2000,
                gift_platform_rake_bps=3000,
                withdrawal_fee_bps=300,
                minimum_withdrawal_fee_credits=Decimal("7.5000"),
                competition_platform_fee_bps=3000,
                stability_controls_json={},
                active=True,
            )
        )
        session.add(
            AdminRuntimeState(
                state_key="admin_god_mode",
                payload_json={
                    "commissions": {
                        "withdrawal_fee_bps": 300,
                        "minimum_withdrawal_fee_credits": "7.5000",
                    }
                },
            )
        )
        session.commit()

        policy = resolve_commission_policy(session)

    assert policy.withdrawal_fee_bps == 300
    assert policy.minimum_withdrawal_fee_credits == Decimal("7.5000")


def test_withdrawal_fee_resolution_fails_closed_when_admin_policy_missing() -> None:
    with make_session() as session:
        with pytest.raises(CommissionPolicyUnavailableError):
            resolve_commission_policy(session)
