from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.economy.economic_policy import EconomicPolicyUnavailableError, resolve_economic_policy


class CommissionPolicyUnavailableError(RuntimeError):
    """Raised when the authoritative Admin commission policy cannot be resolved."""


@dataclass(frozen=True, slots=True)
class CommissionPolicy:
    withdrawal_fee_bps: int
    minimum_withdrawal_fee_credits: Decimal
    policy_rule_key: str
    policy_version: str
    effective_at: object


def resolve_commission_policy(session: Session) -> CommissionPolicy:
    try:
        policy = resolve_economic_policy(session)
    except EconomicPolicyUnavailableError as exc:
        raise CommissionPolicyUnavailableError(str(exc)) from exc
    return CommissionPolicy(
        withdrawal_fee_bps=policy.withdrawal_fee_bps,
        minimum_withdrawal_fee_credits=policy.minimum_withdrawal_fee_credits,
        policy_rule_key=policy.rule.rule_key,
        policy_version=policy.policy_version,
        effective_at=policy.effective_at,
    )


__all__ = ["CommissionPolicy", "CommissionPolicyUnavailableError", "resolve_commission_policy"]
