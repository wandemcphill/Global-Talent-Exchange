from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.admin_engine.service import AdminEngineService
from backend.app.economy.service import EconomyConfigService
from backend.app.models.economy_burn_event import EconomyBurnEvent
from backend.app.models.reward_settlement import RewardSettlement
from backend.app.models.user import User
from backend.app.models.wallet import LedgerEntryReason, LedgerUnit
from backend.app.wallets.service import LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal('0.0001')


class RewardEngineError(ValueError):
    pass


@dataclass(slots=True)
class RewardEngineService:
    session: Session
    wallet_service: WalletService | None = None

    def __post_init__(self) -> None:
        if self.wallet_service is None:
            self.wallet_service = WalletService()

    def _normalize_amount(self, amount: Decimal | int | float | str) -> Decimal:
        return Decimal(str(amount)).quantize(AMOUNT_QUANTUM)

    def _active_competition_fee_bps(self) -> int:
        rule = next(iter(AdminEngineService(self.session).list_reward_rules(active_only=True)), None)
        return int(rule.competition_platform_fee_bps if rule is not None else 1000)

    def settle_reward(self, *, actor: User, user_id: str, competition_key: str, title: str, gross_amount: Decimal, reward_source: str = 'gtex_promotional_pool', note: str | None = None) -> RewardSettlement:
        user = self.session.get(User, user_id)
        if user is None or not user.is_active:
            raise RewardEngineError('Reward recipient user was not found.')
        normalized_gross = self._normalize_amount(gross_amount)
        if normalized_gross <= Decimal('0.0000'):
            raise RewardEngineError('Reward amount must be positive.')
        economy_service = EconomyConfigService(self.session)
        split = economy_service.compute_revenue_split(
            scope="competition_reward",
            gross_amount=normalized_gross,
            fallback_platform_bps=self._active_competition_fee_bps(),
        )
        fee_amount = self._normalize_amount(split.platform_amount)
        burn_amount = self._normalize_amount(split.burn_amount)
        net_amount = self._normalize_amount(normalized_gross - fee_amount - burn_amount)
        user_account = self.wallet_service.get_user_account(self.session, user, LedgerUnit.CREDIT)
        platform_account = self.wallet_service.ensure_platform_account(self.session, LedgerUnit.CREDIT)
        postings = [
            LedgerPosting(account=user_account, amount=net_amount),
            LedgerPosting(account=platform_account, amount=fee_amount - normalized_gross),
        ]
        if burn_amount > Decimal("0.0000"):
            burn_account = self.wallet_service.ensure_platform_burn_account(self.session, LedgerUnit.CREDIT)
            postings.append(LedgerPosting(account=burn_account, amount=burn_amount))
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=postings,
            reason=LedgerEntryReason.COMPETITION_REWARD,
            reference=f'reward:{competition_key}:{user.id}',
            description=f'Competition reward for {title}',
            external_reference=f'reward:{competition_key}:{user.id}',
            actor=actor,
        )
        settlement = RewardSettlement(
            user_id=user.id,
            competition_key=competition_key,
            reward_source=reward_source,
            title=title,
            gross_amount=normalized_gross,
            platform_fee_amount=fee_amount,
            net_amount=net_amount,
            ledger_unit=LedgerUnit.CREDIT,
            ledger_transaction_id=entries[0].transaction_id if entries else None,
            note=note,
            settled_by_user_id=actor.id,
        )
        self.session.add(settlement)
        self.session.flush()
        if burn_amount > Decimal("0.0000"):
            burn_event = EconomyBurnEvent(
                user_id=user.id,
                source_type="reward",
                source_id=settlement.id,
                amount=burn_amount,
                unit=LedgerUnit.CREDIT,
                reason="reward_burn",
                ledger_transaction_id=entries[0].transaction_id if entries else None,
                metadata_json={"rule_key": split.rule_key or "fallback"},
            )
            self.session.add(burn_event)
        return settlement

    def list_settlements_for_user(self, *, user: User, limit: int = 50) -> list[RewardSettlement]:
        stmt = select(RewardSettlement).where(RewardSettlement.user_id == user.id).order_by(RewardSettlement.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def summary_for_user(self, *, user: User) -> dict[str, Decimal | list[RewardSettlement]]:
        total_rewards = self._normalize_amount(self.session.scalar(select(func.coalesce(func.sum(RewardSettlement.net_amount), 0)).where(RewardSettlement.user_id == user.id)) or 0)
        total_platform_fee = self._normalize_amount(self.session.scalar(select(func.coalesce(func.sum(RewardSettlement.platform_fee_amount), 0)).where(RewardSettlement.user_id == user.id)) or 0)
        return {
            'total_rewards': total_rewards,
            'total_platform_fee': total_platform_fee,
            'settlements': self.list_settlements_for_user(user=user, limit=20),
        }
