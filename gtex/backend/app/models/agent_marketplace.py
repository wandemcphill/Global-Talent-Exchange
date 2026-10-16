from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class AgentAskingType(StrEnum):
    TRANSFER = "transfer"
    LOAN = "loan"
    TRIAL = "trial"


class ConversationParticipantRole(StrEnum):
    SCOUT = "scout"
    AGENT = "agent"
    CLUB = "club"


class PlayerConversationStatus(StrEnum):
    ACTIVE = "active"
    NEGOTIATING = "negotiating"
    CLOSED = "closed"


class AgentMarketplaceListing(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_marketplace_listings"
    __table_args__ = (
        UniqueConstraint("player_id", name="uq_agent_marketplace_listings_player_id"),
        Index("ix_agent_marketplace_listings_agent_user_id", "agent_user_id"),
        Index("ix_agent_marketplace_listings_is_available", "is_available"),
        Index("ix_agent_marketplace_listings_asking_type", "asking_type"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    asking_type: Mapped[AgentAskingType] = mapped_column(
        Enum(AgentAskingType, name="agent_marketplace_asking_type", native_enum=False),
        nullable=False,
        default=AgentAskingType.TRANSFER,
        server_default=AgentAskingType.TRANSFER.value,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class PlayerConversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_conversations"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "agent_user_id",
            "initiator_user_id",
            "initiator_role",
            name="uq_player_conversations_identity",
        ),
        Index("ix_player_conversations_agent_user_id", "agent_user_id"),
        Index("ix_player_conversations_initiator_user_id", "initiator_user_id"),
        Index("ix_player_conversations_status", "status"),
        Index("ix_player_conversations_last_message_at", "last_message_at"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    initiator_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    initiator_role: Mapped[ConversationParticipantRole] = mapped_column(
        Enum(ConversationParticipantRole, name="conversation_participant_role", native_enum=False),
        nullable=False,
    )
    status: Mapped[PlayerConversationStatus] = mapped_column(
        Enum(PlayerConversationStatus, name="player_conversation_status", native_enum=False),
        nullable=False,
        default=PlayerConversationStatus.ACTIVE,
        server_default=PlayerConversationStatus.ACTIVE.value,
    )
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PlayerConversationParticipant(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "player_conversation_participants"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "user_id",
            name="uq_player_conversation_participants_conversation_user",
        ),
        Index("ix_player_conversation_participants_user_id", "user_id"),
        Index("ix_player_conversation_participants_role", "role"),
        Index("ix_player_conversation_participants_last_read_at", "last_read_at"),
    )

    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("player_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[ConversationParticipantRole] = mapped_column(
        Enum(ConversationParticipantRole, name="conversation_participant_role", native_enum=False),
        nullable=False,
    )
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )


class PlayerConversationMessage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "player_conversation_messages"
    __table_args__ = (
        Index("ix_player_conversation_messages_conversation_id", "conversation_id"),
        Index("ix_player_conversation_messages_sender_id", "sender_id"),
        Index("ix_player_conversation_messages_created_at", "created_at"),
    )

    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("player_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )


__all__ = [
    "AgentAskingType",
    "AgentMarketplaceListing",
    "ConversationParticipantRole",
    "PlayerConversation",
    "PlayerConversationMessage",
    "PlayerConversationParticipant",
    "PlayerConversationStatus",
]
