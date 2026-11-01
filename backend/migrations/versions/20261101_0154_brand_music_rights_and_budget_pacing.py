"""Add music rights clearance fields and budget pacing indexes.

Revision ID: 20261101_0154_brand_music_rights_and_budget_pacing
Revises: 20261031_0153_brand_advertising_portal
Create Date: 2026-11-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261101_0154_brand_music_rights_and_budget_pacing"
down_revision = "20261031_0153_brand_advertising_portal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "brand_ad_campaigns",
        sa.Column("music_rights_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "brand_ad_campaigns",
        sa.Column("music_rights_holder", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "brand_ad_campaigns",
        sa.Column("music_license_doc_url", sa.String(length=2048), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("brand_ad_campaigns", "music_license_doc_url")
    op.drop_column("brand_ad_campaigns", "music_rights_holder")
    op.drop_column("brand_ad_campaigns", "music_rights_verified")
