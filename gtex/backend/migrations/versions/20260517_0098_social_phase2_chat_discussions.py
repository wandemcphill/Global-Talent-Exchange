"""social phase 2 chat and discussion controls

Revision ID: 20260517_0098_social_phase2_chat_discussions
Revises: 20260517_0097_club_ranking_integrity
Create Date: 2026-05-17 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260517_0098_social_phase2_chat_discussions"
down_revision = "20260517_0097_club_ranking_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "live_threads",
        sa.Column("thread_type", sa.String(length=40), nullable=False, server_default="live_thread"),
    )
    op.add_column(
        "live_threads",
        sa.Column("category", sa.String(length=80), nullable=False, server_default="general"),
    )
    op.add_column("live_threads", sa.Column("body", sa.Text(), nullable=False, server_default=""))
    op.add_column(
        "live_threads",
        sa.Column("visibility", sa.String(length=32), nullable=False, server_default="public"),
    )
    op.add_column(
        "live_threads",
        sa.Column("moderation_status", sa.String(length=32), nullable=False, server_default="visible"),
    )
    op.add_column("live_threads", sa.Column("trend_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("live_threads", sa.Column("locked_by_user_id", sa.String(length=36), nullable=True))
    op.add_column("live_threads", sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_live_threads_thread_type"), "live_threads", ["thread_type"], unique=False)
    op.create_index(op.f("ix_live_threads_category"), "live_threads", ["category"], unique=False)
    op.create_index(op.f("ix_live_threads_locked_by_user_id"), "live_threads", ["locked_by_user_id"], unique=False)

    op.add_column("live_thread_messages", sa.Column("parent_message_id", sa.String(length=36), nullable=True))
    op.add_column(
        "live_thread_messages",
        sa.Column("message_type", sa.String(length=32), nullable=False, server_default="reply"),
    )
    op.add_column(
        "live_thread_messages",
        sa.Column("moderation_status", sa.String(length=32), nullable=False, server_default="visible"),
    )
    op.create_index(
        op.f("ix_live_thread_messages_parent_message_id"),
        "live_thread_messages",
        ["parent_message_id"],
        unique=False,
    )

    op.add_column(
        "private_messages",
        sa.Column(
            "visibility",
            sa.Enum("PUBLIC", "MOD_REVIEW", "HIDDEN", name="communitymessagevisibility", native_enum=False),
            nullable=False,
            server_default="PUBLIC",
        ),
    )

    op.create_table(
        "community_user_blocks",
        sa.Column("blocker_user_id", sa.String(length=36), nullable=False),
        sa.Column("blocked_user_id", sa.String(length=36), nullable=False),
        sa.Column("reason", sa.String(length=160), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["blocked_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["blocker_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("blocker_user_id", "blocked_user_id", name="uq_community_user_blocks_pair"),
    )
    op.create_index(op.f("ix_community_user_blocks_blocker_user_id"), "community_user_blocks", ["blocker_user_id"])
    op.create_index(op.f("ix_community_user_blocks_blocked_user_id"), "community_user_blocks", ["blocked_user_id"])

    op.create_table(
        "community_reactions",
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("reaction_type", sa.String(length=32), nullable=False, server_default="like"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_type", "entity_id", "user_id", "reaction_type", name="uq_community_reaction_once"),
    )
    op.create_index(op.f("ix_community_reactions_entity_type"), "community_reactions", ["entity_type"])
    op.create_index(op.f("ix_community_reactions_entity_id"), "community_reactions", ["entity_id"])
    op.create_index(op.f("ix_community_reactions_user_id"), "community_reactions", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_community_reactions_user_id"), table_name="community_reactions")
    op.drop_index(op.f("ix_community_reactions_entity_id"), table_name="community_reactions")
    op.drop_index(op.f("ix_community_reactions_entity_type"), table_name="community_reactions")
    op.drop_table("community_reactions")

    op.drop_index(op.f("ix_community_user_blocks_blocked_user_id"), table_name="community_user_blocks")
    op.drop_index(op.f("ix_community_user_blocks_blocker_user_id"), table_name="community_user_blocks")
    op.drop_table("community_user_blocks")

    op.drop_column("private_messages", "visibility")

    op.drop_index(op.f("ix_live_thread_messages_parent_message_id"), table_name="live_thread_messages")
    op.drop_column("live_thread_messages", "moderation_status")
    op.drop_column("live_thread_messages", "message_type")
    op.drop_column("live_thread_messages", "parent_message_id")

    op.drop_index(op.f("ix_live_threads_locked_by_user_id"), table_name="live_threads")
    op.drop_index(op.f("ix_live_threads_category"), table_name="live_threads")
    op.drop_index(op.f("ix_live_threads_thread_type"), table_name="live_threads")
    op.drop_column("live_threads", "locked_at")
    op.drop_column("live_threads", "locked_by_user_id")
    op.drop_column("live_threads", "trend_score")
    op.drop_column("live_threads", "moderation_status")
    op.drop_column("live_threads", "visibility")
    op.drop_column("live_threads", "body")
    op.drop_column("live_threads", "category")
    op.drop_column("live_threads", "thread_type")
