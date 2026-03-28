from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from app.infrastructure.outbox import OutboxEvent

from .schemas import (
    BaseCommand,
    CompleteMatchCommand,
    StartMatchCommand,
)


class CommandDispatcher(Protocol):
    def dispatch(self, command: BaseCommand) -> OutboxEvent:
        ...


class OrchestratorService:
    def __init__(
        self,
        command_bus: CommandDispatcher,
    ) -> None:
        self._command_bus = command_bus

    def start_match(self, payload: Mapping[str, Any] | None) -> OutboxEvent:
        normalized_payload = dict(payload or {})
        command = StartMatchCommand(payload=normalized_payload)
        return self._command_bus.dispatch(command)

    def complete_match(self, result: Mapping[str, Any] | None) -> OutboxEvent:
        normalized_result = dict(result or {})
        command = CompleteMatchCommand(result=normalized_result)
        return self._command_bus.dispatch(command)
