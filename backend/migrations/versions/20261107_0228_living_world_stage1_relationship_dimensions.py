"""Add alignment, influence, and loyalty dimensions to owner club relationships for Stage 1.

Revision ID: 20261107_0228_living_world_stage1_relationship_dimensions
Revises: 20261106_0227_owner_club_delegation_and_authority_engine
Create Date: 2026-11-07 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20261107_0228_living_world_stage1_relationship_dimensions"
down_revision = "20261106_0227_owner_club_delegation_and_authority_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "owner_club_relationships" in tables:
        existing_cols = {col["name"] for col in inspector.get_columns("owner_club_relationships")}
        if "alignment" not in existing_cols:
            op.add_column(
                "owner_club_relationships",
                sa.Column("alignment", sa.Integer(), nullable=False, server_default="60"),
            )
        if "influence" not in existing_cols:
            op.add_column(
                "owner_club_relationships",
                sa.Column("influence", sa.Integer(), nullable=False, server_default="50"),
            )
        if "loyalty" not in existing_cols:
            op.add_column(
                "owner_club_relationships",
                sa.Column("loyalty", sa.Integer(), nullable=False, server_default="60"),
            )

    if "owner_club_relationship_history" in tables:
        hist_cols = {col["name"] for col in inspector.get_columns("owner_club_relationship_history")}
        if "delta_alignment" not in hist_cols:
            op.add_column(
                "owner_club_relationship_history",
                sa.Column("delta_alignment", sa.Integer(), nullable=False, server_default="0"),
            )
        if "delta_influence" not in hist_cols:
            op.add_column(
                "owner_club_relationship_history",
                sa.Column("delta_influence", sa.Integer(), nullable=False, server_default="0"),
            )
        if "delta_loyalty" not in hist_cols:
            op.add_column(
                "owner_club_relationship_history",
                sa.Column("delta_loyalty", sa.Integer(), nullable=False, server_default="0"),
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "owner_club_relationship_history" in tables:
        hist_cols = {col["name"] for col in inspector.get_columns("owner_club_relationship_history")}
        if "delta_loyalty" in hist_cols:
            op.drop_column("owner_club_relationship_history", "delta_loyalty")
        if "delta_influence" in hist_cols:
            op.drop_column("owner_club_relationship_history", "delta_influence")
        if "delta_alignment" in hist_cols:
            op.drop_column("owner_club_relationship_history", "delta_alignment")

    if "owner_club_relationships" in tables:
        existing_cols = {col["name"] for col in inspector.get_columns("owner_club_relationships")}
        if "loyalty" in existing_cols:
            op.drop_column("owner_club_relationships", "loyalty")
        if "influence" in existing_cols:
            op.drop_column("owner_club_relationships", "influence")
        if "alignment" in existing_cols:
            op.drop_column("owner_club_relationships", "alignment")
