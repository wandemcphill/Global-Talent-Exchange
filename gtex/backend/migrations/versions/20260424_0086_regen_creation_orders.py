"""Add paid regen creation orders.

Revision ID: 20260424_0086_regen_creation_orders
Revises: 20260423_0085_national_regen_age_bands_and_pool_ids
Create Date: 2026-04-24 09:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260424_0086_regen_creation_orders"
down_revision = "20260423_0085_national_regen_age_bands_and_pool_ids"
branch_labels = None
depends_on = None


request_type_enum = sa.Enum(
    "son",
    "academy_boost",
    "scout_special",
    name="regen_creation_request_type",
    native_enum=False,
)
payment_method_enum = sa.Enum(
    "wallet",
    "korapay",
    name="regen_creation_payment_method",
    native_enum=False,
)
status_enum = sa.Enum(
    "pending_payment",
    "paid",
    "generating",
    "generated",
    "failed",
    "refunded",
    name="regen_creation_order_status",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "regen_creation_orders",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("request_type", request_type_enum, nullable=False, server_default="son"),
        sa.Column("parent_player_id", sa.String(length=36), nullable=True),
        sa.Column("requested_name", sa.String(length=160), nullable=True),
        sa.Column("requested_country_code", sa.String(length=8), nullable=True),
        sa.Column("requested_position", sa.String(length=32), nullable=True),
        sa.Column("amount_coin", sa.Numeric(20, 4), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="COIN"),
        sa.Column("payment_method", payment_method_enum, nullable=False, server_default="wallet"),
        sa.Column("payment_provider", sa.String(length=32), nullable=True),
        sa.Column("payment_reference", sa.String(length=128), nullable=True),
        sa.Column("status", status_enum, nullable=False, server_default="pending_payment"),
        sa.Column("generated_player_id", sa.String(length=36), nullable=True),
        sa.Column("generated_regen_profile_id", sa.String(length=36), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["generated_player_id"], ["ingestion_players.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["generated_regen_profile_id"], ["regen_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_player_id"], ["ingestion_players.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_regen_creation_orders")),
        sa.UniqueConstraint("payment_reference", name="uq_regen_creation_orders_payment_reference"),
    )
    op.create_index("ix_regen_creation_orders_user_id", "regen_creation_orders", ["user_id"], unique=False)
    op.create_index("ix_regen_creation_orders_status", "regen_creation_orders", ["status"], unique=False)
    op.create_index(
        "ix_regen_creation_orders_payment_reference",
        "regen_creation_orders",
        ["payment_reference"],
        unique=False,
    )
    op.create_index(
        "ix_regen_creation_orders_generated_player_id",
        "regen_creation_orders",
        ["generated_player_id"],
        unique=False,
    )
    op.create_index("ix_regen_creation_orders_club_id", "regen_creation_orders", ["club_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_regen_creation_orders_club_id", table_name="regen_creation_orders")
    op.drop_index("ix_regen_creation_orders_generated_player_id", table_name="regen_creation_orders")
    op.drop_index("ix_regen_creation_orders_payment_reference", table_name="regen_creation_orders")
    op.drop_index("ix_regen_creation_orders_status", table_name="regen_creation_orders")
    op.drop_index("ix_regen_creation_orders_user_id", table_name="regen_creation_orders")
    op.drop_table("regen_creation_orders")
