from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def edit(path: str, transform) -> None:
    file = ROOT / path
    text = file.read_text(encoding="utf-8")
    updated = transform(text)
    if updated == text:
        raise SystemExit(f"No change made to {path}")
    file.write_text(updated, encoding="utf-8")


def replace_exact(path: str, old: str, new: str) -> None:
    def transform(text: str) -> str:
        count = text.count(old)
        if count != 1:
            raise SystemExit(f"{path}: expected exactly one match, found {count}")
        return text.replace(old, new, 1)
    edit(path, transform)


def main() -> None:
    replace_exact(
        "backend/app/admin_engine/service.py",
        '"competition_platform_fee_bps": 1000,',
        '"competition_platform_fee_bps": 3000,',
    )

    replace_exact(
        "backend/app/admin_engine/service.py",
        '''    def get_active_reward_rule(self) -> AdminRewardRule | None:\n        return next(iter(self.list_reward_rules(active_only=True)), None)\n''',
        '''    def get_active_reward_rule(self) -> AdminRewardRule | None:\n        rows = list(\n            self.session.scalars(\n                select(AdminRewardRule)\n                .where(AdminRewardRule.active.is_(True))\n                .order_by(AdminRewardRule.updated_at.desc(), AdminRewardRule.id.asc())\n            ).all()\n        )\n        if len(rows) > 1:\n            raise ValueError("Exactly one active Admin reward/economic policy is required.")\n        return rows[0] if rows else None\n''',
    )

    replace_exact(
        "backend/app/admin_engine/service.py",
        '''        record.stability_controls_json = self.normalize_stability_controls_payload(payload.stability_controls)\n        record.active = payload.active\n        record.updated_by_user_id = actor.id\n''',
        '''        record.stability_controls_json = self.normalize_stability_controls_payload(payload.stability_controls)\n        record.active = payload.active\n        if payload.active:\n            self.session.query(AdminRewardRule).filter(\n                AdminRewardRule.active.is_(True),\n                AdminRewardRule.id != record.id,\n            ).update({AdminRewardRule.active: False}, synchronize_session=False)\n        record.updated_by_user_id = actor.id\n''',
    )

    # User-hosted competition fee is always the active Admin economic policy.
    def competition(text: str) -> str:
        if "from app.economy.economic_policy import resolve_economic_policy" not in text:
            anchor = "from app.config.competition_constants import USER_COMPETITION_MAX_PLATFORM_FEE_BPS, USER_COMPETITION_MIN_PARTICIPANTS\n"
            if anchor in text:
                text = text.replace(anchor, "from app.config.competition_constants import USER_COMPETITION_MIN_PARTICIPANTS\nfrom app.economy.economic_policy import resolve_economic_policy\n", 1)
        old = '''        domain_payload = backend_competition_create_request(\n            payload,\n            default_platform_fee_pct=self.fee_service.default_platform_fee_pct,\n        )\n'''
        new = '''        economic_policy = resolve_economic_policy(self.session)\n        domain_payload = backend_competition_create_request(\n            payload,\n            default_platform_fee_pct=Decimal(economic_policy.competition_platform_fee_bps) / Decimal("100"),\n        )\n'''
        if old not in text:
            raise SystemExit("competition orchestrator domain payload block not found")
        text = text.replace(old, new, 1)
        if 'domain_payload.financials.platform_fee_bps = USER_COMPETITION_MAX_PLATFORM_FEE_BPS' in text:
            text = text.replace('domain_payload.financials.platform_fee_bps = USER_COMPETITION_MAX_PLATFORM_FEE_BPS', 'domain_payload.financials.platform_fee_bps = economic_policy.competition_platform_fee_bps', 1)
        if 'competition.platform_fee_bps = USER_COMPETITION_MAX_PLATFORM_FEE_BPS' in text:
            text = text.replace('competition.platform_fee_bps = USER_COMPETITION_MAX_PLATFORM_FEE_BPS', 'competition.platform_fee_bps = economic_policy.competition_platform_fee_bps', 1)
        marker = '            "special_rules": payload.special_rules,\n'
        if marker not in text:
            raise SystemExit("competition metadata marker not found")
        inject = '''            "special_rules": payload.special_rules,\n            "economic_policy": {\n                "rule_key": economic_policy.rule.rule_key,\n                "version": economic_policy.policy_version,\n                "effective_at": economic_policy.effective_at.isoformat(),\n                "competition_platform_fee_bps": economic_policy.competition_platform_fee_bps,\n            },\n'''
        return text.replace(marker, inject, 1)
    edit("backend/app/services/competition_orchestrator.py", competition)

    # Canonical gifts resolve the same authority and publish only after commit.
    replace_exact(
        "backend/app/gift_engine/canonical_service.py",
        "from app.economy.service import EconomyConfigService\n",
        "from app.economy.service import EconomyConfigService\nfrom app.economy.economic_policy import compute_gift_split\n",
    )
    replace_exact(
        "backend/app/gift_engine/canonical_service.py",
        '''        split = EconomyConfigService(self.session).compute_revenue_split(\n            scope="gift",\n            gross_amount=gross_amount,\n            fallback_platform_bps=self._active_gift_rake_bps(),\n        )\n''',
        '        split = compute_gift_split(self.session, gross_amount)\n',
    )
    replace_exact(
        "backend/app/gift_engine/canonical_service.py",
        'fee_rule_version="1",',
        'fee_rule_version=split.policy_version,',
    )
    replace_exact(
        "backend/app/gift_engine/canonical_service.py",
        '        self.event_publisher.publish(event)\n',
        '        self.wallet_service._stage_domain_event(self.session, event=event, durable=True)\n',
    )

    # Remove the canonical hard-coded 5 gifts/minute limiter. Admin SpendingControl is authoritative.
    edit(
        "backend/app/gift_engine/canonical_service.py",
        lambda text: re.sub(
            r'\n        if requested_scope == "gtex_competition" and recipient_user_id:[\s\S]*?\n\n        self\.ensure_football_gift_catalog\(\)',
            '\n        self.ensure_football_gift_catalog()',
            text,
            count=1,
        ),
    )

    # WalletService no longer owns a 10%/5 Coin fallback; omitted values resolve centrally.
    wallet = "backend/app/wallets/service.py"
    edit(wallet, lambda text: text.replace(
        '        withdrawal_fee_bps: int = 1000,\n        minimum_fee: Decimal = Decimal("5.0000"),\n',
        '        withdrawal_fee_bps: int | None = None,\n        minimum_fee: Decimal | None = None,\n',
        1,
    ))
    edit(wallet, lambda text: text.replace('''        fee_tag = LedgerSourceTag.WITHDRAWAL_FEE_BURN\n        fee_amount = self._normalize_amount(\n            max(\n                (normalized_amount * Decimal(withdrawal_fee_bps) / Decimal(10_000)), self._normalize_amount(minimum_fee)\n            )\n        )\n''', '''        fee_tag = LedgerSourceTag.WITHDRAWAL_FEE_BURN\n        if withdrawal_fee_bps is None or minimum_fee is None:\n            from app.economy.economic_policy import resolve_economic_policy\n            policy = resolve_economic_policy(session)\n            withdrawal_fee_bps = policy.withdrawal_fee_bps if withdrawal_fee_bps is None else withdrawal_fee_bps\n            minimum_fee = policy.minimum_withdrawal_fee_credits if minimum_fee is None else minimum_fee\n        fee_amount = self._normalize_amount(\n            max(\n                (normalized_amount * Decimal(withdrawal_fee_bps) / Decimal(10_000)), self._normalize_amount(minimum_fee)\n            )\n        )\n''', 1))
    edit(wallet, lambda text: text.replace(
        '                    "total_debit": str(total_debit),\n',
        '                    "total_debit": str(total_debit),\n                    "fee_policy_rule_key": (policy.rule.rule_key if "policy" in locals() else None),\n                    "fee_policy_version": (policy.policy_version if "policy" in locals() else None),\n                    "fee_policy_effective_at": (policy.effective_at.isoformat() if "policy" in locals() else None),\n',
        1,
    ))

    print("Phase A consistency repairs applied")


if __name__ == "__main__":
    main()
