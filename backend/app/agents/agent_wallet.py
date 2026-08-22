from __future__ import annotations

from dataclasses import dataclass, replace


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
    # Fail closed until explicit payout authorization succeeds.
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
            return WalletBoostDecision(boost_amount=0.0, approved=False, reason="trust_gated")
        if wallet.quality_score < (self.min_quality_threshold - 0.08):
            return WalletBoostDecision(boost_amount=0.0, approved=False, reason="quality_gated")
        if wallet.balance <= 0.5:
            return WalletBoostDecision(boost_amount=0.0, approved=False, reason="insufficient_balance")
        if predicted_reward < 1.10:
            return WalletBoostDecision(boost_amount=0.0, approved=False, reason="reward_below_threshold")
        if feed_pressure > 1.0:
            return WalletBoostDecision(boost_amount=0.0, approved=False, reason="feed_cap_pressure")
        boost_amount = round(
            min(wallet.balance * 0.18, max(predicted_reward - 0.80, 0.0) * max(risk_level, 0.1), 3.0),
            2,
        )
        if boost_amount <= 0.0:
            return WalletBoostDecision(boost_amount=0.0, approved=False, reason="no_budget_needed")
        return WalletBoostDecision(boost_amount=boost_amount, approved=True, reason="approved")

    def apply_spend(self, wallet: AgentWallet, amount: float) -> AgentWallet:
        spend = max(round(float(amount), 2), 0.0)
        if spend <= 0.0:
            return replace(wallet, last_spend=0.0)
        next_balance = max(round(wallet.balance - spend, 2), 0.0)
        next_spend = round(wallet.boost_spend + spend, 2)
        roi = self._roi(earnings=wallet.lifetime_earnings, spend=next_spend)
        return replace(
            wallet,
            balance=next_balance,
            boost_spend=next_spend,
            roi=roi,
            last_spend=spend,
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
        normalized_quality = _clamp(quality_score, 0.0, 1.0)
        normalized_trust = _clamp(trust_score, 0.0, 1.0)
        normalized_repetition = _clamp(repetition_ratio, 0.0, 1.0)
        decay_multiplier = round(
            max(1.0 - (normalized_repetition * 0.75), self.min_decay_multiplier),
            4,
        )
        if normalized_trust < self.min_trust_threshold:
            realized = 0.0
            approved = False
            reason = "trust_score_below_floor"
        elif normalized_quality < self.min_quality_threshold:
            realized = 0.0
            approved = False
            reason = "quality_below_floor"
        else:
            realized = max(round(float(earnings) * decay_multiplier, 2), 0.0)
            approved = True
            reason = "approved" if decay_multiplier >= 0.99 else "repetition_decay"
        next_balance = round(wallet.balance + realized, 2)
        next_earnings = round(wallet.lifetime_earnings + realized, 2)
        updated_wallet = replace(
            wallet,
            balance=next_balance,
            lifetime_earnings=next_earnings,
            roi=self._roi(earnings=next_earnings, spend=wallet.boost_spend),
            last_earnings=realized,
            trust_score=round(normalized_trust, 4),
            quality_score=round(normalized_quality, 4),
            repetition_ratio=round(normalized_repetition, 4),
            payout_eligible=approved,
            last_block_reason=None if approved else reason,
        )
        return updated_wallet, WalletSettlementDecision(
            realized_earnings=realized,
            approved=approved,
            reason=reason,
            quality_score=round(normalized_quality, 4),
            trust_score=round(normalized_trust, 4),
            decay_multiplier=decay_multiplier,
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
