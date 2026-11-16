"""Store generated club crest data URIs without a VARCHAR(255) limit.

Revision ID: 20261116_0256_club_crest_asset_ref_text
Revises: 20261116_0255_optional_trader_recovery_credentials
Create Date: 2026-11-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261116_0256_club_crest_asset_ref_text"
down_revision = "20261116_0255_optional_trader_recovery_credentials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("club_profiles") as batch_op:
        batch_op.alter_column(
            "crest_asset_ref",
            existing_type=sa.String(length=255),
            type_=sa.Text(),
            existing_nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    oversized_count = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM club_profiles " "WHERE crest_asset_ref IS NOT NULL AND length(crest_asset_ref) > 255"
        )
    ).scalar_one()
    if oversized_count:
        raise RuntimeError(
            "Cannot downgrade club crest storage: "
            f"{oversized_count} crest reference(s) exceed 255 characters. "
            "Preserve these assets or migrate them to external storage first."
        )

    with op.batch_alter_table("club_profiles") as batch_op:
        batch_op.alter_column(
            "crest_asset_ref",
            existing_type=sa.Text(),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
