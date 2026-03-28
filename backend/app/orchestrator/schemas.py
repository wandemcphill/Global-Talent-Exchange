from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypeAlias
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


Payload: TypeAlias = dict[str, Any]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OrchestratorSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        use_enum_values=False,
    )


class BaseCommand(OrchestratorSchema):
    command_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=_utc_now)


class BaseEvent(OrchestratorSchema):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = Field(default_factory=_utc_now)


class StartMatchCommand(BaseCommand):
    payload: Payload = Field(default_factory=dict)


class CompleteMatchCommand(BaseCommand):
    result: Payload = Field(default_factory=dict)


class CalculateRewardsCommand(BaseCommand):
    result: Payload = Field(default_factory=dict)


class MatchStartedEvent(BaseEvent):
    payload: Payload = Field(default_factory=dict)


class MatchCompletedEvent(BaseEvent):
    result: Payload = Field(default_factory=dict)


class RewardsDistributedEvent(BaseEvent):
    rewards: Payload = Field(default_factory=dict)

