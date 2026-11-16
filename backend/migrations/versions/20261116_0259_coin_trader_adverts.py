"""Add coin trader adverts, order chat messages, ratings, and profile/order fields.

Revision ID: 20261116_0259_coin_trader_adverts
Revises: 20261116_0258_owner_console_crest_urls_text

Additive only:
- Creates ``coin_trader_adverts``, ``coin_trade_messages``, ``coin_trade_ratings``.
- Adds ``rating_count``, ``completed_orders_count``, ``total_orders_count``,
  and ``last_active_at`` to ``coin_trader_profiles``.
- Adds ``advert_id``, ``payment_window_minutes``, ``quote_expires_at``,
  ``fee_coin``, and ``fee_fiat`` to ``coin_trade_orders``.
- Backfills adverts from ``coin_trader_rates`` without touching existing data.
"""

from __future__ import annotations

from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "20261116_0259_coin_trader_adverts"
down_revision = "20261116_0258_owner_console_crest_urls_text"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("coin_trader_profiles", sa.Column("rating_count", sa.Integer(), server_default="0", nullable=False))
    op.add_column(
        "coin_trader_profiles", sa.Column("completed_orders_count", sa.Integer(), server_default="0", nullable=False)
    )
    op.add_column(
        "coin_trader_profiles", sa.Column("total_orders_count", sa.Integer(), server_default="0", nullable=False)
    )
    op.add_column("coin_trader_profiles", sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "coin_trader_adverts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "trader_profile_id",
            sa.String(length=36),
            sa.ForeignKey("coin_trader_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("coin_unit", sa.String(length=32), nullable=False),
        sa.Column("fiat_currency", sa.String(length=8), nullable=False, server_default="NGN"),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("pricing_mode", sa.String(length=16), nullable=False, server_default="fixed"),
        sa.Column("price_fiat", sa.Numeric(18, 4), nullable=False),
        sa.Column("spread_fiat", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("min_coin_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("max_coin_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("daily_limit_coin", sa.Numeric(18, 4), nullable=True),
        sa.Column("payment_window_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("payment_methods_json", sa.JSON(), nullable=False),
        sa.Column("terms_text", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("admin_paused_reason", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "trader_profile_id",
            "coin_unit",
            "fiat_currency",
            "side",
            name="uq_coin_trader_adverts_profile_unit_fiat_side",
        ),
    )
    op.create_index("ix_coin_trader_adverts_trader_profile_id", "coin_trader_adverts", ["trader_profile_id"])
    op.create_index("ix_coin_trader_adverts_status", "coin_trader_adverts", ["status"])
    op.create_index(
        "ix_coin_trader_adverts_market", "coin_trader_adverts", ["coin_unit", "fiat_currency", "side", "status"]
    )

    op.add_column("coin_trade_orders", sa.Column("advert_id", sa.String(length=36), nullable=True))
    op.add_column("coin_trade_orders", sa.Column("payment_window_minutes", sa.Integer(), nullable=True))
    op.add_column("coin_trade_orders", sa.Column("quote_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("coin_trade_orders", sa.Column("fee_coin", sa.Numeric(18, 4), server_default="0", nullable=False))
    op.add_column("coin_trade_orders", sa.Column("fee_fiat", sa.Numeric(18, 4), server_default="0", nullable=False))
    op.create_index("ix_coin_trade_orders_advert_id", "coin_trade_orders", ["advert_id"])

    op.create_table(
        "coin_trade_messages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "order_id",
            sa.String(length=36),
            sa.ForeignKey("coin_trade_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sender_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sender_name", sa.String(length=120), nullable=False),
        sa.Column("message", sa.String(length=1000), nullable=False),
    )
    op.create_index("ix_coin_trade_messages_order_id", "coin_trade_messages", ["order_id"])
    op.create_index("ix_coin_trade_messages_sender_user_id", "coin_trade_messages", ["sender_user_id"])

    op.create_table(
        "coin_trade_ratings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "order_id",
            sa.String(length=36),
            sa.ForeignKey("coin_trade_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "trader_profile_id",
            sa.String(length=36),
            sa.ForeignKey("coin_trader_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("comment", sa.String(length=500), nullable=True),
        sa.UniqueConstraint("order_id", name="uq_coin_trade_ratings_order_id"),
    )
    op.create_index("ix_coin_trade_ratings_order_id", "coin_trade_ratings", ["order_id"])
    op.create_index("ix_coin_trade_ratings_trader_profile_id", "coin_trade_ratings", ["trader_profile_id"])
    op.create_index("ix_coin_trade_ratings_user_id", "coin_trade_ratings", ["user_id"])

    _backfill_from_rates()


def _backfill_from_rates() -> None:
    bind = op.get_bind()
    rates = bind.execute(
        sa.text(
            "SELECT trader_profile_id, coin_unit, fiat_currency, buy_rate_fiat, sell_rate_fiat, "
            "min_coin_amount, max_coin_amount, is_active FROM coin_trader_rates"
        )
    ).fetchall()
    adverts = sa.table(
        "coin_trader_adverts",
        sa.column("id", sa.String),
        sa.column("trader_profile_id", sa.String),
        sa.column("coin_unit", sa.String),
        sa.column("fiat_currency", sa.String),
        sa.column("side", sa.String),
        sa.column("pricing_mode", sa.String),
        sa.column("price_fiat", sa.Numeric),
        sa.column("spread_fiat", sa.Numeric),
        sa.column("min_coin_amount", sa.Numeric),
        sa.column("max_coin_amount", sa.Numeric),
        sa.column("payment_window_minutes", sa.Integer),
        sa.column("payment_methods_json", sa.JSON),
        sa.column("status", sa.String),
        sa.column("metadata_json", sa.JSON),
    )
    rows = []
    for rate in rates:
        status = "active" if rate.is_active else "paused"
        for side, price in (("sell", rate.sell_rate_fiat), ("buy", rate.buy_rate_fiat)):
            if price is None or float(price) <= 0:
                continue
            rows.append(
                {
                    "id": str(uuid4()),
                    "trader_profile_id": rate.trader_profile_id,
                    "coin_unit": rate.coin_unit,
                    "fiat_currency": rate.fiat_currency,
                    "side": side,
                    "pricing_mode": "fixed",
                    "price_fiat": price,
                    "spread_fiat": 0,
                    "min_coin_amount": rate.min_coin_amount,
                    "max_coin_amount": rate.max_coin_amount,
                    "payment_window_minutes": 45,
                    "payment_methods_json": [],
                    "status": status,
                    "metadata_json": {"migrated_from": "coin_trader_rates"},
                }
            )
    if rows:
        op.bulk_insert(adverts, rows)


def downgrade() -> None:
    op.drop_index("ix_coin_trade_ratings_user_id", table_name="coin_trade_ratings")
    op.drop_index("ix_coin_trade_ratings_trader_profile_id", table_name="coin_trade_ratings")
    op.drop_index("ix_coin_trade_ratings_order_id", table_name="coin_trade_ratings")
    op.drop_table("coin_trade_ratings")
    op.drop_index("ix_coin_trade_messages_sender_user_id", table_name="coin_trade_messages")
    op.drop_index("ix_coin_trade_messages_order_id", table_name="coin_trade_messages")
    op.drop_table("coin_trade_messages")
    op.drop_index("ix_coin_trade_orders_advert_id", table_name="coin_trade_orders")
    op.drop_column("coin_trade_orders", "fee_fiat")
    op.drop_column("coin_trade_orders", "fee_coin")
    op.drop_column("coin_trade_orders", "quote_expires_at")
    op.drop_column("coin_trade_orders", "payment_window_minutes")
    op.drop_column("coin_trade_orders", "advert_id")
    op.drop_index("ix_coin_trader_adverts_market", table_name="coin_trader_adverts")
    op.drop_index("ix_coin_trader_adverts_status", table_name="coin_trader_adverts")
    op.drop_index("ix_coin_trader_adverts_trader_profile_id", table_name="coin_trader_adverts")
    op.drop_table("coin_trader_adverts")
    op.drop_column("coin_trader_profiles", "last_active_at")
    op.drop_column("coin_trader_profiles", "total_orders_count")
    op.drop_column("coin_trader_profiles", "completed_orders_count")
    op.drop_column("coin_trader_profiles", "rating_count")
