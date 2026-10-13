"""Story feed moderation status and schedule.

Revision ID: 20261013_0128_story_feed_moderation
Revises: 20261013_0127_merge_regen_and_country_heads
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261013_0128_story_feed_moderation"
down_revision = "20261013_0127_merge_regen_and_country_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "story_feed_items",
        sa.Column(
            "moderation_status",
            sa.String(length=32),
            nullable=False,
            server_default="published",
        ),
    )
    op.add_column(
        "story_feed_items",
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_story_feed_items_moderation_status",
        "story_feed_items",
        ["moderation_status"],
    )
    op.create_index(
        "ix_story_feed_items_scheduled_for",
        "story_feed_items",
        ["scheduled_for"],
    )


def downgrade() -> None:
    op.drop_index("ix_story_feed_items_scheduled_for", table_name="story_feed_items")
    op.drop_index("ix_story_feed_items_moderation_status", table_name="story_feed_items")
    op.drop_column("story_feed_items", "scheduled_for")
    op.drop_column("story_feed_items", "moderation_status")
