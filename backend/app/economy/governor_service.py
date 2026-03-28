from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.base import generate_uuid, utcnow
from app.models.economy_daily_stat import EconomyDailyStat
from app.models.economy_governor import EconomyGovernorPolicy
from app.models.player_token_market import PlayerShareEvent
from app.models.user import User
from app.models.wallet import LedgerAccount, LedgerAccountKind, LedgerBalanceProjection, LedgerEntryReason, LedgerSourceTag, LedgerUnit
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
DEFAULT_AGENT_MARKET_VOLUME_CAP = Decimal("0.3500")
DEFAULT_PRICE_CHANGE_LIMIT = Decimal("0.2500")
VOLATILITY_PRICE_CHANGE_LIMIT = Decimal("0.0500")
CIRCUIT_BREAKER_PRICE_CHANGE_LIMIT = Decimal("0.0200")
REWARD_PROTECTION_INFLATION_THRESHOLD = Decimal("0.1000")
HIGH_INFLATION_THRESHOLD = Decimal("0.1500")
VOLATILITY_PROTECTION_THRESHOLD = Decimal("0.5000")
CIRCUIT_BREAKER_VOLATILITY_THRESHOLD = Decimal("0.7000")
SAFE_ACTIVE_USER_FLOOR = Decimal("5000.0000")
CRITICAL_ACTIVE_USER_FLOOR = Decimal("1000.0000")
TREASURY_FREE_PRIZE_MULTIPLIER = Decimal("0.8000")
ACTIVE_USER_WINDOW = timedelta(days=1)


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

    def collect_metrics(self) -> dict[str, Decimal]:
        return self.derive_metrics()

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
                "whale_concentration": self.whale_concentration(),
                "active_users": self.active_user_count(),
                "market_volatility": self.market_volatility(),
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
            "whale_concentration": self.whale_concentration(),
            "active_users": self.active_user_count(stat=stat),
            "market_volatility": self.market_volatility(stat=stat),
        }

    def analyze(self, *, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.evaluate(metrics=metrics)

    def evaluate(self, *, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
        policy = self.get_policy()
        normalized_metrics = self._normalize_metrics(metrics or self.derive_metrics())
        actions: list[dict[str, Any]] = []

        if normalized_metrics["daily_mint"] > normalized_metrics["daily_burn"]:
            actions.append({"type": "increase_entry_fee", "value": "0.1000"})

        if normalized_metrics["avg_user_spend"] < Decimal("20.0000"):
            actions.append({"type": "reduce_match_cost", "value": "0.1000"})

        if normalized_metrics["inflation_rate"] >= HIGH_INFLATION_THRESHOLD:
            actions.append({"type": "increase_burn_rate", "value": "0.0500"})
            actions.append({"type": "boost_conversion_incentive", "value": 250})

        if normalized_metrics["whale_concentration"] >= Decimal("0.4500"):
            actions.append({"type": "increase_burn_rate", "value": "0.0250"})
            actions.append({"type": "activate_circuit_breaker", "value": "1"})

        reward_target = self._reward_target(normalized_metrics)
        if self._amount(policy.reward_payout_multiplier) != reward_target:
            actions.append({"type": "set_reward_multiplier", "value": str(reward_target)})

        free_prize_target = self._free_prize_target(normalized_metrics)
        if self._amount(policy.free_prize_multiplier) != free_prize_target:
            actions.append({"type": "set_free_prize_multiplier", "value": str(free_prize_target)})

        agent_activity_target = self._agent_activity_target(normalized_metrics)
        if self._amount(policy.agent_activity_multiplier) != agent_activity_target:
            actions.append({"type": "set_agent_activity", "value": str(agent_activity_target)})

        price_change_target = self._price_change_limit_target(normalized_metrics)
        if self.price_change_limit() != price_change_target:
            actions.append({"type": "adjust_price_caps", "value": str(price_change_target)})

        reward_decay_factor = self.reward_decay_factor(metrics=normalized_metrics)
        if reward_decay_factor < Decimal("1.0000"):
            actions.append({"type": "apply_reward_decay", "value": str(Decimal("1.0000") - reward_decay_factor)})

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
        free_prize_multiplier: Decimal | None = None,
        agent_activity_multiplier: Decimal | None = None,
        price_change_limit: Decimal | None = None,
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
        if free_prize_multiplier is not None:
            policy.free_prize_multiplier = self._bounded_multiplier(free_prize_multiplier)
        if agent_activity_multiplier is not None:
            policy.agent_activity_multiplier = self._bounded_multiplier(agent_activity_multiplier)
        if price_change_limit is not None:
            policy.price_change_limit = self._bounded_price_change_limit(price_change_limit)
        if conversion_bonus_bps is not None:
            policy.conversion_bonus_bps = max(0, min(5_000, int(conversion_bonus_bps)))
        if burn_bonus_bps is not None:
            policy.burn_bonus_bps = max(0, min(5_000, int(burn_bonus_bps)))
        policy.updated_by_user_id = actor.id
        self.session.flush()
        return policy

    def apply_changes(
        self,
        *,
        actor: User,
        decisions: list[dict[str, Any]] | None = None,
        metrics: dict[str, Any] | None = None,
        allow_manual_override: bool = True,
    ) -> dict[str, Any]:
        return self.apply_actions(
            actor=actor,
            actions=decisions,
            metrics=metrics,
            allow_manual_override=allow_manual_override,
        )

    def run_cycle(
        self,
        *,
        actor: User,
        metrics: dict[str, Any] | None = None,
        allow_manual_override: bool = True,
    ) -> dict[str, Any]:
        collected_metrics = self.collect_metrics() if metrics is None else metrics
        decisions = self.analyze(metrics=collected_metrics)["actions"]
        return self.apply_changes(
            actor=actor,
            decisions=decisions,
            metrics=collected_metrics,
            allow_manual_override=allow_manual_override,
        )

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
            elif action_type == "set_reward_multiplier":
                policy.reward_payout_multiplier = self._bounded_multiplier(value)
            elif action_type in {"set_free_prize_multiplier", "cut_free_prizes"}:
                policy.free_prize_multiplier = self._bounded_multiplier(value)
            elif action_type == "set_agent_activity":
                policy.agent_activity_multiplier = self._bounded_multiplier(value)
            elif action_type in {"adjust_price_caps", "limit_price_changes"}:
                target_cap = self._bounded_price_change_limit(
                    value if value is not None else VOLATILITY_PRICE_CHANGE_LIMIT
                )
                policy.price_change_limit = target_cap
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
            return self.clamp_price_change(
                reference_price=Decimal("1.0000"),
                proposed_price=self._amount(policy.tournament_entry_multiplier),
            )
        if "match-view" in normalized:
            return self.clamp_price_change(
                reference_price=Decimal("1.0000"),
                proposed_price=self._amount(policy.match_view_cost_multiplier),
            )
        return Decimal("1.0000")

    def reward_multiplier(self, *, unit: LedgerUnit = LedgerUnit.COIN) -> Decimal:
        multiplier = self._amount(self.get_policy().reward_payout_multiplier)
        treasury_balance = self.treasury_balance(unit=unit)
        threshold = self.treasury_reward_threshold(unit=unit)
        treasury_factor = Decimal("1.0000")
        if treasury_balance > Decimal("0.0000") and treasury_balance < threshold:
            treasury_factor = self._bounded_multiplier(treasury_balance / threshold)
        reward_decay_factor = self.reward_decay_factor()
        return self._bounded_multiplier(multiplier * treasury_factor * reward_decay_factor)

    def free_prize_multiplier(self) -> Decimal:
        return self._amount(self.get_policy().free_prize_multiplier)

    def agent_activity_multiplier(self) -> Decimal:
        return self._amount(self.get_policy().agent_activity_multiplier)

    def price_change_limit(self) -> Decimal:
        return self._bounded_price_change_limit(self.get_policy().price_change_limit)

    def agent_market_volume_cap(self) -> Decimal:
        activity_factor = min(Decimal("1.0000"), self.agent_activity_multiplier())
        return max(Decimal("0.0500"), self._amount(DEFAULT_AGENT_MARKET_VOLUME_CAP * activity_factor))

    def clamp_price_change(
        self,
        *,
        reference_price: Decimal | int | float | str,
        proposed_price: Decimal | int | float | str,
    ) -> Decimal:
        normalized_reference = self._amount(reference_price)
        normalized_proposed = self._amount(proposed_price)
        if normalized_reference <= Decimal("0.0000"):
            return normalized_proposed
        price_change_limit = self.price_change_limit()
        lower_bound = self._amount(normalized_reference * (Decimal("1.0000") - price_change_limit))
        upper_bound = self._amount(normalized_reference * (Decimal("1.0000") + price_change_limit))
        return min(max(normalized_proposed, lower_bound), upper_bound)

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
        scaled_amount = self._amount(
            normalized_amount * self.reward_multiplier(unit=unit) * self.free_prize_multiplier()
        )
        if self.treasury_balance(unit=unit) <= Decimal("0.0000"):
            return scaled_amount
        return min(scaled_amount, self.max_match_funding(unit=unit))

    def burn_bonus_bps(self) -> int:
        return int(self.get_policy().burn_bonus_bps or 0)

    def effective_burn_bonus_bps(self, *, metrics: dict[str, Any] | None = None) -> int:
        normalized_metrics = self._normalize_metrics(metrics or self._policy_metrics_or_derived())
        dynamic_bonus = 0
        if normalized_metrics["inflation_rate"] >= HIGH_INFLATION_THRESHOLD:
            dynamic_bonus += 250
        if normalized_metrics["whale_concentration"] >= Decimal("0.4500"):
            dynamic_bonus += 150
        if self.market_circuit_breaker_active(metrics=normalized_metrics):
            dynamic_bonus += 200
        return max(0, min(5_000, int(self.get_policy().burn_bonus_bps or 0) + dynamic_bonus))

    def active_user_count(self, *, stat: EconomyDailyStat | None = None) -> Decimal:
        metadata = stat.metadata_json if stat is not None else None
        if metadata:
            raw_count = metadata.get("active_users", metadata.get("active_user_count"))
            if raw_count is not None:
                return self._amount(raw_count)
        cutoff = utcnow() - ACTIVE_USER_WINDOW
        active_users = self.session.scalar(
            select(func.count(User.id)).where(
                User.is_active.is_(True),
                User.last_login_at.is_not(None),
                User.last_login_at >= cutoff,
            )
        ) or 0
        return self._amount(active_users)

    def market_volatility(self, *, stat: EconomyDailyStat | None = None) -> Decimal:
        metadata = stat.metadata_json if stat is not None else None
        if metadata:
            raw_volatility = metadata.get("market_volatility")
            if raw_volatility is not None:
                return self._amount(raw_volatility)
        events = self.session.scalars(
            select(PlayerShareEvent)
            .where(PlayerShareEvent.event_type == "performance")
            .order_by(PlayerShareEvent.created_at.desc())
            .limit(25)
        ).all()
        if not events:
            return Decimal("0.0000")
        total_variance = Decimal("0.0000")
        for event in events:
            multiplier = Decimal(str((event.metadata_json or {}).get("multiplier") or "1.0000"))
            total_variance += abs(multiplier - Decimal("1.0000"))
        return self._amount(total_variance / Decimal(len(events)))

    def whale_concentration(self, *, unit: LedgerUnit = LedgerUnit.COIN) -> Decimal:
        rows = self.session.execute(
            select(LedgerBalanceProjection.owner_user_id, func.coalesce(func.sum(LedgerBalanceProjection.balance), 0))
            .join(LedgerAccount, LedgerAccount.id == LedgerBalanceProjection.account_id)
            .where(
                LedgerBalanceProjection.unit == unit,
                LedgerBalanceProjection.owner_user_id.is_not(None),
                LedgerAccount.kind == LedgerAccountKind.USER,
            )
            .group_by(LedgerBalanceProjection.owner_user_id)
        ).all()
        balances = [self._amount(balance) for _user_id, balance in rows if self._amount(balance) > Decimal("0.0000")]
        total = sum(balances, start=Decimal("0.0000"))
        if total <= Decimal("0.0000"):
            return Decimal("0.0000")
        return self._amount(max(balances, default=Decimal("0.0000")) / total)

    def market_circuit_breaker_active(self, *, metrics: dict[str, Any] | None = None) -> bool:
        normalized_metrics = self._normalize_metrics(metrics or self._policy_metrics_or_derived())
        return bool(
            normalized_metrics["inflation_rate"] >= Decimal("0.2500")
            or normalized_metrics["whale_concentration"] >= Decimal("0.4500")
            or normalized_metrics["market_volatility"] >= CIRCUIT_BREAKER_VOLATILITY_THRESHOLD
            or (
                normalized_metrics["daily_mint"] > normalized_metrics["daily_burn"]
                and normalized_metrics["liquidity_pool_balance"] <= Decimal("0.0000")
            )
        )

    def reward_decay_factor(self, *, metrics: dict[str, Any] | None = None) -> Decimal:
        normalized_metrics = self._normalize_metrics(metrics or self._policy_metrics_or_derived())
        decay = Decimal("1.0000")
        if normalized_metrics["inflation_rate"] > Decimal("0.1200"):
            decay -= min(Decimal("0.2000"), normalized_metrics["inflation_rate"] - Decimal("0.1200"))
        if normalized_metrics["whale_concentration"] >= Decimal("0.4500"):
            decay -= Decimal("0.1000")
        if self.market_circuit_breaker_active(metrics=normalized_metrics):
            decay -= Decimal("0.1000")
        return self._bounded_multiplier(max(Decimal("0.6500"), decay))

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
        normalized_metrics["reward_decay_factor"] = self.reward_decay_factor(metrics=normalized_metrics)
        normalized_metrics["whale_concentration"] = self.whale_concentration()
        normalized_metrics["effective_burn_bonus_bps"] = Decimal(str(self.effective_burn_bonus_bps(metrics=normalized_metrics)))
        normalized_metrics["circuit_breaker_active"] = (
            Decimal("1.0000") if self.market_circuit_breaker_active(metrics=normalized_metrics) else Decimal("0.0000")
        )
        normalized_metrics["agent_market_volume_cap"] = self.agent_market_volume_cap()
        return {
            "policy_key": policy.policy_key,
            "mode": policy.mode,
            "tournament_entry_multiplier": self._amount(policy.tournament_entry_multiplier),
            "match_view_cost_multiplier": self._amount(policy.match_view_cost_multiplier),
            "reward_payout_multiplier": self._amount(policy.reward_payout_multiplier),
            "free_prize_multiplier": self._amount(policy.free_prize_multiplier),
            "agent_activity_multiplier": self._amount(policy.agent_activity_multiplier),
            "price_change_limit": self.price_change_limit(),
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
            "whale_concentration": self._amount(metrics.get("whale_concentration", self.whale_concentration())),
            "active_users": self._amount(metrics.get("active_users", self.active_user_count())),
            "market_volatility": self._amount(metrics.get("market_volatility", self.market_volatility())),
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

    @staticmethod
    def _bounded_price_change_limit(value: Decimal | str | int | float | None) -> Decimal:
        if value is None:
            return DEFAULT_PRICE_CHANGE_LIMIT
        normalized = Decimal(str(value)).quantize(AMOUNT_QUANTUM)
        if normalized < Decimal("0.0000"):
            return Decimal("0.0000")
        if normalized > Decimal("1.0000"):
            return Decimal("1.0000")
        return normalized

    def _reward_target(self, metrics: dict[str, Decimal]) -> Decimal:
        if metrics["inflation_rate"] > REWARD_PROTECTION_INFLATION_THRESHOLD:
            return Decimal("0.8000")
        return Decimal("1.0000")

    def _free_prize_target(self, metrics: dict[str, Decimal]) -> Decimal:
        if (
            metrics["treasury_balance"] > Decimal("0.0000")
            and metrics["treasury_balance"] < metrics["treasury_reward_threshold"]
        ):
            return TREASURY_FREE_PRIZE_MULTIPLIER
        return Decimal("1.0000")

    def _agent_activity_target(self, metrics: dict[str, Decimal]) -> Decimal:
        if metrics["market_volatility"] <= VOLATILITY_PROTECTION_THRESHOLD:
            return Decimal("1.0000")
        if metrics["active_users"] < CRITICAL_ACTIVE_USER_FLOOR:
            return Decimal("0.4000")
        if metrics["active_users"] < SAFE_ACTIVE_USER_FLOOR:
            return Decimal("0.5000")
        return Decimal("0.6000")

    def _price_change_limit_target(self, metrics: dict[str, Decimal]) -> Decimal:
        if self.market_circuit_breaker_active(metrics=metrics):
            return CIRCUIT_BREAKER_PRICE_CHANGE_LIMIT
        if metrics["market_volatility"] > VOLATILITY_PROTECTION_THRESHOLD:
            return VOLATILITY_PRICE_CHANGE_LIMIT
        return DEFAULT_PRICE_CHANGE_LIMIT

    def _non_negative_balance(self, account) -> Decimal:
        balance = self._amount(self.wallet_service.get_balance(self.session, account))
        return balance if balance > Decimal("0.0000") else Decimal("0.0000")

    def _policy_metrics_or_derived(self) -> dict[str, Any]:
        policy = self.get_policy()
        if policy.last_metrics_json:
            return dict(policy.last_metrics_json)
        return self.derive_metrics()


__all__ = ["EconomyGovernorError", "EconomyGovernorModeError", "EconomyGovernorService"]
