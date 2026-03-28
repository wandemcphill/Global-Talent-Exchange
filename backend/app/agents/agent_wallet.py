from __future__ import annotations

from dataclasses import dataclass, replace


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(float(value), maximum))


@dataclass(frozen=True, slots=True)
class AgentWallet:
    balance: float = 12.0
    lifetime_earnings: float = 0.0
    boost_spend: float = 0.0
    roi: float = 0.0
    last_spend: float = 0.0
    last_earnings: float = 0.0


@dataclass(frozen=True, slots=True)
class WalletBoostDecision:
    boost_amount: float
    approved: bool
    reason: str


class AgentWalletService:
    def recommend_boost(
        self,
        *,
        wallet: AgentWallet,
        predicted_reward: float,
        risk_level: float,
        feed_pressure: float,
    ) -> WalletBoostDecision:
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

    def settle(self, wallet: AgentWallet, *, earnings: float) -> AgentWallet:
        realized = max(round(float(earnings), 2), 0.0)
        next_balance = round(wallet.balance + realized, 2)
        next_earnings = round(wallet.lifetime_earnings + realized, 2)
        return replace(
            wallet,
            balance=next_balance,
            lifetime_earnings=next_earnings,
            roi=self._roi(earnings=next_earnings, spend=wallet.boost_spend),
            last_earnings=realized,
        )

    @staticmethod
    def _roi(*, earnings: float, spend: float) -> float:
        if spend <= 0.0:
            return round(_clamp(earnings, 0.0, 9999.0), 4)
        return round((earnings - spend) / spend, 4)


__all__ = [
    "AgentWallet",
    "AgentWalletService",
    "WalletBoostDecision",
]
