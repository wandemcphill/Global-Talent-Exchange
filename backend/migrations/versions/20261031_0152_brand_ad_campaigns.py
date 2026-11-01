"""Create the public GTEX brand advertising campaign inventory.

Revision ID: 20261031_0152_brand_ad_campaigns
Revises: 20261027_0151_owner_world_tick_date
Create Date: 2026-10-31
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261031_0152_brand_ad_campaigns"
down_revision = "20261027_0151_owner_world_tick_date"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "brand_ad_campaigns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("advertiser_id", sa.String(length=36), nullable=True),
        sa.Column("brand_name", sa.String(length=160), nullable=False),
        sa.Column("headline", sa.String(length=180), nullable=False),
        sa.Column("description", sa.String(length=360), server_default="", nullable=False),
        sa.Column("placement", sa.String(length=40), nullable=False),
        sa.Column("destination_url", sa.String(length=2048), nullable=False),
        sa.Column("logo_url", sa.String(length=2048), nullable=True),
        sa.Column("creative_url", sa.String(length=2048), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="100", nullable=False),
        sa.Column("is_approved", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "placement IN ('homepage_rail', 'homepage_hero', 'partner_showcase', 'auth_canvas')",
            name="ck_brand_ad_campaigns_valid_placement",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_brand_ad_campaigns"),
    )
    op.create_index(
        "ix_brand_ad_campaigns_delivery",
        "brand_ad_campaigns",
        ["placement", "is_approved", "is_active", "start_at", "end_at"],
        unique=False,
    )
    op.create_index(
        "ix_brand_ad_campaigns_priority",
        "brand_ad_campaigns",
        ["priority"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_brand_ad_campaigns_priority", table_name="brand_ad_campaigns")
    op.drop_index("ix_brand_ad_campaigns_delivery", table_name="brand_ad_campaigns")
    op.drop_table("brand_ad_campaigns")
