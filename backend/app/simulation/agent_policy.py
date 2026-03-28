from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
import math

MAX_AGENT_VOLUME = Decimal("0.35")
BOOTSTRAP_AGENT_COUNT = max(3, math.ceil(Decimal("1.0000") / MAX_AGENT_VOLUME))


class AgentDecision(StrEnum):
    PROVIDE_LIQUIDITY = "provide_liquidity"
    MOMENTUM_BUY = "momentum_buy"
    VALUE_BUY = "value_buy"
    REST = "rest"


@dataclass(frozen=True, slots=True)
class AgentMarketSnapshot:
    market_type: str
    trend: Decimal
    undervalued: bool


class AITradingAgentPolicy:
    def decide(self, market: AgentMarketSnapshot) -> AgentDecision:
        if market.market_type == "low_liquidity":
            return AgentDecision.PROVIDE_LIQUIDITY
        if Decimal(str(market.trend)) > Decimal("0.0500"):
            return AgentDecision.MOMENTUM_BUY
        if market.undervalued:
            return AgentDecision.VALUE_BUY
        return AgentDecision.REST


def blocks_agent_trading(
    *,
    agent_volume: Decimal,
    total_market_volume: Decimal,
    proposed_volume: Decimal,
    active_agent_count: int,
    agent_is_active: bool,
    max_agent_volume: Decimal = MAX_AGENT_VOLUME,
) -> bool:
    normalized_agent_volume = Decimal(str(agent_volume or "0.0000"))
    normalized_total_volume = Decimal(str(total_market_volume or "0.0000"))
    normalized_proposed_volume = Decimal(str(proposed_volume or "0.0000"))
    if normalized_proposed_volume <= Decimal("0.0000"):
        return False
    if not agent_is_active and active_agent_count < BOOTSTRAP_AGENT_COUNT:
        return False
    if agent_is_active and active_agent_count < BOOTSTRAP_AGENT_COUNT:
        return True
    projected_total = normalized_total_volume + normalized_proposed_volume
    if projected_total <= Decimal("0.0000"):
        return False
    projected_agent = normalized_agent_volume + normalized_proposed_volume
    return (projected_agent / projected_total) > Decimal(str(max_agent_volume))


__all__ = [
    "AITradingAgentPolicy",
    "AgentDecision",
    "AgentMarketSnapshot",
    "BOOTSTRAP_AGENT_COUNT",
    "MAX_AGENT_VOLUME",
    "blocks_agent_trading",
]
