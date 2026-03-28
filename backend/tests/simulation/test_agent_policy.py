from __future__ import annotations

from decimal import Decimal

from app.simulation.agent_policy import (
    AITradingAgentPolicy,
    AgentDecision,
    AgentMarketSnapshot,
    BOOTSTRAP_AGENT_COUNT,
    MAX_AGENT_VOLUME,
    blocks_agent_trading,
)
from app.simulation.service import SIMULATION_USER_SPECS


def test_ai_trading_policy_uses_specified_decision_priority() -> None:
    policy = AITradingAgentPolicy()

    assert policy.decide(
        AgentMarketSnapshot(
            market_type="low_liquidity",
            trend=Decimal("0.1200"),
            undervalued=True,
        )
    ) == AgentDecision.PROVIDE_LIQUIDITY
    assert policy.decide(
        AgentMarketSnapshot(
            market_type="normal",
            trend=Decimal("0.0600"),
            undervalued=True,
        )
    ) == AgentDecision.MOMENTUM_BUY
    assert policy.decide(
        AgentMarketSnapshot(
            market_type="normal",
            trend=Decimal("0.0100"),
            undervalued=True,
        )
    ) == AgentDecision.VALUE_BUY


def test_agent_volume_cap_blocks_repeat_overweight_trading() -> None:
    assert BOOTSTRAP_AGENT_COUNT >= 3
    assert MAX_AGENT_VOLUME == Decimal("0.35")

    assert blocks_agent_trading(
        agent_volume=Decimal("0.0000"),
        total_market_volume=Decimal("0.0000"),
        proposed_volume=Decimal("5.0000"),
        active_agent_count=0,
        agent_is_active=False,
    ) is False
    assert blocks_agent_trading(
        agent_volume=Decimal("5.0000"),
        total_market_volume=Decimal("5.0000"),
        proposed_volume=Decimal("1.0000"),
        active_agent_count=1,
        agent_is_active=True,
    ) is True
    assert blocks_agent_trading(
        agent_volume=Decimal("35.0000"),
        total_market_volume=Decimal("100.0000"),
        proposed_volume=Decimal("1.0000"),
        active_agent_count=4,
        agent_is_active=True,
    ) is True
    assert blocks_agent_trading(
        agent_volume=Decimal("20.0000"),
        total_market_volume=Decimal("100.0000"),
        proposed_volume=Decimal("5.0000"),
        active_agent_count=4,
        agent_is_active=True,
    ) is False


def test_simulation_users_are_transparently_bot_labeled() -> None:
    assert SIMULATION_USER_SPECS[0].display_name == "AI Trader Alpha"
    assert all(spec.display_name.startswith("AI Trader ") for spec in SIMULATION_USER_SPECS)
