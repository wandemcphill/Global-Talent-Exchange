"""Shared Admin economic policy seeding for tests.

Production guarantees exactly one active ``AdminRewardRule`` two ways: migration
``20260827_0113_economic_policy_consistency`` seeds it, and
``AdminEngineService.seed_defaults()`` creates it on a fresh install. Tests that
build their schema with ``Base.metadata.create_all`` run neither, so
``resolve_economic_policy()`` correctly fails closed on a database that would
never exist in production.

This helper restores that guarantee without weakening the resolver. Use it in
any test that exercises gifting, competition fees, or withdrawal commission.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select, update

from app.models.admin_rules import AdminRewardRule

CANONICAL_RULE_KEY = "platform-economy-defaults"

#: Mirrors migration 20260827_0113 and AdminEngineService.DEFAULT_REWARD_RULES.
ECONOMIC_POLICY_DEFAULTS: dict[str, Any] = {
    "title": "Platform Economy Defaults",
    "description": "Canonical Admin fee and rake policy for GTEX economic flows.",
    "trading_fee_bps": 2000,
    "gift_platform_rake_bps": 3000,
    "withdrawal_fee_bps": 1000,
    "minimum_withdrawal_fee_credits": Decimal("5.0000"),
    "competition_platform_fee_bps": 3000,
}


def seed_economic_policy(session, *, rule_key: str = CANONICAL_RULE_KEY, **overrides: Any) -> AdminRewardRule:
    """Ensure exactly one active Admin economic policy exists on this session.

    Idempotent: repeated calls update the same rule rather than creating a
    second active row, which would make ``resolve_economic_policy()`` fail
    closed for the opposite reason.
    """
    values: dict[str, Any] = {**ECONOMIC_POLICY_DEFAULTS, **overrides}
    stability_controls = values.pop("stability_controls_json", None)

    record = session.scalar(select(AdminRewardRule).where(AdminRewardRule.rule_key == rule_key))
    if record is None:
        record = AdminRewardRule(rule_key=rule_key)
        session.add(record)
    for field, value in values.items():
        setattr(record, field, value)
    record.stability_controls_json = stability_controls if stability_controls is not None else {}
    record.active = True
    session.flush()

    session.execute(
        update(AdminRewardRule)
        .where(AdminRewardRule.active.is_(True), AdminRewardRule.rule_key != rule_key)
        .values(active=False)
    )
    session.flush()
    return record


__all__ = ["CANONICAL_RULE_KEY", "ECONOMIC_POLICY_DEFAULTS", "seed_economic_policy"]
