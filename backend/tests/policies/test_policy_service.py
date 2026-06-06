from __future__ import annotations

import pytest

from app.policies.service import PolicyService


@pytest.fixture()
def session(gtex_db_session):
    # Shared full-schema engine with per-test rollback; avoids rebuilding 567 tables.
    yield gtex_db_session


def test_get_country_policy_returns_builtin_global_default_when_table_is_empty(session) -> None:
    policy = PolicyService(session).get_country_policy("US")

    assert policy.country_code == "GLOBAL"
    assert policy.deposits_enabled is False
    assert policy.market_trading_enabled is True
    assert policy.platform_reward_withdrawals_enabled is False
    assert policy.active is True
