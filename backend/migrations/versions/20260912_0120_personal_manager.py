"""Add personal_managers table with unique user constraint.

Revision ID: 20260912_0120_personal_manager
Revises: 20260912_0119_academy_facilities_economy

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260912_0120_personal_manager"
down_revision = "20260912_0119_academy_facilities_economy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "personal_managers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("quality_band", sa.String(length=32), nullable=False),
        sa.Column("gsi_min", sa.Integer(), nullable=False),
        sa.Column("gsi_max", sa.Integer(), nullable=False),
        sa.Column("gsi_rating", sa.Integer(), nullable=False),
        sa.Column("fan_coin_price", sa.Integer(), server_default="0", nullable=False),
        sa.Column("permanent", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("transferable", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("salary_bearing", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("tactical_identity_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_personal_managers_user_id"),
    )
    op.create_index(op.f("ix_personal_managers_user_id"), "personal_managers", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_personal_managers_user_id"), table_name="personal_managers")
    op.drop_table("personal_managers")
