from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, ROUND_FLOOR
from enum import StrEnum
from random import Random
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.economy.economy_service import EconomyService
from app.economy.governor_service import EconomyGovernorService
from app.models.base import generate_uuid, utcnow
from app.models.economy_daily_stat import EconomyDailyStat
from app.models.reward_settlement import RewardSettlement
from app.models.user import User, UserRole
from app.models.wallet import (
    LedgerAccount,
    LedgerAccountKind,
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerTransactionType,
    LedgerUnit,
)
from app.services.spending_control_service import SpendingControlService
from app.wallets.service import LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
DEFAULT_LOTTERY_TRIGGER_STEP = Decimal("10000.0000")
DEFAULT_LOTTERY_REWARDS: tuple[Decimal, ...] = (
    Decimal("10.0000"),
    Decimal("25.0000"),
    Decimal("50.0000"),
)
DEFAULT_ACTIVITY_WINDOW = timedelta(days=30)
TREASURY_ENTRY_SHARE_BPS = 2000


class MatchEconomyError(ValueError):
    pass


class MatchEconomyType(StrEnum):
    GTEX_HOSTED = "gtex_hosted"
    USER_HOSTED = "user_hosted"
    FAST_MATCH = "fast_match"


@dataclass(frozen=True, slots=True)
class MatchEconomyContext:
    match_id: str
    match_type: str
    entry_fee: Decimal = Decimal("0.0000")
    prize_pool_unit: LedgerUnit = LedgerUnit.COIN
    title: str = "Match"


@dataclass(frozen=True, slots=True)
class MatchJoinResult:
    transaction_id: str | None
    reference: str
    charged_amount: Decimal
    prize_pool_account_code: str
    prize_pool_balance: Decimal
    payment_unit: LedgerUnit


@dataclass(frozen=True, slots=True)
class MatchPrizeFundingResult:
    transaction_id: str
    reference: str
    funded_amount: Decimal
    source_account_code: str
    prize_pool_account_code: str
    prize_pool_balance: Decimal


@dataclass(frozen=True, slots=True)
class LotteryRewardResult:
    winner_user_id: str
    reward_amount: Decimal
    transaction_id: str
    reference: str
    threshold_index: int
    ledger_unit: LedgerUnit


@dataclass(frozen=True, slots=True)
class LotteryTriggerResult:
    previous_volume: Decimal
    current_volume: Decimal
    trigger_step: Decimal
    triggered_rewards: tuple[LotteryRewardResult, ...]


