from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from app.models import Base
from app.policies.service import PolicyService


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


def test_get_country_policy_returns_builtin_global_default_when_table_is_empty(session) -> None:
    policy = PolicyService(session).get_country_policy("US")

    assert policy.country_code == "GLOBAL"
    assert policy.deposits_enabled is False
    assert policy.market_trading_enabled is True
    assert policy.platform_reward_withdrawals_enabled is False
    assert policy.active is True
