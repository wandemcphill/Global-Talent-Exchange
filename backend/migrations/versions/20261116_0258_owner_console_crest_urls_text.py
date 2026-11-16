"""Widen owner broadcast and newsroom crest/hero URL columns to TEXT.

Revision ID: 20261116_0258_owner_console_crest_urls_text
Revises: 20261116_0257_merge_crest_and_test_account_cleanup_heads
Create Date: 2026-11-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261116_0258_owner_console_crest_urls_text"
down_revision = "20261116_0257_merge_crest_and_test_account_cleanup_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("owner_broadcast_events") as batch_op:
        batch_op.alter_column(
            "club_crest_url",
            existing_type=sa.String(length=255),
            type_=sa.Text(),
            existing_nullable=True,
        )
    with op.batch_alter_table("owner_newsroom_articles") as batch_op:
        batch_op.alter_column(
            "hero_image_url",
            existing_type=sa.String(length=255),
            type_=sa.Text(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "club_crest_url",
            existing_type=sa.String(length=255),
            type_=sa.Text(),
            existing_nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    oversized_broadcast = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM owner_broadcast_events "
            "WHERE club_crest_url IS NOT NULL AND length(club_crest_url) > 255"
        )
    ).scalar_one()
    oversized_newsroom = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM owner_newsroom_articles "
            "WHERE (hero_image_url IS NOT NULL AND length(hero_image_url) > 255) "
            "OR (club_crest_url IS NOT NULL AND length(club_crest_url) > 255)"
        )
    ).scalar_one()
    if oversized_broadcast or oversized_newsroom:
        raise RuntimeError(
            "Cannot downgrade owner console crest URL storage: "
            f"{oversized_broadcast} broadcast event(s) and {oversized_newsroom} newsroom article(s) "
            "exceed 255 characters."
        )

    with op.batch_alter_table("owner_newsroom_articles") as batch_op:
        batch_op.alter_column(
            "club_crest_url",
            existing_type=sa.Text(),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "hero_image_url",
            existing_type=sa.Text(),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
    with op.batch_alter_table("owner_broadcast_events") as batch_op:
        batch_op.alter_column(
            "club_crest_url",
            existing_type=sa.Text(),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