@dataclass(slots=True)
class MatchEconomyEngine:
    session: Session
    wallet_service: WalletService | None = None
    economy_service: EconomyService | None = None
    randomizer: Random | None = None

    def __post_init__(self) -> None:
        if self.wallet_service is None:
            self.wallet_service = WalletService()
        if self.economy_service is None:
            self.economy_service = EconomyService(self.session, wallet_service=self.wallet_service)
        if self.randomizer is None:
            self.randomizer = Random()

    def get_entry_fee(self, match: MatchEconomyContext) -> Decimal:
        match_type = str(match.match_type).strip().lower()
        if match_type == MatchEconomyType.GTEX_HOSTED:
            return Decimal("0.0000")
        if match_type in {MatchEconomyType.USER_HOSTED, MatchEconomyType.FAST_MATCH}:
            return self._normalize_amount(match.entry_fee)
        raise MatchEconomyError(f"Unsupported match type: {match.match_type}")

    def ensure_prize_pool_account(self, match: MatchEconomyContext) -> LedgerAccount:
        code = f"match:{match.match_id}:{match.prize_pool_unit.value}:prize_pool"
        account = self.session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is None:
            account = LedgerAccount(
                code=code,
                label=f"{match.title} Prize Pool",
                unit=match.prize_pool_unit,
                kind=LedgerAccountKind.ESCROW,
            )
            self.session.add(account)
            self.session.flush()
        return account

    def join_match(
        self,
        *,
        user: User,
        match: MatchEconomyContext,
        actor: User | None = None,
        reference: str | None = None,
        idempotency_key: str | None = None,
    ) -> MatchJoinResult:
        prize_pool_account = self.ensure_prize_pool_account(match)
        entry_fee = self.get_entry_fee(match)
        resolved_reference = reference or f"match-join:{match.match_id}:{user.id}"
        if entry_fee <= Decimal("0.0000"):
            return MatchJoinResult(
                transaction_id=None,
                reference=resolved_reference,
                charged_amount=Decimal("0.0000"),
                prize_pool_account_code=prize_pool_account.code,
                prize_pool_balance=self.wallet_service.get_balance(self.session, prize_pool_account),
                payment_unit=match.prize_pool_unit,
            )

        payment = self.economy_service.collect_match_entry(
            user=user,
            payment_unit=match.prize_pool_unit,
            gross_amount=entry_fee,
            destination_account=prize_pool_account,
            fee_bps=0,
            treasury_account=self.wallet_service.ensure_treasury_account(self.session, match.prize_pool_unit),
            treasury_share_bps=TREASURY_ENTRY_SHARE_BPS,
            reference=resolved_reference,
            external_reference=resolved_reference,
            description=f"{match.title} entry fee",
            source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
            actor=actor or user,
            idempotency_key=idempotency_key,
            metadata={
                "match_economy": {
                    "match_id": match.match_id,
                    "match_type": str(match.match_type),
                    "flow": "join_match",
                }
            },
        )
        return MatchJoinResult(
            transaction_id=payment.transaction_id,
            reference=payment.reference,
            charged_amount=payment.gross_amount,
            prize_pool_account_code=prize_pool_account.code,
            prize_pool_balance=self.wallet_service.get_balance(self.session, prize_pool_account),
            payment_unit=payment.payment_unit,
        )

    def fund_gtex_match(
        self,
        *,
        match: MatchEconomyContext,
        prize_amount: Decimal,
        actor: User | None = None,
        reference: str | None = None,
    ) -> MatchPrizeFundingResult:
        amount = self._normalize_amount(prize_amount)
        if amount <= Decimal("0.0000"):
            raise MatchEconomyError("GTEX match prize funding amount must be positive.")
        if str(match.match_type).strip().lower() != MatchEconomyType.GTEX_HOSTED.value:
            raise MatchEconomyError("GTEX prize funding is only valid for GTEX hosted matches.")

        prize_pool_account = self.ensure_prize_pool_account(match)
        governor = EconomyGovernorService(self.session, wallet_service=self.wallet_service)
        funded_amount = governor.scale_reward_amount(amount=amount, unit=match.prize_pool_unit)
        if funded_amount <= Decimal("0.0000"):
            raise MatchEconomyError("Treasury controls blocked this GTEX match funding request.")

        promo_pool_account = self.wallet_service.ensure_promo_pool_account(self.session, match.prize_pool_unit)
        promo_pool_balance = self.wallet_service.get_balance(self.session, promo_pool_account)
        promo_pool_top_up = self._normalize_amount(max(funded_amount - promo_pool_balance, Decimal("0.0000")))
        if promo_pool_top_up > Decimal("0.0000"):
            if not governor.can_fund_match(amount=promo_pool_top_up, unit=match.prize_pool_unit):
                raise MatchEconomyError("Treasury reserve would fall below the required 3x match buffer.")
            treasury_account = self.wallet_service.ensure_treasury_account(self.session, match.prize_pool_unit)
            self.wallet_service.append_transaction(
                self.session,
                postings=[
                    LedgerPosting(
                        account=treasury_account,
                        amount=-promo_pool_top_up,
                        source_tag=LedgerSourceTag.PROMO_POOL_CREDIT,
                        transaction_type=LedgerTransactionType.PROMO_POOL_CREDIT,
                    ),
                    LedgerPosting(
                        account=promo_pool_account,
                        amount=promo_pool_top_up,
                        source_tag=LedgerSourceTag.PROMO_POOL_CREDIT,
                        transaction_type=LedgerTransactionType.PROMO_POOL_CREDIT,
                    ),
                ],
                reason=LedgerEntryReason.ADJUSTMENT,
                source_tag=LedgerSourceTag.PROMO_POOL_CREDIT,
                reference=f"gtex-promo-topup:{match.match_id}:{generate_uuid()}",
                external_reference=f"gtex-promo-topup:{match.match_id}",
                description=f"Treasury top-up for {match.title} rewards pool",
                actor=actor,
                transaction_type=LedgerTransactionType.PROMO_POOL_CREDIT,
                metadata={
                    "match_economy": {
                        "match_id": match.match_id,
                        "match_type": str(match.match_type),
                        "flow": "treasury_to_rewards_pool",
                    }
                },
            )

        resolved_reference = reference or f"gtex-match-funding:{match.match_id}:{generate_uuid()}"
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(
                    account=promo_pool_account,
                    amount=-funded_amount,
                    source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD,
                ),
                LedgerPosting(
                    account=prize_pool_account,
                    amount=funded_amount,
                    source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD,
                ),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD,
            reference=resolved_reference,
            external_reference=resolved_reference,
            description=f"GTEX prize funding for {match.title}",
            actor=actor,
            metadata={
                "match_economy": {
                    "match_id": match.match_id,
                    "match_type": str(match.match_type),
                    "flow": "fund_gtex_match",
                }
            },
        )
        return MatchPrizeFundingResult(
            transaction_id=entries[0].transaction_id,
            reference=resolved_reference,
            funded_amount=funded_amount,
            source_account_code=promo_pool_account.code,
            prize_pool_account_code=prize_pool_account.code,
            prize_pool_balance=self.wallet_service.get_balance(self.session, prize_pool_account),
        )

    def record_match_volume(
        self,
        *,
        amount: Decimal,
        unit: LedgerUnit,
        actor: User | None = None,
        trigger_step: Decimal = DEFAULT_LOTTERY_TRIGGER_STEP,
        reward_options: Sequence[Decimal] = DEFAULT_LOTTERY_REWARDS,
        activity_window: timedelta = DEFAULT_ACTIVITY_WINDOW,
    ) -> LotteryTriggerResult:
        normalized_increment = self._coin_volume(amount=amount, unit=unit)
        threshold = self._normalize_amount(trigger_step)
        if threshold <= Decimal("0.0000"):
            raise MatchEconomyError("Lottery trigger step must be positive.")

        previous_volume = self.total_match_volume()
        stats = self._get_or_create_daily_stat()
        stats.match_spend_amount = self._normalize_amount(stats.match_spend_amount + normalized_increment)
        self.session.flush()

        current_volume = self._normalize_amount(previous_volume + normalized_increment)
        previous_threshold_index = self._threshold_index(previous_volume, threshold)
        current_threshold_index = self._threshold_index(current_volume, threshold)

        rewards: list[LotteryRewardResult] = []
        for threshold_index in range(previous_threshold_index + 1, current_threshold_index + 1):
            rewards.append(
                self.run_lottery(
                    threshold_index=threshold_index,
                    actor=actor,
                    reward_options=reward_options,
                    activity_window=activity_window,
                )
            )

        return LotteryTriggerResult(
            previous_volume=previous_volume,
            current_volume=current_volume,
            trigger_step=threshold,
            triggered_rewards=tuple(rewards),
        )

    def run_lottery(
        self,
        *,
        threshold_index: int,
        actor: User | None = None,
        reward_options: Sequence[Decimal] = DEFAULT_LOTTERY_REWARDS,
        activity_window: timedelta = DEFAULT_ACTIVITY_WINDOW,
    ) -> LotteryRewardResult:
        normalized_rewards = self._normalize_reward_options(reward_options)
        eligible_users = self.list_eligible_users(activity_window=activity_window)
        if not eligible_users:
            raise MatchEconomyError("No eligible users are available for the lottery.")

        winner = self.randomizer.choice(eligible_users)
        reward_amount = self.randomizer.choice(normalized_rewards)
        reward_amount = EconomyGovernorService(
            self.session,
            wallet_service=self.wallet_service,
        ).scale_reward_amount(amount=reward_amount, unit=LedgerUnit.COIN)
        if reward_amount <= Decimal("0.0000"):
            raise MatchEconomyError("Treasury controls reduced the lottery reward below the minimum payout.")

        promo_pool_account = self.wallet_service.ensure_promo_pool_account(self.session, LedgerUnit.COIN)
        if self.wallet_service.get_balance(self.session, promo_pool_account) < reward_amount:
            raise MatchEconomyError("Rewards pool balance is lower than the lottery reward.")

        reference = f"lottery:{threshold_index}:{winner.id}"
        control_reference = f"lottery-control:{threshold_index}:{winner.id}"
        control = SpendingControlService(self.session).evaluate_reward(
            reference_key=control_reference,
            amount=reward_amount,
            ledger_unit=LedgerUnit.COIN,
            actor_user_id=actor.id if actor is not None else None,
            target_user_id=winner.id,
            competition_key=f"lottery:{threshold_index}",
            reward_source="lottery_volume_trigger",
            metadata_json={
                "threshold_index": threshold_index,
                "reward_origin": "match_volume",
            },
        )

        winner_account = self.wallet_service.get_user_account(self.session, winner, LedgerUnit.COIN)
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(
                    account=winner_account,
                    amount=reward_amount,
                    source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD,
                ),
                LedgerPosting(
                    account=promo_pool_account,
                    amount=-reward_amount,
                    source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD,
                ),
            ],
            reason=LedgerEntryReason.COMPETITION_REWARD,
            source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD,
            reference=reference,
            external_reference=reference,
            description="Volume-triggered lottery reward",
            actor=actor,
            metadata={
                "match_economy": {
                    "flow": "run_lottery",
                    "threshold_index": threshold_index,
                }
            },
        )
        settlement = RewardSettlement(
            user_id=winner.id,
            competition_key=f"lottery:{threshold_index}",
            reward_source="lottery_volume_trigger",
            title="Volume Lottery Reward",
            gross_amount=reward_amount,
            platform_fee_amount=Decimal("0.0000"),
            net_amount=reward_amount,
            ledger_unit=LedgerUnit.COIN,
            ledger_transaction_id=entries[0].transaction_id,
            note="Triggered by match volume threshold.",
            settled_by_user_id=actor.id if actor is not None else None,
        )
        self.session.add(settlement)
        self.session.flush()
        SpendingControlService(self.session).record_evaluation(
            control,
            entity_id=settlement.id,
            ledger_transaction_id=entries[0].transaction_id,
            metadata_json={"reward_settlement_id": settlement.id},
        )
        return LotteryRewardResult(
            winner_user_id=winner.id,
            reward_amount=reward_amount,
            transaction_id=entries[0].transaction_id,
            reference=reference,
            threshold_index=threshold_index,
            ledger_unit=LedgerUnit.COIN,
        )

    def list_eligible_users(self, *, activity_window: timedelta = DEFAULT_ACTIVITY_WINDOW) -> list[User]:
        cutoff = utcnow() - activity_window
        statement = (
            select(User)
            .where(
                User.is_active.is_(True),
                User.role.notin_((UserRole.ADMIN, UserRole.SUPER_ADMIN)),
                func.coalesce(User.last_login_at, User.created_at) >= cutoff,
            )
            .order_by(User.created_at.asc(), User.id.asc())
        )
        return list(self.session.scalars(statement).all())

    def total_match_volume(self) -> Decimal:
        total = self.session.scalar(select(func.coalesce(func.sum(EconomyDailyStat.match_spend_amount), 0)))
        return self._normalize_amount(total or 0)

    def _get_or_create_daily_stat(self) -> EconomyDailyStat:
        today = utcnow().date()
        item = self.session.get(EconomyDailyStat, today)
        if item is None:
            item = EconomyDailyStat(date=today)
            self.session.add(item)
            self.session.flush()
        return item

    def _coin_volume(self, *, amount: Decimal, unit: LedgerUnit) -> Decimal:
        normalized_amount = self._normalize_amount(amount)
        if normalized_amount <= Decimal("0.0000"):
            raise MatchEconomyError("Recorded match volume must be positive.")
        # Match-volume accounting is already expressed in the economic unit supplied by
        # the caller.  Fan Coin is intentionally not reverse-convertible into GTEX Coin.
        # Normalize the recorded volume directly rather than invoking the wallet
        # conversion API, which correctly rejects CREDIT -> COIN conversion.
        if unit in {LedgerUnit.COIN, LedgerUnit.CREDIT}:
            return normalized_amount
        raise MatchEconomyError(f"Unsupported match volume unit: {unit!s}")

    @staticmethod
    def _threshold_index(amount: Decimal, threshold: Decimal) -> int:
        return int((amount / threshold).to_integral_value(rounding=ROUND_FLOOR))

    def _normalize_reward_options(self, reward_options: Sequence[Decimal]) -> tuple[Decimal, ...]:
        normalized_items: list[Decimal] = []
        for item in reward_options:
            normalized = self._normalize_amount(item)
            if normalized > Decimal("0.0000"):
                normalized_items.append(normalized)
        normalized = tuple(normalized_items)
        if not normalized:
            raise MatchEconomyError("Lottery rewards must contain at least one positive amount.")
        return normalized

    @staticmethod
    def _normalize_amount(amount: Decimal | int | float | str) -> Decimal:
        return Decimal(str(amount)).quantize(AMOUNT_QUANTUM)


__all__ = [
    "DEFAULT_ACTIVITY_WINDOW",
    "DEFAULT_LOTTERY_REWARDS",
    "DEFAULT_LOTTERY_TRIGGER_STEP",
    "LotteryRewardResult",
    "LotteryTriggerResult",
    "MatchEconomyContext",
    "MatchEconomyEngine",
    "MatchEconomyError",
    "MatchEconomyType",
    "MatchJoinResult",
    "MatchPrizeFundingResult",
]
