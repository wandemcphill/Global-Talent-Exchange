from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.admin_runtime_state import AdminRuntimeState

ADMIN_GOD_MODE_STATE_KEY = "admin_god_mode"


class CommissionPolicyUnavailableError(RuntimeError):
    """Raised when the authoritative Admin commission policy cannot be resolved."""


@dataclass(frozen=True, slots=True)
class CommissionPolicy:
    withdrawal_fee_bps: int
    minimum_withdrawal_fee_credits: Decimal


def resolve_commission_policy(session: Session) -> CommissionPolicy:
    row = session.scalar(
        select(AdminRuntimeState).where(AdminRuntimeState.state_key == ADMIN_GOD_MODE_STATE_KEY)
    )
    if row is None:
        raise CommissionPolicyUnavailableError("Admin commission policy is unavailable.")

    payload = dict(row.payload_json or {})
    commissions = payload.get("commissions")
    if not isinstance(commissions, dict):
        raise CommissionPolicyUnavailableError("Admin commission policy is malformed.")

    raw_bps = commissions.get("withdrawal_fee_bps")
    raw_minimum = commissions.get("minimum_withdrawal_fee_credits")
    if raw_bps is None or raw_minimum is None:
        raise CommissionPolicyUnavailableError("Admin withdrawal fee policy is incomplete.")

    try:
        bps = int(raw_bps)
        minimum = Decimal(str(raw_minimum))
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise CommissionPolicyUnavailableError("Admin withdrawal fee policy is invalid.") from exc

    if bps < 0 or bps > 10000:
        raise CommissionPolicyUnavailableError("Admin withdrawal fee policy is outside the valid range.")
    if minimum < Decimal("0.0000"):
        raise CommissionPolicyUnavailableError("Admin minimum withdrawal fee cannot be negative.")

    return CommissionPolicy(
        withdrawal_fee_bps=bps,
        minimum_withdrawal_fee_credits=minimum,
    )


__all__ = ["CommissionPolicy", "CommissionPolicyUnavailableError", "resolve_commission_policy"]
