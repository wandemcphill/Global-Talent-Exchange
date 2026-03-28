from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, TypeAlias

from sqlalchemy.orm import Session

from app.core.events import DomainEvent
from app.infrastructure.outbox import OutboxEvent, write_event

from .schemas import BaseCommand
from .schemas import CalculateRewardsCommand, CompleteMatchCommand, StartMatchCommand


CommandHandler: TypeAlias = Callable[[BaseCommand], Any]


class CommandHandlerNotRegisteredError(LookupError):
    pass


class CommandBus:
    def __init__(
        self,
        handlers: Mapping[type[BaseCommand], CommandHandler] | None = None,
    ) -> None:
        self._handlers: dict[type[BaseCommand], CommandHandler] = {}
        if handlers is not None:
            for command_type, handler in handlers.items():
                self.register(command_type, handler)

    def register(self, command_type: type[BaseCommand], handler: CommandHandler) -> None:
        self._handlers[command_type] = handler

    def dispatch(self, command: BaseCommand) -> Any:
        handler = self._resolve_handler(command)
        return handler(command)

    def _resolve_handler(self, command: BaseCommand) -> CommandHandler:
        command_type = type(command)

        if command_type in self._handlers:
            return self._handlers[command_type]

        for registered_type, handler in self._handlers.items():
            if isinstance(command, registered_type):
                return handler

        raise CommandHandlerNotRegisteredError(
            f"No command handler registered for {command_type.__name__}."
        )


class OutboxCommandDispatcher:
    def __init__(
        self,
        *,
        session: Session,
        producer_name: str = "gtex-api",
    ) -> None:
        self._session = session
        self._producer_name = producer_name

    def dispatch(self, command: BaseCommand) -> OutboxEvent:
        event = self._domain_event_for(command)
        return write_event(event, session=self._session)

    def _domain_event_for(self, command: BaseCommand) -> DomainEvent:
        event_name = _command_event_name(command)
        payload = command.model_dump(mode="json")
        match_id = _match_id_for(command)
        requested_status = _requested_status_for(command)
        return DomainEvent(
            name=event_name,
            payload={
                "match_id": match_id,
                "command_id": command.command_id,
                "command_name": type(command).__name__,
                "match_status": requested_status,
                "command": payload,
            },
            aggregate_id=match_id,
            aggregate_type="competition_match",
            producer=self._producer_name,
            partition_key=match_id,
            headers={
                "message_kind": "command",
                "command_name": type(command).__name__,
            },
        )


def _command_event_name(command: BaseCommand) -> str:
    if isinstance(command, StartMatchCommand):
        return "orchestrator.command.match.start"
    if isinstance(command, CompleteMatchCommand):
        return "orchestrator.command.match.complete"
    if isinstance(command, CalculateRewardsCommand):
        return "orchestrator.command.match.rewards"
    return f"orchestrator.command.{type(command).__name__.lower()}"


def _match_id_for(command: BaseCommand) -> str:
    payload_key = "payload" if isinstance(command, StartMatchCommand) else "result"
    payload = getattr(command, payload_key, {})
    match_id = str((payload or {}).get("match_id") or "").strip()
    if match_id:
        return match_id
    return command.command_id


def _requested_status_for(command: BaseCommand) -> str:
    if isinstance(command, StartMatchCommand):
        return "queued"
    if isinstance(command, CompleteMatchCommand):
        return "completed"
    return "pending"
