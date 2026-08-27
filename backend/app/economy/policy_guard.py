from __future__ import annotations

from decimal import Decimal
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from sqlalchemy.orm import Session

from app.economy.economic_policy import resolve_economic_policy
from app.models.admin_rules import AdminRewardRule

F = TypeVar("F", bound=Callable[..., Any])


def central_competition_fee_bps(session: Session) -> int:
    """Return the only execution-authoritative competition fee."""
    return resolve_economic_policy(session).competition_platform_fee_bps


def central_withdrawal_fee(session: Session) -> tuple[int, Decimal, str, str, str]:
    policy = resolve_economic_policy(session)
    return (
        policy.withdrawal_fee_bps,
        policy.minimum_withdrawal_fee_credits,
        policy.rule.rule_key,
        policy.policy_version,
        policy.effective_at.isoformat(),
    )


def assert_single_active_policy(session: Session) -> AdminRewardRule:
    policy = resolve_economic_policy(session)
    return policy.rule


def require_central_competition_fee(session: Session, supplied_bps: int | None) -> int:
    """Reject stale/caller-supplied fee drift and return the live Admin fee."""
    fee = central_competition_fee_bps(session)
    if supplied_bps is not None and int(supplied_bps) != fee:
        raise ValueError(f"Competition fee drift: supplied {supplied_bps} bps, active policy is {fee} bps.")
    return fee


__all__ = [
    "assert_single_active_policy",
    "central_competition_fee_bps",
    "central_withdrawal_fee",
    "require_central_competition_fee",
]
