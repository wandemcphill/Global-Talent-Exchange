from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.agent_marketplace import (
    AgentAskingType,
    ConversationParticipantRole,
    PlayerConversationStatus,
)


class AgentMarketplaceListingUpsert(BaseModel):
    is_available: bool = True
    asking_type: AgentAskingType = AgentAskingType.TRANSFER
    note: str | None = Field(default=None, max_length=2000)


class AgentMarketplacePlayerView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    player_name: str
    position: str | None
    nationality: str | None
    current_club_name: str | None
    age: int | None
    current_value_credits: float | None
    movement_pct: float | None
    trend_score: float | None
    market_interest_score: int | None
    average_rating: float | None
    is_available: bool
    availability_label: str
    asking_type: AgentAskingType
    marketplace_note: str | None
    agent_user_id: str
    agent_name: str
    updated_at: datetime


class AgentMarketplacePlayerListView(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    players: list[AgentMarketplacePlayerView] = Field(validation_alias="items")
    limit: int
    next_cursor: str | None = None
    has_more: bool
    total: int


class AgentMarketplaceListingView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    agent_user_id: str
    agent_name: str
    is_available: bool
    asking_type: AgentAskingType
    note: str | None
    updated_at: datetime


class AgentMarketplaceMineView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    listings: list[AgentMarketplacePlayerView]


class ConversationStartRequest(BaseModel):
    player_id: str = Field(min_length=1)
    message: str = Field(min_length=1, max_length=4000)
    actor_role: Literal["scout", "club"] | None = None


class ConversationMessageCreateRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ConversationStatusUpdateRequest(BaseModel):
    status: PlayerConversationStatus


class ConversationParticipantView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    display_name: str
    role: ConversationParticipantRole
    last_read_at: datetime | None


class ConversationMessageView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    sender_id: str
    sender_name: str
    sender_role: ConversationParticipantRole
    message: str
    created_at: datetime


class ConversationPlayerContextView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    player_name: str
    position: str | None
    current_club_name: str | None
    asking_type: AgentAskingType
    marketplace_note: str | None
    agent_name: str


class ConversationSummaryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    player: ConversationPlayerContextView
    status: PlayerConversationStatus
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None
    latest_message_preview: str | None
    unread_count: int
    participants: list[ConversationParticipantView]


class ConversationDetailView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversation: ConversationSummaryView
    messages: list[ConversationMessageView]
