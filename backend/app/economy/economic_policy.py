from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.admin_rules import AdminRewardRule


class EconomicPolicyUnavailableError(RuntimeError):
    """Raised when the platform has no unambiguous active economic policy."""


@dataclass(frozen=True, slots=True)
class EconomicPolicy:
    rule: AdminRewardRule
    policy_version: str
    effective_at: datetime

    @property
    def trading_fee_bps(self) -> int:
        return int(self.rule.trading_fee_bps)

    @property
    def gift_platform_rake_bps(self) -> int:
        return int(self.rule.gift_platform_rake_bps)

    @property
    def withdrawal_fee_bps(self) -> int:
        return int(self.rule.withdrawal_fee_bps)

    @property
    def minimum_withdrawal_fee_credits(self) -> Decimal:
        return Decimal(str(self.rule.minimum_withdrawal_fee_credits))

    @property
    def competition_platform_fee_bps(self) -> int:
        return int(self.rule.competition_platform_fee_bps)


def resolve_economic_policy(session: Session) -> EconomicPolicy:
    rows = list(
        session.scalars(
            select(AdminRewardRule)
            .where(AdminRewardRule.active.is_(True))
            .order_by(AdminRewardRule.updated_at.desc(), AdminRewardRule.id.asc())
        ).all()
    )
    if not rows:
        raise EconomicPolicyUnavailableError("No active Admin economic policy exists.")
    if len(rows) != 1:
        raise EconomicPolicyUnavailableError("Exactly one active Admin economic policy is required.")
    rule = rows[0]
    payload = {
        "rule_key": rule.rule_key,
        "trading_fee_bps": int(rule.trading_fee_bps),
        "gift_platform_rake_bps": int(rule.gift_platform_rake_bps),
        "withdrawal_fee_bps": int(rule.withdrawal_fee_bps),
        "minimum_withdrawal_fee_credits": str(Decimal(str(rule.minimum_withdrawal_fee_credits))),
        "competition_platform_fee_bps": int(rule.competition_platform_fee_bps),
        "stability_controls_json": rule.stability_controls_json or {},
        "effective_at": rule.updated_at.isoformat() if rule.updated_at else None,
    }
    version = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
    return EconomicPolicy(rule=rule, policy_version=version, effective_at=rule.updated_at)


@dataclass(frozen=True, slots=True)
class EconomicGiftSplit:
    gross_amount: Decimal
    platform_amount: Decimal
    recipient_amount: Decimal
    creator_amount: Decimal
    burn_amount: Decimal
    rule_key: str
    policy_version: str


def compute_gift_split(session: Session, gross_amount: Decimal) -> EconomicGiftSplit:
    quant = Decimal("0.0001")
    gross = Decimal(str(gross_amount)).quantize(quant)
    if gross <= 0:
        raise EconomicPolicyUnavailableError("Gift gross amount must be positive.")
    policy = resolve_economic_policy(session)
    bps = policy.gift_platform_rake_bps
    if not 0 <= bps <= 10_000:
        raise EconomicPolicyUnavailableError("Admin gift rake is outside the valid range.")
    platform_amount = (gross * Decimal(bps) / Decimal(10_000)).quantize(quant)
    burn_amount = Decimal("0.0000")
    try:
        from app.economy.governor_service import EconomyGovernorService
        burn_bps = max(0, min(10_000, int(EconomyGovernorService(session).burn_bonus_bps())))
        burn_amount = (gross * Decimal(burn_bps) / Decimal(10_000)).quantize(quant)
    except Exception:
        burn_amount = Decimal("0.0000")
    if platform_amount + burn_amount > gross:
        burn_amount = max(Decimal("0.0000"), gross - platform_amount)
    return EconomicGiftSplit(
        gross_amount=gross,
        platform_amount=platform_amount,
        recipient_amount=(gross - platform_amount - burn_amount).quantize(quant),
        creator_amount=Decimal("0.0000"),
        burn_amount=burn_amount,
        rule_key=policy.rule.rule_key,
        policy_version=policy.policy_version,
    )


__all__ = ["EconomicGiftSplit", "EconomicPolicy", "EconomicPolicyUnavailableError", "compute_gift_split", "resolve_economic_policy"]
