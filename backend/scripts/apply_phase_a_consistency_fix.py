from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count}")
    write(path, text.replace(old, new, 1))


def main() -> None:
    write("backend/app/economy/economic_policy.py", '''from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.admin_rules import AdminRewardRule


class EconomicPolicyUnavailableError(RuntimeError):
    pass


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
    q = Decimal("0.0001")
    gross = Decimal(str(gross_amount)).quantize(q)
    if gross <= 0:
        raise EconomicPolicyUnavailableError("Gift gross amount must be positive.")
    policy = resolve_economic_policy(session)
    platform_bps = policy.gift_platform_rake_bps
    if not 0 <= platform_bps <= 10_000:
        raise EconomicPolicyUnavailableError("Admin gift rake is outside the valid range.")
    platform_amount = (gross * Decimal(platform_bps) / Decimal(10_000)).quantize(q)
    burn_amount = Decimal("0.0000")
    try:
        from app.economy.governor_service import EconomyGovernorService
        burn_bps = max(0, min(10_000, int(EconomyGovernorService(session).burn_bonus_bps())))
        burn_amount = (gross * Decimal(burn_bps) / Decimal(10_000)).quantize(q)
    except Exception:
        burn_amount = Decimal("0.0000")
    if platform_amount + burn_amount > gross:
        burn_amount = max(Decimal("0.0000"), gross - platform_amount)
    return EconomicGiftSplit(
        gross_amount=gross,
        platform_amount=platform_amount,
        recipient_amount=(gross - platform_amount - burn_amount).quantize(q),
        creator_amount=Decimal("0.0000"),
        burn_amount=burn_amount,
        rule_key=policy.rule.rule_key,
        policy_version=policy.policy_version,
    )


__all__ = [
    "EconomicGiftSplit",
    "EconomicPolicy",
    "EconomicPolicyUnavailableError",
    "compute_gift_split",
    "resolve_economic_policy",
]
''')

    replace_once("backend/app/admin_engine/service.py", '"competition_platform_fee_bps": 1000,', '"competition_platform_fee_bps": 3000,')
    replace_once(
        "backend/app/admin_engine/service.py",
        '''    def get_active_reward_rule(self) -> AdminRewardRule | None:
        return next(iter(self.list_reward_rules(active_only=True)), None)
''',
        '''    def get_active_reward_rule(self) -> AdminRewardRule | None:
        rows = list(
            self.session.scalars(
                select(AdminRewardRule)
                .where(AdminRewardRule.active.is_(True))
                .order_by(AdminRewardRule.updated_at.desc(), AdminRewardRule.id.asc())
            ).all()
        )
        if len(rows) > 1:
            raise ValueError("Exactly one active Admin reward/economic policy is required.")
        return rows[0] if rows else None
''',
    )
    replace_once(
        "backend/app/admin_engine/service.py",
        '''        record.stability_controls_json = self.normalize_stability_controls_payload(payload.stability_controls)
        record.active = payload.active
        record.updated_by_user_id = actor.id
''',
        '''        record.stability_controls_json = self.normalize_stability_controls_payload(payload.stability_controls)
        record.active = payload.active
        if payload.active:
            self.session.query(AdminRewardRule).filter(
                AdminRewardRule.active.is_(True), AdminRewardRule.id != record.id
            ).update({AdminRewardRule.active: False}, synchronize_session=False)
        record.updated_by_user_id = actor.id
''',
    )
    replace_once(
        "backend/app/admin_engine/schemas.py",
        "competition_platform_fee_bps: int = Field(default=3000, ge=0, le=5000)",
        "competition_platform_fee_bps: int = Field(default=3000, ge=0, le=3000)",
    )

    write("backend/app/treasury/commission_policy.py", '''from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.economy.economic_policy import EconomicPolicyUnavailableError, resolve_economic_policy


class CommissionPolicyUnavailableError(RuntimeError):
    pass


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
''')

    # User-hosted competition fee is resolved in the DB-backed orchestrator, where a Session exists.
    opath = "backend/app/services/competition_orchestrator.py"
    text = read(opath)
    if "from app.economy.economic_policy import resolve_economic_policy" not in text:
        text = text.replace(
            "from app.config.competition_constants import USER_COMPETITION_MAX_PLATFORM_FEE_BPS, USER_COMPETITION_MIN_PARTICIPANTS\n",
            "from app.config.competition_constants import USER_COMPETITION_MIN_PARTICIPANTS\nfrom app.economy.economic_policy import resolve_economic_policy\n",
            1,
        )
    old = '''        domain_payload = backend_competition_create_request(
            payload,
            default_platform_fee_pct=self.fee_service.default_platform_fee_pct,
        )
'''
    new = '''        economic_policy = resolve_economic_policy(self.session)
        domain_payload = backend_competition_create_request(
            payload,
            default_platform_fee_pct=Decimal(economic_policy.competition_platform_fee_bps) / Decimal("100"),
        )
'''
    if old not in text:
        raise SystemExit("competition_orchestrator: domain payload block not found")
    text = text.replace(old, new, 1)
    text = text.replace(
        '            domain_payload.financials.platform_fee_bps = USER_COMPETITION_MAX_PLATFORM_FEE_BPS\n',
        '            domain_payload.financials.platform_fee_bps = economic_policy.competition_platform_fee_bps\n',
        1,
    )
    text = text.replace(
        '            competition.platform_fee_bps = USER_COMPETITION_MAX_PLATFORM_FEE_BPS\n',
        '            competition.platform_fee_bps = economic_policy.competition_platform_fee_bps\n',
        1,
    )
    marker = '''            "special_rules": payload.special_rules,
'''
    inject = '''            "special_rules": payload.special_rules,
            "economic_policy": {
                "rule_key": economic_policy.rule.rule_key,
                "version": economic_policy.policy_version,
                "effective_at": economic_policy.effective_at.isoformat(),
                "competition_platform_fee_bps": economic_policy.competition_platform_fee_bps,
            },
'''
    if marker not in text:
        raise SystemExit("competition_orchestrator: metadata marker not found")
    text = text.replace(marker, inject, 1)
    write(opath, text)

    for path in ["backend/app/gift_engine/canonical_service.py", "backend/app/gift_engine/service.py"]:
        text = read(path)
        if "from app.economy.economic_policy import compute_gift_split" not in text:
            anchor = "from app.economy.service import EconomyConfigService\n"
            if anchor in text:
                text = text.replace(anchor, anchor + "from app.economy.economic_policy import compute_gift_split\n", 1)
            else:
                text = text.replace("from app.models.base import generate_uuid, utcnow\n", "from app.models.base import generate_uuid, utcnow\nfrom app.economy.economic_policy import compute_gift_split\n", 1)
        split_block = '''        split = EconomyConfigService(self.session).compute_revenue_split(
            scope="gift",
            gross_amount=gross_amount,
            fallback_platform_bps=self._active_gift_rake_bps(),
        )
'''
        if split_block in text:
            text = text.replace(split_block, "        split = compute_gift_split(self.session, gross_amount)\n", 1)
        text = text.replace(
            '        self.event_publisher.publish(event)\n',
            '        self.wallet_service._stage_domain_event(self.session, event=event, durable=True)\n',
            1,
        )
        write(path, text)
    replace_once("backend/app/gift_engine/canonical_service.py", 'fee_rule_version="1",', "fee_rule_version=split.policy_version,")

    wpath = "backend/app/wallets/service.py"
    text = read(wpath)
    replace = ('        withdrawal_fee_bps: int = 1000,\n        minimum_fee: Decimal = Decimal("5.0000"),\n', '        withdrawal_fee_bps: int | None = None,\n        minimum_fee: Decimal | None = None,\n')
    if replace[0] in text:
        text = text.replace(*replace, 1)
    old_fee = '''        fee_tag = LedgerSourceTag.WITHDRAWAL_FEE_BURN
        fee_amount = self._normalize_amount(
            max(
                (normalized_amount * Decimal(withdrawal_fee_bps) / Decimal(10_000)), self._normalize_amount(minimum_fee)
            )
        )
'''
    new_fee = '''        fee_tag = LedgerSourceTag.WITHDRAWAL_FEE_BURN
        if withdrawal_fee_bps is None or minimum_fee is None:
            from app.economy.economic_policy import resolve_economic_policy
            policy = resolve_economic_policy(session)
            withdrawal_fee_bps = policy.withdrawal_fee_bps if withdrawal_fee_bps is None else withdrawal_fee_bps
            minimum_fee = policy.minimum_withdrawal_fee_credits if minimum_fee is None else minimum_fee
        fee_amount = self._normalize_amount(
            max(
                (normalized_amount * Decimal(withdrawal_fee_bps) / Decimal(10_000)), self._normalize_amount(minimum_fee)
            )
        )
'''
    if old_fee not in text:
        raise SystemExit("wallet service: fee block not found")
    text = text.replace(old_fee, new_fee, 1)
    text = text.replace(
        '                    "total_debit": str(total_debit),\n',
        '                    "total_debit": str(total_debit),\n                    "fee_policy_rule_key": (policy.rule.rule_key if "policy" in locals() else None),\n                    "fee_policy_version": (policy.policy_version if "policy" in locals() else None),\n                    "fee_policy_effective_at": (policy.effective_at.isoformat() if "policy" in locals() else None),\n',
        1,
    )
    write(wpath, text)

    # The compatibility AgentWallet may expose balance fields, but cannot mutate money.
    apath = "backend/app/agents/agent_wallet.py"
    text = read(apath)
    if "AgentWallet is a ledger projection only" not in text:
        start = text.index("    def apply_spend(")
        end = text.index("    @staticmethod\n    def _roi", start)
        stub = '''    def apply_spend(self, wallet: AgentWallet, amount: float) -> AgentWallet:
        raise RuntimeError("AgentWallet is a ledger projection only. Use AgentLedgerService for monetary spend.")

    def settle(self, wallet: AgentWallet, *, earnings: float, quality_score: float, trust_score: float, repetition_ratio: float):
        raise RuntimeError("AgentWallet is a ledger projection only. Use AgentLedgerService for settlement and payout authorization.")

'''
        text = text[:start] + stub + text[end:]
        write(apath, text)

    # Remove duplicate hard-coded match-gift rate checks. SpendingControl is the control-plane authority.
    for path in ["backend/app/gift_engine/canonical_service.py", "backend/app/gift_engine/service.py"]:
        text = read(path)
        text = re.sub(
            r'\n        if requested_scope == "gtex_competition" and recipient_user_id:[\\s\\S]*?\n\n        self\.ensure_football_gift_catalog\(\)',
            "\n        self.ensure_football_gift_catalog()",
            text,
            count=1,
        )
        text = re.sub(
            r'\n        if normalized_scope == "gtex_competition":[\\s\\S]*?\n        gift = self\.session\.scalar',
            "\n        gift = self.session.scalar",
            text,
            count=1,
        )
        write(path, text)

    write("backend/migrations/versions/20260827_0114_economic_policy_authority.py", '''"""Normalize the Phase A economic-policy baseline and collapse duplicate active rows."""\n\nfrom alembic import op\nimport sqlalchemy as sa\n\nrevision = "20260827_0114_economic_policy_authority"\ndown_revision = "20260827_0113_economic_policy_consistency"\nbranch_labels = None\ndepends_on = None\n\ndef upgrade():\n    c = op.get_bind()\n    c.execute(sa.text("UPDATE admin_reward_rules SET competition_platform_fee_bps=3000 WHERE rule_key='platform-economy-defaults' AND competition_platform_fee_bps IN (1000,2000)"))\n    c.execute(sa.text("UPDATE admin_reward_rules SET active=FALSE WHERE active AND id <> (SELECT id FROM admin_reward_rules WHERE active ORDER BY updated_at DESC, id ASC LIMIT 1)"))\n    c.execute(sa.text("UPDATE competition_templates SET platform_fee_bps=3000 WHERE platform_fee_bps IN (1000,2000)"))\n\ndef downgrade():\n    pass\n''')

    hpath = "docs/implementation/PHASE_A_LATEST_HANDOFF_ADDENDUM_20260822.md"
    text = read(hpath)
    if "centralized AdminRewardRule economic policy authority" not in text:
        text += "\n\n## Phase A consistency sweep 2026-08-27\n\nThe economic fee authority is centralized on the active AdminRewardRule. User-hosted competition fees are resolved from the live policy rather than a caller-provided maximum; gifting and withdrawals resolve the same authority; economic operations carry a policy fingerprint; compatibility AgentWallet money mutation fails closed; and gift events use commit-safe durable publication.\n"
        write(hpath, text)
    print("Phase A consistency sweep applied")


if __name__ == "__main__":
    main()
