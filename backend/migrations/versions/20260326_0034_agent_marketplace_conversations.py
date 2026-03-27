"""Add agent marketplace listings and player conversations.

Revision ID: 20260326_0034_agent_marketplace_conversations
Revises: 20260324_0033_merge_auth_email_and_bulk_import_heads
Create Date: 2026-03-26 23:35:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260326_0034_agent_marketplace_conversations"
down_revision = "20260324_0033_merge_auth_email_and_bulk_import_heads"
branch_labels = None
depends_on = None


asking_type_enum = sa.Enum(
    "transfer",
    "loan",
    "trial",
    name="agent_marketplace_asking_type",
    native_enum=False,
)
participant_role_enum = sa.Enum(
    "scout",
    "agent",
    "club",
    name="conversation_participant_role",
    native_enum=False,
)
conversation_status_enum = sa.Enum(
    "active",
    "negotiating",
    "closed",
    name="player_conversation_status",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "agent_marketplace_listings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("agent_user_id", sa.String(length=36), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("asking_type", asking_type_enum, nullable=False, server_default="transfer"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["agent_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", name="uq_agent_marketplace_listings_player_id"),
    )
    op.create_index(
        "ix_agent_marketplace_listings_agent_user_id",
        "agent_marketplace_listings",
        ["agent_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_marketplace_listings_is_available",
        "agent_marketplace_listings",
        ["is_available"],
        unique=False,
    )
    op.create_index(
        "ix_agent_marketplace_listings_asking_type",
        "agent_marketplace_listings",
        ["asking_type"],
        unique=False,
    )

    op.create_table(
        "player_conversations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("agent_user_id", sa.String(length=36), nullable=False),
        sa.Column("initiator_user_id", sa.String(length=36), nullable=False),
        sa.Column("initiator_role", participant_role_enum, nullable=False),
        sa.Column("status", conversation_status_enum, nullable=False, server_default="active"),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["agent_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["initiator_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "player_id",
            "agent_user_id",
            "initiator_user_id",
            "initiator_role",
            name="uq_player_conversations_identity",
        ),
    )
    op.create_index("ix_player_conversations_agent_user_id", "player_conversations", ["agent_user_id"], unique=False)
    op.create_index(
        "ix_player_conversations_initiator_user_id",
        "player_conversations",
        ["initiator_user_id"],
        unique=False,
    )
    op.create_index("ix_player_conversations_status", "player_conversations", ["status"], unique=False)
    op.create_index(
        "ix_player_conversations_last_message_at",
        "player_conversations",
        ["last_message_at"],
        unique=False,
    )

    op.create_table(
        "player_conversation_participants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role", participant_role_enum, nullable=False),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["conversation_id"], ["player_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "conversation_id",
            "user_id",
            name="uq_player_conversation_participants_conversation_user",
        ),
    )
    op.create_index(
        "ix_player_conversation_participants_user_id",
        "player_conversation_participants",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_player_conversation_participants_role",
        "player_conversation_participants",
        ["role"],
        unique=False,
    )
    op.create_index(
        "ix_player_conversation_participants_last_read_at",
        "player_conversation_participants",
        ["last_read_at"],
        unique=False,
    )

    op.create_table(
        "player_conversation_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("sender_id", sa.String(length=36), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["conversation_id"], ["player_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_player_conversation_messages_conversation_id",
        "player_conversation_messages",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        "ix_player_conversation_messages_sender_id",
        "player_conversation_messages",
        ["sender_id"],
        unique=False,
    )
    op.create_index(
        "ix_player_conversation_messages_created_at",
        "player_conversation_messages",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_player_conversation_messages_created_at", table_name="player_conversation_messages")
    op.drop_index("ix_player_conversation_messages_sender_id", table_name="player_conversation_messages")
    op.drop_index("ix_player_conversation_messages_conversation_id", table_name="player_conversation_messages")
    op.drop_table("player_conversation_messages")

    op.drop_index("ix_player_conversation_participants_last_read_at", table_name="player_conversation_participants")
    op.drop_index("ix_player_conversation_participants_role", table_name="player_conversation_participants")
    op.drop_index("ix_player_conversation_participants_user_id", table_name="player_conversation_participants")
    op.drop_table("player_conversation_participants")

    op.drop_index("ix_player_conversations_last_message_at", table_name="player_conversations")
    op.drop_index("ix_player_conversations_status", table_name="player_conversations")
    op.drop_index("ix_player_conversations_initiator_user_id", table_name="player_conversations")
    op.drop_index("ix_player_conversations_agent_user_id", table_name="player_conversations")
    op.drop_table("player_conversations")

    op.drop_index("ix_agent_marketplace_listings_asking_type", table_name="agent_marketplace_listings")
    op.drop_index("ix_agent_marketplace_listings_is_available", table_name="agent_marketplace_listings")
    op.drop_index("ix_agent_marketplace_listings_agent_user_id", table_name="agent_marketplace_listings")
    op.drop_table("agent_marketplace_listings")
