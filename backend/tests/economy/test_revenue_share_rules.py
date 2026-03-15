from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from backend.app.economy.service import EconomyConfigService
from backend.app.models import Base, RevenueShareRule


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


def test_compute_revenue_split_applies_rule(session) -> None:
    rule = RevenueShareRule(
        rule_key="gift-default",
        scope="gift",
        title="Gift default",
        description=None,
        platform_share_bps=3000,
        creator_share_bps=1000,
        recipient_share_bps=None,
        burn_bps=500,
        priority=10,
        active=True,
    )
    session.add(rule)
    session.commit()

    service = EconomyConfigService(session)
    split = service.compute_revenue_split(scope="gift", gross_amount=Decimal("100.0000"))

    assert split.platform_amount == Decimal("30.0000")
    assert split.creator_amount == Decimal("10.0000")
    assert split.burn_amount == Decimal("5.0000")
    assert split.recipient_amount == Decimal("55.0000")
