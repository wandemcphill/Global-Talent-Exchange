"""Add gift catalog and service pricing rules."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260314_0022"
down_revision = "20260314_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gift_catalog",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("tier", sa.String(length=32), nullable=False, server_default=sa.text("'standard'")),
        sa.Column("fancoin_price", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0.0000")),
        sa.Column("animation_key", sa.String(length=64), nullable=True),
        sa.Column("sound_key", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], name="fk_gift_catalog_updated_by_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_gift_catalog"),
        sa.UniqueConstraint("key", name="uq_gift_catalog_key"),
    )
    op.create_index("ix_gift_catalog_key", "gift_catalog", ["key"], unique=False)

    op.create_table(
        "service_pricing_rules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("service_key", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_coin", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0.0000")),
        sa.Column("price_fancoin_equivalent", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0.0000")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], name="fk_service_pricing_rules_updated_by_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_service_pricing_rules"),
        sa.UniqueConstraint("service_key", name="uq_service_pricing_rules_service_key"),
    )
    op.create_index("ix_service_pricing_rules_service_key", "service_pricing_rules", ["service_key"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_service_pricing_rules_service_key", table_name="service_pricing_rules")
    op.drop_table("service_pricing_rules")

    op.drop_index("ix_gift_catalog_key", table_name="gift_catalog")
    op.drop_table("gift_catalog")
