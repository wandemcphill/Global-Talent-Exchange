"""Add automatic creator attention earnings wallet and ledger.

Revision ID: 20260329_0060_creator_attention_earnings
Revises: 20260328_0059_agent_state_persistence
Create Date: 2026-03-29 09:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_0060_creator_attention_earnings"
down_revision = "20260328_0059_agent_state_persistence"
branch_labels = None
depends_on = None


clip_earning_event_type = sa.Enum(
    "impression",
    "like",
    "share",
    name="clip_earning_event_type",
    native_enum=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    clip_earning_event_type.create(bind, checkfirst=True)

    op.create_table(
        "creator_wallet",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("creator_user_id", sa.String(length=36), nullable=False),
        sa.Column("total_impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_likes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_shares", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_earnings_credit", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("available_balance_credit", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["creator_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("creator_user_id", name="uq_creator_wallet_creator_user_id"),
    )
    op.create_index("ix_creator_wallet_creator_user_id", "creator_wallet", ["creator_user_id"], unique=False)
    op.create_index("ix_creator_wallet_last_event_at", "creator_wallet", ["last_event_at"], unique=False)

    op.create_table(
        "clip_earnings_log",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("clip_id", sa.String(length=200), nullable=False),
        sa.Column("creator_user_id", sa.String(length=36), nullable=False),
        sa.Column("viewer_user_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", clip_earning_event_type, nullable=False),
        sa.Column("reference_key", sa.String(length=191), nullable=False),
        sa.Column("impression_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("like_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("share_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("base_rate_credit", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("engagement_bonus_credit", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("virality_bonus_credit", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("earnings_delta_credit", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("creator_wallet_balance_credit", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["creator_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["viewer_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference_key", name="uq_clip_earnings_log_reference_key"),
    )
    op.create_index("ix_clip_earnings_log_clip_id", "clip_earnings_log", ["clip_id"], unique=False)
    op.create_index("ix_clip_earnings_log_creator_user_id", "clip_earnings_log", ["creator_user_id"], unique=False)
    op.create_index("ix_clip_earnings_log_viewer_user_id", "clip_earnings_log", ["viewer_user_id"], unique=False)
    op.create_index("ix_clip_earnings_log_event_type", "clip_earnings_log", ["event_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_clip_earnings_log_event_type", table_name="clip_earnings_log")
    op.drop_index("ix_clip_earnings_log_viewer_user_id", table_name="clip_earnings_log")
    op.drop_index("ix_clip_earnings_log_creator_user_id", table_name="clip_earnings_log")
    op.drop_index("ix_clip_earnings_log_clip_id", table_name="clip_earnings_log")
    op.drop_table("clip_earnings_log")

    op.drop_index("ix_creator_wallet_last_event_at", table_name="creator_wallet")
    op.drop_index("ix_creator_wallet_creator_user_id", table_name="creator_wallet")
    op.drop_table("creator_wallet")

    bind = op.get_bind()
    clip_earning_event_type.drop(bind, checkfirst=True)
