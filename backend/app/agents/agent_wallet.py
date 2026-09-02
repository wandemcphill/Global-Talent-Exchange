from __future__ import annotations

from dataclasses import dataclass


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(float(value), maximum))


@dataclass(frozen=True, slots=True)
class AgentWallet:
    # Compatibility projection only. Monetary authority is the canonical ledger.
    balance: float = 0.0
    lifetime_earnings: float = 0.0
    boost_spend: float = 0.0
    roi: float = 0.0
    last_spend: float = 0.0
    last_earnings: float = 0.0
    trust_score: float = 0.8
    quality_score: float = 0.65
    repetition_ratio: float = 0.0
    payout_eligible: bool = False
    last_block_reason: str | None = None


@dataclass(frozen=True, slots=True)
class WalletBoostDecision:
    boost_amount: float
    approved: bool
    reason: str


@dataclass(frozen=True, slots=True)
class WalletSettlementDecision:
    realized_earnings: float
    approved: bool
    reason: str
    quality_score: float
    trust_score: float
    decay_multiplier: float


class AgentWalletService:
    min_quality_threshold: float = 0.58
    min_trust_threshold: float = 0.60
    min_decay_multiplier: float = 0.25

    def recommend_boost(
        self,
        *,
        wallet: AgentWallet,
        predicted_reward: float,
        risk_level: float,
        feed_pressure: float,
    ) -> WalletBoostDecision:
        if wallet.trust_score < self.min_trust_threshold:
            return WalletBoostDecision(0.0, False, "trust_gated")
        if wallet.quality_score < (self.min_quality_threshold - 0.08):
            return WalletBoostDecision(0.0, False, "quality_gated")
        if wallet.balance <= 0.5:
            return WalletBoostDecision(0.0, False, "insufficient_balance")
        if predicted_reward < 1.10:
            return WalletBoostDecision(0.0, False, "reward_below_threshold")
        if feed_pressure > 1.0:
            return WalletBoostDecision(0.0, False, "feed_cap_pressure")
        boost_amount = round(
            min(wallet.balance * 0.18, max(predicted_reward - 0.80, 0.0) * max(risk_level, 0.1), 3.0), 2
        )
        if boost_amount <= 0.0:
            return WalletBoostDecision(0.0, False, "no_budget_needed")
        return WalletBoostDecision(boost_amount, True, "approved")

    def apply_spend(self, wallet: AgentWallet, amount: float) -> AgentWallet:
        raise RuntimeError(
            "AgentWallet is a ledger projection only. Use AgentLedgerService for monetary spend."
        )

    def settle(
        self,
        wallet: AgentWallet,
        *,
        earnings: float,
        quality_score: float,
        trust_score: float,
        repetition_ratio: float,
    ) -> tuple[AgentWallet, WalletSettlementDecision]:
        raise RuntimeError(
            "AgentWallet is a ledger projection only. Use AgentLedgerService for settlement and explicit payout authorization."
        )

    @staticmethod
    def _roi(*, earnings: float, spend: float) -> float:
        if spend <= 0.0:
            return round(_clamp(earnings, 0.0, 9999.0), 4)
        return round((earnings - spend) / spend, 4)


__all__ = [
    "AgentWallet",
    "AgentWalletService",
    "WalletSettlementDecision",
    "WalletBoostDecision",
]
