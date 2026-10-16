from __future__ import annotations

from typing import Any


_AGENT_MANAGER_EXPORTS = {
    "AgentManagerSummaryView",
    "AgentPerformanceReceiptView",
    "AgentPerformanceRequest",
    "AgentRunRequest",
    "AgentRunResponse",
    "AgentRuntimeConfigUpdateRequest",
    "AgentRuntimeConfigView",
    "CreatorAgentManager",
    "CreatorAgentView",
    "bind_creator_agent_manager",
    "ensure_creator_agent_manager",
    "shutdown_creator_agent_manager",
}

__all__ = sorted(_AGENT_MANAGER_EXPORTS)


def __getattr__(name: str) -> Any:
    if name not in _AGENT_MANAGER_EXPORTS:
        raise AttributeError(name)
    from app.agents import agent_manager as _agent_manager

    return getattr(_agent_manager, name)
