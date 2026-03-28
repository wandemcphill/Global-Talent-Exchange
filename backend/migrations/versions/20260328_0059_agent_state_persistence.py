"""Persist creator agent state, wallets, and performance logs.

Revision ID: 20260328_0059_agent_state_persistence
Revises: 20260328_0058_creator_marketplace
Create Date: 2026-03-28 18:45:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260328_0059_agent_state_persistence"
down_revision = "20260328_0058_creator_marketplace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("handle", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("style", sa.String(length=48), nullable=False),
        sa.Column("target", sa.String(length=64), nullable=False),
        sa.Column("last_generated_clip_id", sa.String(length=200), nullable=True),
        sa.Column("last_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("state_version", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("agent_id"),
    )
    op.create_index("ix_agents_style", "agents", ["style"], unique=False)
    op.create_index("ix_agents_last_generated_at", "agents", ["last_generated_at"], unique=False)

    op.create_table(
        "agent_strategies",
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("risk_level", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("avg_duration", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("tempo", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("audience_bias", sa.String(length=32), nullable=False, server_default="general"),
        sa.Column("preferred_formats_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("event_focus_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("cadence_minutes", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("experimental_share", sa.Float(), nullable=False, server_default="0.3"),
        sa.Column("global_exposure_feedback", sa.Float(), nullable=False, server_default="0"),
        sa.Column("shared_brain", sa.String(length=32), nullable=False, server_default="copilot"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.agent_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("agent_id"),
    )

    op.create_table(
        "agent_learning_state",
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("exploration_rate", sa.Float(), nullable=False, server_default="0.35"),
        sa.Column("last_reward", sa.Float(), nullable=False, server_default="0"),
        sa.Column("average_reward", sa.Float(), nullable=False, server_default="0"),
        sa.Column("win_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("loss_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_posts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_rewards", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_penalties", sa.Float(), nullable=False, server_default="0"),
        sa.Column("preferred_formats_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.agent_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("agent_id"),
    )

    op.create_table(
        "agent_wallets",
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("balance", sa.Float(), nullable=False, server_default="12"),
        sa.Column("lifetime_earnings", sa.Float(), nullable=False, server_default="0"),
        sa.Column("boost_spend", sa.Float(), nullable=False, server_default="0"),
        sa.Column("roi", sa.Float(), nullable=False, server_default="0"),
        sa.Column("last_spend", sa.Float(), nullable=False, server_default="0"),
        sa.Column("last_earnings", sa.Float(), nullable=False, server_default="0"),
        sa.Column("trust_score", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0.65"),
        sa.Column("repetition_ratio", sa.Float(), nullable=False, server_default="0"),
        sa.Column("payout_eligible", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("last_block_reason", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.agent_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("agent_id"),
    )

    op.create_table(
        "agent_performance_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("clip_id", sa.String(length=200), nullable=False),
        sa.Column("primary_format", sa.String(length=48), nullable=False),
        sa.Column("variant_formats_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("reward_total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("trust_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("payout_eligible", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("payout_block_reason", sa.String(length=64), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("watch_time", sa.Float(), nullable=False, server_default="0"),
        sa.Column("shares", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("share_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("comment_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("velocity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("penalties", sa.Float(), nullable=False, server_default="0"),
        sa.Column("earnings", sa.Float(), nullable=False, server_default="0"),
        sa.Column("skip_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("orchestrator_weight", sa.Float(), nullable=False, server_default="0"),
        sa.Column("global_exposure_feedback", sa.Float(), nullable=False, server_default="0"),
        sa.Column("winner_variant_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.agent_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_performance_logs_agent_id", "agent_performance_logs", ["agent_id"], unique=False)
    op.create_index("ix_agent_performance_logs_clip_id", "agent_performance_logs", ["clip_id"], unique=False)
    op.create_index("ix_agent_performance_logs_created_at", "agent_performance_logs", ["created_at"], unique=False)
    op.create_index(
        "ix_agent_performance_logs_agent_format",
        "agent_performance_logs",
        ["agent_id", "primary_format"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_agent_performance_logs_agent_format", table_name="agent_performance_logs")
    op.drop_index("ix_agent_performance_logs_created_at", table_name="agent_performance_logs")
    op.drop_index("ix_agent_performance_logs_clip_id", table_name="agent_performance_logs")
    op.drop_index("ix_agent_performance_logs_agent_id", table_name="agent_performance_logs")
    op.drop_table("agent_performance_logs")

    op.drop_table("agent_wallets")
    op.drop_table("agent_learning_state")
    op.drop_table("agent_strategies")

    op.drop_index("ix_agents_last_generated_at", table_name="agents")
    op.drop_index("ix_agents_style", table_name="agents")
    op.drop_table("agents")
