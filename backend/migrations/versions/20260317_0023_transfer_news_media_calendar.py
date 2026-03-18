"""Add highlight amplification persistence for transfer/news/calendar lane."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260317_0023_transfer_news_media_calendar"
down_revision = "20260317_0022_fan_wars_nations_cup"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "highlight_share_amplifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("export_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("story_feed_item_id", sa.String(length=36), nullable=True),
        sa.Column("channel", sa.String(length=32), server_default=sa.text("'story_feed'"), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'published'"), nullable=False),
        sa.Column("subject_type", sa.String(length=48), nullable=True),
        sa.Column("subject_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["export_id"], ["highlight_share_exports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["story_feed_item_id"], ["story_feed_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_highlight_share_amplifications"),
    )
    op.create_index(
        "ix_highlight_share_amplifications_export_id",
        "highlight_share_amplifications",
        ["export_id"],
        unique=False,
    )
    op.create_index(
        "ix_highlight_share_amplifications_user_id",
        "highlight_share_amplifications",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_highlight_share_amplifications_story_feed_item_id",
        "highlight_share_amplifications",
        ["story_feed_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_highlight_share_amplifications_subject",
        "highlight_share_amplifications",
        ["subject_type", "subject_id"],
        unique=False,
    )
    op.create_index(
        "ix_highlight_share_amplifications_channel_status",
        "highlight_share_amplifications",
        ["channel", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_highlight_share_amplifications_channel_status", table_name="highlight_share_amplifications")
    op.drop_index("ix_highlight_share_amplifications_subject", table_name="highlight_share_amplifications")
    op.drop_index("ix_highlight_share_amplifications_story_feed_item_id", table_name="highlight_share_amplifications")
    op.drop_index("ix_highlight_share_amplifications_user_id", table_name="highlight_share_amplifications")
    op.drop_index("ix_highlight_share_amplifications_export_id", table_name="highlight_share_amplifications")
    op.drop_table("highlight_share_amplifications")
