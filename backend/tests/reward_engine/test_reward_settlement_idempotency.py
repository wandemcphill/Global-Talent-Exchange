from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.admin_engine.schemas import AdminRewardRuleStabilityControls
from app.auth.service import AuthService
from app.models import (
    AdminRewardRule,
    Base,
    LedgerEntry,
    LedgerUnit,
    RewardSettlement,
)
from app.reward_engine.service import RewardEngineService


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


def _create_user(session, *, email: str, username: str):
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password="SuperSecret1",
    )
    session.commit()
    return user


def test_reward_settlement_is_idempotent_and_prevents_double_crediting(session) -> None:
    admin = _create_user(session, email="idempotent-admin@example.com", username="idempotent-admin")
    recipient = _create_user(session, email="idempotent-user@example.com", username="idempotent-user")

    session.add(
        AdminRewardRule(
            rule_key="idempotency-rules",
            title="Idempotency Rules",
            description="Testing idempotency.",
            trading_fee_bps=2000,
            gift_platform_rake_bps=3000,
            withdrawal_fee_bps=1000,
            minimum_withdrawal_fee_credits=Decimal("5.0000"),
            competition_platform_fee_bps=1000,
            stability_controls_json=AdminRewardRuleStabilityControls().model_dump(mode="json"),
            active=True,
        )
    )
    session.commit()

    service = RewardEngineService(session)
    service.credit_promo_pool(actor=admin, amount=Decimal("500.0000"))
    session.commit()

    comp_key = "comp:idempotency-test:1"
    reward_src = "gtex_promotional_pool"

    # First settlement
    first = service.settle_reward(
        actor=admin,
        user_id=recipient.id,
        competition_key=comp_key,
        title="First Place Prize",
        gross_amount=Decimal("100.0000"),
        reward_source=reward_src,
    )
    session.commit()

    # Second settlement call with exact same user, competition, reward_source
    second = service.settle_reward(
        actor=admin,
        user_id=recipient.id,
        competition_key=comp_key,
        title="First Place Prize Retry",
        gross_amount=Decimal("100.0000"),
        reward_source=reward_src,
    )
    session.commit()

    assert first.id == second.id
    assert first.net_amount == second.net_amount

    # Confirm only 1 RewardSettlement record in DB
    settlements = list(
        session.scalars(
            select(RewardSettlement).where(
                RewardSettlement.competition_key == comp_key,
                RewardSettlement.user_id == recipient.id,
                RewardSettlement.reward_source == reward_src,
            )
        ).all()
    )
    assert len(settlements) == 1

    # Confirm ledger entries were only created once for this idempotency key
    ledger_entries = list(
        session.scalars(
            select(LedgerEntry).where(LedgerEntry.external_reference == f"reward:{comp_key}:{recipient.id}")
        ).all()
    )
    # 3 entries in posting (user_account, platform_account, promo_pool_account)
    assert len(ledger_entries) == 3
