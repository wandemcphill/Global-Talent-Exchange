"""Add coin trader marketplace and escrow orders.

Revision ID: 20260510_0091_coin_trader_marketplace
Revises: 20260510_0090_transfer_hub_terms
Create Date: 2026-05-10 12:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260510_0091_coin_trader_marketplace"
down_revision = "20260510_0090_transfer_hub_terms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "coin_trader_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("country_code", sa.String(length=8), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="applied"),
        sa.Column("tier", sa.String(length=32), nullable=False, server_default="bronze"),
        sa.Column("completion_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("average_release_minutes", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rating", sa.Float(), nullable=False, server_default="0"),
        sa.Column("terms_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("payment_methods_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("bank_accounts_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("liquidity_snapshot_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("approved_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_coin_trader_profiles_user_id"),
    )
    op.create_index("ix_coin_trader_profiles_user_id", "coin_trader_profiles", ["user_id"], unique=False)
    op.create_index("ix_coin_trader_profiles_country_code", "coin_trader_profiles", ["country_code"], unique=False)
    op.create_index("ix_coin_trader_profiles_status", "coin_trader_profiles", ["status"], unique=False)
    op.create_index("ix_coin_trader_profiles_tier", "coin_trader_profiles", ["tier"], unique=False)

    op.create_table(
        "coin_trader_rates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("trader_profile_id", sa.String(length=36), nullable=False),
        sa.Column("coin_unit", sa.String(length=16), nullable=False),
        sa.Column("fiat_currency", sa.String(length=8), nullable=False, server_default="NGN"),
        sa.Column("buy_rate_fiat", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("sell_rate_fiat", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("min_coin_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("max_coin_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("available_liquidity", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["trader_profile_id"], ["coin_trader_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trader_profile_id",
            "coin_unit",
            "fiat_currency",
            name="uq_coin_trader_rates_profile_unit_fiat",
        ),
    )
    op.create_index("ix_coin_trader_rates_trader_profile_id", "coin_trader_rates", ["trader_profile_id"], unique=False)

    op.create_table(
        "coin_trade_orders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("trader_profile_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("direction", sa.String(length=32), nullable=False),
        sa.Column("coin_unit", sa.String(length=16), nullable=False),
        sa.Column("coin_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("quoted_rate_fiat", sa.Numeric(18, 4), nullable=False),
        sa.Column("fiat_total", sa.Numeric(18, 4), nullable=False),
        sa.Column("fiat_currency", sa.String(length=8), nullable=False, server_default="NGN"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="created"),
        sa.Column("escrow_owner_user_id", sa.String(length=36), nullable=True),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("payment_method", sa.String(length=80), nullable=True),
        sa.Column("payment_window_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proof_submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disputed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proof_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("terms_snapshot_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("ledger_refs_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["escrow_owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["trader_profile_id"], ["coin_trader_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_coin_trade_orders_idempotency_key"),
    )
    op.create_index("ix_coin_trade_orders_trader_profile_id", "coin_trade_orders", ["trader_profile_id"], unique=False)
    op.create_index("ix_coin_trade_orders_user_id", "coin_trade_orders", ["user_id"], unique=False)
    op.create_index("ix_coin_trade_orders_direction", "coin_trade_orders", ["direction"], unique=False)
    op.create_index("ix_coin_trade_orders_status", "coin_trade_orders", ["status"], unique=False)
    op.create_index("ix_coin_trade_orders_escrow_owner_user_id", "coin_trade_orders", ["escrow_owner_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_coin_trade_orders_escrow_owner_user_id", table_name="coin_trade_orders")
    op.drop_index("ix_coin_trade_orders_status", table_name="coin_trade_orders")
    op.drop_index("ix_coin_trade_orders_direction", table_name="coin_trade_orders")
    op.drop_index("ix_coin_trade_orders_user_id", table_name="coin_trade_orders")
    op.drop_index("ix_coin_trade_orders_trader_profile_id", table_name="coin_trade_orders")
    op.drop_table("coin_trade_orders")

    op.drop_index("ix_coin_trader_rates_trader_profile_id", table_name="coin_trader_rates")
    op.drop_table("coin_trader_rates")

    op.drop_index("ix_coin_trader_profiles_tier", table_name="coin_trader_profiles")
    op.drop_index("ix_coin_trader_profiles_status", table_name="coin_trader_profiles")
    op.drop_index("ix_coin_trader_profiles_country_code", table_name="coin_trader_profiles")
    op.drop_index("ix_coin_trader_profiles_user_id", table_name="coin_trader_profiles")
    op.drop_table("coin_trader_profiles")
