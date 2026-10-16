from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping

from services.economy.wallet import Wallet


_BASE_REWARDS = {
    "viral_clip": 50,
    "match_win": 20,
    "engagement_spike": 12,
    "livestream_feature": 18,
    "creator_streak": 15,
}


@dataclass(frozen=True, slots=True)
class RewardQuote:
    event: str
    coins: int
    reason: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def reward_user(event: str, metadata: Mapping[str, object] | None = None) -> int:
    payload = metadata or {}
    normalized = event.strip().lower()
    reward = _BASE_REWARDS.get(normalized, 0)
    if normalized == "viral_clip":
        reward += min(30, max(0, int(payload.get("viral_score") or 0) - 70) // 2)
    if normalized == "match_win" and bool(payload.get("upset")):
        reward += 10
    if normalized == "engagement_spike":
        reward += min(25, int(payload.get("engagement_delta") or 0) // 1000)
    return reward


class RewardEngine:
    def quote(self, event: str, *, metadata: Mapping[str, object] | None = None) -> RewardQuote:
        coins = reward_user(event, metadata=metadata)
        reason = f"Reward for {event.strip().lower().replace('_', ' ')}"
        return RewardQuote(event=event.strip().lower(), coins=coins, reason=reason)

    def apply(self, wallet: Wallet, event: str, *, metadata: Mapping[str, object] | None = None) -> RewardQuote:
        quote = self.quote(event, metadata=metadata)
        if quote.coins > 0:
            wallet.credit_coins(quote.coins, event=quote.event, note=quote.reason)
        return quote
