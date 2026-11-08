"""Merge the parallel living-world and commercial-network migration heads.

Revision ID: 20261108_0229_merge_owner_world_and_commercial_heads
Revises: 20261107_0228_gtex_commercial_network, 20261107_0228_living_world_stage1_relationship_dimensions
Create Date: 2026-11-08 02:00:00.000000
"""

revision = "20261108_0229_merge_owner_world_and_commercial_heads"
down_revision = (
    "20261107_0228_gtex_commercial_network",
    "20261107_0228_living_world_stage1_relationship_dimensions",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Both parent revisions perform their own schema changes. This revision
    # only joins the migration graph after both branches have been applied.
    pass


def downgrade() -> None:
    # Parent revisions own their respective downgrade operations.
    pass
