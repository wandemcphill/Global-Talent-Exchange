"""Merge the parallel living-world and commercial-network migration heads.

Revision ID: 20261108_0229_merge_owner_world_and_commercial_heads
Revises: 20261107_0228_gtex_commercial_network, 20261107_0228_living_world_stage1_relationship_dimensions
Create Date: 2026-11-08 02:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20261108_0229_merge_owner_world_and_commercial_heads"
down_revision = (
    "20261107_0228_gtex_commercial_network",
    "20261107_0228_living_world_stage1_relationship_dimensions",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "brand_ad_campaigns" in inspector.get_table_names():
        indexes = {idx["name"] for idx in inspector.get_indexes("brand_ad_campaigns")}
        if "ix_brand_ad_campaigns_workspace" not in indexes:
            op.create_index(
                "ix_brand_ad_campaigns_workspace",
                "brand_ad_campaigns",
                ["workspace_id", "status"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "brand_ad_campaigns" in inspector.get_table_names():
        indexes = {idx["name"] for idx in inspector.get_indexes("brand_ad_campaigns")}
        if "ix_brand_ad_campaigns_workspace" in indexes:
            op.drop_index("ix_brand_ad_campaigns_workspace", table_name="brand_ad_campaigns")
