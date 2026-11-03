"""Add music rights clearance fields and budget pacing indexes.

Revision ID: 20261101_0154_brand_music_rights_and_budget_pacing
Revises: 20261101_0152_korapay_paystack_payout_and_order_fields
Create Date: 2026-11-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261101_0154_brand_music_rights_and_budget_pacing"
down_revision = "20261101_0152_korapay_paystack_payout_and_order_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("brand_ad_campaigns"):
        return

    existing_cols = {col["name"] for col in inspector.get_columns("brand_ad_campaigns")}
    if "music_rights_verified" not in existing_cols:
        op.add_column(
            "brand_ad_campaigns",
            sa.Column("music_rights_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
    if "music_rights_holder" not in existing_cols:
        op.add_column(
            "brand_ad_campaigns",
            sa.Column("music_rights_holder", sa.String(length=160), nullable=True),
        )
    if "music_license_doc_url" not in existing_cols:
        op.add_column(
            "brand_ad_campaigns",
            sa.Column("music_license_doc_url", sa.String(length=2048), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("brand_ad_campaigns"):
        return

    existing_cols = {col["name"] for col in inspector.get_columns("brand_ad_campaigns")}
    if "music_license_doc_url" in existing_cols:
        op.drop_column("brand_ad_campaigns", "music_license_doc_url")
    if "music_rights_holder" in existing_cols:
        op.drop_column("brand_ad_campaigns", "music_rights_holder")
    if "music_rights_verified" in existing_cols:
        op.drop_column("brand_ad_campaigns", "music_rights_verified")
