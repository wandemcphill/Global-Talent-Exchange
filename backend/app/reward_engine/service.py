from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from app.economy.economic_policy import EconomicPolicyUnavailableError, compute_competition_reward_split
from app.economy.governor_service import EconomyGovernorService
from app.models.base import generate_uuid
from app.models.economy_burn_event import EconomyBurnEvent
from app.models.reward_settlement import RewardSettlement
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit
from app.services.spending_control_service import SpendingControlService, SpendingControlViolation
from app.wallets.service import LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal('0.0001')


class RewardEngineError(ValueError):
    def __init__(self, detail: str, *, reason: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.reason = reason or detail


@dataclass(slots=True)
class RewardEngineService:
    session: Session
    wallet_service: WalletService | None = None
    event_publisher: EventPublisher | None = None

    def __post_init__(self) -> None:
        if self.event_publisher is None:
            self.event_publisher = InMemoryEventPublisher()
        if self.wallet_service is None:
            self.wallet_service = WalletService(event_publisher=self.event_publisher)

    def _normalize_amount(self, amount: Decimal | int | float | str) -> Decimal:
        return Decimal(str(amount)).quantize(AMOUNT_QUANTUM)

    @staticmethod
    def _reward_source_tag(reward_source: str) -> LedgerSourceTag:
        normalized = (reward_source or "").strip().lower()
        if "national" in normalized:
            return LedgerSourceTag.NATIONAL_COMPETITION_REWARD
        return LedgerSourceTag.PLATFORM_COMPETITION_REWARD

    @staticmethod
    def _reward_transaction_type(reward_source: str) -> LedgerTransactionType:
        if "lottery" in (reward_source or "").strip().lower():
            return LedgerTransactionType.LOTTERY_REWARD
        return LedgerTransactionType.MATCH_REWARD

    def settle_reward(
        self,
        *,
        actor: User,
        user_id: str,
        competition_key: str,
        title: str,
        gross_amount: Decimal,
        reward_source: str = 'gtex_promotional_pool',
        note: str | None = None,
        ledger_unit: LedgerUnit = LedgerUnit.COIN,
    ) -> RewardSettlement:
        user = self.session.get(User, user_id)
        if user is None or not user.is_active:
            raise RewardEngineError('Reward recipient user was not found.', reason="recipient_not_found")
        governor = EconomyGovernorService(self.session, wallet_service=self.wallet_service)
        normalized_gross = self._normalize_amount(Decimal(gross_amount) * governor.reward_multiplier())
        if normalized_gross <= Decimal('0.0000'):
            raise RewardEngineError('Reward amount must be positive.', reason="reward_amount_invalid")
        try:
            split = compute_competition_reward_split(self.session, normalized_gross)
        except EconomicPolicyUnavailableError as exc:
            raise RewardEngineError(str(exc), reason="economic_policy_unavailable") from exc
        fee_amount = self._normalize_amount(split.platform_amount)
        burn_amount = self._normalize_amount(split.burn_amount)
        net_amount = self._normalize_amount(normalized_gross - fee_amount - burn_amount)
        source_tag = self._reward_source_tag(reward_source)
        transaction_type = self._reward_transaction_type(reward_source)
        user_account = self.wallet_service.get_user_account(self.session, user, ledger_unit)
        platform_account = self.wallet_service.ensure_platform_account(self.session, ledger_unit)
        promo_pool_account = self.wallet_service.ensure_promo_pool_account(self.session, ledger_unit)
        promo_pool_balance = self.wallet_service.get_balance(self.session, promo_pool_account)
        if promo_pool_balance < normalized_gross:
            raise RewardEngineError("Promo pool balance is lower than the reward amount.", reason="promo_pool_insufficient")
        control_reference = f"reward-control:{competition_key}:{user.id}:{generate_uuid()}"
        try:
            control_evaluation = SpendingControlService(self.session).evaluate_reward(
                reference_key=control_reference,
                amount=normalized_gross,
                ledger_unit=ledger_unit,
                actor_user_id=actor.id,
                target_user_id=user.id,
                competition_key=competition_key,
                reward_source=reward_source,
                metadata_json={
                    "title": title,
                    "competition_key": competition_key,
                    "reward_source": reward_source,
                },
            )
        except SpendingControlViolation as exc:
            raise RewardEngineError(exc.detail, reason="spending_controls_blocked") from exc
        postings = [
            LedgerPosting(account=user_account, amount=net_amount, source_tag=source_tag, transaction_type=transaction_type),
            LedgerPosting(account=platform_account, amount=fee_amount, source_tag=source_tag, transaction_type=transaction_type),
            LedgerPosting(account=promo_pool_account, amount=-normalized_gross, source_tag=source_tag, transaction_type=transaction_type),
        ]
        if burn_amount > Decimal("0.0000"):
            burn_account = self.wallet_service.ensure_platform_burn_account(self.session, ledger_unit)
            postings.append(
                LedgerPosting(
                    account=burn_account,
                    amount=burn_amount,
                    source_tag=source_tag,
                    transaction_type=transaction_type,
                )
            )
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=postings,
            reason=LedgerEntryReason.COMPETITION_REWARD,
            source_tag=source_tag,
            reference=f'reward:{competition_key}:{user.id}',
            description=f'Competition reward for {title}',
            external_reference=f'reward:{competition_key}:{user.id}',
            actor=actor,
            transaction_type=transaction_type,
        )
        settlement = RewardSettlement(
            user_id=user.id,
            competition_key=competition_key,
            reward_source=reward_source,
            title=title,
            gross_amount=normalized_gross,
            platform_fee_amount=fee_amount,
            net_amount=net_amount,
            ledger_unit=ledger_unit,
            ledger_transaction_id=entries[0].transaction_id if entries else None,
            note=note,
            settled_by_user_id=actor.id,
        )
        self.session.add(settlement)
        self.session.flush()
        SpendingControlService(self.session).record_evaluation(
            control_evaluation,
            entity_id=settlement.id,
            ledger_transaction_id=entries[0].transaction_id if entries else None,
            metadata_json={"reward_settlement_id": settlement.id},
        )
        if burn_amount > Decimal("0.0000"):
            burn_event = EconomyBurnEvent(
                user_id=user.id,
                source_type="reward",
                source_id=settlement.id,
                amount=burn_amount,
                unit=ledger_unit,
                reason="reward_burn",
                ledger_transaction_id=entries[0].transaction_id if entries else None,
                metadata_json={"rule_key": split.rule_key or "fallback"},
            )
            self.session.add(burn_event)
        self.event_publisher.publish(
            DomainEvent(
                name="reward_granted",
                payload={
                    "reward_settlement_id": settlement.id,
                    "user_id": user.id,
                    "competition_key": competition_key,
                    "reward_source": reward_source,
                    "gross_amount": str(normalized_gross),
                    "net_amount": str(net_amount),
                    "ledger_unit": ledger_unit.value,
                    "transaction_id": entries[0].transaction_id if entries else None,
                },
            )
        )
        return settlement

    def credit_promo_pool(
        self,
        *,
        actor: User,
        amount: Decimal,
        unit: LedgerUnit = LedgerUnit.COIN,
        reference: str | None = None,
        note: str | None = None,
    ) -> tuple[str | None, str]:
        normalized_amount = self._normalize_amount(amount)
        if normalized_amount <= Decimal("0.0000"):
            raise RewardEngineError("Promo pool credit amount must be positive.")
        promo_pool_account = self.wallet_service.ensure_promo_pool_account(self.session, unit)
        platform_account = self.wallet_service.ensure_platform_account(self.session, unit)
        resolved_reference = reference or f"promo-pool:{generate_uuid()}"
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(
                    account=platform_account,
                    amount=-normalized_amount,
                    source_tag=LedgerSourceTag.PROMO_POOL_CREDIT,
                    transaction_type=LedgerTransactionType.PROMO_POOL_CREDIT,
                ),
                LedgerPosting(
                    account=promo_pool_account,
                    amount=normalized_amount,
                    source_tag=LedgerSourceTag.PROMO_POOL_CREDIT,
                    transaction_type=LedgerTransactionType.PROMO_POOL_CREDIT,
                ),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.PROMO_POOL_CREDIT,
            reference=resolved_reference,
            description=note or "Promo pool credit",
            actor=actor,
            transaction_type=LedgerTransactionType.PROMO_POOL_CREDIT,
        )
        transaction_id = entries[0].transaction_id if entries else None
        self.event_publisher.publish(
            DomainEvent(
                name="promo_pool_credited",
                payload={
                    "transaction_id": transaction_id,
                    "amount": str(normalized_amount),
                    "unit": unit.value,
                    "reference": resolved_reference,
                },
            )
        )
        return transaction_id, resolved_reference

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
