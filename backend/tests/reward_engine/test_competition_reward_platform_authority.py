"""Behavioral proof for EA-P0-1: the canonical Admin economic policy
(AdminRewardRule.competition_platform_fee_bps, via resolve_economic_policy) is
the SOLE authority for the platform fee on competition-reward settlement.

A legacy/deprecated RevenueShareRule row for scope="competition_reward" must
never be able to override it, and settlement must fail closed when the
canonical policy itself is missing or ambiguous. These tests exercise the
real RewardEngineService.settle_reward end to end - not a source/AST scan.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.economy.service import DEFAULT_REVENUE_SHARE_RULES, EconomyConfigService
from app.models.admin_rules import AdminRewardRule
from app.models.base import Base
from app.models.revenue_share_rule import RevenueShareRule
from app.models.user import User, UserRole
from app.reward_engine.service import RewardEngineError, RewardEngineService
from app.wallets.service import WalletService
from backend.tests.support.economic_policy import seed_economic_policy


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


def _create_user(session, *, user_id: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        id=user_id,
        email=f"{user_id}@example.com",
        username=user_id,
        password_hash="hashed",
        role=role,
    )
    session.add(user)
    session.flush()
    WalletService().ensure_default_accounts(session, user)
    session.flush()
    return user


def _seed_legacy_competition_reward_rule(session, *, platform_share_bps: int, active: bool = True) -> RevenueShareRule:
    rule = RevenueShareRule(
        rule_key="competition-reward-default",
        scope="competition_reward",
        title="Legacy Competition Reward Split",
        description="Deprecated pre-Phase-A revenue split rule.",
        platform_share_bps=platform_share_bps,
        creator_share_bps=0,
        recipient_share_bps=None,
        burn_bps=0,
        priority=10,
        active=active,
    )
    session.add(rule)
    session.flush()
    return rule


def _settle(session, *, admin: User, recipient: User, gross: Decimal = Decimal("100.0000")):
    service = RewardEngineService(session)
    service.credit_promo_pool(actor=admin, amount=gross * 5)
    session.commit()
    settlement = service.settle_reward(
        actor=admin,
        user_id=recipient.id,
        competition_key="gtex-world-cup-2026",
        title="Final Bonus",
        gross_amount=gross,
    )
    session.commit()
    return settlement


def test_admin_policy_wins_over_active_legacy_revenue_share_rule(session) -> None:
    admin = _create_user(session, user_id="p01-admin-1", role=UserRole.ADMIN)
    recipient = _create_user(session, user_id="p01-recipient-1")
    seed_economic_policy(session, competition_platform_fee_bps=3000)  # Admin policy = 30%
    _seed_legacy_competition_reward_rule(session, platform_share_bps=1000)  # Legacy = 10%

    settlement = _settle(session, admin=admin, recipient=recipient)

    assert settlement.platform_fee_amount == Decimal("30.0000")  # 30% of 100, NOT 10%


def test_admin_policy_still_wins_after_legacy_rule_is_deactivated(session) -> None:
    admin = _create_user(session, user_id="p01-admin-2", role=UserRole.ADMIN)
    recipient = _create_user(session, user_id="p01-recipient-2")
    seed_economic_policy(session, competition_platform_fee_bps=3000)
    _seed_legacy_competition_reward_rule(session, platform_share_bps=1000, active=False)

    settlement = _settle(session, admin=admin, recipient=recipient)

    assert settlement.platform_fee_amount == Decimal("30.0000")


def test_settlement_fails_closed_with_zero_active_admin_reward_rules(session) -> None:
    admin = _create_user(session, user_id="p01-admin-3", role=UserRole.ADMIN)
    recipient = _create_user(session, user_id="p01-recipient-3")
    # No AdminRewardRule seeded at all: resolve_economic_policy has nothing to resolve.
    _seed_legacy_competition_reward_rule(session, platform_share_bps=1000)

    service = RewardEngineService(session)
    service.credit_promo_pool(actor=admin, amount=Decimal("500.0000"))
    session.commit()

    with pytest.raises(RewardEngineError) as exc_info:
        service.settle_reward(
            actor=admin,
            user_id=recipient.id,
            competition_key="gtex-world-cup-2026",
            title="Final Bonus",
            gross_amount=Decimal("100.0000"),
        )
    assert exc_info.value.reason == "economic_policy_unavailable"


def test_settlement_fails_closed_with_two_active_admin_reward_rules(session) -> None:
    admin = _create_user(session, user_id="p01-admin-4", role=UserRole.ADMIN)
    recipient = _create_user(session, user_id="p01-recipient-4")
    seed_economic_policy(session, rule_key="policy-a", competition_platform_fee_bps=3000)
    # Add a SECOND active rule directly (seed_economic_policy would normally
    # deactivate the first; bypass that to reproduce the ambiguous state).
    session.add(
        AdminRewardRule(
            rule_key="policy-b",
            title="Second active policy",
            description="Ambiguous duplicate active policy.",
            trading_fee_bps=2000,
            gift_platform_rake_bps=3000,
            withdrawal_fee_bps=1000,
            minimum_withdrawal_fee_credits=Decimal("5.0000"),
            competition_platform_fee_bps=1500,
            stability_controls_json={},
            active=True,
        )
    )
    session.flush()

    service = RewardEngineService(session)
    service.credit_promo_pool(actor=admin, amount=Decimal("500.0000"))
    session.commit()

    with pytest.raises(RewardEngineError) as exc_info:
        service.settle_reward(
            actor=admin,
            user_id=recipient.id,
            competition_key="gtex-world-cup-2026",
            title="Final Bonus",
            gross_amount=Decimal("100.0000"),
        )
    assert exc_info.value.reason == "economic_policy_unavailable"


def test_changing_legacy_revenue_share_rule_does_not_move_competition_reward_economics(session) -> None:
    admin = _create_user(session, user_id="p01-admin-5", role=UserRole.ADMIN)
    recipient_one = _create_user(session, user_id="p01-recipient-5a")
    recipient_two = _create_user(session, user_id="p01-recipient-5b")
    seed_economic_policy(session, competition_platform_fee_bps=3000)
    legacy = _seed_legacy_competition_reward_rule(session, platform_share_bps=1000)

    first = _settle(session, admin=admin, recipient=recipient_one)
    assert first.platform_fee_amount == Decimal("30.0000")

    # Swing the legacy rule to an extreme value - it must still have zero effect.
    legacy.platform_share_bps = 9999
    session.flush()
    session.commit()

    second = _settle(session, admin=admin, recipient=recipient_two)
    # The governor's reward_multiplier() can legitimately move gross_amount
    # between settlements (an unrelated anti-inflation control), so compare
    # the fee as a rate of the actual gross rather than a fixed dollar amount -
    # what matters here is that the swung-to-9999 legacy rule contributed 0%.
    expected_second_fee = (second.gross_amount * Decimal("3000") / Decimal("10000")).quantize(Decimal("0.0001"))
    assert second.platform_fee_amount == expected_second_fee


def test_gift_scope_legacy_revenue_share_rule_is_unaffected(session) -> None:
    """P0-1's fix is scoped to competition_reward only: the gift scope's
    legacy RevenueShareRule authority (a separate, non-Phase-A flow) must keep
    working exactly as before."""
    economy = EconomyConfigService(session)
    economy.seed_defaults()
    session.commit()

    gift_rule = session.scalar(select(RevenueShareRule).where(RevenueShareRule.scope == "gift"))
    assert gift_rule is not None
    assert gift_rule.rule_key == DEFAULT_REVENUE_SHARE_RULES[0]["rule_key"]

    split = economy.compute_revenue_split(
        scope="gift",
        gross_amount=Decimal("10.0000"),
        fallback_platform_bps=0,
    )
    assert split.platform_amount == Decimal("3.0000")  # unchanged: still driven by RevenueShareRule
