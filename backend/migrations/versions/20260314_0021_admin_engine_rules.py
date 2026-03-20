"""Add admin engine feature flags, calendar rules, and reward rules."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260314_0021"
down_revision = "20260314_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_feature_flags",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("feature_key", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("audience", sa.String(length=32), nullable=False, server_default=sa.text("'global'")),
        sa.Column("updated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], name="fk_admin_feature_flags_updated_by_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_admin_feature_flags"),
    )
    op.create_index("ix_admin_feature_flags_feature_key", "admin_feature_flags", ["feature_key"], unique=True)

    op.create_table(
        "admin_calendar_rules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("rule_key", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("world_cup_exclusive", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("config_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("updated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], name="fk_admin_calendar_rules_updated_by_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_admin_calendar_rules"),
    )
    op.create_index("ix_admin_calendar_rules_rule_key", "admin_calendar_rules", ["rule_key"], unique=True)

    op.create_table(
        "admin_reward_rules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("rule_key", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("trading_fee_bps", sa.Integer(), nullable=False, server_default=sa.text("2000")),
        sa.Column("gift_platform_rake_bps", sa.Integer(), nullable=False, server_default=sa.text("3000")),
        sa.Column("withdrawal_fee_bps", sa.Integer(), nullable=False, server_default=sa.text("1000")),
        sa.Column("minimum_withdrawal_fee_credits", sa.Numeric(18, 4), nullable=False, server_default=sa.text("5.0000")),
        sa.Column("competition_platform_fee_bps", sa.Integer(), nullable=False, server_default=sa.text("1000")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], name="fk_admin_reward_rules_updated_by_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_admin_reward_rules"),
    )
    op.create_index("ix_admin_reward_rules_rule_key", "admin_reward_rules", ["rule_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_admin_reward_rules_rule_key", table_name="admin_reward_rules")
    op.drop_table("admin_reward_rules")

    op.drop_index("ix_admin_calendar_rules_rule_key", table_name="admin_calendar_rules")
    op.drop_table("admin_calendar_rules")

    op.drop_index("ix_admin_feature_flags_feature_key", table_name="admin_feature_flags")
    op.drop_table("admin_feature_flags")
