from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import generate_uuid, utcnow
from app.models.economy_daily_stat import EconomyDailyStat
from app.models.economy_governor import EconomyGovernorPolicy
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.wallets.service import (
    LedgerPosting,
    WalletConversionQuote,
    WalletConversionResult,
    WalletService,
)

AMOUNT_QUANTUM = Decimal("0.0001")
MIN_MULTIPLIER = Decimal("0.1000")
MAX_MULTIPLIER = Decimal("5.0000")
TREASURY_BUFFER_MULTIPLE = Decimal("3.0000")
TREASURY_LOW_BALANCE_THRESHOLD = Decimal("25.0000")


class EconomyGovernorError(ValueError):
    pass


class EconomyGovernorModeError(EconomyGovernorError):
    pass


class EconomyGovernorService:
    def __init__(self, session: Session, *, wallet_service: WalletService | None = None) -> None:
        self.session = session
        self.wallet_service = wallet_service or WalletService()

    def get_policy(self) -> EconomyGovernorPolicy:
        policy = self.session.scalar(
            select(EconomyGovernorPolicy).where(EconomyGovernorPolicy.policy_key == "default")
        )
        if policy is None:
            policy = EconomyGovernorPolicy(policy_key="default")
            self.session.add(policy)
            self.session.flush()
        return policy

    def derive_metrics(self) -> dict[str, Decimal]:
        stat = self.session.scalars(
            select(EconomyDailyStat).order_by(EconomyDailyStat.date.desc()).limit(1)
        ).first()
        if stat is None:
            return {
                "gtex_supply": Decimal("0.0000"),
                "fan_supply": Decimal("0.0000"),
                "daily_burn": Decimal("0.0000"),
                "daily_mint": Decimal("0.0000"),
                "avg_user_spend": Decimal("0.0000"),
                "inflation_rate": Decimal("0.0000"),
                "treasury_balance": self.treasury_balance(),
                "rewards_pool_balance": self.rewards_pool_balance(),
                "liquidity_pool_balance": self.liquidity_pool_balance(),
                "treasury_reward_threshold": self.treasury_reward_threshold(),
                "treasury_buffer_multiple": TREASURY_BUFFER_MULTIPLE,
            }
        daily_burn = self._amount(Decimal(stat.gtex_burned) + Decimal(stat.fan_burned))
        daily_mint = self._amount(Decimal(stat.gtex_minted) + Decimal(stat.fan_minted))
        match_entry_count = int((stat.metadata_json or {}).get("match_entry_count", 0) or 0)
        avg_user_spend = (
            self._amount(Decimal(stat.match_spend_amount) / Decimal(match_entry_count))
            if match_entry_count > 0
            else Decimal("0.0000")
        )
        supply = self._amount(Decimal(stat.gtex_supply) + Decimal(stat.fan_supply))
        inflation_rate = (
            self._amount((daily_mint - daily_burn) / supply)
            if supply > Decimal("0.0000")
            else Decimal("0.0000")
        )
        return {
            "gtex_supply": self._amount(stat.gtex_supply),
            "fan_supply": self._amount(stat.fan_supply),
            "daily_burn": daily_burn,
            "daily_mint": daily_mint,
            "avg_user_spend": avg_user_spend,
            "inflation_rate": inflation_rate,
            "treasury_balance": self.treasury_balance(),
            "rewards_pool_balance": self.rewards_pool_balance(),
            "liquidity_pool_balance": self.liquidity_pool_balance(),
            "treasury_reward_threshold": self.treasury_reward_threshold(),
            "treasury_buffer_multiple": TREASURY_BUFFER_MULTIPLE,
        }

    def evaluate(self, *, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
        policy = self.get_policy()
        normalized_metrics = self._normalize_metrics(metrics or self.derive_metrics())
        actions: list[dict[str, Any]] = []

        if normalized_metrics["daily_mint"] > normalized_metrics["daily_burn"]:
            actions.append({"type": "increase_entry_fee", "value": "0.1000"})
            actions.append({"type": "reduce_rewards", "value": "0.1500"})

        if normalized_metrics["avg_user_spend"] < Decimal("20.0000"):
            actions.append({"type": "reduce_match_cost", "value": "0.1000"})

        if normalized_metrics["inflation_rate"] >= Decimal("0.1500"):
            actions.append({"type": "increase_burn_rate", "value": "0.0500"})
            actions.append({"type": "boost_conversion_incentive", "value": 250})

        if (
            normalized_metrics["treasury_balance"] > Decimal("0.0000")
            and normalized_metrics["treasury_balance"] < normalized_metrics["treasury_reward_threshold"]
            and not any(str(action.get("type") or "").strip().lower() == "reduce_rewards" for action in actions)
        ):
            actions.append({"type": "reduce_rewards", "value": "0.2000"})

        policy.last_metrics_json = self._metrics_payload(normalized_metrics)
        policy.last_actions_json = [dict(action) for action in actions]
        policy.last_evaluated_at = utcnow()
        self.session.flush()
        return {
            "mode": policy.mode,
            "metrics": policy.last_metrics_json,
            "actions": policy.last_actions_json,
        }

    def update_policy(
        self,
        *,
        actor: User,
        mode: str | None = None,
        tournament_entry_multiplier: Decimal | None = None,
        match_view_cost_multiplier: Decimal | None = None,
        reward_payout_multiplier: Decimal | None = None,
        conversion_bonus_bps: int | None = None,
        burn_bonus_bps: int | None = None,
    ) -> EconomyGovernorPolicy:
        policy = self.get_policy()
        if mode is not None:
            normalized_mode = mode.strip().lower()
            if normalized_mode not in {"auto", "manual"}:
                raise EconomyGovernorModeError("Governor mode must be auto or manual.")
            policy.mode = normalized_mode
        if tournament_entry_multiplier is not None:
            policy.tournament_entry_multiplier = self._bounded_multiplier(tournament_entry_multiplier)
        if match_view_cost_multiplier is not None:
            policy.match_view_cost_multiplier = self._bounded_multiplier(match_view_cost_multiplier)
        if reward_payout_multiplier is not None:
            policy.reward_payout_multiplier = self._bounded_multiplier(reward_payout_multiplier)
        if conversion_bonus_bps is not None:
            policy.conversion_bonus_bps = max(0, min(5_000, int(conversion_bonus_bps)))
        if burn_bonus_bps is not None:
            policy.burn_bonus_bps = max(0, min(5_000, int(burn_bonus_bps)))
        policy.updated_by_user_id = actor.id
        self.session.flush()
        return policy

    def apply_actions(
        self,
        *,
        actor: User,
        actions: list[dict[str, Any]] | None = None,
        metrics: dict[str, Any] | None = None,
        allow_manual_override: bool = True,
    ) -> dict[str, Any]:
        policy = self.get_policy()
        if policy.mode != "auto" and not allow_manual_override:
            raise EconomyGovernorModeError("Governor policy is in manual mode.")
        evaluation = self.evaluate(metrics=metrics) if actions is None else {
            "actions": actions,
            "metrics": self._metrics_payload(self._normalize_metrics(metrics or self.derive_metrics())),
        }
        applied_actions = list(evaluation["actions"])
        for action in applied_actions:
            action_type = str(action.get("type") or "").strip().lower()
            value = action.get("value")
            if action_type == "increase_entry_fee":
                factor = Decimal("1.0000") + self._amount(value)
                policy.tournament_entry_multiplier = self._bounded_multiplier(
                    Decimal(policy.tournament_entry_multiplier) * factor
                )
            elif action_type == "reduce_match_cost":
                factor = Decimal("1.0000") - self._amount(value)
                policy.match_view_cost_multiplier = self._bounded_multiplier(
                    Decimal(policy.match_view_cost_multiplier) * factor
                )
            elif action_type == "reduce_rewards":
                factor = Decimal("1.0000") - self._amount(value)
                policy.reward_payout_multiplier = self._bounded_multiplier(
                    Decimal(policy.reward_payout_multiplier) * factor
                )
            elif action_type == "boost_conversion_incentive":
                policy.conversion_bonus_bps = max(0, min(5_000, int(policy.conversion_bonus_bps) + int(value or 0)))
            elif action_type == "increase_burn_rate":
                delta_bps = int((self._amount(value) * Decimal("10000")).quantize(Decimal("1")))
                policy.burn_bonus_bps = max(0, min(5_000, int(policy.burn_bonus_bps) + delta_bps))
        policy.updated_by_user_id = actor.id
        policy.last_actions_json = [dict(action) for action in applied_actions]
        policy.last_applied_at = utcnow()
        self.session.flush()
        return self.snapshot(metrics=evaluation.get("metrics"))

    def pricing_multiplier_for_service(self, service_key: str | None) -> Decimal:
        if not service_key:
            return Decimal("1.0000")
        policy = self.get_policy()
        normalized = service_key.strip().lower()
        if normalized == "tournament-entry":
            return self._amount(policy.tournament_entry_multiplier)
        if "match-view" in normalized:
            return self._amount(policy.match_view_cost_multiplier)
        return Decimal("1.0000")

    def reward_multiplier(self, *, unit: LedgerUnit = LedgerUnit.COIN) -> Decimal:
        multiplier = self._amount(self.get_policy().reward_payout_multiplier)
        treasury_balance = self.treasury_balance(unit=unit)
        threshold = self.treasury_reward_threshold(unit=unit)
        if treasury_balance <= Decimal("0.0000") or treasury_balance >= threshold:
            return multiplier
        dynamic_factor = self._bounded_multiplier(treasury_balance / threshold)
        return self._bounded_multiplier(multiplier * dynamic_factor)

    def treasury_balance(self, *, unit: LedgerUnit = LedgerUnit.COIN) -> Decimal:
        return self._non_negative_balance(self.wallet_service.ensure_treasury_account(self.session, unit))

    def rewards_pool_balance(self, *, unit: LedgerUnit = LedgerUnit.COIN) -> Decimal:
        return self._non_negative_balance(self.wallet_service.ensure_rewards_pool_account(self.session, unit))

    def liquidity_pool_balance(self, *, unit: LedgerUnit = LedgerUnit.COIN) -> Decimal:
        return self._non_negative_balance(self.wallet_service.ensure_liquidity_pool_account(self.session, unit))

    def treasury_reward_threshold(self, *, unit: LedgerUnit = LedgerUnit.COIN) -> Decimal:
        del unit
        return TREASURY_LOW_BALANCE_THRESHOLD

    def can_fund_match(self, *, amount: Decimal, unit: LedgerUnit = LedgerUnit.COIN) -> bool:
        normalized_amount = self._amount(amount)
        if normalized_amount <= Decimal("0.0000"):
            return False
        return self.treasury_balance(unit=unit) > self._amount(normalized_amount * TREASURY_BUFFER_MULTIPLE)

    def max_match_funding(self, *, unit: LedgerUnit = LedgerUnit.COIN) -> Decimal:
        treasury_balance = self.treasury_balance(unit=unit)
        if treasury_balance <= Decimal("0.0000"):
            return Decimal("0.0000")
        buffer_safe_balance = treasury_balance - AMOUNT_QUANTUM
        if buffer_safe_balance <= Decimal("0.0000"):
            return Decimal("0.0000")
        return self._amount(buffer_safe_balance / TREASURY_BUFFER_MULTIPLE)

    def scale_reward_amount(self, *, amount: Decimal, unit: LedgerUnit = LedgerUnit.COIN) -> Decimal:
        normalized_amount = self._amount(amount)
        if normalized_amount <= Decimal("0.0000"):
            return Decimal("0.0000")
        scaled_amount = self._amount(normalized_amount * self.reward_multiplier(unit=unit))
        if self.treasury_balance(unit=unit) <= Decimal("0.0000"):
            return scaled_amount
        return min(scaled_amount, self.max_match_funding(unit=unit))

    def burn_bonus_bps(self) -> int:
        return int(self.get_policy().burn_bonus_bps or 0)

    def quote_conversion(self, *, source_unit: LedgerUnit, amount: Decimal) -> WalletConversionQuote:
        base_quote = self.wallet_service.quote_conversion(source_unit=source_unit, amount=amount)
        policy = self.get_policy()
        target_amount = base_quote.target_amount
        if source_unit == LedgerUnit.COIN and int(policy.conversion_bonus_bps or 0) > 0:
            target_amount = self._amount(
                target_amount * (Decimal("1.0000") + Decimal(int(policy.conversion_bonus_bps)) / Decimal("10000"))
            )
        rate = self._amount(target_amount / base_quote.source_amount)
        return WalletConversionQuote(
            source_unit=base_quote.source_unit,
            source_amount=base_quote.source_amount,
            target_unit=base_quote.target_unit,
            target_amount=target_amount,
            rate=rate,
        )

    def convert_wallet_units(
        self,
        *,
        user: User,
        amount: Decimal,
        source_unit: LedgerUnit,
        actor: User | None = None,
        reference: str | None = None,
        idempotency_key: str | None = None,
    ) -> WalletConversionResult:
        quote = self.quote_conversion(source_unit=source_unit, amount=amount)
        source_account = self.wallet_service.get_user_account(self.session, user, quote.source_unit)
        target_account = self.wallet_service.get_user_account(self.session, user, quote.target_unit)
        source_platform_account = self.wallet_service.ensure_platform_account(self.session, quote.source_unit)
        target_platform_account = self.wallet_service.ensure_platform_account(self.session, quote.target_unit)
        resolved_reference = reference or f"wallet-conversion:{generate_uuid()}"
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(account=source_account, amount=-quote.source_amount),
                LedgerPosting(account=source_platform_account, amount=quote.source_amount),
                LedgerPosting(account=target_platform_account, amount=-quote.target_amount),
                LedgerPosting(account=target_account, amount=quote.target_amount),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            reference=resolved_reference,
            description=(
                f"Converted {quote.source_amount} {quote.source_unit.value} "
                f"to {quote.target_amount} {quote.target_unit.value}"
            ),
            external_reference=resolved_reference,
            actor=actor or user,
            idempotency_key=idempotency_key,
            metadata={
                "conversion": {
                    "source_unit": quote.source_unit.value,
                    "source_amount": str(quote.source_amount),
                    "target_unit": quote.target_unit.value,
                    "target_amount": str(quote.target_amount),
                    "rate": str(quote.rate),
                    "conversion_bonus_bps": int(self.get_policy().conversion_bonus_bps or 0),
                }
            },
        )
        return WalletConversionResult(
            transaction_id=entries[0].transaction_id,
            reference=resolved_reference,
            source_unit=quote.source_unit,
            source_amount=quote.source_amount,
            target_unit=quote.target_unit,
            target_amount=quote.target_amount,
        )

    def snapshot(self, *, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
        policy = self.get_policy()
        normalized_metrics = self._normalize_metrics(metrics or self.derive_metrics())
        recommended = self.evaluate(metrics=normalized_metrics)["actions"]
        return {
            "policy_key": policy.policy_key,
            "mode": policy.mode,
            "tournament_entry_multiplier": self._amount(policy.tournament_entry_multiplier),
            "match_view_cost_multiplier": self._amount(policy.match_view_cost_multiplier),
            "reward_payout_multiplier": self._amount(policy.reward_payout_multiplier),
            "conversion_bonus_bps": int(policy.conversion_bonus_bps or 0),
            "burn_bonus_bps": int(policy.burn_bonus_bps or 0),
            "metrics": self._metrics_payload(normalized_metrics),
            "recommended_actions": recommended,
            "last_evaluated_at": policy.last_evaluated_at,
            "last_applied_at": policy.last_applied_at,
            "updated_at": policy.updated_at,
        }

    def _normalize_metrics(self, metrics: dict[str, Any]) -> dict[str, Decimal]:
        treasury_balance = metrics["treasury_balance"] if "treasury_balance" in metrics else self.treasury_balance()
        rewards_pool_balance = metrics["rewards_pool_balance"] if "rewards_pool_balance" in metrics else self.rewards_pool_balance()
        liquidity_pool_balance = metrics["liquidity_pool_balance"] if "liquidity_pool_balance" in metrics else self.liquidity_pool_balance()
        treasury_reward_threshold = (
            metrics["treasury_reward_threshold"]
            if "treasury_reward_threshold" in metrics
            else self.treasury_reward_threshold()
        )
        treasury_buffer_multiple = (
            metrics["treasury_buffer_multiple"]
            if "treasury_buffer_multiple" in metrics
            else TREASURY_BUFFER_MULTIPLE
        )
        return {
            "gtex_supply": self._amount(metrics.get("gtex_supply", "0.0000")),
            "fan_supply": self._amount(metrics.get("fan_supply", "0.0000")),
            "daily_burn": self._amount(metrics.get("daily_burn", "0.0000")),
            "daily_mint": self._amount(metrics.get("daily_mint", "0.0000")),
            "avg_user_spend": self._amount(metrics.get("avg_user_spend", "0.0000")),
            "inflation_rate": self._amount(metrics.get("inflation_rate", "0.0000")),
            "treasury_balance": self._amount(treasury_balance),
            "rewards_pool_balance": self._amount(rewards_pool_balance),
            "liquidity_pool_balance": self._amount(liquidity_pool_balance),
            "treasury_reward_threshold": self._amount(treasury_reward_threshold),
            "treasury_buffer_multiple": self._amount(treasury_buffer_multiple),
        }

    @staticmethod
    def _metrics_payload(metrics: dict[str, Decimal]) -> dict[str, str]:
        return {key: str(value) for key, value in metrics.items()}

    @staticmethod
    def _amount(value: Any) -> Decimal:
        return Decimal(str(value or "0.0000")).quantize(AMOUNT_QUANTUM)

    @staticmethod
    def _bounded_multiplier(value: Decimal | str | int | float) -> Decimal:
        normalized = Decimal(str(value)).quantize(AMOUNT_QUANTUM)
        if normalized < MIN_MULTIPLIER:
            return MIN_MULTIPLIER
        if normalized > MAX_MULTIPLIER:
            return MAX_MULTIPLIER
        return normalized

    def _non_negative_balance(self, account) -> Decimal:
        balance = self._amount(self.wallet_service.get_balance(self.session, account))
        return balance if balance > Decimal("0.0000") else Decimal("0.0000")


__all__ = ["EconomyGovernorError", "EconomyGovernorModeError", "EconomyGovernorService"]
