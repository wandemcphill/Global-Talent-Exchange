from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.admin_engine.schemas import AdminRewardRuleStabilityControls
from backend.app.auth.service import AuthService
from backend.app.models import (
    AdminRewardRule,
    Base,
    SpendingControlAuditEvent,
    SpendingControlDecision,
)
from backend.app.reward_engine.service import RewardEngineError, RewardEngineService


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


def test_reward_controls_flag_near_limit_and_block_daily_count_limit(session) -> None:
    admin = _create_user(session, email="reward-admin@example.com", username="reward-admin")
    recipient = _create_user(session, email="reward-user@example.com", username="reward-user")

    session.add(
        AdminRewardRule(
            rule_key="reward-controls",
            title="Reward Controls",
            description="Clamp repeat rewards per user.",
            trading_fee_bps=2000,
            gift_platform_rake_bps=3000,
            withdrawal_fee_bps=1000,
            minimum_withdrawal_fee_credits=Decimal("5.0000"),
            competition_platform_fee_bps=1000,
            stability_controls_json=AdminRewardRuleStabilityControls(
                reward={
                    "max_amount": "500.0000",
                    "daily_user_limit": "1000.0000",
                    "daily_user_count_limit": 1,
                    "burst_window_seconds": 3600,
                    "burst_max_count": 2,
                    "duplicate_window_seconds": 900,
                    "review_threshold_bps": 8000,
                }
            ).model_dump(mode="json"),
            active=True,
        )
    )
    session.commit()

    service = RewardEngineService(session)
    service.credit_promo_pool(actor=admin, amount=Decimal("500.0000"))
    session.commit()

    first = service.settle_reward(
        actor=admin,
        user_id=recipient.id,
        competition_key="gtex-world-cup-2026",
        title="Quarter Final Bonus",
        gross_amount=Decimal("100.0000"),
        reward_source="gtex_promotional_pool",
    )
    session.commit()

    with pytest.raises(RewardEngineError, match="daily user reward count limit"):
        service.settle_reward(
            actor=admin,
            user_id=recipient.id,
            competition_key="gtex-world-cup-2026",
            title="Semi Final Bonus",
            gross_amount=Decimal("90.0000"),
            reward_source="gtex_promotional_pool",
        )

    first_audit = session.scalar(
        select(SpendingControlAuditEvent)
        .where(SpendingControlAuditEvent.entity_id == first.id)
        .order_by(SpendingControlAuditEvent.created_at.asc())
    )
    assert first_audit is not None
    assert first_audit.decision == SpendingControlDecision.REVIEW
    assert first_audit.primary_reason_code == "daily_user_count_limit_near"

    blocked = session.scalar(
        select(SpendingControlAuditEvent)
        .where(SpendingControlAuditEvent.decision == SpendingControlDecision.BLOCKED)
        .order_by(SpendingControlAuditEvent.created_at.desc())
    )
    assert blocked is not None
    assert blocked.control_scope == "reward"
    assert blocked.primary_reason_code == "daily_user_count_limit_exceeded"
