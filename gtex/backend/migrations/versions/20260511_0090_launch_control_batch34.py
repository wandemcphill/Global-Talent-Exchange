"""Add Batch 34 launch control fields and audit tables.

Revision ID: 20260511_0090_launch_control_batch34
Revises: 20260510_0091_coin_trader_marketplace
Create Date: 2026-05-11 09:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260511_0090_launch_control_batch34"
down_revision = "20260510_0091_coin_trader_marketplace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("admin_feature_flags") as batch_op:
        batch_op.add_column(sa.Column("launch_state", sa.String(length=32), nullable=False, server_default="public"))
        batch_op.add_column(
            sa.Column("allowed_roles_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))
        )
        batch_op.add_column(
            sa.Column("allowed_regions_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))
        )
        batch_op.add_column(sa.Column("beta_only", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        batch_op.add_column(
            sa.Column("kill_switch_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false"))
        )
        batch_op.add_column(sa.Column("maintenance_message", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))

    op.create_table(
        "admin_feature_flag_audit_log",
        sa.Column("feature_key", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("previous_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("next_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_feature_flag_audit_log_actor_user_id", "admin_feature_flag_audit_log", ["actor_user_id"])
    op.create_index("ix_admin_feature_flag_audit_log_feature_key", "admin_feature_flag_audit_log", ["feature_key"])

    op.create_table(
        "admin_beta_access_grants",
        sa.Column("feature_key", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("granted_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["granted_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feature_key", "user_id", name="uq_admin_beta_access_grants_feature_user"),
    )
    op.create_index("ix_admin_beta_access_grants_feature_key", "admin_beta_access_grants", ["feature_key"])


def downgrade() -> None:
    op.drop_index("ix_admin_beta_access_grants_feature_key", table_name="admin_beta_access_grants")
    op.drop_table("admin_beta_access_grants")
    op.drop_index("ix_admin_feature_flag_audit_log_feature_key", table_name="admin_feature_flag_audit_log")
    op.drop_index("ix_admin_feature_flag_audit_log_actor_user_id", table_name="admin_feature_flag_audit_log")
    op.drop_table("admin_feature_flag_audit_log")

    with op.batch_alter_table("admin_feature_flags") as batch_op:
        batch_op.drop_column("metadata_json")
        batch_op.drop_column("maintenance_message")
        batch_op.drop_column("kill_switch_enabled")
        batch_op.drop_column("beta_only")
        batch_op.drop_column("allowed_regions_json")
        batch_op.drop_column("allowed_roles_json")
        batch_op.drop_column("launch_state")
